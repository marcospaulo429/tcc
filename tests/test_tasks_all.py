"""Sanidade do pool combinado v2+v3."""
from environment.tasks_all import STRATA, TASKS, get_task


def test_pool_size_and_unique_ids():
    ids = [t["task_id"] for t in TASKS]
    assert len(ids) == 30
    assert len(set(ids)) == 30


def test_strata_cover_all():
    assert set(STRATA) == {t["task_id"] for t in TASKS}
    assert sorted(set(STRATA.values())) == ["C", "L", "S", "V2"]


def test_get_task():
    assert get_task("invoice_pricing")["task_id"] == "invoice_pricing"
    assert get_task("s_freight_quote")["task_id"] == "s_freight_quote"
