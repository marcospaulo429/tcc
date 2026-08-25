"""Pré-registro 31 (DIARIO 2026-08-26) — braço outcome-only EPISODE-MATCHED.

Responde ao confound R1-W1 (painel rodada 7): no Ato 4 o outcome-only venceu
com 279–284 episódios contra 137–139 (ch) e 68–70 (chm_cm). Aqui avaliamos o
θ do run outcome existente FATIADO no episódio N (treino é determinístico e
train_log.jsonl grava θ após cada episódio), no MESMO protocolo held-out do
c1d. Nenhum treino novo.

Estágios (idempotentes via arquivos de saída):
  1. fidelity: re-avalia θ final do outcome s1 → deve reproduzir 0.440
     (gate de validade; divergiu → ABORTA).
  2. ch-match  (primário):  N = 139/139/137 (s1/s2/s3).
  3. chm-match (secundário): N = 70/68/70.

Uso: uv run python -m experiments.ato4_em --out runs/ato4_em
"""
import argparse
import json
from pathlib import Path

from environment.registry import resolve_task
from rl.policy import CENTER_C1B
from rl.train_c1 import CountingLLM, evaluate

LAMBDA = 5.0
CH_MATCH = {1: 139, 2: 139, 3: 137}
CHM_MATCH = {1: 70, 2: 68, 3: 70}
REFS = {"outcome_full": (0.440, 0.443), "ch": (0.398, 0.405),
        "keep_zero_chm": 0.392}


def theta_at(seed: int, n_episodes: int) -> list[float]:
    """θ após n_episodes de treino = linha episode_idx n_episodes−1."""
    path = Path(f"runs/c1d_outcome_s{seed}/train_log.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["episode_idx"] == n_episodes - 1:
                return row["theta"]
    raise ValueError(f"episode_idx {n_episodes - 1} ausente em {path}")


def outcome_summary(seed: int) -> dict:
    return json.loads(Path(f"runs/c1d_outcome_s{seed}/summary.json").read_text())


def heldout_tasks() -> list[dict]:
    pool = json.loads(Path("runs/c1d_margem/pool.json").read_text())
    return [resolve_task(tid) for tid in pool["heldout"]]


def run_cell(name: str, theta: list[float], seed: int, out: Path,
             tasks: list[dict]) -> dict:
    cell_path = out / f"{name}.json"
    if cell_path.exists():
        print(f"[ato4_em] pula {name} (existe)")
        return json.loads(cell_path.read_text())
    from agent.llm import LLMClient
    llm = CountingLLM(LLMClient())
    res = evaluate(tasks, llm, theta, seed, out / name,
                   lambda_cost=LAMBDA, center=CENTER_C1B)
    res |= {"cell": name, "seed": seed, "theta": theta,
            "llm_calls": llm.call_count}
    out.mkdir(parents=True, exist_ok=True)
    cell_path.write_text(json.dumps(res, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"[ato4_em] {name}: mean_R_eff={res['mean_R_eff']:.4f} "
          f"mean_R={res['mean_R']:.4f} calls={res['llm_calls']}")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="pré-reg 31: outcome episode-matched")
    ap.add_argument("--out", default="runs/ato4_em")
    ap.add_argument("--skip-fidelity", action="store_true",
                    help="só depois do gate ter passado uma vez")
    args = ap.parse_args()
    out = Path(args.out)
    tasks = heldout_tasks()

    if not args.skip_fidelity:
        ref = outcome_summary(1)
        fid = run_cell("fidelity_s1_full", ref["theta"], 1, out, tasks)
        ref_val = ref["heldout"]["mean_R_eff"]
        if abs(fid["mean_R_eff"] - ref_val) > 1e-9:
            raise SystemExit(
                f"FIDELITY GATE FALHOU: {fid['mean_R_eff']:.6f} != {ref_val:.6f} "
                "— investigar serving antes de interpretar (pré-reg 31).")
        print("[ato4_em] fidelity gate OK")

    summary: dict = {"refs": REFS, "cells": {}}
    for tag, match in (("ch_match", CH_MATCH), ("chm_match", CHM_MATCH)):
        for seed, n in match.items():
            name = f"{tag}_s{seed}"
            res = run_cell(name, theta_at(seed, n), seed, out, tasks)
            summary["cells"][name] = {"n_episodes": n,
                                      "mean_R_eff": res["mean_R_eff"],
                                      "mean_R": res["mean_R"]}
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
