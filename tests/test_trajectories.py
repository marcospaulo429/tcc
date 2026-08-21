import json
from pathlib import Path

import pytest

from trajectories.recorder import Recorder
from trajectories.schema import Decision, Trajectory, load_trajectory, save_trajectory


def _state(turn: int) -> dict:
    return {
        "messages": [{"role": "user", "content": f"turno {turn}"}],
        "workspace": {"main.py": "print('oi')"},
        "turn": turn,
        "context_tokens": 100 * turn,
    }


def test_round_trip(tmp_path: Path):
    traj = Trajectory(task_id="task-1", config={"model": "m", "temperature": 0.0, "seed": 42})
    specs = [
        ("model", "tool_call", {"action": "write_file", "path": "a.py", "content": "x = 1"}),
        ("harness", "context_policy", {"action": "summarize_context"}),
        ("model", "tool_call", {"action": "run_tests"}),
    ]
    for i, (dtype, dpoint, action) in enumerate(specs):
        dec = Decision(
            trajectory_id=traj.trajectory_id,
            index=i,
            decision_type=dtype,
            decision_point=dpoint,
            state_before=_state(i),
            available_actions=[action, {"action": "noop"}],
            chosen_action=action,
            observation={"ok": True, "i": i},
            costs={"prompt_tokens": 10 * (i + 1), "completion_tokens": i + 1, "wall_time_s": 0.5},
            t_start="2026-08-21T00:00:00+00:00",
            t_end="2026-08-21T00:00:01+00:00",
            parent_id=traj.decisions[-1].decision_id if traj.decisions else None,
        )
        traj.decisions.append(dec)
    traj.final_reward = 1.0
    traj.success = True
    traj.meta = {
        "started_at": "2026-08-21T00:00:00+00:00",
        "finished_at": "2026-08-21T00:01:00+00:00",
        "total_prompt_tokens": 60,
        "total_completion_tokens": 6,
    }

    path = tmp_path / "t.jsonl"
    save_trajectory(traj, path)
    loaded = load_trajectory(path)
    assert loaded.to_dict() == traj.to_dict()


def test_recorder_flow(tmp_path: Path):
    rec = Recorder(tmp_path)
    tid = rec.start("task-2", {"model": "m", "seed": 1})
    assert rec.trajectory is not None and rec.trajectory.trajectory_id == tid

    d1 = rec.record(
        "model",
        "tool_call",
        _state(0),
        [{"action": "write_file"}],
        {"action": "write_file", "path": "b.py", "content": ""},
    )
    rec.observe(d1, {"ok": True}, costs={"prompt_tokens": 100, "completion_tokens": 20})

    d2 = rec.record(
        "harness",
        "termination",
        _state(1),
        [{"action": "stop"}, {"action": "continue"}],
        {"action": "stop"},
        parent_id=d1,
    )
    rec.observe(d2, {"stopped": True}, costs={"prompt_tokens": 50, "completion_tokens": 5})

    path = rec.finish(final_reward=0.5, success=True)
    assert path == tmp_path / f"{tid}.jsonl"
    assert rec.trajectory is None

    lines = [json.loads(l) for l in path.read_text().splitlines()]
    assert lines[0]["kind"] == "trajectory"
    assert "decisions" not in lines[0]
    assert [l["kind"] for l in lines[1:]] == ["decision", "decision"]
    assert [l["index"] for l in lines[1:]] == [0, 1]
    assert lines[0]["meta"]["total_prompt_tokens"] == 150
    assert lines[0]["meta"]["total_completion_tokens"] == 25
    assert lines[2]["parent_id"] == d1

    loaded = load_trajectory(path)
    assert loaded.trajectory_id == tid
    assert len(loaded.decisions) == 2
    assert loaded.decisions[0].costs["prompt_tokens"] == 100
    assert loaded.decisions[0].costs["wall_time_s"] == 0.0  # merge preserva default
    assert loaded.decisions[0].t_end is not None


def test_start_twice_raises(tmp_path: Path):
    rec = Recorder(tmp_path)
    rec.start("task-3", {})
    with pytest.raises(RuntimeError):
        rec.start("task-4", {})
    rec.finish(final_reward=0.0, success=False)
    rec.start("task-4", {})  # após finish, pode abrir nova
