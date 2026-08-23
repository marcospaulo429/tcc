"""Sanidade do pool MBPP+ congelado (pré-registro 16, D3)."""
import inspect
import random

import pytest

from environment.sandbox import Sandbox
from environment.tasks_mbpp import _CANONICAL_SAMPLE, STRATA, TASKS, get_task

SEED = 20260821


def test_pool_size_and_unique_ids():
    ids = [t["task_id"] for t in TASKS]
    assert len(ids) == 60
    assert len(set(ids)) == 60


def test_schema_and_strata():
    for t in TASKS:
        assert set(t) == {"task_id", "prompt", "starter_code", "test_code"}
    assert set(STRATA) == {t["task_id"] for t in TASKS}
    assert set(STRATA.values()) == {"MBPP"}


def test_asserts_per_task_between_6_and_10():
    for t in TASKS:
        n = t["test_code"].count("def test_")
        assert 6 <= n <= 10, t["task_id"]
        assert t["test_code"].count("assert ") == n, t["task_id"]


def test_starter_raises_not_implemented():
    for t in TASKS:
        ns: dict = {}
        exec(t["starter_code"], ns)
        fn = next(v for v in ns.values() if callable(v))
        params = inspect.signature(fn).parameters
        args = [None] * sum(
            p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            and p.default is p.empty
            for p in params.values()
        )
        with pytest.raises(NotImplementedError):
            fn(*args)


def test_prompt_mentions_function_and_solution_py():
    for t in TASKS:
        ns: dict = {}
        exec(t["starter_code"], ns)
        fn_name = next(k for k, v in ns.items() if callable(v))
        assert fn_name in t["prompt"], t["task_id"]
        assert "solution.py" in t["prompt"], t["task_id"]


def test_canonical_sample_passes_generated_tests():
    ids = [t["task_id"] for t in TASKS]
    sample_ids = sorted(random.Random(SEED).sample(sorted(ids), 5))
    assert sorted(_CANONICAL_SAMPLE) == sample_ids
    for tid in sample_ids:
        task = get_task(tid)
        sandbox = Sandbox()
        try:
            sandbox.write_file("solution.py", _CANONICAL_SAMPLE[tid])
            result = sandbox.run_tests(task["test_code"])
        finally:
            sandbox.cleanup()
        n = task["test_code"].count("def test_")
        assert result["success"] and result["total"] == n, (tid, result["output"])


def test_get_task_roundtrip():
    tid = TASKS[0]["task_id"]
    assert get_task(tid)["task_id"] == tid
    with pytest.raises(KeyError):
        get_task("nao_existe")


def test_registry_resolve_mbpp():
    from environment.registry import resolve_task
    from environment.tasks_mbpp import TASKS
    t = resolve_task(TASKS[0]["task_id"])
    assert t["task_id"] == TASKS[0]["task_id"]
