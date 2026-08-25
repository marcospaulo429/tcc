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


def build_flip_queue(traj: Trajectory, index: int, flip_action: dict) -> tuple[int, list[dict]]:
    """Fila forçada p/ flipar a decisão `index` mesmo em ponto não-canônico
    (observation_policy/test_schedule do V2): entra no último ponto canônico <= index
    e força as decisões originais do span, terminando no flip. Recusa quando um
    tool_call FORÇADO é precedido por retry no original (a ação forçada pula o call
    do modelo e o contexto perderia a troca de retry — prefixo não reconstruível).
    Retorna (entry_index, forced_actions)."""
    d = traj.decisions
    entry = max(i for i in range(index + 1) if d[i].decision_point in Episode.PHASES)
    queue = []
    for k in range(entry, index + 1):
        if d[k].decision_point == "tool_call" and k > 0 \
                and d[k - 1].decision_point == "retry":
            raise ValueError(
                f"tool_call idx {k} precedido por retry — prefixo não reconstruível sob ação forçada")
        action = flip_action if k == index else \
            {kk: v for kk, v in d[k].chosen_action.items() if kk != "forced"}
        queue.append({"point": d[k].decision_point, "action": action})
    return entry, queue


def replay_from(traj: Trajectory, index: int, llm, out_dir: str | Path,
                override_action: dict | None = None,
                override_actions: list[dict] | None = None) -> dict:
    """override_actions = [{"point": str, "action": dict}] consumidas em ordem (fila);
    a PRIMEIRA entrada deve casar o decision_point do índice de partida.
    override_action (singular) mantém o comportamento anterior (fila de 1)."""
    d = traj.decisions[index]
    if d.decision_point not in Episode.PHASES:
        raise NotImplementedError(
            f"replay a partir de '{d.decision_point}' não suportado — use build_flip_queue")
    if override_actions:
        assert override_actions[0]["point"] == d.decision_point, \
            (f"primeira forced action ({override_actions[0]['point']}) deve casar o "
             f"decision_point do índice de partida ({d.decision_point})")

    sandbox = Sandbox()
    sandbox.restore(d.state_before["workspace"])
    hcfg = dict(traj.config["harness"])
    if hcfg.pop("kind", None) == "v2":
        from agent.harness_v2 import HarnessV2
        from agent.loop_v2 import EpisodeV2
        harness, ep_cls = HarnessV2(**hcfg), EpisodeV2
    else:
        harness, ep_cls = Harness(**hcfg), Episode
    episode = ep_cls(resolve_task(traj.task_id), llm, harness, Recorder(out_dir), sandbox)
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
