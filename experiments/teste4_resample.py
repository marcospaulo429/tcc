"""Teste 4 — Sensibilidade de re-amostragem de a′ (pré-registro 21, P4.1).

PRÉ-REGISTRO (PLANO-EXECUCAO.md, item 21, commit e7fb544 ANTES de rodar):
- População: as 56 instâncias reward-pivotais do census 4B (teste3_{g450,g600,g900,mt6}),
  pivotal = ¬timed_out ∧ (C_H≠0 ∨ C_M≠0 ∨ C_HM≠0).
- Para cada instância, re-amostra a′ com o MESMO procedimento de interventions/model.py
  (temp 0.8, primeira ação válida ≠ original) sob 3 schedules disjuntos pré-fixados:
  (3001–3008), (4001–4008), (5001–5008). Cada a′ encontrada custa 2 replays (M e HM);
  C_H não depende de a′ e é reusado do census. Sem schedules extras em caso de falha.
- Par (instância, a′) INFORMATIVO se C_H≠0 ∨ C_M(a′)≠0 ∨ C_HM(a′)≠0.
- Desfechos sobre pares informativos de SLACK (g450/g600/g900):
  s1 estável: taxa de screening exato (C_HM==C_M) ≥ 0.90;
  s2 parcial: 0.75–0.90; s3 frágil: < 0.75.
- Secundários (descritivos): persistência das 3 quebras de mt6; fração de a′ ≠ a′
  publicado; taxa de "sem alternativa" por schedule.
- Piso: coberto pelos nulos já medidos nas mesmas configs (queue_floor_ok em todos
  os teste3_*); teste0 não é re-rodado.
"""
import argparse
import json
import random
from pathlib import Path

from agent.llm import LLMClient
from interventions.model import _canonical, sample_alternative
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories
from .teste3 import _by_index, sanitize

SCHEDULES = {
    "s3000": tuple(range(3001, 3009)),
    "s4000": tuple(range(4001, 4009)),
    "s5000": tuple(range(5001, 5009)),
}
SLACK = ("g450", "g600", "g900")
CONFIGS = ("g450", "g600", "g900", "mt6")
BOOT_SEED = 20260824


def pivotal_rows(t3_dir: Path) -> list[dict]:
    rows = load_rows(t3_dir / "cf_results.jsonl")
    return [r for r in rows if not r.get("final_timed_out")
            and any(x != 0 for x in (r["C_H"], r["C_M"], r["C_HM"]))]


def run_config(config: str, runs_dir: Path, out_root: Path, llm) -> None:
    t3 = runs_dir / f"teste3_{config}"
    baseline = runs_dir / f"teste0_{config}" / "baseline"
    out = out_root / config
    results = out / "results.jsonl"
    done = done_keys(load_rows(results),
                     ("trajectory_id", "cp_index", "schedule"))
    trajs = {t.trajectory_id: t for t in load_trajectories(baseline)}
    published = {(s["trajectory_id"], s["cp_index"]): s["sample"]
                 for s in load_rows(t3 / "samples.jsonl") if s["sample"]["found"]}
    for cf in pivotal_rows(t3):
        tid, cpi = cf["trajectory_id"], cf["cp_index"]
        traj = trajs[tid]
        cp, tc = _by_index(traj, cpi), _by_index(traj, cf["index"])
        orig = sanitize(tc.chosen_action)
        flip = cf["direction"].split("->")[1]
        pub_alt = published[(tid, cpi)]["action"]
        for sched, seeds in SCHEDULES.items():
            if (tid, cpi, sched) in done:
                continue
            base = {"config": config, "regime": "slack" if config in SLACK
                    else "pressure", "task_id": cf["task_id"],
                    "trajectory_id": tid, "cp_index": cpi, "index": cf["index"],
                    "schedule": sched, "direction": cf["direction"],
                    "C_H": cf["C_H"],
                    "published_screened": cf["C_HM"] == cf["C_M"]}
            sample = sample_alternative(llm, tc.state_before["messages"], orig,
                                        seeds=seeds)
            if not sample["found"]:
                append_row(results, {**base, "found": False,
                                     "n_tried": sample["n_tried"]})
                print(f"[t4:{config}] {cf['task_id']} cp={cpi} {sched} "
                      f"SEM ALTERNATIVA", flush=True)
                continue
            alt = sample["action"]
            r_m = replay_from(traj, tc.index, llm, out / "replays",
                              override_action=alt)
            r_hm = replay_from(traj, cpi, llm, out / "replays", override_actions=[
                {"point": "context_policy", "action": {"action": flip}},
                {"point": "tool_call", "action": alt}])
            r_orig = traj.final_reward
            c_m = r_orig - r_m["reward"]
            c_hm = r_orig - r_hm["reward"]
            screened = c_hm == c_m
            informative = any(x != 0 for x in (cf["C_H"], c_m, c_hm))
            append_row(results, {
                **base, "found": True, "seed": sample["seed"],
                "n_tried": sample["n_tried"],
                "same_as_published": _canonical(alt) == _canonical(pub_alt),
                "transition": f"{orig['action']}->{alt['action']}",
                "r_orig": r_orig, "r_cf_m": r_m["reward"],
                "r_cf_hm": r_hm["reward"], "C_M": c_m, "C_HM": c_hm,
                "I": c_hm - cf["C_H"] - c_m, "screened": screened,
                "informative": informative,
                "final_timed_out": r_m["final_timed_out"] or
                                   r_hm["final_timed_out"],
                "replay_trajs": {"m": r_m["trajectory_path"],
                                 "hm": r_hm["trajectory_path"]}})
            print(f"[t4:{config}] {cf['task_id']} cp={cpi} {sched} "
                  f"screened={screened} informativo={informative} "
                  f"novo_a'={not (_canonical(alt) == _canonical(pub_alt))}",
                  flush=True)


def _cluster_boot_ci(pairs: list[dict], n_boot: int = 10000) -> list[float]:
    """CI 95% da taxa de screening por bootstrap clusterizado por task."""
    by_task: dict[str, list[bool]] = {}
    for p in pairs:
        by_task.setdefault(p["task_id"], []).append(p["screened"])
    tasks = sorted(by_task)
    rng = random.Random(BOOT_SEED)
    rates = []
    for _ in range(n_boot):
        sel = [by_task[rng.choice(tasks)] for _ in tasks]
        flat = [x for grp in sel for x in grp]
        rates.append(sum(flat) / len(flat))
    rates.sort()
    return [rates[int(0.025 * n_boot)], rates[int(0.975 * n_boot)]]


def summarize(out_root: Path) -> dict:
    rows = [r for c in CONFIGS
            for r in load_rows(out_root / c / "results.jsonl")]
    found = [r for r in rows if r["found"] and not r.get("final_timed_out")]
    info = [r for r in found if r["informative"]]
    slack_info = [r for r in info if r["regime"] == "slack"]
    n_scr = sum(r["screened"] for r in slack_info)
    rate = n_scr / len(slack_info) if slack_info else None
    outcome = None
    if rate is not None:
        outcome = ("s1_estavel" if rate >= 0.90 else
                   "s2_parcial" if rate >= 0.75 else "s3_fragil")
    tasks_slack: dict[str, list[bool]] = {}
    for r in slack_info:
        tasks_slack.setdefault(r["task_id"], []).append(r["screened"])
    # secundário: persistência das quebras publicadas de mt6
    mt6_breaks = [r for r in info if r["config"] == "mt6"
                  and not r["published_screened"]]
    summary = {
        "n_rows": len(rows),
        "n_no_alternative": sum(1 for r in rows if not r["found"]),
        "no_alternative_by_schedule": {
            s: sum(1 for r in rows if r["schedule"] == s and not r["found"])
            for s in SCHEDULES},
        "n_timed_out_excluded": sum(1 for r in rows
                                    if r["found"] and r.get("final_timed_out")),
        "n_found": len(found),
        "n_informative": len(info),
        "frac_new_alternative": (sum(not r["same_as_published"] for r in found)
                                 / len(found)) if found else None,
        "slack": {
            "n_informative_pairs": len(slack_info),
            "n_screened": n_scr,
            "screening_rate": rate,
            "ci95_cluster_task": _cluster_boot_ci(slack_info)
                                 if slack_info else None,
            "outcome_preregistrado": outcome,
            "by_task": {k: {"n": len(v), "screened": sum(v)}
                        for k, v in sorted(tasks_slack.items())},
            "non_screened_pairs": [
                {k: r[k] for k in ("config", "task_id", "cp_index", "schedule",
                                   "C_H", "C_M", "C_HM", "I", "transition")}
                for r in slack_info if not r["screened"]],
        },
        "mt6": {
            "n_informative_pairs": len([r for r in info
                                        if r["config"] == "mt6"]),
            "n_screened": sum(r["screened"] for r in info
                              if r["config"] == "mt6"),
            "published_break_points_redrawn": [
                {k: r[k] for k in ("task_id", "cp_index", "schedule",
                                   "screened", "C_M", "C_HM", "I")}
                for r in mt6_breaks],
        },
    }
    (out_root / "summary.json").parent.mkdir(parents=True, exist_ok=True)
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", default="runs/teste4_resample")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()
    out_root = Path(args.out)
    if not args.summary_only:
        llm = LLMClient(max_tokens=1200)
        for config in CONFIGS:
            run_config(config, Path(args.runs_dir), out_root, llm)
    print(json.dumps(summarize(out_root), indent=2, ensure_ascii=False))
