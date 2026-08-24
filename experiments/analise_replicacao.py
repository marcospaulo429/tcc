"""Análise de replicação D2c/D2d/D3 (pré-registros 14–16).

Por tag, computa as quantidades pré-registradas — SEM pooling entre modelos
ou ambientes (pré-registros 7, 15, 16):
- piso (noise_floor do teste3) e queue_floor_ok;
- screening: fração de pontos com C_HM == C_M EXATO (todos os pontos,
  pré-registro 10), global e na direção confirmatória;
- quebras: pontos não-saturados com C_HM != C_M (o sinal de interação);
- saturação e n por direção (frações de descarte, pré-registro f).

Uso: uv run python -m experiments.analise_replicacao [--tags t1 t2 ...]
Escreve experiments/results/<data>_replicacao.json e imprime tabela.
"""
import argparse
import datetime
import json
from pathlib import Path

CONF = "keep_context->summarize_context"
DEFAULT_TAGS = ["g600", "mt6", "q17_g600", "q17_mt6",
                "q8_g600", "q8_mt6", "q8_mt4", "mbpp_g600", "mbpp_mt6",
                "v5cur_g600", "v5cur_mt6", "q4cur_g600", "q4cur_mt6"]


def analyze_tag(tag: str) -> dict | None:
    d = Path(f"runs/teste3_{tag}")
    if not (d / "summary.json").exists():
        return None
    summ = json.loads((d / "summary.json").read_text())
    rows = [json.loads(l) for l in (d / "cf_results.jsonl").read_text().splitlines()]
    out = {
        "tag": tag,
        "queue_floor_ok": summ["queue_floor_ok"],
        "noise_floor": summ["noise_floor"],
        "n_points": len(rows),
    }
    for label, sel in [("all", rows), ("conf", [r for r in rows if r["direction"] == CONF])]:
        screened = [r for r in sel if r["C_HM"] == r["C_M"]]
        nonsat = [r for r in sel if not r["saturated"]]
        breaks = [r for r in nonsat if r["C_HM"] != r["C_M"]]
        out[label] = {
            "n": len(sel),
            "n_screened_exact": len(screened),
            "n_saturated": sum(r["saturated"] for r in sel),
            "n_nonsat": len(nonsat),
            "n_breaks_nonsat": len(breaks),
            "break_tasks": sorted({(r["task_id"], r["cp_index"]) for r in breaks}),
            "I_nonsat": sorted(round(r["I"], 4) for r in nonsat),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="*", default=DEFAULT_TAGS)
    args = ap.parse_args()
    results = [r for t in args.tags if (r := analyze_tag(t))]
    print(f"{'tag':<12}{'floor':>6}{'n':>5}{'screen':>8}{'sat':>5}{'nonsat':>8}{'breaks':>8}  (direção confirmatória)")
    for r in results:
        c = r["conf"]
        print(f"{r['tag']:<12}{r['noise_floor']:>6}{c['n']:>5}"
              f"{c['n_screened_exact']:>8}{c['n_saturated']:>5}{c['n_nonsat']:>8}{c['n_breaks_nonsat']:>8}")
    out = Path("experiments/results") / f"{datetime.date.today().isoformat()}_replicacao.json"
    out.write_text(json.dumps(results, indent=1))
    print(f"\nescrito: {out}")


if __name__ == "__main__":
    main()
