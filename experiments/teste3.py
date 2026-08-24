"""Teste 3 — Interação harness×modelo, I(H,M).

PRÉ-REGISTRO:
- I = C(H,M) − C(H) − C(M), com C(·) = R_orig − R_cf. Piso: noise_floor do Teste 0 v2.
- a′ é a alternativa ÚNICA amostrada do estado ORIGINAL do tool_call (do-operator);
  sob o contexto flipado dos turnos seguintes, o efeito de a′ pode ser incoerente —
  isso FAZ PARTE de I por construção, não é confound.
- by_direction = DOIS EXPERIMENTOS DISTINTOS (mesma limitação do Teste 1):
  confirmatória = keep_context->summarize_context; a outra direção é exploratória.
- Critério de sucesso: ≥1 ponto com |I| > piso NÃO-saturado na direção confirmatória,
  CONDICIONADO a 100% de exatidão nos replays nulos de fila (queue_floor_ok).
- Saturado = qualquer um de {r_cf_h, r_cf_m, r_cf_hm} ∈ {0.0, 1.0} (teto/piso da
  recompensa mascara interação); fora do critério, reportado à parte.
- Pontos elegíveis: turno t com (a) context_policy cujo flip é não-vácuo (mesma
  lógica do Teste 1, params do harness da trajetória) e (b) tool_call do MESMO
  turno sem retry.

Fases idempotentes (done_keys):
1. a′ → samples.jsonl (reusa de --samples-from quando existe; senão amostra);
2. nulos de fila → null_results.jsonl (fila [context_policy orig, tool_call orig];
   ΔR != 0 em qualquer ponto ⇒ queue_floor_ok=false, análise de I inválida);
3. 3 replays/ponto → cf_results.jsonl (C(H) flip singular; C(M) a′ singular;
   C(HM) fila [flip, a′]);
4. summary.json.
"""
import argparse
import json
import random
from pathlib import Path

from agent.harness import summarize_is_vacuous
from agent.llm import LLMClient
from interventions.model import sample_alternative
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories

SEED = 20260821
FLIP = {"keep_context": "summarize_context", "summarize_context": "keep_context"}
CONFIRMATORY_DIRECTION = "keep_context->summarize_context"


def sanitize(action: dict) -> dict:
    """Remove chaves não-canônicas de records ("forced") antes de reusar a ação."""
    return {k: v for k, v in action.items() if k != "forced"}


def eligible_pairs(traj, max_per_traj: int):
    """Pares (context_policy, tool_call) do mesmo turno: flip não-vácuo E sem retry."""
    h = traj.config["harness"]
    kw = {"keep_last": h.get("keep_last", 4), "task_chars": h.get("task_chars", 0),
          "summarizer": h.get("summarizer", "rule")}
    retry_turns = {d.state_before["turn"] for d in traj.decisions
                   if d.decision_point == "retry"}
    tc_by_turn = {d.state_before["turn"]: d for d in traj.decisions
                  if d.decision_point == "tool_call"}
    pairs = []
    for d in traj.decisions:
        if d.decision_point != "context_policy":
            continue
        t = d.state_before["turn"]
        if t in retry_turns or t not in tc_by_turn:
            continue
        if summarize_is_vacuous(d.state_before["messages"], **kw):
            continue
        pairs.append((d, tc_by_turn[t]))
    rng = random.Random(f"{SEED}:t3:{traj.trajectory_id}")
    if len(pairs) > max_per_traj:
        pairs = rng.sample(pairs, max_per_traj)
    return sorted(pairs, key=lambda p: p[0].index)


def _by_index(traj, index: int):
    return next(x for x in traj.decisions if x.index == index)


def run_sampling(baseline_dir: Path, out: Path, llm, max_per_traj: int,
                 samples_from: Path):
    samples_path = out / "samples.jsonl"
    done = done_keys(load_rows(samples_path), ("trajectory_id", "index"))
    # reuso de a′ do Teste 2 para o mesmo (trajectory_id, index do tool_call)
    reuse = {(r["trajectory_id"], r["index"]): r["sample"]
             for r in load_rows(samples_from) if r["sample"]["found"]}
    for traj in load_trajectories(baseline_dir):
        for cp, tc in eligible_pairs(traj, max_per_traj):
            if (traj.trajectory_id, tc.index) in done:
                continue
            orig = sanitize(tc.chosen_action)
            key = (traj.trajectory_id, tc.index)
            reused = key in reuse
            sample = reuse[key] if reused else \
                sample_alternative(llm, tc.state_before["messages"], orig)
            append_row(samples_path, {
                "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
                "index": tc.index, "cp_index": cp.index,
                "turn": tc.state_before["turn"],
                "original_action": orig, "reused": reused, "sample": sample})
            print(f"[sample] {traj.task_id} idx={tc.index} reused={reused} "
                  f"found={sample['found']}", flush=True)


def run_nulls(baseline_dir: Path, out: Path, llm):
    """Fila [context_policy ORIGINAL, tool_call ORIGINAL] a partir do context_policy;
    qualquer ΔR != 0 invalida a análise de I (queue_floor_ok=false), mas grava tudo."""
    results = out / "null_results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "cp_index"))
    trajs = {t.trajectory_id: t for t in load_trajectories(baseline_dir)}
    for s in load_rows(out / "samples.jsonl"):
        if (s["trajectory_id"], s["cp_index"]) in done:
            continue
        traj = trajs[s["trajectory_id"]]
        cp, tc = _by_index(traj, s["cp_index"]), _by_index(traj, s["index"])
        r = replay_from(traj, cp.index, llm, out / "replays", override_actions=[
            {"point": "context_policy", "action": sanitize(cp.chosen_action)},
            {"point": "tool_call", "action": sanitize(tc.chosen_action)}])
        dr = r["reward"] - traj.final_reward
        append_row(results, {
            "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
            "cp_index": cp.index, "index": tc.index,
            "r_orig": traj.final_reward, "r_replay": r["reward"],
            "dr": dr, "exact": dr == 0.0,
            "final_timed_out": r["final_timed_out"],
            "replay_traj": r["trajectory_path"]})
        print(f"[null] {traj.task_id} cp_idx={cp.index} dR={dr:+.2f}", flush=True)


def run_cf(baseline_dir: Path, out: Path, llm):
    results = out / "cf_results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "cp_index"))
    trajs = {t.trajectory_id: t for t in load_trajectories(baseline_dir)}
    for s in load_rows(out / "samples.jsonl"):
        if not s["sample"]["found"]:
            continue
        if (s["trajectory_id"], s["cp_index"]) in done:
            continue
        traj = trajs[s["trajectory_id"]]
        cp, tc = _by_index(traj, s["cp_index"]), _by_index(traj, s["index"])
        cp_chosen = sanitize(cp.chosen_action)["action"]
        flip = FLIP[cp_chosen]
        alt = s["sample"]["action"]
        r_h = replay_from(traj, cp.index, llm, out / "replays",
                          override_action={"action": flip})
        r_m = replay_from(traj, tc.index, llm, out / "replays",
                          override_action=alt)
        r_hm = replay_from(traj, cp.index, llm, out / "replays", override_actions=[
            {"point": "context_policy", "action": {"action": flip}},
            {"point": "tool_call", "action": alt}])
        r_orig = traj.final_reward
        c_h = r_orig - r_h["reward"]
        c_m = r_orig - r_m["reward"]
        c_hm = r_orig - r_hm["reward"]
        i_val = c_hm - c_h - c_m
        saturated = any(x in (0.0, 1.0) for x in
                        (r_h["reward"], r_m["reward"], r_hm["reward"]))
        append_row(results, {
            "task_id": traj.task_id, "trajectory_id": traj.trajectory_id,
            "cp_index": cp.index, "index": tc.index,
            "direction": f"{cp_chosen}->{flip}",
            "transition": f"{s['original_action']['action']}->{alt['action']}",
            "r_orig": r_orig, "r_cf_h": r_h["reward"], "r_cf_m": r_m["reward"],
            "r_cf_hm": r_hm["reward"],
            "C_H": c_h, "C_M": c_m, "C_HM": c_hm, "I": i_val,
            "saturated": saturated,
            "turn": cp.state_before["turn"],
            "context_tokens_before": cp.state_before["context_tokens"],
            "final_timed_out": any(x["final_timed_out"] for x in (r_h, r_m, r_hm)),
            "replay_trajs": {"h": r_h["trajectory_path"],
                             "m": r_m["trajectory_path"],
                             "hm": r_hm["trajectory_path"]}})
        print(f"[cf] {traj.task_id} cp_idx={cp.index} I={i_val:+.2f} "
              f"sat={saturated}", flush=True)


def summarize(out: Path, noise_floor: float) -> dict:
    samples = load_rows(out / "samples.jsonl")
    nulls = load_rows(out / "null_results.jsonl")
    rows = load_rows(out / "cf_results.jsonl")
    clean = [r for r in rows if not r.get("final_timed_out")]
    by_dir, by_task, turns = {}, {}, {}
    for r in clean:
        by_dir.setdefault(r["direction"], []).append(r)
        by_task.setdefault(r["task_id"], []).append(r["I"])
        turns[str(r["turn"])] = turns.get(str(r["turn"]), 0) + 1
    summary = {
        # condicionante pré-registrada: nulos de fila 100% exatos
        "queue_floor_ok": bool(nulls) and all(n["exact"] for n in nulls),
        "n_null_replays": len(nulls),
        "n_null_inexact": sum(not n["exact"] for n in nulls),
        "n_points_sampled": len(samples),
        "n_no_alternative": sum(1 for s in samples if not s["sample"]["found"]),
        "n_counterfactuals": len(rows),
        "n_timed_out_excluded": len(rows) - len(clean),
        "noise_floor": noise_floor,
        "confirmatory_direction": CONFIRMATORY_DIRECTION,
        # dois experimentos distintos — nunca agregar direções
        "by_direction": {k: {
            "n": len(v),
            "n_saturated": sum(r["saturated"] for r in v),
            "I_values": [r["I"] for r in v],
            "n_above_floor_nonsaturated": sum(
                abs(r["I"]) > noise_floor and not r["saturated"] for r in v),
        } for k, v in sorted(by_dir.items())},
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
    ap.add_argument("--out", default="runs/teste3_v2")
    ap.add_argument("--max-per-traj", type=int, default=2)
    ap.add_argument("--samples-from", default="runs/teste2_v2/samples.jsonl")
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
    run_sampling(baseline, out, llm, args.max_per_traj, Path(args.samples_from))
    run_nulls(baseline, out, llm)
    run_cf(baseline, out, llm)
    print(json.dumps(summarize(out, floor), indent=2, ensure_ascii=False))
