"""Testes do credit/dataset.py com fixtures sintéticas (nunca lê runs/ reais)."""
import json

import pytest

from credit.dataset import build_dataset
from trajectories.schema import Decision, Trajectory, save_trajectory

TAG = "g600"


def _dec(traj_id, index, point, turn, tokens, n_msgs, action, obs):
    return Decision(
        trajectory_id=traj_id, index=index, decision_type="harness",
        decision_point=point,
        state_before={"turn": turn, "context_tokens": tokens,
                      "messages": [{"role": "user", "content": "x"}] * n_msgs},
        chosen_action=action, observation=obs)


def _make_traj():
    traj = Trajectory(
        task_id="shift_cipher",
        config={"harness": {"summarize_threshold_tokens": 600, "max_turns": 12,
                            "keep_last": 4, "task_chars": 240}},
        final_reward=1.0, success=True)
    tid = traj.trajectory_id
    traj.decisions = [
        _dec(tid, 0, "context_policy", 0, 314, 2, {"action": "keep_context"},
             {"messages_before": 2, "messages_after": 2}),
        _dec(tid, 1, "tool_call", 0, 320, 2, {"action": "write_file",
             "path": "sol.py", "content": "x = 1\n"}, {"ok": True}),
        _dec(tid, 2, "termination", 0, 330, 3, {"action": "continue"},
             {"turn": 0, "tests_passed": False}),
        _dec(tid, 3, "context_policy", 1, 499, 4, {"action": "keep_context"},
             {"messages_before": 4, "messages_after": 4}),
        _dec(tid, 4, "tool_call", 1, 505, 4, {"action": "run_tests"},
             {"passed": 3, "failed": 5, "errors": 0, "total": 8}),
        _dec(tid, 5, "termination", 1, 510, 5, {"action": "continue"},
             {"turn": 1, "tests_passed": False}),
        _dec(tid, 6, "context_policy", 2, 700, 6, {"action": "keep_context"},
             {"messages_before": 6, "messages_after": 6}),
        _dec(tid, 7, "tool_call", 2, 710, 6, {"action": "write_file",
             "path": "sol.py", "content": "x = 2\n"}, {"ok": True}),
    ]
    return traj


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


@pytest.fixture
def synthetic_runs(tmp_path):
    runs = tmp_path / "runs"
    traj = _make_traj()
    tid = traj.trajectory_id
    save_trajectory(traj, runs / f"teste0_{TAG}" / "baseline" / f"{tid}.jsonl")
    (runs / f"teste0_{TAG}" / "summary.json").write_text(
        json.dumps({"noise_floor": 0.05, "n_replays": 30}))
    _write_jsonl(runs / f"teste1_{TAG}" / "cf_results.jsonl", [
        {"task_id": "shift_cipher", "trajectory_id": tid, "index": 6, "rep": 0,
         "chosen": "keep_context", "forced": "summarize_context",
         "r_orig": 1.0, "r_cf": 0.25, "C": 0.75,
         "context_tokens_before": 700, "n_messages_before": 6, "turn": 2,
         "n_retries": 0, "n_give_ups": 0, "final_timed_out": False,
         "replay_traj": "x.jsonl"},
        {"task_id": "shift_cipher", "trajectory_id": tid, "index": 3, "rep": 0,
         "chosen": "keep_context", "forced": "summarize_context",
         "r_orig": 1.0, "r_cf": 1.0, "C": 0.0,
         "context_tokens_before": 499, "n_messages_before": 4, "turn": 1,
         "n_retries": 0, "n_give_ups": 0, "final_timed_out": True,
         "replay_traj": "y.jsonl"},
    ])
    _write_jsonl(runs / f"teste2_{TAG}" / "cf_results.jsonl", [
        {"task_id": "shift_cipher", "trajectory_id": tid, "index": 1,
         "chosen": "write_file", "forced": "write_file",
         "transition": "write_file->write_file", "content_diff_chars": 5,
         "r_orig": 1.0, "r_cf": 0.5, "C": 0.5,
         "context_tokens_before": 320, "n_messages_before": 2, "turn": 0,
         "n_retries": 0, "n_give_ups": 0, "final_timed_out": False,
         "replay_traj": "z.jsonl"},
        # trajetória baseline inexistente + task fora do STRATA → V1 + missing_traj
        {"task_id": "task_desconhecida", "trajectory_id": "nao_existe", "index": 0,
         "chosen": "write_file", "forced": "run_tests",
         "transition": "write_file->run_tests", "content_diff_chars": None,
         "r_orig": 0.5, "r_cf": 0.5, "C": 0.0,
         "context_tokens_before": 100, "n_messages_before": 2, "turn": 0,
         "n_retries": 0, "n_give_ups": 0, "final_timed_out": False,
         "replay_traj": "w.jsonl"},
    ])
    _write_jsonl(runs / f"teste3_{TAG}" / "cf_results.jsonl", [
        {"task_id": "shift_cipher", "trajectory_id": tid,
         "cp_index": 6, "index": 7,
         "direction": "keep_context->summarize_context",
         "transition": "write_file->write_file",
         "r_orig": 1.0, "r_cf_h": 0.25, "r_cf_m": 1.0, "r_cf_hm": 1.0,
         "C_H": 0.75, "C_M": 0.0, "C_HM": 0.0, "I": -0.75, "saturated": True,
         "turn": 2, "context_tokens_before": 700, "final_timed_out": False,
         "replay_trajs": {"h": "a", "m": "b", "hm": "c"}},
    ])
    return runs, tid


def _build(runs, out, tags_thresholds=((TAG, 600),)):
    configs = [{"tag": t, "threshold": th, "runs_dir": str(runs)}
               for t, th in tags_thresholds]
    return build_dataset(configs, out)


def _load(out):
    return [json.loads(line) for line in out.read_text().splitlines()]


def test_build_covers_three_quantities(synthetic_runs, tmp_path):
    runs, _ = synthetic_runs
    out = tmp_path / "dataset.jsonl"
    summary = _build(runs, out)
    rows = _load(out)
    assert summary["n_rows"] == len(rows) == 5
    assert summary["by_quantity"] == {"C_H": 2, "C_M": 2, "I": 1}
    assert summary["by_config"] == {TAG: 5}
    by_q = {}
    for r in rows:
        by_q.setdefault(r["quantity"], []).append(r)
    assert by_q["C_H"][0]["value"] == 0.75
    assert by_q["I"][0]["value"] == -0.75
    assert by_q["I"][0]["saturated"] is True
    assert by_q["C_H"][0]["saturated"] is False
    assert all(r["noise_floor"] == 0.05 for r in rows)
    assert all(r["config_tag"] == TAG and r["threshold"] == 600 for r in rows)


def test_features_pre_correct(synthetic_runs, tmp_path):
    runs, tid = synthetic_runs
    out = tmp_path / "dataset.jsonl"
    _build(runs, out)
    rows = _load(out)
    # teste1 no index 6 (turn 2): última run_tests anterior é idx 4 (3/8), 1 write
    r = next(x for x in rows if x["quantity"] == "C_H" and x["decision_index"] == 6)
    fp = r["features_pre"]
    assert fp["tests_passed_so_far"] == 3
    assert fp["tests_total_so_far"] == 8
    assert fp["n_writes_so_far"] == 1
    assert fp["turn"] == 2
    assert fp["context_tokens_before"] == 700
    assert fp["n_messages_before"] == 6
    assert fp["decision_point"] == "context_policy"
    assert fp["action_type"] == "keep_context"
    assert fp["frac_turns_elapsed"] == pytest.approx(2 / 12)
    # teste1 no index 3 (turn 1): nenhuma run_tests anterior
    r3 = next(x for x in rows if x["quantity"] == "C_H" and x["decision_index"] == 3)
    assert r3["features_pre"]["tests_passed_so_far"] == 0
    assert r3["features_pre"]["n_writes_so_far"] == 1
    # teste3 usa cp_index (6) para features_pre, decision_index = 7 (fonte)
    ri = next(x for x in rows if x["quantity"] == "I")
    assert ri["decision_index"] == 7
    assert ri["features_pre"]["decision_point"] == "context_policy"
    assert ri["features_pre"]["tests_passed_so_far"] == 3
    # features_post
    r2 = next(x for x in rows if x["quantity"] == "C_M" and x["decision_index"] == 1)
    assert r2["features_post"]["content_diff_chars"] == 5
    assert r2["features_post"]["transition"] == "write_file->write_file"
    assert r2["features_post"]["r_cf"] == 0.5
    assert ri["features_post"]["direction"] == "keep_context->summarize_context"
    assert ri["features_post"]["r_cf_hm"] == 1.0


def test_missing_config_tolerated(synthetic_runs, tmp_path):
    runs, _ = synthetic_runs
    out = tmp_path / "dataset.jsonl"
    summary = _build(runs, out, ((TAG, 600), ("g450", 450)))
    assert summary["by_config"] == {TAG: 5}
    assert "g450" not in summary["by_config"]
    assert len(summary["missing"]["g450"]) == 5  # summary, baseline e 3 cf_results
    assert summary["missing"][TAG] == []


def test_stratum_and_missing_traj(synthetic_runs, tmp_path):
    runs, _ = synthetic_runs
    out = tmp_path / "dataset.jsonl"
    summary = _build(runs, out)
    rows = _load(out)
    unknown = next(x for x in rows if x["task_id"] == "task_desconhecida")
    assert unknown["stratum"] == "V1"
    assert all(v is None for v in unknown["features_pre"].values())
    assert summary["missing_traj"] == 1
    known = next(x for x in rows if x["quantity"] == "I")
    assert known["stratum"] == "V2"
    assert summary["by_stratum"] == {"V2": 4, "V1": 1}


def test_excluded_timeout_propagated(synthetic_runs, tmp_path):
    runs, _ = synthetic_runs
    out = tmp_path / "dataset.jsonl"
    _build(runs, out)
    rows = _load(out)
    timed = next(x for x in rows if x["quantity"] == "C_H" and x["decision_index"] == 3)
    clean = next(x for x in rows if x["quantity"] == "C_H" and x["decision_index"] == 6)
    assert timed["excluded_timeout"] is True
    assert clean["excluded_timeout"] is False
