"""Testes de referência para environment/tasks_v4.py (pool D4, pré-registro 17).

Invariantes do estrato H:
- 24 tasks, ids únicos com prefixo h_, 3-4 arquivos por task;
- 10-14 funções de teste por task, 1 assert cada;
- starter_code levanta NotImplementedError e não contém constante crítica;
- constantes críticas ausentes de prompt[:240], presentes em prompt[240:];
- para uma amostra determinística de 4 tasks, a solução canônica embutida
  dá reward 1.0 no sandbox e o starter puro dá reward 0.0.
"""

import re

import pytest

from environment.registry import resolve_task
from environment.sandbox import Sandbox
from environment.tasks_v4 import CRITICAL_CONSTANTS, STRATA, TASKS, get_task

TASK_IDS = [t["task_id"] for t in TASKS]

# amostra determinística pré-fixada (diversidade: numérica multi-arquivo,
# validador de strings, máquina de estados, split com half-up)
SAMPLE_IDS = [
    "h_customs_clearance",
    "h_sku_validator",
    "h_turnstile_fsm",
    "h_stream_royalties",
]

SAMPLE_SOLUTIONS: dict[str, dict[str, str]] = {
    "h_customs_clearance": {
        "fx_utils.py": '''
def to_local(amount: float, currency: str) -> float:
    rates = {"EUR": 5.2731, "GBP": 6.1408, "USD": 4.9377, "LOC": 1.0}
    return amount * rates[currency]
''',
        "round_utils.py": '''
import math


def half_up2(x: float) -> float:
    return math.floor(x * 100 + 0.5) / 100
''',
        "solution.py": '''
from fx_utils import to_local
from round_utils import half_up2


def clearance(items):
    total = 0.0
    for category, amount, currency in items:
        local = to_local(amount, currency)
        if category.startswith("QX-"):
            rate = 0.1873
        elif category.startswith("RM-"):
            rate = 0.0942
        else:
            rate = 0.2417
        if local < 683:
            rate = 0.0
        total += half_up2(local + local * rate)
    total += 41.85
    if len(items) > 7:
        total *= 0.9315
    return half_up2(total)
''',
    },
    "h_sku_validator": {
        "checksum_utils.py": '''
def checksum(digits: str) -> int:
    total = 0
    for i, ch in enumerate(digits):
        d = int(ch)
        total += d * 3 if i % 2 == 0 else d
    return total % 43
''',
        "prefix_utils.py": '''
def prefix_ok(sku: str) -> bool:
    return sku.startswith("KP-") or sku.startswith("VN-")
''',
        "solution.py": '''
from checksum_utils import checksum
from prefix_utils import prefix_ok


def validate(sku):
    if len(sku) != 11:
        return "ERR_74"
    if not prefix_ok(sku):
        return "ERR_29"
    tail = sku[-8:]
    if not tail.isdigit():
        return "ERR_50"
    if checksum(tail) != 19:
        return "ERR_88"
    return "OK:" + tail
''',
    },
    "h_turnstile_fsm": {
        "card_utils.py": '''
def card_ok(card: str) -> bool:
    return card.startswith("MT-") and len(card) == 9
''',
        "fare_utils.py": '''
def fare(zone: int) -> float:
    if zone == 1:
        return 2.85
    if zone == 2:
        return 4.6
    return 7.15
''',
        "solution.py": '''
from card_utils import card_ok
from fare_utils import fare


def run(events):
    state = "LOCKED"
    total = 0.0
    passages = 0
    errors = 0
    for ev in events:
        if errors >= 3:
            break
        if ev[0] == "tap":
            _, card, zone = ev
            if state == "LOCKED":
                if card_ok(card):
                    total += fare(zone)
                    state = "UNLOCKED"
                else:
                    errors += 1
            else:
                errors += 1
        else:
            if state == "UNLOCKED":
                state = "LOCKED"
                passages += 1
            else:
                errors += 1
    if errors >= 3:
        state = "JAMMED"
    return f"{state}|{passages}|{total:.2f}"
''',
    },
    "h_stream_royalties": {
        "rate_utils.py": '''
def per_stream(region: str) -> float:
    if region == "NA":
        return 0.00473
    if region == "EU":
        return 0.00311
    return 0.00187
''',
        "split_utils.py": '''
def writer_share(gross: float) -> float:
    return gross * 0.3842
''',
        "fee_utils.py": '''
def agency_fee(gross: float) -> float:
    return gross * 0.0917
''',
        "solution.py": '''
import math

from fee_utils import agency_fee
from rate_utils import per_stream
from split_utils import writer_share


def _half_up(x):
    return math.floor(x * 100 + 0.5) / 100


def payout(streams, region):
    gross = streams * per_stream(region)
    if gross < 25:
        return (0.0, 0.0)
    w = _half_up(writer_share(gross))
    p = _half_up(gross - w - agency_fee(gross))
    return (w, p)
''',
    },
}


def test_pool_has_24_tasks():
    assert len(TASKS) == 24


def test_ids_unique_and_prefixed():
    assert len(set(TASK_IDS)) == 24
    assert all(tid.startswith("h_") for tid in TASK_IDS)


def test_strata_all_h():
    assert set(STRATA) == set(TASK_IDS)
    assert set(STRATA.values()) == {"H"}


def test_critical_constants_cover_all_tasks():
    assert set(CRITICAL_CONSTANTS) == set(TASK_IDS)
    for tid, consts in CRITICAL_CONSTANTS.items():
        assert 6 <= len(consts) <= 12, tid


def test_get_task_and_registry_resolve():
    for tid in TASK_IDS:
        assert get_task(tid)["task_id"] == tid
        assert resolve_task(tid)["task_id"] == tid
    with pytest.raises(KeyError):
        get_task("h_nao_existe")


@pytest.mark.parametrize("task", TASKS, ids=TASK_IDS)
def test_test_function_count(task):
    n = len(re.findall(r"^def test_", task["test_code"], flags=re.M))
    assert 10 <= n <= 14


@pytest.mark.parametrize("task", TASKS, ids=TASK_IDS)
def test_one_assert_per_test_function(task):
    n_tests = len(re.findall(r"^def test_", task["test_code"], flags=re.M))
    n_asserts = len(re.findall(r"^    assert ", task["test_code"], flags=re.M))
    assert n_tests == n_asserts


@pytest.mark.parametrize("task", TASKS, ids=TASK_IDS)
def test_starter_raises_not_implemented(task):
    namespace: dict = {}
    exec(task["starter_code"], namespace)
    func = next(v for v in namespace.values() if callable(v))
    with pytest.raises(NotImplementedError):
        try:
            func()
        except TypeError:
            n_args = func.__code__.co_argcount
            func(*[None] * n_args)


@pytest.mark.parametrize("task", TASKS, ids=TASK_IDS)
def test_constants_after_char_240_and_absent_from_starter(task):
    for const in CRITICAL_CONSTANTS[task["task_id"]]:
        assert const in task["prompt"][240:], const
        assert const not in task["prompt"][:240], const
        assert const not in task["starter_code"], const


@pytest.mark.parametrize("task", TASKS, ids=TASK_IDS)
def test_prompt_preamble_is_generic(task):
    # os primeiros 240 chars não podem conter nenhum literal numérico
    assert not re.search(r"\d", task["prompt"][:240])


@pytest.mark.parametrize("tid", SAMPLE_IDS)
def test_reference_solution_full_reward(tid):
    task = get_task(tid)
    sandbox = Sandbox()
    try:
        for relpath, content in SAMPLE_SOLUTIONS[tid].items():
            sandbox.write_file(relpath, content)
        result = sandbox.run_tests(task["test_code"])
    finally:
        sandbox.cleanup()
    assert result["success"], result["output"]


@pytest.mark.parametrize("tid", SAMPLE_IDS)
def test_starter_zero_reward(tid):
    task = get_task(tid)
    sandbox = Sandbox()
    try:
        sandbox.write_file("solution.py", task["starter_code"])
        result = sandbox.run_tests(task["test_code"])
    finally:
        sandbox.cleanup()
    assert result["reward"] == 0.0
