"""Análise D4 (pré-registro 17) — 0 rollouts, pós-cadeia v4.

(a) piso: delegado a analise_replicacao (tags v4cur_*).
(b) mecanismo: nos pontos com C_H != 0, associação re-injeção (a′ contém >=1
    constante crítica, matching por substring do repr no dump JSON do a′)
    × quebra raw de screening (C_HM != C_M). Fisher exato unilateral
    (alternativa: quebras concentram-se nos pontos SEM re-injeção), alpha=0.05.
(c) exploratória direcional: taxa de quebra raw pressure >= slack.

Escreve experiments/results/2026-08-23_v4_mecanismo.json.
"""
import json
from math import comb
from pathlib import Path

from environment.tasks_v4 import CRITICAL_CONSTANTS as _C4
from environment.tasks_v5 import CRITICAL_CONSTANTS as _C5

CRITICAL_CONSTANTS = _C4 | _C5
TAGS = {"slack": "v5cur_g600", "pressure": "v5cur_mt6"}


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
            "reinjects": any(c in txt for c in consts),
        }


def fisher_one_sided(a, b, c, d):
    """P(X >= a) hipergeométrica; linhas = (não-reinjeta, reinjeta),
    colunas = (quebra, não-quebra)."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    denom = comb(n, c1)
    return sum(comb(r1, x) * comb(n - r1, c1 - x)
               for x in range(a, min(r1, c1) + 1)) / denom


def main():
    out = {}
    for regime, tag in TAGS.items():
        pts = list(points(tag))
        active = [p for p in pts if p["C_H"] != 0.0]
        a = sum(1 for p in active if not p["reinjects"] and p["raw_break"])
        b = sum(1 for p in active if not p["reinjects"] and not p["raw_break"])
        c = sum(1 for p in active if p["reinjects"] and p["raw_break"])
        d = sum(1 for p in active if p["reinjects"] and not p["raw_break"])
        p_val = fisher_one_sided(a, b, c, d) if active else None
        out[regime] = {
            "tag": tag, "n_points": len(pts),
            "raw_breaks": sum(p["raw_break"] for p in pts),
            "raw_breaks_nonsat": sum(p["raw_break"] and not p["saturated"] for p in pts),
            "n_active_CH": len(active),
            "table_noreinj_reinj_x_break_nobreak": [[a, b], [c, d]],
            "fisher_one_sided_p": p_val,
            "break_tasks": sorted({p["task_id"] for p in pts if p["raw_break"]}),
            "points": pts,
        }
    n_s, k_s = out["slack"]["n_points"], out["slack"]["raw_breaks"]
    n_p, k_p = out["pressure"]["n_points"], out["pressure"]["raw_breaks"]
    out["exploratory_c"] = {
        "rate_slack": k_s / n_s if n_s else None,
        "rate_pressure": k_p / n_p if n_p else None,
        "directional_holds": (k_p / n_p >= k_s / n_s) if n_s and n_p else None,
    }
    path = Path("experiments/results/2026-08-23_v4b_mecanismo.json")
    path.write_text(json.dumps(out, indent=1))
    for regime in TAGS:
        o = out[regime]
        print(regime, f"pontos={o['n_points']} quebras={o['raw_breaks']} "
              f"(nonsat={o['raw_breaks_nonsat']}) ativos={o['n_active_CH']} "
              f"tabela={o['table_noreinj_reinj_x_break_nobreak']} "
              f"fisher_p={o['fisher_one_sided_p']}")
    print("exploratória (c):", out["exploratory_c"], "\nescrito:", path)


if __name__ == "__main__":
    main()
