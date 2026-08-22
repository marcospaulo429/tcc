"""Pool combinado v2+v3 (30 tasks) para o grid da Fase A (PLANO-EXECUCAO.md)."""
from environment.tasks_v2 import TASKS as TASKS_V2
from environment.tasks_v3 import CRITICAL_CONSTANTS, STRATA as STRATA_V3
from environment.tasks_v3 import TASKS as TASKS_V3

TASKS: list[dict] = TASKS_V2 + TASKS_V3
# estrato das v2 = "L" de fato (longas, constantes pós-240), rotulado "V2" p/ análise
STRATA: dict[str, str] = {t["task_id"]: "V2" for t in TASKS_V2} | STRATA_V3

__all__ = ["TASKS", "STRATA", "CRITICAL_CONSTANTS"]


def get_task(task_id: str) -> dict:
    for t in TASKS:
        if t["task_id"] == task_id:
            return t
    raise KeyError(task_id)
