"""Teste 6 — Estimando alternativo a′ₛ: amostragem do estado SUMARIZADO (pré-reg 26, P4.2).

PRÉ-REGISTRO (PLANO-EXECUCAO.md, item 26, commitado ANTES de rodar):
- População: instâncias reward-pivotais do census 4B (teste3_{g450,g600,g900,mt6})
  com direção keep_context->summarize_context (a crítica do estimando só se
  aplica a essas; nos flips de restauração o a′ publicado já vem do estado pobre).
- a′ₛ amostrado de msgs_s = summarize_messages(state_before, keep_last, task_chars)
  — o estado que o modelo veria sob o flip h′ — com o MESMO procedimento de
  interventions/model.py, schedule único (7001–7008), sem extras.
- 2 replays por a′ₛ (braços M e HM); C_H reusado do census.
- Desfechos sobre pares informativos de SLACK: s1 screening ≥0.90 (objeção do
  estimando morre) / s2 0.75–0.90 / s3 <0.75 (headline parcialmente construído
  pelo estimando — reescopar, equally reportable).
- Secundários: quebras de mt6 sob a′ₛ; taxa de "sem alternativa"; a′ₛ ≠ a′ público.
"""
import argparse
import json
import random
from pathlib import Path

from agent.harness import summarize_messages
from agent.llm import LLMClient
from interventions.model import _canonical, sample_alternative
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories
from .teste3 import _by_index, sanitize
from .teste4_resample import _cluster_boot_ci, pivotal_rows

SEEDS = tuple(range(7001, 7009))
SLACK = ("g450", "g600", "g900")
CONFIGS = ("g450", "g600", "g900", "mt6")
DIRECTION = "keep_context->summarize_context"


def run_config(config: str, runs_dir: Path, out_root: Path, llm) -> None:
    t3 = runs_dir / f"teste3_{config}"
    baseline = runs_dir / f"teste0_{config}" / "baseline"
    out = out_root / config
    results = out / "results.jsonl"
    done = done_keys(load_rows(results), ("trajectory_id", "cp_index"))
    trajs = {t.trajectory_id: t for t in load_trajectories(baseline)}
    published = {(s["trajectory_id"], s["cp_index"]): s["sample"]
                 for s in load_rows(t3 / "samples.jsonl") if s["sample"]["found"]}
    for cf in pivotal_rows(t3):
        if cf["direction"] != DIRECTION:
            continue
        tid, cpi = cf["trajectory_id"], cf["cp_index"]
        if (tid, cpi) in done:
            continue
        traj = trajs[tid]
        cp, tc = _by_index(traj, cpi), _by_index(traj, cf["index"])
        orig = sanitize(tc.chosen_action)
        h = traj.config["harness"]
        msgs_s = summarize_messages(cp.state_before["messages"],
                                    h.get("keep_last", 4),
                                    h.get("task_chars", 0))
        base = {"config": config,
                "regime": "slack" if config in SLACK else "pressure",
                "task_id": cf["task_id"], "trajectory_id": tid,
                "cp_index": cpi, "index": cf["index"],
                "direction": cf["direction"], "C_H": cf["C_H"],
                "published_screened": cf["C_HM"] == cf["C_M"]}
        sample = sample_alternative(llm, msgs_s, orig, seeds=SEEDS)
        if not sample["found"]:
            append_row(results, {**base, "found": False,
                                 "n_tried": sample["n_tried"]})
            print(f"[t6:{config}] {cf['task_id']} cp={cpi} SEM ALTERNATIVA",
                  flush=True)
            continue
        alt = sample["action"]
        pub = published.get((tid, cpi))
        r_m = replay_from(traj, tc.index, llm, out / "replays",
                          override_action=alt)
        r_hm = replay_from(traj, cpi, llm, out / "replays", override_actions=[
            {"point": "context_policy",
             "action": {"action": "summarize_context"}},
            {"point": "tool_call", "action": alt}])
        r_orig = traj.final_reward
        c_m = r_orig - r_m["reward"]
        c_hm = r_orig - r_hm["reward"]
        screened = c_hm == c_m
        informative = any(x != 0 for x in (cf["C_H"], c_m, c_hm))
        append_row(results, {
            **base, "found": True, "seed": sample["seed"],
            "n_tried": sample["n_tried"],
            "same_as_published": bool(pub) and
                                 _canonical(alt) == _canonical(pub["action"]),
            "transition": f"{orig['action']}->{alt['action']}",
            "r_orig": r_orig, "r_cf_m": r_m["reward"],
            "r_cf_hm": r_hm["reward"], "C_M": c_m, "C_HM": c_hm,
            "I": c_hm - cf["C_H"] - c_m, "screened": screened,
            "informative": informative,
            "final_timed_out": r_m["final_timed_out"] or
                               r_hm["final_timed_out"],
            "replay_trajs": {"m": r_m["trajectory_path"],
                             "hm": r_hm["trajectory_path"]}})
        print(f"[t6:{config}] {cf['task_id']} cp={cpi} screened={screened} "
              f"informativo={informative}", flush=True)


def summarize(out_root: Path) -> dict:
    rows = [r for c in CONFIGS for r in load_rows(out_root / c / "results.jsonl")]
    found = [r for r in rows if r.get("found")]
    ok = [r for r in found if not r["final_timed_out"]]
    info_slack = [r for r in ok if r["regime"] == "slack" and r["informative"]]
    n_scr = sum(r["screened"] for r in info_slack)
    rate = n_scr / len(info_slack) if info_slack else None
    outcome = None
    if rate is not None:
        outcome = "s1" if rate >= 0.90 else ("s2" if rate >= 0.75 else "s3")
    mt6 = [r for r in ok if r["config"] == "mt6"]
    summary = {
        "pre_registro": 26,
        "n_instancias": len(rows), "n_sem_alternativa": len(rows) - len(found),
        "n_timed_out": len(found) - len(ok),
        "slack_informativos": len(info_slack),
        "slack_screened": n_scr,
        "slack_rate": rate,
        "slack_ci95_cluster_task": _cluster_boot_ci(info_slack)
        if info_slack else None,
        "novo_vs_publicado": sum(not r["same_as_published"] for r in ok),
        "mt6": [{"task_id": r["task_id"], "cp_index": r["cp_index"],
                 "published_screened": r["published_screened"],
                 "screened": r["screened"], "C_M": r["C_M"],
                 "C_HM": r["C_HM"]} for r in mt6],
        "outcome": outcome,
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Teste 6: estimando a'_s (pré-reg 26)")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", default="runs/teste6_estimando")
    args = ap.parse_args()
    runs_dir, out_root = Path(args.runs_dir), Path(args.out)
    llm = LLMClient()
    for config in CONFIGS:
        run_config(config, runs_dir, out_root, llm)
    print(json.dumps(summarize(out_root), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
