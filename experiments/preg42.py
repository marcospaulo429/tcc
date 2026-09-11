"""Pré-registro 42 — quarta célula R(h′, a) fora da tripla V1/4B.

Generaliza experiments.quarto_braco (stage v1) para células externas já
censadas (teste3_<cfg>/cf_results.jsonl + teste0_<cfg>/baseline). Um replay
por ponto com fila [cp: flip, tc: a original]. Pivotais (C_H ≠ 0) primeiro.

Gate: revalidação nula (2 pontos/config, fila 100% original) — todos exatos,
senão aborta. Roda na H100 via Slurm (slurm/preg42.sbatch).

Uso:
  python -m experiments.preg42 --stage gate --cells mbpp_g600,mbpp_mt6,he_g600,he_mt6,g450,g600,g900
  python -m experiments.preg42 --stage run  --cells mbpp_g600,mbpp_mt6,he_g600,he_mt6
  python -m experiments.preg42 --stage relatorio
"""
import argparse
import json
import statistics
from pathlib import Path

from agent.llm import LLMClient
from experiments.common import append_row, done_keys, load_rows, load_trajectories
from experiments.teste3 import FLIP, _by_index, sanitize
from trajectories.replay import replay_from

OUT = Path("runs/preg42")
PRIMARY = ("mbpp_g600", "mbpp_mt6", "he_g600", "he_mt6")
SECONDARY_8B = ("q8_g600", "q8_mt4", "q8_mt6")
TERTIARY_17B = ("mbpp17_g600", "mbpp17_mt6", "q17_g600", "q17_mt6")


def _trajs(cfg: str) -> dict:
    return {t.trajectory_id: t
            for t in load_trajectories(Path(f"runs/teste0_{cfg}/baseline"))}


def _cf_rows(cfg: str) -> list[dict]:
    return load_rows(Path(f"runs/teste3_{cfg}/cf_results.jsonl"))


def _fila(traj, r: dict, flip: bool) -> list[dict]:
    cp, tc = _by_index(traj, r["cp_index"]), _by_index(traj, r["index"])
    cp_action = sanitize(cp.chosen_action)
    if flip:
        cp_action = {"action": FLIP[cp_action["action"]]}
    return [{"point": "context_policy", "action": cp_action},
            {"point": "tool_call", "action": sanitize(tc.chosen_action)}]


def stage_gate(llm, cells):
    rows_path = OUT / "gate_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    for cfg in cells:
        trajs = _trajs(cfg)
        alvo = sorted(_cf_rows(cfg), key=lambda r: (r["task_id"], r["cp_index"]))[:2]
        for r in alvo:
            if (cfg, r["task_id"], r["cp_index"]) in feitos:
                continue
            traj = trajs[r["trajectory_id"]]
            res = replay_from(traj, r["cp_index"], llm, OUT / "replays",
                              override_actions=_fila(traj, r, flip=False))
            dr = res["reward"] - traj.final_reward
            append_row(rows_path, {"cfg": cfg, "task_id": r["task_id"],
                                   "index": r["cp_index"], "dR": dr,
                                   "exact": dr == 0.0})
            print(f"[gate {cfg}] {r['task_id']} cp{r['cp_index']} dR={dr:+.2f}",
                  flush=True)
    rows = [r for r in load_rows(rows_path) if r["cfg"] in cells]
    ok = bool(rows) and all(r["exact"] for r in rows)
    print(json.dumps({"gate_ok": ok, "n": len(rows), "cells": list(cells),
                      "n_inexact": sum(not r["exact"] for r in rows)}), flush=True)
    if not ok:
        raise SystemExit("GATE NULO FALHOU — abortando (pré-reg 42)")


def stage_run(llm, cells):
    rows_path = OUT / "rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "trajectory_id", "cp_index"))
    for cfg in cells:
        trajs = _trajs(cfg)
        # pivotais (C_H != 0) primeiro: são o endpoint primário
        ordem = sorted(_cf_rows(cfg),
                       key=lambda r: (r["C_H"] == 0, r["task_id"], r["cp_index"]))
        for r in ordem:
            if (cfg, r["trajectory_id"], r["cp_index"]) in feitos:
                continue
            traj = trajs[r["trajectory_id"]]
            res = replay_from(traj, r["cp_index"], llm, OUT / "replays",
                              override_actions=_fila(traj, r, flip=True))
            r_ha = res["reward"]
            c_ha = round(r["r_orig"] - r_ha, 4)
            append_row(rows_path, {
                "cfg": cfg, "task_id": r["task_id"],
                "trajectory_id": r["trajectory_id"],
                "cp_index": r["cp_index"], "index": r["index"],
                "direction": r["direction"], "r_orig": r["r_orig"],
                "r_ha": r_ha, "C_Ha": c_ha, "C_H": r["C_H"], "C_M": r["C_M"],
                "C_HM": r["C_HM"], "I": r["I"],
                "I_fact": round(r["C_HM"] - c_ha - r["C_M"], 4),
                "exact_ha": r_ha == r["r_orig"],
                "pivotal": r["C_H"] != 0,
                "screened": r["C_HM"] == r["C_M"],
                "saturated": r.get("saturated"),
                "final_timed_out": res["final_timed_out"],
                "replay_traj": res["trajectory_path"]})
            print(f"[{cfg}] {r['task_id']} cp{r['cp_index']} piv={r['C_H'] != 0} "
                  f"R(h',a)={r_ha:.2f} R={r['r_orig']:.2f} C_H={r['C_H']:+.2f}",
                  flush=True)


def _resumo(rs: list[dict]) -> dict:
    piv = [r for r in rs if r["pivotal"] and r["screened"]]
    npiv = [r for r in rs if not r["pivotal"]]
    ifs = [r["I_fact"] for r in rs]
    return {"n": len(rs), "n_pivotal_screened": len(piv),
            "n_exact_ha_pivotal": sum(r["exact_ha"] for r in piv),
            "frac_exact_ha_pivotal": round(sum(r["exact_ha"] for r in piv) / len(piv), 4) if piv else None,
            "n_nonpivotal": len(npiv),
            "n_exact_ha_nonpivotal": sum(r["exact_ha"] for r in npiv),
            "n_CH_diff_CHa": sum(r["C_H"] != r["C_Ha"] for r in rs),
            "n_I_fact_zero": sum(x == 0.0 for x in ifs),
            "I_fact_max_abs": max((abs(x) for x in ifs), default=None),
            "pares_unicos": len({(r["task_id"], r["cp_index"]) for r in rs}),
            "tasks_unicas": len({r["task_id"] for r in rs})}


def stage_relatorio():
    rows = load_rows(OUT / "rows.jsonl")
    gate = load_rows(OUT / "gate_rows.jsonl")
    prim = [r for r in rows if r["cfg"] in PRIMARY]
    res_prim = _resumo(prim)
    frac = res_prim["frac_exact_ha_pivotal"]
    desfecho = None
    if frac is not None:
        desfecho = "s1_replica" if frac >= 0.90 else \
            ("s2_parcial" if frac >= 0.60 else "s3_artefato_desenho")
    cells = sorted({r["cfg"] for r in rows})
    report = {
        "gate": {"ok": bool(gate) and all(r["exact"] for r in gate),
                 "n": len(gate), "n_inexact": sum(not r["exact"] for r in gate),
                 "cells": sorted({r["cfg"] for r in gate})},
        "primario_4b_externo": {**res_prim, "desfecho": desfecho,
                                 "cells": [c for c in PRIMARY if c in cells]},
        "secundario_8b": _resumo([r for r in rows if r["cfg"] in SECONDARY_8B]),
        "terciario_17b": _resumo([r for r in rows if r["cfg"] in TERTIARY_17B]),
        "por_cell": {c: _resumo([r for r in rows if r["cfg"] == c]) for c in cells},
        "quebras": [{k: r[k] for k in ("cfg", "task_id", "cp_index", "direction",
                                       "C_Ha", "C_H", "C_M", "C_HM", "I", "I_fact")}
                    for r in rows if not r["exact_ha"]],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["gate", "run", "relatorio"])
    ap.add_argument("--cells", default=",".join(PRIMARY))
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cells = tuple(c for c in args.cells.split(",") if c)
    if args.stage == "relatorio":
        stage_relatorio()
    elif args.stage == "gate":
        stage_gate(LLMClient(max_tokens=1200), cells)  # paridade com teste0/teste3
    else:
        stage_run(LLMClient(max_tokens=1200), cells)
