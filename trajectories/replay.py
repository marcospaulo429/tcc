"""Replay engine: reexecuta uma trajetória a partir de qualquer decisão.

- Intervenção nula (Teste 0): override_action=None — política re-decide tudo ao vivo.
- Counterfactual (Teste 1+): override_action força a decisão no ponto; resto ao vivo.
C(d) = R_original − R_replay.
"""
from pathlib import Path

from agent.harness import Harness
from agent.loop import Episode
from environment.registry import resolve_task
from environment.sandbox import Sandbox
from trajectories.recorder import Recorder
from trajectories.schema import Trajectory


def replay_from(traj: Trajectory, index: int, llm, out_dir: str | Path,
                override_action: dict | None = None,
                override_actions: list[dict] | None = None) -> dict:
    """override_actions = [{"point": str, "action": dict}] consumidas em ordem (fila);
    a PRIMEIRA entrada deve casar o decision_point do índice de partida.
    override_action (singular) mantém o comportamento anterior (fila de 1)."""
    d = traj.decisions[index]
    if d.decision_point not in Episode.PHASES:
        raise NotImplementedError(f"replay a partir de '{d.decision_point}' não suportado")
    if override_actions:
        assert override_actions[0]["point"] == d.decision_point, \
            (f"primeira forced action ({override_actions[0]['point']}) deve casar o "
             f"decision_point do índice de partida ({d.decision_point})")

    sandbox = Sandbox()
    sandbox.restore(d.state_before["workspace"])
    harness = Harness(**traj.config["harness"])
    episode = Episode(resolve_task(traj.task_id), llm, harness, Recorder(out_dir), sandbox)
    try:
        result = episode.run(resume={
            "messages": d.state_before["messages"],
            "turn": d.state_before["turn"],
            "entry_point": d.decision_point,
            "forced_action": override_action,
            "forced_actions": override_actions,
            # C2: insumos da decisão de termination gravados no state_before
            "last_action": d.state_before.get("last_action"),
            "tests_passed": d.state_before.get("tests_passed", False),
        })
    finally:
        sandbox.cleanup()
    result["replayed_from_index"] = index
    result["override_action"] = override_action
    result["override_actions"] = override_actions
    return result
