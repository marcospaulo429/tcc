"""Fila de forced actions (peek-match) e replay com fila — tudo com LLM fake, sem vLLM."""
import itertools
import json

import pytest

from agent.harness import Harness
from agent.loop import Episode
from environment.registry import resolve_task
from environment.sandbox import Sandbox
from environment.tasks import get_task
from trajectories.recorder import Recorder
from trajectories.replay import replay_from
from trajectories.schema import load_trajectory

RLE_SOLUTION = '''def rle_encode(s):
    if not s:
        return ""
    out, prev, count = [], s[0], 1
    for c in s[1:]:
        if c == prev:
            count += 1
        else:
            out.append(prev + str(count))
            prev, count = c, 1
    out.append(prev + str(count))
    return "".join(out)
'''

BAD_WRITE = {"action": "write_file", "path": "solution.py",
             "content": "def rle_encode(s):\n    return s\n"}


class FakeLLM:
    """Roteiro determinístico cíclico (mesmo padrão de test_loop_replay)."""

    def __init__(self, script):
        self._iter = itertools.cycle(script)

    def config(self):
        return {"model": "fake", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kwargs):
        return {"text": next(self._iter), "prompt_tokens": 10, "completion_tokens": 5,
                "wall_time_s": 0.0, "finish_reason": "stop"}


def make_script():
    good = json.dumps({"action": "write_file", "path": "solution.py",
                       "content": RLE_SOLUTION})
    return [json.dumps(BAD_WRITE), '{"action": "run_tests"}', good,
            '{"action": "run_tests"}', '{"action": "finish"}']


def run_baseline(tmp_path):
    task = get_task("rle_encode")
    ep = Episode(task, FakeLLM(make_script()), Harness(max_turns=8),
                 Recorder(tmp_path / "base"))
    result = ep.run()
    ep.sandbox.cleanup()
    return task, result


def resume_episode(traj, index, llm, out_dir, forced_actions):
    """Resume direto do Episode (sem o assert de primeiro-ponto do replay_from)."""
    d = traj.decisions[index]
    sandbox = Sandbox()
    sandbox.restore(d.state_before["workspace"])
    ep = Episode(resolve_task(traj.task_id), llm, Harness(**traj.config["harness"]),
                 Recorder(out_dir), sandbox)
    try:
        return ep.run(resume={
            "messages": d.state_before["messages"], "turn": d.state_before["turn"],
            "entry_point": d.decision_point, "forced_actions": forced_actions,
            "last_action": d.state_before.get("last_action"),
            "tests_passed": d.state_before.get("tests_passed", False)})
    finally:
        sandbox.cleanup()


def rotated_script(n):
    s = make_script()
    return s[n:] + s[:n]


def test_queue_of_two_consumed_in_order_no_leak(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    # fila [context_policy, tool_call] do turno 0; o tool_call forçado substitui a
    # 1ª chamada do modelo, então o script começa da 2ª ação
    r = replay_from(traj, 0, FakeLLM(rotated_script(1)), tmp_path / "replays",
                    override_actions=[
                        {"point": "context_policy", "action": {"action": "keep_context"}},
                        {"point": "tool_call", "action": BAD_WRITE}])
    assert r["reward"] == traj.final_reward
    rep = load_trajectory(r["trajectory_path"])
    assert rep.decisions[0].decision_point == "context_policy"
    assert rep.decisions[0].chosen_action["forced"] is True
    assert rep.decisions[1].decision_point == "tool_call"
    assert rep.decisions[1].chosen_action["forced"] is True
    # nada de "_point"/"forced" pode vazar para as mensagens do contexto
    for d in rep.decisions:
        for m in d.state_before["messages"]:
            content = m.get("content") or ""
            assert "_point" not in content
            assert '"forced"' not in content


def test_head_mismatch_waits_and_live_decision_runs(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    # head é tool_call mas entramos em context_policy: decisão ao vivo, head espera
    r = resume_episode(traj, 0, FakeLLM(rotated_script(1)), tmp_path / "replays",
                       [{"point": "tool_call", "action": BAD_WRITE}])
    assert r["reward"] == traj.final_reward
    rep = load_trajectory(r["trajectory_path"])
    assert rep.decisions[0].decision_point == "context_policy"
    assert rep.decisions[0].chosen_action["forced"] is False
    assert rep.decisions[1].decision_point == "tool_call"
    assert rep.decisions[1].chosen_action["forced"] is True


def test_unconsumed_queue_raises(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    last_term = max(d.index for d in traj.decisions
                    if d.decision_point == "termination")
    with pytest.raises(RuntimeError, match="não consumidas"):
        resume_episode(traj, last_term, FakeLLM(make_script()), tmp_path / "replays",
                       [{"point": "termination", "action": {"action": "terminate"}},
                        {"point": "tool_call", "action": {"action": "finish"}}])


def test_replay_from_asserts_first_point_matches(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    # índice 0 é context_policy; primeira entrada tool_call deve falhar o assert
    with pytest.raises(AssertionError):
        replay_from(traj, 0, FakeLLM(make_script()), tmp_path / "replays",
                    override_actions=[{"point": "tool_call", "action": BAD_WRITE}])


def test_singular_forced_action_still_works(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    idx = next(d.index for d in traj.decisions if d.decision_point == "termination")
    r = replay_from(traj, idx, FakeLLM(make_script()), tmp_path / "cf",
                    override_action={"action": "terminate"})
    assert r["reward"] < traj.final_reward
