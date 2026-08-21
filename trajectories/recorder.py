"""Recorder de trajetórias: registra decisões e persiste em JSONL."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from trajectories.schema import Decision, Trajectory, default_costs, save_trajectory


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Recorder:
    def __init__(self, out_dir: str | Path):
        self.out_dir = Path(out_dir)
        self._trajectory: Trajectory | None = None
        self._by_id: dict[str, Decision] = {}

    @property
    def trajectory(self) -> Trajectory | None:
        return self._trajectory

    def start(self, task_id: str, config: dict) -> str:
        if self._trajectory is not None:
            raise RuntimeError(
                f"Trajetória {self._trajectory.trajectory_id} ainda aberta; chame finish() antes."
            )
        self._trajectory = Trajectory(
            task_id=task_id,
            config=config,
            meta={"started_at": _now_iso()},
        )
        self._by_id = {}
        return self._trajectory.trajectory_id

    def record(
        self,
        decision_type: str,
        decision_point: str,
        state_before: dict,
        available_actions: list,
        chosen_action: dict,
        parent_id: str | None = None,
    ) -> str:
        if self._trajectory is None:
            raise RuntimeError("Nenhuma trajetória aberta; chame start() antes.")
        dec = Decision(
            trajectory_id=self._trajectory.trajectory_id,
            index=len(self._trajectory.decisions),
            decision_type=decision_type,
            decision_point=decision_point,
            state_before=state_before,
            available_actions=available_actions,
            chosen_action=chosen_action,
            t_start=_now_iso(),
            parent_id=parent_id,
        )
        self._trajectory.decisions.append(dec)
        self._by_id[dec.decision_id] = dec
        return dec.decision_id

    def observe(self, decision_id: str, observation: dict, costs: dict | None = None) -> None:
        if self._trajectory is None:
            raise RuntimeError("Nenhuma trajetória aberta.")
        dec = self._by_id.get(decision_id)
        if dec is None:
            raise KeyError(f"Decisão desconhecida: {decision_id}")
        dec.observation = observation
        if costs:
            dec.costs = {**dec.costs, **costs}
        dec.t_end = _now_iso()

    def finish(self, final_reward: float, success: bool) -> Path:
        if self._trajectory is None:
            raise RuntimeError("Nenhuma trajetória aberta; chame start() antes.")
        traj = self._trajectory
        traj.final_reward = final_reward
        traj.success = success
        prompt = sum(d.costs.get("prompt_tokens", 0) for d in traj.decisions)
        completion = sum(d.costs.get("completion_tokens", 0) for d in traj.decisions)
        traj.meta.update(
            finished_at=_now_iso(),
            total_prompt_tokens=prompt,
            total_completion_tokens=completion,
        )
        path = save_trajectory(traj, self.out_dir / f"{traj.trajectory_id}.jsonl")
        self._trajectory = None
        self._by_id = {}
        return path
