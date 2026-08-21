"""Teste 1 — Sinal causal do harness.

Hipótese: trocar summarize_context ↔ keep_context em UM ponto produz C(d) = R_orig − R_cf
distinguível do piso de ruído do Teste 0.
Variável manipulada: só a decisão context_policy no ponto; resto ao vivo.
Baseline: distribuição de |ΔR| sob intervenção nula (summary.json do Teste 0).
Riscos mapeados: confound de comprimento de contexto (registramos tokens antes/depois),
pontos não aleatórios (amostragem uniforme seedada entre os elegíveis), task dominante
(reporte por task).

LIMITAÇÕES DE DESENHO (reportar junto com os resultados, nunca agregar direções):
- Assimetria estrutural (I1): após forçar summarize→keep, o harness determinístico pode
  re-decidir summarize no turno seguinte — essa direção mede "summarize adiado 1 turno".
  A direção keep→summarize tende a persistir (contexto cai abaixo do threshold).
- Viés de seleção (I2): o filtro não-vácuo seleciona turnos tardios/episódios longos, e a
  direção do flip é determinada por context_tokens (confound perfeito direção×contexto).
  by_direction são dois experimentos distintos.
Piso de detecção pré-registrado: noise_floor = max|ΔR| do Teste 0 (sem timeouts).
"""
import argparse
import json
import random
from pathlib import Path

from agent.harness import summarize_is_vacuous
from agent.llm import LLMClient
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories

SEED = 20260821
FLIP = {"keep_context": "summarize_context", "summarize_context": "keep_context"}


def eligible_points(traj, max_per_traj: int):
    """context_policy onde o flip NÃO é vácuo (summarize teria efeito real)."""
    points = [d for d in traj.decisions
              if d.decision_point == "context_policy"
              and not summarize_is_vacuous(d.state_before["messages"])]
    rng = random.Random(f"{SEED}:t1:{traj.trajectory_id}")
    if len(points) > max_per_traj:
        points = rng.sample(points, max_per_traj)
    return sorted(points, key=lambda d: d.index)


def run(baseline_dir: Path, out: Path, llm: LLMClient, max_per_traj: int, reps: int):
    results = out / "cf_results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "index", "rep"))
    for traj in load_trajectories(baseline_dir):
        for d in eligible_points(traj, max_per_traj):
            chosen = d.chosen_action["action"]
            forced = FLIP[chosen]
            for rep in range(reps):
                if (traj.trajectory_id, d.index, rep) in done:
                    continue
                r = replay_from(traj, d.index, llm, out / "replays",
                                override_action={"action": forced})
                c = traj.final_reward - r["reward"]
                append_row(results, {
                    "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
                    "index": d.index, "rep": rep,
                    "chosen": chosen, "forced": forced,
                    "r_orig": traj.final_reward, "r_cf": r["reward"], "C": c,
                    "context_tokens_before": d.state_before["context_tokens"],
                    "n_messages_before": len(d.state_before["messages"]),
                    "turn": d.state_before["turn"],
                    "n_retries": r["n_retries"], "n_give_ups": r["n_give_ups"],
                    "final_timed_out": r["final_timed_out"],
                    "replay_traj": r["trajectory_path"]})
                print(f"[cf] {traj.task_id} idx={d.index} {chosen}->{forced} "
                      f"C={c:+.2f}", flush=True)


def summarize(out: Path, noise_floor: float) -> dict:
    rows = load_rows(out / "cf_results.jsonl")
    clean = [r for r in rows if not r.get("final_timed_out")]
    n = len(clean)
    abs_c = [abs(r["C"]) for r in clean]
    above = [r for r in clean if abs(r["C"]) > noise_floor]
    by_dir, by_task = {}, {}
    for r in clean:
        by_dir.setdefault(f"{r['chosen']}->{r['forced']}", []).append(r["C"])
        by_task.setdefault(r["task_id"], []).append(r["C"])
    summary = {
        "n_counterfactuals": len(rows),
        "n_timed_out_excluded": len(rows) - n,
        "noise_floor": noise_floor,
        "frac_above_floor": len(above) / n if n else None,
        "mean_C": sum(r["C"] for r in clean) / n if n else None,
        "mean_abs_C": sum(abs_c) / n if n else None,
        "by_direction": {k: {"n": len(v), "mean_C": sum(v) / len(v),
                             "frac_nonzero": sum(x != 0 for x in v) / len(v)}
                         for k, v in by_dir.items()},
        "by_task": {k: {"n": len(v), "mean_C": sum(v) / len(v),
                        "n_above_floor": sum(abs(x) > noise_floor for x in v)}
                    for k, v in sorted(by_task.items())},
        "points_above_floor": [{"task_id": r["task_id"], "index": r["index"],
                                "dir": f"{r['chosen']}->{r['forced']}", "C": r["C"]}
                               for r in above],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="runs/teste0/baseline")
    ap.add_argument("--out", default="runs/teste1")
    ap.add_argument("--max-per-traj", type=int, default=2)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--noise-floor", type=float, default=None,
                    help="default: lê noise_floor (max|dR|) de runs/teste0/summary.json")
    args = ap.parse_args()
    floor = args.noise_floor
    if floor is None:
        floor = json.loads(Path("runs/teste0/summary.json").read_text())["noise_floor"]
    out = Path(args.out)
    llm = LLMClient(max_tokens=1200)
    run(Path(args.baseline), out, llm, args.max_per_traj, args.reps)
    print(json.dumps(summarize(out, floor), indent=2, ensure_ascii=False))
