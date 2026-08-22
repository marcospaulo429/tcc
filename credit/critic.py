"""Fase B (PLANO-EXECUCAO.md) — critic vs baselines dose-matched [P7, P8].

Prevê o crédito counterfactual (C_H, C_M, I) a partir de features `pre`
(computáveis antes da decisão). Estatística pré-registrada: zero-inflation
(classificador |y|>0 + regressor condicional), split por TASK (GroupKFold),
bootstrap clusterizado por task, precision@k com k=10 FIXO.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

QUANTITIES = ("C_H", "C_M", "I")
PRECISION_K = 10  # pré-registro P7c: fixado antes de ver dados
MIN_POINTS = 20
MIN_TASKS = 3
NUMERIC_PRE = ("turn", "context_tokens_before", "n_messages_before",
               "tests_passed_so_far", "tests_total_so_far", "n_writes_so_far",
               "frac_turns_elapsed")
CATEGORICAL_PRE = ("decision_point", "action_type")
N_RANDOM_PERMS = 100


@dataclass
class Xy:
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray  # task_id por linha
    feature_names: list[str]
    meta: list[dict] = field(default_factory=list)

    @property
    def n_tasks(self) -> int:
        return len(set(self.groups.tolist()))

    def column(self, name: str) -> np.ndarray:
        return self.X[:, self.feature_names.index(name)]


def prepare(rows: list[dict], quantity: str) -> Xy:
    """Filtra por quantity, remove excluded_timeout, saturated (só I) e
    features_pre com None; monta X (numéricas + one-hot + threshold), y, groups."""
    kept: list[dict] = []
    for r in rows:
        if r.get("quantity") != quantity or r.get("excluded_timeout"):
            continue
        if quantity == "I" and r.get("saturated"):
            continue
        feats = r.get("features_pre") or {}
        if any(feats.get(k) is None for k in NUMERIC_PRE + CATEGORICAL_PRE):
            continue
        kept.append(r)
    cats = {c: sorted({r["features_pre"][c] for r in kept}) for c in CATEGORICAL_PRE}
    names = list(NUMERIC_PRE) + ["threshold"]  # config sempre covariável (pré-registro)
    for c in CATEGORICAL_PRE:
        names += [f"{c}={v}" for v in cats[c]]
    X = np.zeros((len(kept), len(names)))
    for i, r in enumerate(kept):
        feats = r["features_pre"]
        for j, k in enumerate(NUMERIC_PRE):
            X[i, j] = float(feats[k])
        X[i, len(NUMERIC_PRE)] = float(r.get("threshold") or 0.0)
        for c in CATEGORICAL_PRE:
            X[i, names.index(f"{c}={feats[c]}")] = 1.0
    y = np.array([float(r["value"]) for r in kept])
    groups = np.array([r["task_id"] for r in kept])
    meta = [{"stratum": r.get("stratum"), "config_tag": r.get("config_tag")}
            for r in kept]
    return Xy(X=X, y=y, groups=groups, feature_names=names, meta=meta)


# ---------------------------------------------------------------- métricas ---

def _rank(a: np.ndarray) -> np.ndarray:
    """Ranks com média em empates (para Spearman sem scipy)."""
    order = np.argsort(a, kind="stable")
    ranks = np.empty(len(a))
    ranks[order] = np.arange(len(a), dtype=float)
    # média nos empates
    for v in np.unique(a):
        mask = a == v
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.all(a == a[0]) or np.all(b == b[0]):
        return float("nan")
    ra, rb = _rank(a), _rank(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def _spearman_clustered(y: np.ndarray, yhat: np.ndarray,
                        groups: np.ndarray) -> float:
    """Média por task (>=3 pontos) ponderada por n."""
    vals, weights = [], []
    for g in np.unique(groups):
        mask = groups == g
        if mask.sum() < 3:
            continue
        s = _spearman(y[mask], yhat[mask])
        if not np.isnan(s):
            vals.append(s)
            weights.append(mask.sum())
    if not vals:
        return float("nan")
    return float(np.average(vals, weights=weights))


def _precision_at_k(y: np.ndarray, score: np.ndarray, k: int = PRECISION_K) -> float:
    k = min(k, len(y))
    if k == 0:
        return float("nan")
    top_true = set(np.argsort(-np.abs(y), kind="stable")[:k].tolist())
    top_pred = set(np.argsort(-score, kind="stable")[:k].tolist())
    return len(top_true & top_pred) / k


def _auroc(labels: np.ndarray, score: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return float("nan")
    return float(roc_auc_score(labels, score))


def _metrics(y: np.ndarray, groups: np.ndarray, p_nonzero: np.ndarray,
             score: np.ndarray, reg_pred: np.ndarray | None) -> dict:
    labels = (np.abs(y) > 0).astype(int)
    out = {
        "auroc": _auroc(labels, p_nonzero),
        "spearman_clustered": _spearman_clustered(y, score, groups),
        "spearman_pooled": _spearman(y, score),
        "precision_at_10": _precision_at_k(y, np.abs(score)),
    }
    if reg_pred is not None:
        nz = labels == 1
        out["mae_nonzero"] = (float(np.mean(np.abs(y[nz] - reg_pred[nz])))
                              if nz.any() else float("nan"))
    else:
        out["mae_nonzero"] = None
    return out


def _bootstrap_ci(y: np.ndarray, groups: np.ndarray, seed: int, n_boot: int,
                  metric_fn) -> dict:
    """Bootstrap CLUSTERIZADO POR TASK: resample de tasks inteiras."""
    rng = np.random.default_rng(seed)
    tasks = np.unique(groups)
    idx_by_task = {g: np.flatnonzero(groups == g) for g in tasks}
    samples: dict[str, list[float]] = {}
    for _ in range(n_boot):
        chosen = rng.choice(tasks, size=len(tasks), replace=True)
        idx = np.concatenate([idx_by_task[g] for g in chosen])
        # re-rotula tasks repetidas como clusters distintos
        boot_groups = np.concatenate(
            [np.full(len(idx_by_task[g]), f"{g}#{i}") for i, g in enumerate(chosen)])
        for name, val in metric_fn(idx, boot_groups).items():
            samples.setdefault(name, []).append(val)
    ci = {}
    for name, vals in samples.items():
        arr = np.array(vals, dtype=float)
        if np.all(np.isnan(arr)):
            ci[name] = {"lo": None, "med": None, "hi": None}
        else:
            lo, med, hi = np.nanpercentile(arr, [2.5, 50, 97.5])
            ci[name] = {"lo": float(lo), "med": float(med), "hi": float(hi)}
    return ci


def _skip_reason(xy: Xy) -> str | None:
    if len(xy.y) < MIN_POINTS:
        return f"n={len(xy.y)} < {MIN_POINTS} pontos"
    if xy.n_tasks < MIN_TASKS:
        return f"{xy.n_tasks} < {MIN_TASKS} tasks"
    return None


def _group_kfold(xy: Xy) -> list[tuple[np.ndarray, np.ndarray]]:
    k = min(5, xy.n_tasks)
    return list(GroupKFold(n_splits=k).split(xy.X, xy.y, xy.groups))


# ---------------------------------------------------------------- critic -----

_MODELS = {
    "linear": (lambda seed: LogisticRegression(max_iter=1000, random_state=seed),
               lambda seed: Ridge(random_state=seed)),
    "gbm": (lambda seed: GradientBoostingClassifier(random_state=seed),
            lambda seed: GradientBoostingRegressor(random_state=seed)),
}


def evaluate(xy: Xy, model_name: str, seed: int, n_boot: int = 1000) -> dict:
    """Dois estágios (zero-inflation): cls |y|>0 + regressor condicional.
    Predições out-of-fold com GroupKFold por task; IC bootstrap por task."""
    reason = _skip_reason(xy)
    if reason:
        return {"skipped": reason}
    make_cls, make_reg = _MODELS[model_name]
    y, groups = xy.y, xy.groups
    labels = (np.abs(y) > 0).astype(int)
    p_nonzero = np.zeros(len(y))
    reg_pred = np.zeros(len(y))
    folds_report = []
    for train, test in _group_kfold(xy):
        assert not set(groups[train]) & set(groups[test])
        folds_report.append({"train_tasks": sorted(set(groups[train].tolist())),
                             "test_tasks": sorted(set(groups[test].tolist()))})
        if len(np.unique(labels[train])) < 2:
            p_nonzero[test] = float(labels[train].mean())
        else:
            cls = make_cls(seed).fit(xy.X[train], labels[train])
            p_nonzero[test] = cls.predict_proba(xy.X[test])[:, 1]
        nz_train = train[labels[train] == 1]
        if len(nz_train) >= 2:
            reg = make_reg(seed).fit(xy.X[nz_train], y[nz_train])
            reg_pred[test] = reg.predict(xy.X[test])
        else:
            reg_pred[test] = y[train].mean() if len(train) else 0.0
    score = p_nonzero * reg_pred  # valor esperado sob zero-inflation

    def metric_fn(idx, boot_groups):
        return _metrics(y[idx], boot_groups, p_nonzero[idx], score[idx],
                        reg_pred[idx])

    return {
        "model": model_name,
        "n": len(y),
        "n_tasks": xy.n_tasks,
        "metrics": _metrics(y, groups, p_nonzero, score, reg_pred),
        "ci95": _bootstrap_ci(y, groups, seed, n_boot, metric_fn),
        "folds": folds_report,
    }


# ---------------------------------------------------------------- baselines --

def _baseline_result(xy: Xy, score: np.ndarray, seed: int, n_boot: int) -> dict:
    y, groups = xy.y, xy.groups

    def metric_fn(idx, boot_groups):
        return _metrics(y[idx], boot_groups, score[idx], score[idx], None)

    return {
        "n": len(y),
        "n_tasks": xy.n_tasks,
        "metrics": _metrics(y, groups, score, score, None),
        "ci95": _bootstrap_ci(y, groups, seed, n_boot, metric_fn),
    }


def evaluate_baselines(xy: Xy, seed: int, n_boot: int = 1000) -> dict:
    """Baselines dose-matched pré-registrados: position, context_size, random."""
    reason = _skip_reason(xy)
    if reason:
        return {"skipped": reason}
    y, groups = xy.y, xy.groups
    out = {
        "position": _baseline_result(xy, -xy.column("turn"), seed, n_boot),
        "context_size": _baseline_result(
            xy, xy.column("context_tokens_before"), seed, n_boot),
    }
    # random: média de N_RANDOM_PERMS permutações para as métricas de ranking
    rng = np.random.default_rng(seed)
    perm_metrics: dict[str, list[float]] = {}
    for _ in range(N_RANDOM_PERMS):
        score = rng.permutation(len(y)).astype(float)
        for name, val in _metrics(y, groups, score, score, None).items():
            if val is not None:
                perm_metrics.setdefault(name, []).append(val)
    rand_point = {name: float(np.nanmean(vals))
                  for name, vals in perm_metrics.items()}
    rand_point["mae_nonzero"] = None

    boot_rng = np.random.default_rng(seed + 1)

    def rand_metric_fn(idx, boot_groups):
        score = boot_rng.permutation(len(idx)).astype(float)
        return _metrics(y[idx], boot_groups, score, score, None)

    out["random"] = {
        "n": len(y),
        "n_tasks": xy.n_tasks,
        "metrics": rand_point,
        "ci95": _bootstrap_ci(y, groups, seed, n_boot, rand_metric_fn),
    }
    return out


# ---------------------------------------------------------------- report -----

def run_report(dataset_path: str | Path, out_path: str | Path, seed: int) -> dict:
    rows = [json.loads(line)
            for line in Path(dataset_path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    report: dict = {"dataset": str(dataset_path), "seed": seed, "quantities": {}}
    for quantity in QUANTITIES:
        xy = prepare(rows, quantity)
        reason = _skip_reason(xy)
        if reason:
            report["quantities"][quantity] = {"skipped": reason}
            continue
        report["quantities"][quantity] = {
            "n": len(xy.y),
            "n_tasks": xy.n_tasks,
            "linear": evaluate(xy, "linear", seed),
            "gbm": evaluate(xy, "gbm", seed),
            "baselines": evaluate_baselines(xy, seed),
        }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20260821)
    args = ap.parse_args()
    report = run_report(args.dataset, args.out, args.seed)
    print(json.dumps({q: ({"skipped": v["skipped"]} if "skipped" in v
                          else {"n": v["n"], "n_tasks": v["n_tasks"]})
                      for q, v in report["quantities"].items()},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
