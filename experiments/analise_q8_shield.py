"""Análise do escudo invertido no 8B (reviews 9-10) — 0 rollouts.

Caracteriza TODAS as quebras raw do 8B (g600, mt6, mt4): identidade da task,
estrutura (C_H, C_M, C_HM, I) e se o a′ amostrado re-injeta as constantes
críticas da task (matching: substring do repr da constante no dump JSON do
a′ — valores distintivos tipo "14.75"). Compara com as MESMAS tasks no 4B
g600. Escreve experiments/results/2026-08-23_q8_shield_invertido.json.
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
    breaks_by_tag = {tag: [p for p in points(tag) if p["raw_break"]]
                     for tag in ["q8_g600", "q8_mt6", "q8_mt4"]}
    break_tasks = {p["task_id"] for p in breaks_by_tag["q8_g600"]}
    q4_same = [p for p in points("g600") if p["task_id"] in break_tasks]
    raw_rates = {}
    for tag in ["q8_g600", "q8_mt6", "q8_mt4"]:
        rows = [json.loads(l) for l in open(f"runs/teste3_{tag}/cf_results.jsonl")]
        raw_rates[tag] = {"n": len(rows),
                          "raw_breaks": sum(r["C_HM"] != r["C_M"] for r in rows)}
    slack_tasks = {p["task_id"] for p in breaks_by_tag["q8_g600"]}
    recurrence = {tag: {"break_tasks": sorted({p["task_id"] for p in ps}),
                        "n_recurring_from_slack": len({p["task_id"] for p in ps} & slack_tasks)}
                  for tag, ps in breaks_by_tag.items()}
    out = {"breaks_by_tag": breaks_by_tag,
           "g600_4b_same_tasks": q4_same,
           "raw_break_rates_q8": raw_rates,
           "recurrence": recurrence}
    path = Path("experiments/results/2026-08-23_q8_shield_invertido.json")
    path.write_text(json.dumps(out, indent=1))
    for tag, ps in breaks_by_tag.items():
        for p in ps:
            print(tag, p["task_id"], f"C_H={p['C_H']:+.2f} C_M={p['C_M']:+.2f} C_HM={p['C_HM']:+.2f} I={p['I']:+.2f}",
                  "in_a'", p["n_consts_in_aprime"], "/", p["n_consts"], "sat", p["saturated"])
    print("recurrence:", json.dumps(recurrence["q8_mt6"]), json.dumps(recurrence["q8_mt4"]))
    print("raw rates:", raw_rates, "\nescrito:", path)


if __name__ == "__main__":
    main()
