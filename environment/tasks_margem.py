"""União tasks_all (30) ∪ tasks_curated (22) sem duplicatas — candidatos do C1c."""
from environment.tasks_all import TASKS as TASKS_ALL
from environment.tasks_curated import TASKS as TASKS_CURATED

_seen: set[str] = set()
TASKS: list[dict] = []
for _t in TASKS_ALL + TASKS_CURATED:
    if _t["task_id"] not in _seen:
        _seen.add(_t["task_id"])
        TASKS.append(_t)
