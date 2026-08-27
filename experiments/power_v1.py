"""Análise descritiva 2.1: power gate per-atrator post hoc na célula V1.

Espelho do critério do pré-reg 39 sobre artefatos congelados do Act 4:
margem de thr600 (alvo condicional) sobre keep_always e summarize_always em
mean R_eff(λ), grade registrada {2,5,10,25}, λ* = argmax min-margem, ABRE sse
min-margem ≥ 0.10. Zero rollouts. Saída: runs/preg39/power_v1_report.json.
"""
import json
from pathlib import Path

MARGEM_MIN = 0.10
GRID = (2.0, 5.0, 10.0, 25.0)


def _reff(reward: float, tokens: int, lam: float) -> float:
    return reward - lam * tokens / 1e5


def main() -> None:
    margem = json.load(open("runs/c1c_margem/margem_report.json"))
    summ = json.load(open("runs/c1d_margem/summ_report.json"))
    pool = json.load(open("runs/c1d_margem/pool.json"))
    conjuntos = {"todas_52": sorted(margem),
                 "viaveis_12": sorted(pool["train"] + pool["heldout"])}
    rep = {"criterio": "margem mín de thr600 sobre {keep, summ} em mean R_eff >= 0.10",
           "grid": GRID, "conjuntos": {}}
    for nome, tasks in conjuntos.items():
        por_lambda = {}
        for lam in GRID:
            medias = {}
            for pol, fonte in (("thr600", lambda t: margem[t]["thr600"]),
                               ("keep", lambda t: margem[t]["keep"]),
                               ("summ", lambda t: summ[t])):
                vals = [_reff(fonte(t)["reward"], fonte(t)["prompt_tokens"], lam)
                        for t in tasks]
                medias[pol] = sum(vals) / len(vals)
            margens = {"keep": medias["thr600"] - medias["keep"],
                       "summ": medias["thr600"] - medias["summ"]}
            por_lambda[lam] = {"medias": {k: round(v, 4) for k, v in medias.items()},
                               "margens": {k: round(v, 4) for k, v in margens.items()},
                               "min_margem": round(min(margens.values()), 4)}
        lam_star = max(GRID, key=lambda l: (por_lambda[l]["min_margem"], -l))
        rep["conjuntos"][nome] = {
            "n_tasks": len(tasks), "por_lambda": por_lambda,
            "lambda_star": lam_star,
            "min_margem_star": por_lambda[lam_star]["min_margem"],
            "gate_abre": por_lambda[lam_star]["min_margem"] >= MARGEM_MIN}
    Path("runs/preg39/power_v1_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
