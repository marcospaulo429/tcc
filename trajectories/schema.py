"""Schema serializável de trajetórias e decisões, com persistência JSONL."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def new_id() -> str:
    return uuid.uuid4().hex


def default_costs() -> dict:
    return {"prompt_tokens": 0, "completion_tokens": 0, "wall_time_s": 0.0}


@dataclass
class Decision:
    trajectory_id: str
    index: int
    decision_type: str  # "model" | "harness"
    decision_point: str
    state_before: dict
    available_actions: list = field(default_factory=list)
    chosen_action: dict = field(default_factory=dict)
    observation: dict | None = None
    costs: dict = field(default_factory=default_costs)
    t_start: str = ""
    t_end: str | None = None
    parent_id: str | None = None
    decision_id: str = field(default_factory=new_id)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "trajectory_id": self.trajectory_id,
            "index": self.index,
            "decision_type": self.decision_type,
            "decision_point": self.decision_point,
            "state_before": self.state_before,
            "available_actions": self.available_actions,
            "chosen_action": self.chosen_action,
            "observation": self.observation,
            "costs": self.costs,
            "t_start": self.t_start,
            "t_end": self.t_end,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Decision":
        return cls(
            decision_id=d["decision_id"],
            trajectory_id=d["trajectory_id"],
            index=d["index"],
            decision_type=d["decision_type"],
            decision_point=d["decision_point"],
            state_before=d["state_before"],
            available_actions=d["available_actions"],
            chosen_action=d["chosen_action"],
            observation=d["observation"],
            costs=d["costs"],
            t_start=d["t_start"],
            t_end=d["t_end"],
            parent_id=d["parent_id"],
        )


@dataclass
class Trajectory:
    task_id: str
    config: dict = field(default_factory=dict)
    decisions: list = field(default_factory=list)
    final_reward: float | None = None
    success: bool | None = None
    meta: dict = field(default_factory=dict)
    trajectory_id: str = field(default_factory=new_id)

    def to_dict(self) -> dict:
        return {
            "trajectory_id": self.trajectory_id,
            "task_id": self.task_id,
            "config": self.config,
            "decisions": [d.to_dict() for d in self.decisions],
            "final_reward": self.final_reward,
            "success": self.success,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Trajectory":
        return cls(
            trajectory_id=d["trajectory_id"],
            task_id=d["task_id"],
            config=d["config"],
            decisions=[Decision.from_dict(x) for x in d["decisions"]],
            final_reward=d["final_reward"],
            success=d["success"],
            meta=d["meta"],
        )


def save_trajectory(traj: Trajectory, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = traj.to_dict()
    header.pop("decisions")
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "trajectory", **header}, ensure_ascii=False) + "\n")
        for dec in sorted(traj.decisions, key=lambda d: d.index):
            f.write(json.dumps({"kind": "decision", **dec.to_dict()}, ensure_ascii=False) + "\n")
    return path


def load_trajectory(path: str | Path) -> Trajectory:
    header: dict | None = None
    decisions: list[Decision] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec: dict[str, Any] = json.loads(line)
            kind = rec.pop("kind")
            if kind == "trajectory":
                header = rec
            elif kind == "decision":
                decisions.append(Decision.from_dict(rec))
            else:
                raise ValueError(f"Registro desconhecido: kind={kind!r}")
    if header is None:
        raise ValueError(f"Arquivo sem header de trajetória: {path}")
    decisions.sort(key=lambda d: d.index)
    header["decisions"] = [d.to_dict() for d in decisions]
    return Trajectory.from_dict(header)
