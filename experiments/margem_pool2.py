"""C1d / Act 4 estágio A′ — pool sob objetivo são (pré-reg 27).

Regra pré-registrada (PLANO-EXECUCAO.md item 27, commitado ANTES de rodar):
1. Mede summarize-always determinístico nas mesmas 52 tasks (keep/thr600
   REUTILIZADOS de runs/c1c_margem/margem_report.json — mesma config,
   determinístico).
2. Seleção analítica: para λ ∈ {2, 5, 10, 25}, task ELEGÍVEL se thr600 domina
   ESTRITAMENTE keep-always E summarize-always em R_eff(λ) (sem timeouts);
   λ* = λ que maximiza elegíveis (empate → menor λ). Pool = elegíveis por
   margem mínima de dominância desc, cap 16, mínimo 10 (senão ABORTA —
   reportável). Treino = ranks pares, held-out = ímpares.

Saída: runs/c1d_margem/summ_report.json + runs/c1d_margem/pool.json
(com lambda_star; consumido por rl/train_c1 --pool-json e --lambda-cost).
"""
import argparse
import json
from pathlib import Path

from agent.harness import Harness
from agent.llm import LLMClient
from experiments.margem_pool import FixedPolicyHarness, run_policy

LAMBDA_GRID = (2.0, 5.0, 10.0, 25.0)
CAP = 16
MIN_POOL = 10


class SummAlwaysHarness(FixedPolicyHarness):
    def __init__(self, **kw):
        Harness.__init__(self, **kw)
        self.mode = "summ"

    def decide_context_policy(self, messages):
        return "summarize_context"


def run_summ(task: dict, llm, out_dir: Path) -> dict:
    from agent.loop import Episode
    from trajectories.recorder import Recorder
    from trajectories.schema import load_trajectory
    ep = Episode(task, llm, SummAlwaysHarness(), Recorder(out_dir))
    try:
        r = ep.run()
    finally:
        ep.sandbox.cleanup()
    traj = load_trajectory(r["trajectory_path"])
    tokens = sum(d.costs.get("prompt_tokens", 0) for d in traj.decisions)
    return {"reward": r["reward"], "prompt_tokens": tokens,
            "timed_out": r["final_timed_out"]}


def r_eff(entry: dict, lam: float) -> float:
    return entry["reward"] - lam * (entry["prompt_tokens"] / 100000.0)


def select(report_c1c: dict, summ: dict) -> dict:
    """Seleção analítica declarada: λ*, elegíveis, pool, split."""
    per_lambda = {}
    for lam in LAMBDA_GRID:
        elig = []
        for tid, row in report_c1c.items():
            k, t, s = row["keep"], row["thr600"], summ[tid]
            if k["timed_out"] or t["timed_out"] or s["timed_out"]:
                continue
            rt, rk, rs = r_eff(t, lam), r_eff(k, lam), r_eff(s, lam)
            if rt > rk and rt > rs:
                elig.append((tid, round(min(rt - rk, rt - rs), 4)))
        per_lambda[lam] = elig
    lam_star = min(LAMBDA_GRID,
                   key=lambda l: (-len(per_lambda[l]), l))
    ranked = sorted(per_lambda[lam_star], key=lambda x: (-x[1], x[0]))[:CAP]
    return {"lambda_grid": {str(l): len(per_lambda[l]) for l in LAMBDA_GRID},
            "lambda_star": lam_star,
            "viable": len(ranked) >= MIN_POOL,
            "n": len(ranked), "ranked": ranked,
            "train": [tid for i, (tid, _) in enumerate(ranked) if i % 2 == 0],
            "heldout": [tid for i, (tid, _) in enumerate(ranked) if i % 2 == 1]}


def main() -> None:
    argparse.ArgumentParser(description="C1d estágio A': pool sob objetivo são "
                            "(pré-reg 27)").parse_args()
    report_c1c = json.loads(
        Path("runs/c1c_margem/margem_report.json").read_text())
    out = Path("runs/c1d_margem")
    out.mkdir(parents=True, exist_ok=True)
    summ_path = out / "summ_report.json"
    summ = json.loads(summ_path.read_text()) if summ_path.exists() else {}
    llm = LLMClient(max_tokens=1200)
    from environment.registry import resolve_task
    for tid in sorted(report_c1c):
        if tid in summ:
            continue
        summ[tid] = run_summ(resolve_task(tid), llm, out / "episodes")
        summ_path.write_text(json.dumps(summ, indent=1, ensure_ascii=False))
        print(f"[c1d] {tid} summ R={summ[tid]['reward']:.2f} "
              f"tok={summ[tid]['prompt_tokens']}", flush=True)
    pool = select(report_c1c, summ)
    (out / "pool.json").write_text(json.dumps(pool, indent=1, ensure_ascii=False))
    print(json.dumps(pool, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
