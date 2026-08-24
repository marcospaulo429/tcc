"""C1c estágio A — construção do pool de treino com margem verificada (pré-reg 24).

Regra pré-registrada: candidatos = tasks_all (30) ∪ tasks_curated (22, únicos);
para cada task, 2 episódios determinísticos (política keep-always e thr600, os
mesmos policies fixos da calibração C1), margem m = R_eff(thr600) − R_eff(keep)
a λ=25. Pool margem-verificada = tasks com m > 0, ordenadas por m desc, cap 16;
treino = ranks pares (0,2,...), held-out = ranks ímpares. Abortar se < 8 tasks.

Saída: runs/c1c_margem/margem_report.json + pool em runs/c1c_margem/pool.json.
"""
import json
from pathlib import Path

from agent.harness import Harness
from agent.llm import LLMClient
from agent.loop import Episode
from trajectories.recorder import Recorder

LAMBDA = 25.0
CAP = 16
MIN_POOL = 8


class FixedPolicyHarness(Harness):
    """keep-always ou thr600 (threshold em tokens estimados), demais decisões V1."""

    def __init__(self, mode: str, **kw):
        super().__init__(**kw)
        self.mode = mode

    def decide_context_policy(self, messages):
        if self.mode == "keep":
            return "keep_context"
        from agent.harness import estimate_tokens
        return "summarize_context" if estimate_tokens(messages) > 600 else "keep_context"


def r_eff(reward: float, prompt_tokens: int) -> float:
    return reward - LAMBDA * (prompt_tokens / 100000.0)


def run_policy(task: dict, llm, mode: str, out_dir: Path) -> dict:
    from trajectories.schema import load_trajectory
    ep = Episode(task, llm, FixedPolicyHarness(mode), Recorder(out_dir))
    try:
        r = ep.run()
    finally:
        ep.sandbox.cleanup()
    traj = load_trajectory(r["trajectory_path"])
    tokens = sum(d.costs.get("prompt_tokens", 0) for d in traj.decisions)
    return {"reward": r["reward"], "prompt_tokens": tokens,
            "r_eff": r_eff(r["reward"], tokens),
            "timed_out": r["final_timed_out"]}


def main() -> None:
    import argparse
    argparse.ArgumentParser(description="C1c estágio A: pool por margem "
                            "(pré-reg 24)").parse_args()
    from environment.tasks_all import TASKS as T_ALL
    from environment.tasks_curated import TASKS as T_CUR
    seen, tasks = set(), []
    for t in T_ALL + T_CUR:
        if t["task_id"] not in seen:
            seen.add(t["task_id"])
            tasks.append(t)
    out = Path("runs/c1c_margem")
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "margem_report.json"
    rows = json.loads(report_path.read_text()) if report_path.exists() else {}
    llm = LLMClient(max_tokens=1200)
    for t in sorted(tasks, key=lambda t: t["task_id"]):
        if t["task_id"] in rows:
            continue
        keep = run_policy(t, llm, "keep", out / "episodes")
        thr = run_policy(t, llm, "thr600", out / "episodes")
        rows[t["task_id"]] = {"keep": keep, "thr600": thr,
                              "margin": round(thr["r_eff"] - keep["r_eff"], 4)}
        report_path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(f"[margem] {t['task_id']} m={rows[t['task_id']]['margin']:+.4f}",
              flush=True)
    ranked = sorted(((tid, r["margin"]) for tid, r in rows.items()
                     if r["margin"] > 0 and not r["thr600"]["timed_out"]
                     and not r["keep"]["timed_out"]),
                    key=lambda x: (-x[1], x[0]))[:CAP]
    pool = {"viable": len(ranked) >= MIN_POOL,
            "n": len(ranked), "ranked": ranked,
            "train": [tid for i, (tid, _) in enumerate(ranked) if i % 2 == 0],
            "heldout": [tid for i, (tid, _) in enumerate(ranked) if i % 2 == 1]}
    (out / "pool.json").write_text(json.dumps(pool, indent=1, ensure_ascii=False))
    print(json.dumps(pool, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
