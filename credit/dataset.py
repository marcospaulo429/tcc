"""A4 (PLANO-EXECUCAO.md) — consolida counterfactuals dos Testes 1/2/3 de múltiplas
configs num JSONL único para treinar o critic (Fase B).

Cada linha: identificação (quantity/config/task/estrato), target (value, r_orig,
saturated, excluded_timeout), features_pre (computáveis ANTES da decisão — P8) e
features_post (só análise).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from environment.tasks_all import STRATA as _STRATA_ALL
from environment.tasks_mbpp import STRATA as _STRATA_MBPP
from trajectories.schema import Trajectory, load_trajectory

STRATA = _STRATA_ALL | _STRATA_MBPP  # task_ids não colidem entre os ambientes

DEFAULT_MAX_TURNS = 12

# (subdir do teste, nome da quantity, campo do target)
SOURCES = (("teste1", "C_H", "C"), ("teste2", "C_M", "C"), ("teste3", "I", "I"))

PRE_KEYS = ("turn", "context_tokens_before", "n_messages_before", "decision_point",
            "action_type", "tests_passed_so_far", "tests_total_so_far",
            "n_writes_so_far", "frac_turns_elapsed")


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _load_baselines(baseline_dir: Path) -> dict[str, Trajectory]:
    trajs: dict[str, Trajectory] = {}
    for p in sorted(baseline_dir.glob("*.jsonl")):
        t = load_trajectory(p)
        trajs[t.trajectory_id] = t
    return trajs


def _features_pre(traj: Trajectory, index: int) -> dict | None:
    """Features do estado da decisão `index` na trajetória baseline (só passado)."""
    d = next((x for x in traj.decisions if x.index == index), None)
    if d is None:
        return None
    passed, total, n_writes = 0, 0, 0
    for prev in traj.decisions:
        if prev.index >= index or prev.decision_point != "tool_call":
            continue
        obs = prev.observation
        if isinstance(obs, dict) and "passed" in obs:
            passed, total = obs.get("passed", 0), obs.get("total", 0)
        if prev.chosen_action.get("action") == "write_file":
            n_writes += 1
    max_turns = traj.config.get("harness", {}).get("max_turns", DEFAULT_MAX_TURNS)
    turn = d.state_before.get("turn")
    return {
        "turn": turn,
        "context_tokens_before": d.state_before.get("context_tokens"),
        "n_messages_before": len(d.state_before.get("messages", [])),
        "decision_point": d.decision_point,
        "action_type": d.chosen_action.get("action"),
        "tests_passed_so_far": passed,
        "tests_total_so_far": total,
        "n_writes_so_far": n_writes,
        "frac_turns_elapsed": turn / max_turns if turn is not None else None,
    }


def _null_features() -> dict:
    return {k: None for k in PRE_KEYS}


def _make_record(quantity: str, value_field: str, row: dict, tag: str,
                 threshold: int | float | None, noise_floor: float | None,
                 trajs: dict[str, Trajectory]) -> tuple[dict, bool]:
    """Retorna (record, missing_traj)."""
    # teste3: features_pre ancoradas na decisão context_policy (cp_index)
    join_index = row["cp_index"] if quantity == "I" else row["index"]
    traj = trajs.get(row["trajectory_id"])
    feats = _features_pre(traj, join_index) if traj is not None else None
    missing_traj = feats is None
    if missing_traj:
        feats = _null_features()
    if quantity == "I":
        saturated = bool(row.get("saturated", False))
        post = {"content_diff_chars": None,
                "direction": row.get("direction"),
                "transition": row.get("transition"),
                "r_cf_h": row.get("r_cf_h"), "r_cf_m": row.get("r_cf_m"),
                "r_cf_hm": row.get("r_cf_hm")}
    else:
        saturated = False
        post = {"content_diff_chars": row.get("content_diff_chars"),
                "direction": None,
                "transition": row.get("transition"),
                "r_cf": row.get("r_cf")}
    rec = {
        "quantity": quantity,
        "config_tag": tag,
        "threshold": threshold,
        "task_id": row["task_id"],
        "trajectory_id": row["trajectory_id"],
        "decision_index": row["index"],
        "turn": row.get("turn"),
        "stratum": STRATA.get(row["task_id"], "V1"),
        "noise_floor": noise_floor,
        "value": row[value_field],
        "r_orig": row.get("r_orig"),
        "saturated": saturated,
        "excluded_timeout": bool(row.get("final_timed_out", False)),
        "features_pre": feats,
        "features_post": post,
    }
    return rec, missing_traj


def build_dataset(configs: list[dict], out_path: str | Path) -> dict:
    """configs = [{"tag": "g600", "threshold": 600, "runs_dir": "runs"}, ...].
    Lê runs/teste{1,2,3}_<tag>/cf_results.jsonl + runs/teste0_<tag>/{baseline,summary.json}.
    Grava JSONL consolidado em out_path e retorna dict-resumo (contagens por
    quantity/estrato/config). Tolerante a arquivos ausentes (config incompleta →
    inclui o que houver, conta em "missing")."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary: dict = {"n_rows": 0, "by_quantity": {}, "by_stratum": {},
                     "by_config": {}, "missing": {}, "missing_traj": 0}
    with out_path.open("w", encoding="utf-8") as f:
        for cfg in configs:
            tag, threshold = cfg["tag"], cfg.get("threshold")
            runs = Path(cfg.get("runs_dir", "runs"))
            missing: list[str] = []
            noise_floor = None
            summary_path = runs / f"teste0_{tag}" / "summary.json"
            if summary_path.exists():
                noise_floor = json.loads(
                    summary_path.read_text(encoding="utf-8")).get("noise_floor")
            else:
                missing.append(str(summary_path))
            baseline_dir = runs / f"teste0_{tag}" / "baseline"
            trajs = _load_baselines(baseline_dir) if baseline_dir.is_dir() else {}
            if not baseline_dir.is_dir():
                missing.append(str(baseline_dir))
            for teste, quantity, value_field in SOURCES:
                path = runs / f"{teste}_{tag}" / "cf_results.jsonl"
                if not path.exists():
                    missing.append(str(path))
                    continue
                for row in _load_rows(path):
                    rec, missing_traj = _make_record(
                        quantity, value_field, row, tag, threshold,
                        noise_floor, trajs)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    summary["n_rows"] += 1
                    summary["missing_traj"] += missing_traj
                    for key, val in (("by_quantity", quantity),
                                     ("by_stratum", rec["stratum"]),
                                     ("by_config", tag)):
                        summary[key][val] = summary[key].get(val, 0) + 1
            summary["missing"][tag] = missing
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tags", nargs="+", required=True)
    ap.add_argument("--thresholds", nargs="+", type=int, required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if len(args.tags) != len(args.thresholds):
        ap.error("--tags e --thresholds devem ter o mesmo comprimento")
    configs = [{"tag": t, "threshold": th, "runs_dir": args.runs_dir}
               for t, th in zip(args.tags, args.thresholds)]
    print(json.dumps(build_dataset(configs, args.out), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
