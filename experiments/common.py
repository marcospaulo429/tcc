"""Helpers compartilhados dos experimentos."""
import json
from pathlib import Path

from trajectories.schema import Trajectory, load_trajectory


def load_trajectories(dir_path: str | Path) -> list[Trajectory]:
    return [load_trajectory(p) for p in sorted(Path(dir_path).glob("*.jsonl"))]


def append_row(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # linha truncada por crash no meio do write; a rep será refeita
    return rows


def done_keys(rows: list[dict], key_fields: tuple[str, ...]) -> set[tuple]:
    return {tuple(r[k] for k in key_fields) for r in rows}
