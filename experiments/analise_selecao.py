"""Análise de composição da seleção em C(M): pontos com a′ encontrado vs. não.

Pergunta (review causal): os pontos descartados por "sem alternativa amostrável"
diferem sistematicamente dos retidos em covariáveis observáveis (turn,
context_tokens, posição relativa na trajetória)? Se sim, o contraste de regime
4B vs. 8B pode ser artefato de composição, não de regime.

Fonte: runs/teste3_{cfg}/samples.jsonl (found por ponto) + trajetórias baseline
em runs/teste0_{cfg}/baseline/ (context_tokens por decisão).

Saída: experiments/results/2026-08-24_analise_selecao.json + resumo no stdout.
Falha (exit 1) se artefatos exigidos não existirem.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 20260824
N_BOOT = 10_000

CONFIGS_4B = ["g450", "g600", "g900", "mt6"]
CONFIGS_8B = ["q8_g600", "q8_mt6", "q8_mt4"]
POOL_MATCHED = {"4B": ["g600", "mt6"], "8B": ["q8_g600", "q8_mt6"]}


def load_points(cfg: str) -> list[dict]:
    samples = ROOT / f"runs/teste3_{cfg}/samples.jsonl"
    basedir = ROOT / f"runs/teste0_{cfg}/baseline"
    if not samples.exists() or not basedir.exists():
        print(f"DRIFT: artefatos ausentes para {cfg}: {samples} / {basedir}")
        sys.exit(1)
    ctx: dict[tuple[str, int], tuple[int, int]] = {}
    n_dec: dict[str, int] = {}
    for tf in basedir.glob("*.jsonl"):
        tid = tf.stem
        count = 0
        for line in tf.open():
            r = json.loads(line)
            if r.get("kind") != "decision" and "decision_type" not in r:
                continue
            if r.get("decision_type") != "model":
                continue
            sb = r.get("state_before") or {}
            ctx[(tid, r["index"])] = (sb.get("context_tokens", -1), sb.get("turn", -1))
            count += 1
        n_dec[tid] = count
    rows = [json.loads(line) for line in samples.open()]
    # total de checkpoints por trajetória derivado do próprio samples.jsonl
    max_cp: dict[str, int] = {}
    for r in rows:
        max_cp[r["trajectory_id"]] = max(max_cp.get(r["trajectory_id"], 0), r["cp_index"])
    pts = []
    for r in rows:
        tid = r["trajectory_id"]
        tokens, _ = ctx.get((tid, r["index"]), (-1, -1))
        pts.append(
            {
                "config": cfg,
                "task_id": r["task_id"],
                "found": bool(r["sample"]["found"]),
                "turn": r["turn"],
                "context_tokens": tokens,
                "rel_pos": r["cp_index"] / max(max_cp[tid], 1),
            }
        )
    return pts


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def cohend(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va = sum((x - mean(a)) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mean(b)) ** 2 for x in b) / (len(b) - 1)
    sp = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
    return (mean(a) - mean(b)) / sp if sp > 0 else float("nan")


def cluster_boot_diff(pts: list[dict], var: str, rng: random.Random) -> dict:
    """CI 95% (bootstrap por task) da diferença de médias found − not_found."""
    tasks = sorted({p["task_id"] for p in pts})
    by_task = {t: [p for p in pts if p["task_id"] == t] for t in tasks}
    diffs = []
    for _ in range(N_BOOT):
        sample = [p for t in rng.choices(tasks, k=len(tasks)) for p in by_task[t]]
        f = [p[var] for p in sample if p["found"] and p[var] >= 0]
        nf = [p[var] for p in sample if not p["found"] and p[var] >= 0]
        if f and nf:
            diffs.append(mean(f) - mean(nf))
    diffs.sort()
    if not diffs:
        return {"diff": float("nan"), "ci": [float("nan")] * 2}
    f = [p[var] for p in pts if p["found"] and p[var] >= 0]
    nf = [p[var] for p in pts if not p["found"] and p[var] >= 0]
    return {
        "diff": mean(f) - mean(nf),
        "ci": [diffs[int(0.025 * len(diffs))], diffs[min(int(0.975 * len(diffs)), len(diffs) - 1)]],
    }


def describe(pts: list[dict], rng: random.Random) -> dict:
    found = [p for p in pts if p["found"]]
    notf = [p for p in pts if not p["found"]]
    out = {
        "n": len(pts),
        "n_found": len(found),
        "discard_rate": round(len(notf) / len(pts), 3) if pts else float("nan"),
        "covariates": {},
    }
    for var in ("turn", "context_tokens", "rel_pos"):
        f = [p[var] for p in found if p[var] >= 0]
        nf = [p[var] for p in notf if p[var] >= 0]
        out["covariates"][var] = {
            "mean_found": round(mean(f), 2),
            "mean_not_found": round(mean(nf), 2),
            "cohen_d": round(cohend(f, nf), 3),
            **{k: ([round(x, 2) for x in v] if isinstance(v, list) else round(v, 3))
               for k, v in cluster_boot_diff(pts, var, rng).items()},
        }
    return out


def main() -> None:
    rng = random.Random(SEED)
    all_pts = {c: load_points(c) for c in CONFIGS_4B + CONFIGS_8B}
    report: dict = {"seed": SEED, "per_config": {}, "pooled": {}}
    for c, pts in all_pts.items():
        report["per_config"][c] = describe(pts, rng)
    for label, cfgs in POOL_MATCHED.items():
        pooled = [p for c in cfgs for p in all_pts[c]]
        report["pooled"][f"pool_matched_{label}"] = describe(pooled, rng)
    # contraste entre modelos nas covariáveis dos pontos RETIDOS (onde quebras são mensuráveis)
    ret = {
        label: [p for c in cfgs for p in all_pts[c] if p["found"]]
        for label, cfgs in POOL_MATCHED.items()
    }
    report["retained_contrast"] = {
        var: {
            "mean_4B": round(mean([p[var] for p in ret["4B"] if p[var] >= 0]), 2),
            "mean_8B": round(mean([p[var] for p in ret["8B"] if p[var] >= 0]), 2),
            "cohen_d": round(
                cohend(
                    [p[var] for p in ret["4B"] if p[var] >= 0],
                    [p[var] for p in ret["8B"] if p[var] >= 0],
                ),
                3,
            ),
        }
        for var in ("turn", "context_tokens", "rel_pos")
    }
    out = ROOT / "experiments/results/2026-08-24_analise_selecao.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"\nartefato: {out}")


if __name__ == "__main__":
    main()
