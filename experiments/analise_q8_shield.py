"""Análise do escudo invertido no 8B (review 9, W1) — 0 rollouts.

Nos pontos de quebra raw do q8_g600, mede se o a′ amostrado re-injeta as
constantes críticas da task (mecanismo estrutural da anatomia); compara com
os pontos das MESMAS tasks no 4B g600. Escreve
experiments/results/2026-08-23_q8_shield_invertido.json.
"""
import json
from pathlib import Path

from environment.tasks_v3 import CRITICAL_CONSTANTS


def points(tag: str):
    samples = {(s["trajectory_id"], s["index"]): s
               for s in map(json.loads, open(f"runs/teste2_{tag}/samples.jsonl"))}
    for r in map(json.loads, open(f"runs/teste3_{tag}/cf_results.jsonl")):
        s = samples.get((r["trajectory_id"], r["index"]))
        consts = [str(c) for c in CRITICAL_CONSTANTS.get(r["task_id"], [])]
        txt = json.dumps(s["sample"]) if s else ""
        yield {
            "task_id": r["task_id"], "cp_index": r["cp_index"],
            "raw_break": r["C_HM"] != r["C_M"], "saturated": r["saturated"],
            "C_H": r["C_H"], "C_M": r["C_M"], "C_HM": r["C_HM"], "I": r["I"],
            "n_consts": len(consts),
            "n_consts_in_aprime": sum(1 for c in consts if c in txt),
        }


def main():
    q8 = list(points("q8_g600"))
    break_tasks = {p["task_id"] for p in q8 if p["raw_break"]}
    q4_same = [p for p in points("g600") if p["task_id"] in break_tasks]
    raw_rates = {}
    for tag in ["q8_g600", "q8_mt6", "q8_mt4"]:
        rows = [json.loads(l) for l in open(f"runs/teste3_{tag}/cf_results.jsonl")]
        raw_rates[tag] = {"n": len(rows),
                          "raw_breaks": sum(r["C_HM"] != r["C_M"] for r in rows)}
    out = {"q8_g600_breaks": [p for p in q8 if p["raw_break"]],
           "g600_4b_same_tasks": q4_same,
           "raw_break_rates_q8": raw_rates}
    path = Path("experiments/results/2026-08-23_q8_shield_invertido.json")
    path.write_text(json.dumps(out, indent=1))
    for p in out["q8_g600_breaks"]:
        print("8B", p["task_id"], "C_H", p["C_H"], "in_a'", p["n_consts_in_aprime"], "/", p["n_consts"])
    for p in q4_same:
        print("4B", p["task_id"], "break", p["raw_break"], "in_a'", p["n_consts_in_aprime"], "/", p["n_consts"])
    print("raw rates:", raw_rates, "\nescrito:", path)


if __name__ == "__main__":
    main()
