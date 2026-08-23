"""Pré-registro 16 (secundário, PLANO-EXECUCAO.md) — generalização do critic
ambiente A→B.

Treina o MESMO modelo zero-inflated do critic (classificador |y|>0 + regressor
condicional) em TODO o dataset A (sem CV) e prediz no dataset B inteiro
(held-out por construção — ambientes disjuntos). Reporta Pearson/Spearman com
IC95 por bootstrap clusterizado por task, AUC, precision@10 e dois baselines:
preditor constante (média de y no A) e nulo por permutação de y_pred no B.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from credit.critic import (
    _MODELS,
    _auroc,
    _bootstrap_ci,
    _precision_at_k,
    _spearman,
    _spearman_clustered,
    MIN_POINTS,
    MIN_TASKS,
    QUANTITIES,
    Xy,
    prepare,
)

DEFAULT_SEED = 20260821
N_PERMUTATIONS = 100
N_BOOT = 1000


def _align_features(test_xy: Xy, train_names: list[str]) -> np.ndarray:
    """Projeta X do teste no espaço de features do treino: colunas ausentes no
    teste viram 0 (categoria não vista no B); colunas extras do B são descartadas."""
    X = np.zeros((len(test_xy.y), len(train_names)))
    for j, name in enumerate(train_names):
        if name in test_xy.feature_names:
            X[:, j] = test_xy.column(name)
    return X


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.all(a == a[0]) or np.all(b == b[0]):
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _fit_predict(train_xy: Xy, X_test: np.ndarray, model_name: str,
                 seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Zero-inflation igual ao critic.evaluate(), mas treino completo no A.
    Retorna (p_nonzero, score) no B."""
    make_cls, make_reg = _MODELS[model_name]
    labels = (np.abs(train_xy.y) > 0).astype(int)
    if len(np.unique(labels)) < 2:
        p_nonzero = np.full(len(X_test), float(labels.mean()))
    else:
        cls = make_cls(seed).fit(train_xy.X, labels)
        p_nonzero = cls.predict_proba(X_test)[:, 1]
    nz = labels == 1
    if nz.sum() >= 2:
        reg = make_reg(seed).fit(train_xy.X[nz], train_xy.y[nz])
        reg_pred = reg.predict(X_test)
    else:
        reg_pred = np.full(len(X_test), train_xy.y.mean() if len(train_xy.y) else 0.0)
    return p_nonzero, p_nonzero * reg_pred  # valor esperado sob zero-inflation


def _transfer_metrics(y: np.ndarray, groups: np.ndarray, p_nonzero: np.ndarray,
                      score: np.ndarray) -> dict:
    labels = (np.abs(y) > 0).astype(int)
    return {
        "pearson": _pearson(y, score),
        "spearman_pooled": _spearman(y, score),
        "spearman_clustered": _spearman_clustered(y, score, groups),
        "auroc": _auroc(labels, p_nonzero),
        "precision_at_10": _precision_at_k(y, np.abs(score)),
        "mae": float(np.mean(np.abs(y - score))),
    }


def _permutation_null(y: np.ndarray, groups: np.ndarray, score: np.ndarray,
                      seed: int, n_perms: int) -> dict:
    """Nulo por permutação de y_pred dentro do B; p-valor bilateral do
    Spearman clusterizado observado."""
    obs = _spearman_clustered(y, score, groups)
    if np.isnan(obs):
        return {"n_perms": n_perms, "spearman_clustered_obs": None, "p_value": None}
    rng = np.random.default_rng(seed)
    n_ge = 0
    for _ in range(n_perms):
        perm = _spearman_clustered(y, rng.permutation(score), groups)
        if not np.isnan(perm) and abs(perm) >= abs(obs):
            n_ge += 1
    return {"n_perms": n_perms,
            "spearman_clustered_obs": float(obs),
            "p_value": (n_ge + 1) / (n_perms + 1)}


def _insufficient(xy: Xy, side: str) -> str | None:
    if len(xy.y) < MIN_POINTS:
        return f"{side}: n={len(xy.y)} < {MIN_POINTS} pontos"
    if xy.n_tasks < MIN_TASKS:
        return f"{side}: {xy.n_tasks} < {MIN_TASKS} tasks"
    return None


def evaluate_transfer(train_xy: Xy, test_xy: Xy, seed: int,
                      n_boot: int = N_BOOT, n_perms: int = N_PERMUTATIONS) -> dict:
    y, groups = test_xy.y, test_xy.groups
    X_test = _align_features(test_xy, train_xy.feature_names)
    out: dict = {
        "n_train": len(train_xy.y),
        "n_tasks_train": train_xy.n_tasks,
        "n_test": len(y),
        "n_tasks_test": test_xy.n_tasks,
        "models": {},
        "baseline_constant": None,
    }
    for model_name in _MODELS:
        p_nonzero, score = _fit_predict(train_xy, X_test, model_name, seed)

        def metric_fn(idx, boot_groups, p=p_nonzero, s=score):
            return _transfer_metrics(y[idx], boot_groups, p[idx], s[idx])

        out["models"][model_name] = {
            "metrics": _transfer_metrics(y, groups, p_nonzero, score),
            "ci95": _bootstrap_ci(y, groups, seed, n_boot, metric_fn),
            "permutation_null": _permutation_null(y, groups, score, seed, n_perms),
        }
    const = float(train_xy.y.mean())
    out["baseline_constant"] = {
        "prediction": const,
        "mae": float(np.mean(np.abs(y - const))),
    }
    return out


def run_transfer(train_path: str | Path, test_path: str | Path,
                 out_path: str | Path, seed: int = DEFAULT_SEED,
                 n_boot: int = N_BOOT, n_perms: int = N_PERMUTATIONS) -> dict:
    def _load(path):
        return [json.loads(line)
                for line in Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip()]

    train_rows, test_rows = _load(train_path), _load(test_path)
    report: dict = {"train_data": str(train_path), "test_data": str(test_path),
                    "seed": seed, "quantities": {}}
    for quantity in QUANTITIES:
        train_xy = prepare(train_rows, quantity)
        test_xy = prepare(test_rows, quantity)
        reason = _insufficient(train_xy, "train") or _insufficient(test_xy, "test")
        if reason:
            report["quantities"][quantity] = {"insufficient_data": reason}
            continue
        report["quantities"][quantity] = evaluate_transfer(
            train_xy, test_xy, seed, n_boot=n_boot, n_perms=n_perms)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-data", required=True)
    ap.add_argument("--test-data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    report = run_transfer(args.train_data, args.test_data, args.out, args.seed)
    print(json.dumps({q: ({"insufficient_data": v["insufficient_data"]}
                          if "insufficient_data" in v
                          else {"n_train": v["n_train"], "n_test": v["n_test"],
                                "n_tasks_test": v["n_tasks_test"]})
                      for q, v in report["quantities"].items()},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
