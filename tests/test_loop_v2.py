"""Loop V2 + replay com LLM fake: 5 tipos de decisão, replay nulo exato, flip por fila."""
import itertools

from agent.harness_v2 import HarnessV2
from agent.loop_v2 import EpisodeV2, parse_action_v2, serialize_action_v2
from environment.tasks_swe import TASKS, get_task
from trajectories.recorder import Recorder
from trajectories.replay import build_flip_queue, replay_from
from trajectories.schema import load_trajectory


class FakeLLM:
    def __init__(self, script):
        self._iter = itertools.cycle(script)

    def config(self):
        return {"model": "fake", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kw):
        return {"text": next(self._iter), "prompt_tokens": 10, "completion_tokens": 5,
                "wall_time_s": 0.0}


def _task():
    return TASKS[0]


def _script(task, fix: bool):
    content = (task["canonical_files"][task["bug_file"]] if fix
               else task["repo_files"][task["bug_file"]])
    return [
        "isto não é uma ação válida",  # dispara retry
        "LIST",
        f"READ {task['bug_file']}",
        "TEST",
        f"WRITE {task['bug_file']}",  # fase 1: sem conteúdo
        f"```python\n{content}```",   # fase 2: bloco com o conteúdo
        "FINISH",
    ]


def _run(tmp_path, sub, fix=True):
    task = _task()
    ep = EpisodeV2(task, FakeLLM(_script(task, fix)), HarnessV2(max_turns=8),
                   Recorder(tmp_path / sub))
    result = ep.run()
    ep.sandbox.cleanup()
    return task, result


def test_parse_v2_canonico():
    assert parse_action_v2("LIST") == {"action": "list_files"}
    assert parse_action_v2("READ a.py") == {"action": "read_file", "path": "a.py"}
    assert parse_action_v2("READ") is None
    assert parse_action_v2("WRITE a.py") == {"action": "write_file", "path": "a.py"}  # parcial
    assert parse_action_v2("WRITE a.py\n```python\nx = 1\n```") == {
        "action": "write_file", "path": "a.py", "content": "x = 1\n"}
    assert parse_action_v2("nada") is None
    # round-trip: serialização canônica é parseável de volta
    a = {"action": "write_file", "path": "a.py", "content": "x = 1"}
    assert parse_action_v2(serialize_action_v2(a)) == {
        "action": "write_file", "path": "a.py", "content": "x = 1\n"}


def test_episode_v2_cobre_5_tipos_e_reward(tmp_path):
    _, result = _run(tmp_path, "base")
    assert result["success"] and result["reward"] == 1.0
    traj = load_trajectory(result["trajectory_path"])
    pontos = {d.decision_point for d in traj.decisions}
    assert {"context_policy", "tool_call", "termination", "retry",
            "test_schedule", "observation_policy"} <= pontos
    # ordem de execução: tool_call do write vem ANTES do test_schedule aninhado
    pts = [d.decision_point for d in traj.decisions]
    i_ts = pts.index("test_schedule")
    assert pts[i_ts - 1] == "tool_call"


def test_episode_v2_sem_fix_reward_parcial(tmp_path):
    task, result = _run(tmp_path, "semfix", fix=False)
    assert 0.0 < result["reward"] < 1.0 and not result["success"]


def test_replay_nulo_forcando_tudo_reproduz_reward(tmp_path):
    _, result = _run(tmp_path, "nulo_base")
    traj = load_trajectory(result["trajectory_path"])
    queue = [{"point": d.decision_point,
              "action": {k: v for k, v in d.chosen_action.items() if k != "forced"}}
             for d in traj.decisions if d.decision_point != "retry"]
    rep = replay_from(traj, 0, FakeLLM(["nunca chamado"]), tmp_path / "nulo_rep",
                      override_actions=queue)
    assert rep["reward"] == result["reward"] == 1.0


def test_flip_observation_policy_por_fila(tmp_path):
    _, result = _run(tmp_path, "flip_base")
    traj = load_trajectory(result["trajectory_path"])
    idx = next(i for i, d in enumerate(traj.decisions)
               if d.decision_point == "observation_policy")
    entry, queue = build_flip_queue(traj, idx, {"action": "compact_output"})
    assert traj.decisions[entry].decision_point in EpisodeV2.PHASES
    assert queue[-1] == {"point": "observation_policy", "action": {"action": "compact_output"}}
    assert all(item["point"] != "retry" for item in queue)


def test_flip_queue_recusa_span_com_retry(tmp_path):
    _, result = _run(tmp_path, "retry_base")
    traj = load_trajectory(result["trajectory_path"])
    i_retry = next(i for i, d in enumerate(traj.decisions) if d.decision_point == "retry")
    i_alvo = next(i for i in range(i_retry + 1, len(traj.decisions))
                  if traj.decisions[i].decision_point == "tool_call")
    # span context_policy..tool_call do 1º turno contém o retry → recusa
    try:
        build_flip_queue(traj, i_alvo, {"action": "finish"})
        recusou = False
    except ValueError:
        recusou = True
    assert recusou


def test_registry_resolve_swe():
    assert get_task(TASKS[0]["task_id"])["task_id"] == TASKS[0]["task_id"]
    from environment.registry import resolve_task
    assert resolve_task(TASKS[0]["task_id"])["family"] == TASKS[0]["family"]
