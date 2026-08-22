"""Teste 0 — Replay fidelity.

Hipótese: replay com intervenção nula reproduz o mesmo R (temperature 0, seed fixa).
Fase A: 1 episódio baseline por task (10 rollouts).
Fase B: por trajetória, 3 pontos de replay amostrados uniformemente × 3 repetições,
        intervenção nula (90 rollouts). Piso de detecção = distribuição de |ΔR|.
Execução SEQUENCIAL de propósito: concorrência no vLLM muda o batching e contaminaria
a medida de determinismo.

PRÉ-REGISTRO (antes de rodar o Teste 1): o piso de detecção primário é max|ΔR| sobre
replays nulos SEM timeout de infra (timed_out=True é artefato e é reportado à parte);
p95 é secundário (zero-inflado se o determinismo for bom). Convenção de sinal:
dr = r_replay − r_orig (teste0); C = r_orig − r_cf (teste1).
"""
import argparse
import importlib
import json
import random
from pathlib import Path

from agent.harness import Harness
from agent.llm import LLMClient
from agent.loop import Episode
from trajectories.recorder import Recorder
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories

SEED = 20260821


def run_baselines(out: Path, llm: LLMClient, tasks: list[dict], harness_kw: dict):
    base_dir = out / "baseline"
    results = out / "baseline_results.jsonl"
    done = done_keys(load_rows(results), ("task_id",))
    for task in tasks:
        if (task["task_id"],) in done:
            continue
        print(f"[baseline] {task['task_id']} ...", flush=True)
        ep = Episode(task, llm, Harness(**harness_kw), Recorder(base_dir))
        try:
            r = ep.run()
        finally:
            ep.sandbox.cleanup()
        append_row(results, {"task_id": task["task_id"], **r})
        print(f"[baseline] {task['task_id']} reward={r['reward']:.2f} "
              f"({r['wall_time_s']:.0f}s)", flush=True)


def run_null_replays(out: Path, llm: LLMClient, n_points: int, n_reps: int):
    results = out / "replay_results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "index", "rep"))
    for traj in load_trajectories(out / "baseline"):
        eligible = [d for d in traj.decisions if d.decision_point in Episode.PHASES]
        rng = random.Random(f"{SEED}:{traj.trajectory_id}")
        points = sorted(rng.sample(range(len(eligible)), min(n_points, len(eligible))))
        for p in points:
            d = eligible[p]
            for rep in range(n_reps):
                if (traj.trajectory_id, d.index, rep) in done:
                    continue
                r = replay_from(traj, d.index, llm, out / "replays")
                dr = r["reward"] - traj.final_reward
                # Retries irmãos: gravados ANTES do tool_call (dentro de
                # _call_and_parse), mas reexecutados pelo replay que parte do
                # tool_call — contam no sufixo esperado (causa raiz do falso
                # mismatch de config_renderer/inventory_restock, ver Fase 0.1).
                n_sibling_retries = 0
                j = d.index - 1
                while (d.decision_point == "tool_call" and j >= 0
                       and traj.decisions[j].decision_point == "retry"
                       and traj.decisions[j].state_before.get("turn")
                       == d.state_before.get("turn")):
                    n_sibling_retries += 1
                    j -= 1
                append_row(results, {
                    "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
                    "index": d.index, "decision_type": d.decision_type,
                    "decision_point": d.decision_point, "rep": rep,
                    "r_orig": traj.final_reward, "r_replay": r["reward"],
                    "dr": dr, "exact": dr == 0.0,
                    "n_retries": r["n_retries"], "n_give_ups": r["n_give_ups"],
                    "final_timed_out": r["final_timed_out"],
                    "n_decisions_replay": r["n_decisions"],
                    "n_decisions_suffix": len(traj.decisions) - d.index
                    + n_sibling_retries,
                    "replay_traj": r["trajectory_path"]})
                print(f"[replay] {traj.task_id} idx={d.index} rep={rep} "
                      f"dR={dr:+.2f}", flush=True)


def summarize(out: Path) -> dict:
    rows = load_rows(out / "replay_results.jsonl")
    clean = [r for r in rows if not r.get("final_timed_out")]
    abs_dr = sorted(abs(r["dr"]) for r in clean)
    n = len(abs_dr)
    def pct(p):
        return abs_dr[min(n - 1, int(p * n))] if n else None
    by_point, by_task = {}, {}
    for r in clean:
        by_point.setdefault(r["decision_point"], []).append(abs(r["dr"]))
        by_task.setdefault(r["task_id"], []).append(abs(r["dr"]))
    summary = {
        "n_replays": len(rows),
        "n_timed_out_excluded": len(rows) - n,
        "exact_rate": sum(r["exact"] for r in clean) / n if n else None,
        "mean_abs_dr": sum(abs_dr) / n if n else None,
        "max_abs_dr": abs_dr[-1] if n else None,
        "p95_abs_dr": pct(0.95),
        "noise_floor": abs_dr[-1] if n else None,  # pré-registrado: max|dR| sem timeouts
        "suffix_len_mismatches": sum(
            1 for r in clean if r["n_decisions_replay"] != r["n_decisions_suffix"]),
        "by_decision_point": {k: {"n": len(v), "exact": sum(x == 0 for x in v) / len(v),
                                  "mean_abs": sum(v) / len(v)} for k, v in by_point.items()},
        "by_task": {k: {"n": len(v), "exact": sum(x == 0 for x in v) / len(v)}
                    for k, v in sorted(by_task.items())},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/teste0")
    ap.add_argument("--points", type=int, default=3)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tasks-module", default="environment.tasks")
    ap.add_argument("--threshold", type=int, default=1200)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--task-chars", type=int, default=240)
    args = ap.parse_args()
    out = Path(args.out)
    tasks = importlib.import_module(args.tasks_module).TASKS
    harness_kw = {"summarize_threshold_tokens": args.threshold,
                  "max_turns": args.max_turns, "task_chars": args.task_chars}
    llm = LLMClient(max_tokens=1200)
    run_baselines(out, llm, tasks, harness_kw)
    run_null_replays(out, llm, args.points, args.reps)
    print(json.dumps(summarize(out), indent=2, ensure_ascii=False))
