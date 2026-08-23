"""Resolve task_id em qualquer conjunto de tasks registrado."""
import importlib

_MODULES = ("environment.tasks", "environment.tasks_v2", "environment.tasks_v3",
            "environment.tasks_mbpp")


def resolve_task(task_id: str) -> dict:
    for mod_name in _MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        try:
            return mod.get_task(task_id)
        except KeyError:
            continue
    raise KeyError(task_id)
