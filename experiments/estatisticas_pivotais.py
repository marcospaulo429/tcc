"""Regenera as estatísticas de pontos pivotais do paper e FALHA em caso de drift.

Análogo de reconcilia_nulos.py para a análise pivotal (pedido do painel: toda
estatística publicada deve ser re-derivável de runs/ por script que quebra).

Deriva de runs/teste3_*/cf_results.jsonl:
- census 4B original (g450/g600/g900/mt6): 56 instâncias pivotais, 53 screened
  (P binomial 4.1e-13), 22 pares únicos task×ponto (19 screened, P 4.3e-4),
  16 tasks (13 integralmente screened) + CI 95% bootstrap clusterizado por task;
- replicações em termos pivotais: MBPP+ 4B, MBPP+ 1.7B, 8B (3 configs),
  pool curado 4B (D5) e 8B (v5cur).

Pivotal = ¬final_timed_out ∧ (C_H≠0 ∨ C_M≠0 ∨ C_HM≠0); screened = C_HM == C_M.
"""
import json
import random
import sys
from math import comb
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
CENSUS = ("g450", "g600", "g900", "mt6")
# valores publicados: (pivotais, screened) por run de replicação
PAPER_REPLICATIONS = {
    "teste3_mbpp_g600": (5, 5), "teste3_mbpp_mt6": (6, 6),
    "teste3_mbpp17_g600": (12, 12), "teste3_mbpp17_mt6": (12, 12),
    "teste3_q8_g600": (23, 18), "teste3_q8_mt4": (28, 21),
    "teste3_q8_mt6": (27, 21),
    "teste3_q4cur_g600": (8, 4), "teste3_q4cur_mt6": (13, 11),
    "teste3_v5cur_g600": (15, 12), "teste3_v5cur_mt6": (22, 19),
}
PAPER = {"pivotal": 56, "screened": 53, "uniq": 22, "uniq_screened": 19,
         "tasks": 16, "tasks_full": 13}
BOOT_SEED = 20260824


def load(run: str) -> list[dict]:
    rows = [json.loads(l) for l in open(RUNS / run / "cf_results.jsonl")]
    return [r for r in rows if not r.get("final_timed_out")]


def pivotal(rows):
    return [r for r in rows
            if any(x != 0 for x in (r["C_H"], r["C_M"], r["C_HM"]))]


def screened(r) -> bool:
    return r["C_HM"] == r["C_M"]


def binom_p_ge(k: int, n: int) -> float:
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n


def cluster_ci(piv: list[dict], n_boot: int = 10000) -> list[float]:
    by_task: dict[str, list[bool]] = {}
    for r in piv:
        by_task.setdefault(r["task_id"], []).append(screened(r))
    tasks = sorted(by_task)
    rng = random.Random(BOOT_SEED)
    rates = sorted(
        (lambda flat: sum(flat) / len(flat))(
            [x for t in (rng.choice(tasks) for _ in tasks)
             for x in by_task[t]])
        for _ in range(n_boot))
    return [rates[int(0.025 * n_boot)], rates[int(0.975 * n_boot)]]


def main() -> int:
    piv = [r for c in CENSUS for r in pivotal(load(f"teste3_{c}"))]
    n_scr = sum(screened(r) for r in piv)
    uniq: dict[tuple, list[bool]] = {}
    tasks: dict[str, list[bool]] = {}
    for r in piv:
        uniq.setdefault((r["task_id"], r["cp_index"]), []).append(screened(r))
        tasks.setdefault(r["task_id"], []).append(screened(r))
    got = {"pivotal": len(piv), "screened": n_scr, "uniq": len(uniq),
           "uniq_screened": sum(all(v) for v in uniq.values()),
           "tasks": len(tasks),
           "tasks_full": sum(all(v) for v in tasks.values())}
    print("census 4B:", got)
    print(f"  P(>= {n_scr}/{len(piv)}) = {binom_p_ge(n_scr, len(piv)):.2e}")
    print(f"  P(>= {got['uniq_screened']}/{got['uniq']}) = "
          f"{binom_p_ge(got['uniq_screened'], got['uniq']):.2e}")
    print(f"  fração screened {n_scr/len(piv):.3f}, CI95 cluster-task "
          f"{cluster_ci(piv)}")
    ok = got == PAPER
    if not ok:
        print(f"DRIFT no census: esperado {PAPER}")
    for run, (p_piv, p_scr) in PAPER_REPLICATIONS.items():
        rp = pivotal(load(run))
        rs = sum(screened(r) for r in rp)
        match = (len(rp), rs) == (p_piv, p_scr)
        ok = ok and match
        print(f"{run}: pivotais={len(rp)} screened={rs} "
              f"{'OK' if match else f'DRIFT (paper: {p_piv},{p_scr})'}")
    print("RECONCILIADO" if ok else "FALHOU")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
