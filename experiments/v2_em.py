"""Pré-registro 32 (DIARIO 2026-08-26) — contabilidade EPISODE-MATCHED do braço outcome V2.

Declarado no pré-reg 32: além da parada dual (budget_calls OU max_episodes), o braço
outcome é fatiado post-hoc nos números de episódios dos braços de crédito (ch, chm_cm)
por seed, com gate de fidelidade — mesmo desenho do pré-reg 31 (experiments/ato4_em.py).

O treino é determinístico por seed e train_log.jsonl grava θ após cada episódio, então
o braço episode-matched é o run outcome existente fatiado em N; só a avaliação held-out
(6 tasks, greedy, CENTER_V2, λ* do pool) é nova.

Estágios (idempotentes via arquivos de saída em --out):
  1. fidelity: re-avalia θ final do outcome s1 → deve reproduzir heldout.mean_R_eff
     do summary.json bit a bit (divergiu → ABORTA, investigar serving).
  2. ch_match_s{1,2,3}:  N = episodes do braço ch por seed.
  3. chm_match_s{1,2,3}: N = episodes do braço chm_cm por seed.

Uso: uv run python -m experiments.v2_em --out runs/v2_em
"""
import argparse
import importlib
import json
from pathlib import Path

from rl.policy_v2 import CENTER_V2
from rl.train_c1 import CountingLLM
from rl.train_v2 import evaluate

RUNS = Path("runs/v2_train")


def load_pool() -> dict:
    return json.loads((RUNS / "pool.json").read_text())


def arm_summary(arm: str, seed: int) -> dict:
    return json.loads((RUNS / f"{arm}_s{seed}" / "summary.json").read_text())


def theta_at(seed: int, n_episodes: int) -> list[float]:
    """θ após n_episodes de treino outcome = linha episode_idx n_episodes−1."""
    path = RUNS / f"outcome_s{seed}" / "train_log.jsonl"
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["episode_idx"] == n_episodes - 1:
                return row["theta"]
    raise ValueError(f"episode_idx {n_episodes - 1} ausente em {path}")


def heldout_tasks(pool: dict, tasks_module: str) -> list[dict]:
    by_id = {t["task_id"]: t
             for t in importlib.import_module(tasks_module).TASKS}
    return [by_id[tid] for tid in pool["heldout"]]


def run_cell(name: str, theta: list[float], seed: int, out: Path,
             tasks: list[dict], lambda_cost: float, harness_kw: dict) -> dict:
    cell_path = out / f"{name}.json"
    if cell_path.exists():
        print(f"[v2_em] pula {name} (existe)")
        return json.loads(cell_path.read_text())
    from agent.llm import LLMClient
    llm = CountingLLM(LLMClient())
    res = evaluate(tasks, llm, theta, seed, out / name,
                   lambda_cost=lambda_cost, center=CENTER_V2,
                   harness_kw=harness_kw)
    res |= {"cell": name, "seed": seed, "theta": theta,
            "llm_calls": llm.call_count}
    out.mkdir(parents=True, exist_ok=True)
    cell_path.write_text(json.dumps(res, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"[v2_em] {name}: mean_R_eff={res['mean_R_eff']:.4f} "
          f"mean_R={res['mean_R']:.4f} calls={res['llm_calls']}")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="pré-reg 32: outcome V2 episode-matched")
    ap.add_argument("--out", default="runs/v2_em")
    ap.add_argument("--tasks-module", default="environment.tasks_swe")
    ap.add_argument("--skip-fidelity", action="store_true",
                    help="só depois do gate ter passado uma vez")
    args = ap.parse_args()
    out = Path(args.out)
    pool = load_pool()
    lam = pool["lambda_star"]
    tasks = heldout_tasks(pool, args.tasks_module)
    ref1 = arm_summary("outcome", 1)
    harness_kw = ref1["harness_kw"]

    if not args.skip_fidelity:
        fid = run_cell("fidelity_s1_full", ref1["theta"], 1, out, tasks,
                       lam, harness_kw)
        ref_val = ref1["heldout"]["mean_R_eff"]
        if abs(fid["mean_R_eff"] - ref_val) > 1e-9:
            raise SystemExit(
                f"FIDELITY GATE FALHOU: {fid['mean_R_eff']:.6f} != {ref_val:.6f} "
                "— investigar serving antes de interpretar (pré-reg 32).")
        print("[v2_em] fidelity gate OK")

    summary: dict = {"lambda_star": lam, "cells": {}, "refs": {}}
    for tag, credit_arm in (("ch_match", "ch"), ("chm_match", "chm_cm")):
        for seed in (1, 2, 3):
            n = arm_summary(credit_arm, seed)["episodes"]
            name = f"{tag}_s{seed}"
            res = run_cell(name, theta_at(seed, n), seed, out, tasks,
                           lam, harness_kw)
            summary["cells"][name] = {"n_episodes": n,
                                      "mean_R_eff": res["mean_R_eff"],
                                      "mean_R": res["mean_R"]}
    for arm in ("outcome", "ch", "chm_cm", "zero"):
        summary["refs"][arm] = {
            f"s{s}": {"episodes": arm_summary(arm, s)["episodes"],
                      "heldout_mean_R_eff": arm_summary(arm, s)["heldout"]["mean_R_eff"]}
            for s in (1, 2, 3)}
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
