"""Valida loop+replay com LLM fake determinístico — replay nulo DEVE reproduzir R exatamente."""
import itertools

from agent.harness import Harness
from agent.loop import Episode
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


class FakeLLM:
    """Roteiro determinístico: escreve solução errada, testa, escreve certa, testa, finish."""

    def __init__(self, script):
        self._iter = itertools.cycle(script)

    def config(self):
        return {"model": "fake", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages):
        return {"text": next(self._iter), "prompt_tokens": 10, "completion_tokens": 5,
                "wall_time_s": 0.0}


def make_script(task):
    import json
    bad = json.dumps({"action": "write_file", "path": "solution.py",
                      "content": "def rle_encode(s):\n    return s\n"})
    good = json.dumps({"action": "write_file", "path": "solution.py", "content": RLE_SOLUTION})
    return [bad, '{"action": "run_tests"}', good, '{"action": "run_tests"}', '{"action": "finish"}']


def run_baseline(tmp_path):
    task = get_task("rle_encode")
    llm = FakeLLM(make_script(task))
    ep = Episode(task, llm, Harness(max_turns=8), Recorder(tmp_path / "base"))
    result = ep.run()
    ep.sandbox.cleanup()
    return task, result


def test_episode_records_both_layers(tmp_path):
    _, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    types = {d.decision_type for d in traj.decisions}
    points = {d.decision_point for d in traj.decisions}
    assert types == {"model", "harness"}
    assert {"context_policy", "tool_call", "termination"} <= points
    assert traj.final_reward == 1.0 and traj.success


def test_null_replay_reproduces_reward_from_every_point(tmp_path):
    task, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    for d in traj.decisions:
        # o FakeLLM cíclico precisa ser re-alinhado ao ponto do replay: conta tool_calls já feitos
        n_model = sum(1 for x in traj.decisions[:d.index] if x.decision_type == "model")
        script = make_script(task)
        llm = FakeLLM(script[n_model:] + script[:n_model])
        r = replay_from(traj, d.index, llm, tmp_path / "replays")
        assert r["reward"] == traj.final_reward, f"divergência no index {d.index} ({d.decision_point})"
        # C2: replay nulo não pode executar decisões a mais nem a menos que o sufixo original
        assert r["n_decisions"] == len(traj.decisions) - d.index, \
            f"replay do index {d.index} ({d.decision_point}) executou " \
            f"{r['n_decisions']} decisões, sufixo original tem {len(traj.decisions) - d.index}"


def test_counterfactual_termination_changes_reward(tmp_path):
    task, result = run_baseline(tmp_path)
    traj = load_trajectory(result["trajectory_path"])
    # primeira decisão de termination (após escrever solução ERRADA): forçar terminate → reward cai
    idx = next(d.index for d in traj.decisions if d.decision_point == "termination")
    llm = FakeLLM(make_script(task))
    r = replay_from(traj, idx, llm, tmp_path / "cf", override_action={"action": "terminate"})
    assert r["reward"] < traj.final_reward
