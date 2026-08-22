"""Teste 2 — Sinal causal do modelo, C(model).

PRÉ-REGISTRO:
- Variável manipulada: SÓ a ação do modelo (tool_call) no ponto — do-operator com
  frozen policy à la C3: a ação forçada substitui a decisão, o resto re-decide ao vivo.
- Métrica: C = R_orig − R_cf. Piso de detecção: noise_floor do Teste 0 v2
  (max|ΔR| de replays nulos sem timeout).
- ANÁLISE PRIMÁRIA POR TRANSIÇÃO (write_file→write_file, write_file→run_tests, ...):
  transições diferentes são manipulações qualitativamente diferentes; NUNCA
  interpretar mean_C agregado entre transições.
- Exclusões pré-registradas: (a) replays com timeout de infra (final_timed_out);
  (b) pontos tool_call de turno que teve retry/give_up — o state_before gravado não
  corresponde à primeira chamada do modelo no turno; (c) pontos sem a′ válida em
  8 seeds (contados e reportados, nunca substituídos).

Fases idempotentes (done_keys):
1. amostragem de a′ → samples.jsonl (persistida ANTES de qualquer replay;
   resume nunca re-amostra);
2. replays counterfactuais → cf_results.jsonl (só found=True);
3. summary.json.
"""
import argparse
import difflib
import json
import random
from pathlib import Path

from agent.llm import LLMClient
from interventions.model import sample_alternative
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories

SEED = 20260821


def sanitize(action: dict) -> dict:
    """Remove chaves não-canônicas de records ("forced") antes de reusar a ação."""
    return {k: v for k, v in action.items() if k != "forced"}


def retry_turns(traj) -> set:
    return {d.state_before["turn"] for d in traj.decisions
            if d.decision_point == "retry"}


def eligible_points(traj, max_per_traj: int):
    """tool_call SEM decisão retry no mesmo turno da mesma trajetória,
    amostrados uniformemente com rng seedada por trajetória."""
    excluded = retry_turns(traj)
    points = [d for d in traj.decisions
              if d.decision_point == "tool_call"
              and d.state_before["turn"] not in excluded]
    rng = random.Random(f"{SEED}:t2:{traj.trajectory_id}")
    if len(points) > max_per_traj:
        points = rng.sample(points, max_per_traj)
    return sorted(points, key=lambda d: d.index)


def content_diff_lines(orig: dict, alt: dict) -> int | None:
    """write_file→write_file: nº de linhas do unified_diff dos contents; senão None."""
    if orig.get("action") == "write_file" and alt.get("action") == "write_file":
        return len(list(difflib.unified_diff(orig["content"].splitlines(),
                                             alt["content"].splitlines())))
    return None


def run_sampling(baseline_dir: Path, out: Path, llm, max_per_traj: int):
    samples_path = out / "samples.jsonl"
    done = done_keys(load_rows(samples_path), ("trajectory_id", "index"))
    for traj in load_trajectories(baseline_dir):
        for d in eligible_points(traj, max_per_traj):
            if (traj.trajectory_id, d.index) in done:
                continue
            orig = sanitize(d.chosen_action)
            sample = sample_alternative(llm, d.state_before["messages"], orig)
            append_row(samples_path, {
                "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
                "index": d.index, "turn": d.state_before["turn"],
                "original_action": orig, "sample": sample})
            print(f"[sample] {traj.task_id} idx={d.index} "
                  f"found={sample['found']} n_tried={sample['n_tried']}", flush=True)


def run_replays(baseline_dir: Path, out: Path, llm):
    results = out / "cf_results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "index"))
    trajs = {t.trajectory_id: t for t in load_trajectories(baseline_dir)}
    for s in load_rows(out / "samples.jsonl"):
        if not s["sample"]["found"]:
            continue
        if (s["trajectory_id"], s["index"]) in done:
            continue
        traj = trajs[s["trajectory_id"]]
        d = next(x for x in traj.decisions if x.index == s["index"])
        orig, alt = s["original_action"], s["sample"]["action"]
        r = replay_from(traj, d.index, llm, out / "replays", override_action=alt)
        c = traj.final_reward - r["reward"]
        transition = f"{orig['action']}->{alt['action']}"
        append_row(results, {
            "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
            "index": d.index, "chosen": orig["action"], "forced": alt["action"],
            "transition": transition,
            "content_diff_chars": content_diff_lines(orig, alt),
            "r_orig": traj.final_reward, "r_cf": r["reward"], "C": c,
            "context_tokens_before": d.state_before["context_tokens"],
            "n_messages_before": len(d.state_before["messages"]),
            "turn": d.state_before["turn"],
            "n_retries": r["n_retries"], "n_give_ups": r["n_give_ups"],
            "final_timed_out": r["final_timed_out"],
            "replay_traj": r["trajectory_path"]})
        print(f"[cf] {traj.task_id} idx={d.index} {transition} C={c:+.2f}", flush=True)


def summarize(baseline_dir: Path, out: Path, noise_floor: float) -> dict:
    samples = load_rows(out / "samples.jsonl")
    rows = load_rows(out / "cf_results.jsonl")
    clean = [r for r in rows if not r.get("final_timed_out")]
    n = len(clean)
    n_excluded_retry = sum(
        sum(1 for d in traj.decisions
            if d.decision_point == "tool_call"
            and d.state_before["turn"] in retry_turns(traj))
        for traj in load_trajectories(baseline_dir))
    by_transition, by_task, turns = {}, {}, {}
    for r in clean:
        by_transition.setdefault(r["transition"], []).append(r["C"])
        by_task.setdefault(r["task_id"], []).append(r["C"])
        turns[str(r["turn"])] = turns.get(str(r["turn"]), 0) + 1
    summary = {
        "n_points_sampled": len(samples),
        "n_no_alternative": sum(1 for s in samples if not s["sample"]["found"]),
        "n_excluded_retry": n_excluded_retry,
        "n_counterfactuals": len(rows),
        "n_timed_out_excluded": len(rows) - n,
        "noise_floor": noise_floor,
        "frac_above_floor": (sum(abs(r["C"]) > noise_floor for r in clean) / n
                             if n else None),
        # análise primária: POR TRANSIÇÃO (nunca interpretar mean_C agregado)
        "by_transition": {k: {
            "n": len(v),
            "frac_above_floor": sum(abs(x) > noise_floor for x in v) / len(v),
            "mean_abs_C": sum(abs(x) for x in v) / len(v),
            "max_abs_C": max(abs(x) for x in v),
        } for k, v in sorted(by_transition.items())},
        "by_task": {k: {"n": len(v),
                        "n_above_floor": sum(abs(x) > noise_floor for x in v)}
                    for k, v in sorted(by_task.items())},
        "turn_distribution": dict(sorted(turns.items())),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="runs/teste0_v2/baseline")
    ap.add_argument("--out", default="runs/teste2_v2")
    ap.add_argument("--max-per-traj", type=int, default=3)
    ap.add_argument("--noise-floor", type=float, default=None,
                    help="default: lê noise_floor (max|dR|) de --floor-from")
    ap.add_argument("--floor-from", default="runs/teste0_v2/summary.json")
    args = ap.parse_args()
    floor = args.noise_floor
    if floor is None:
        floor = json.loads(Path(args.floor_from).read_text())["noise_floor"]
    out = Path(args.out)
    baseline = Path(args.baseline)
    llm = LLMClient(max_tokens=1200)
    run_sampling(baseline, out, llm, args.max_per_traj)
    run_replays(baseline, out, llm)
    print(json.dumps(summarize(baseline, out, floor), indent=2, ensure_ascii=False))
