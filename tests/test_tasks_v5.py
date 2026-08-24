"""Testes de referência para environment/tasks_v5.py (pool D4b, pré-registro 18).

Invariantes do estrato H (perfil fracionário):
- 20 tasks, ids únicos com prefixo x_, 3-4 arquivos por task;
- 10-14 funções de teste por task, 1 assert cada;
- starter_code levanta NotImplementedError e não contém constante crítica;
- constantes críticas ausentes de prompt[:240], presentes em prompt[240:];
- preâmbulo (primeiros 240 chars) sem nenhum dígito;
- para uma amostra determinística de 4 tasks, a solução canônica embutida
  dá reward 1.0 no sandbox e o starter puro dá reward 0.0.
"""

import re

import pytest

from environment.registry import resolve_task
from environment.sandbox import Sandbox
from environment.tasks_v5 import CRITICAL_CONSTANTS, STRATA, TASKS, get_task

TASK_IDS = [t["task_id"] for t in TASKS]

# amostra determinística pré-fixada (diversidade: FSM com lockout, validador
# com normalização+checksum, ledger FIFO com expiração, rating com precedência)
SAMPLE_IDS = [
    "x_vault_lock",
    "x_plate_validator",
    "x_loyalty_ledger",
    "x_spot_power",
]

SAMPLE_SOLUTIONS: dict[str, dict[str, str]] = {
    "x_vault_lock": {
        "pin_utils.py": '''
def pin_ok(pin: str) -> bool:
    return len(pin) == 6 and pin.isdigit() and int(pin) % 73 == 21
''',
        "alarm_utils.py": '''
def alarm_level(total_fails: int) -> str:
    if total_fails >= 5:
        return "AL-RED"
    if total_fails >= 3:
        return "AL-AMB"
    return "AL-OFF"
''',
        "solution.py": '''
from alarm_utils import alarm_level
from pin_utils import pin_ok


def operate(events):
    state = "LOCKED"
    opens = 0
    consec = 0
    total_fails = 0
    lockout_left = 0
    for ev in events:
        if lockout_left > 0:
            lockout_left -= 1
            continue
        if ev[0] == "enter":
            if state == "OPEN":
                continue
            if pin_ok(ev[1]):
                state = "OPEN"
                consec = 0
            else:
                consec += 1
                total_fails += 1
                if consec == 3:
                    lockout_left = 4
                    consec = 0
        elif ev[0] == "close":
            if state == "OPEN":
                state = "LOCKED"
                opens += 1
    return f"{state}|{opens}|{alarm_level(total_fails)}"
''',
    },
    "x_plate_validator": {
        "norm_utils.py": '''
def normalize(raw: str) -> str:
    s = raw.replace(" ", "").replace("-", "")
    s = s.upper()
    return s.replace("O", "0").replace("I", "1")
''',
        "rank_utils.py": '''
ALPHABET = "BCDFGHJKLMNPQRSTVWXZ"


def rank(ch: str) -> int:
    return ALPHABET.find(ch)
''',
        "solution.py": '''
from norm_utils import normalize
from rank_utils import rank


def validate(raw):
    s = normalize(raw)
    if len(s) != 7:
        return "E_LEN"
    if not s[2:6].isdigit():
        return "E_DIG"
    r_first, r_second, r_last = rank(s[0]), rank(s[1]), rank(s[6])
    if r_first < 0 or r_second < 0 or r_last < 0:
        return "E_ALPHA"
    total = (r_first + r_second) * 5 + sum(int(c) for c in s[2:6]) * 11
    if total % 20 != r_last:
        return "E_CHK"
    return "OK-" + s
''',
    },
    "x_loyalty_ledger": {
        "bonus_utils.py": '''
def bonus(pts: int) -> int:
    if pts > 500:
        return int(pts * 0.15)
    return 0
''',
        "lot_utils.py": '''
from bonus_utils import bonus


def lot_size(pts: int) -> int:
    return min(pts + bonus(pts), 3000)
''',
        "expiry_utils.py": '''
def usable(earn_day: int, day: int) -> bool:
    return day - earn_day < 90
''',
        "solution.py": '''
from expiry_utils import usable
from lot_utils import lot_size


def settle(events):
    lots = []
    rejected = 0
    expired_total = 0

    def sweep(day):
        nonlocal expired_total
        kept = []
        for lot in lots:
            if usable(lot[0], day):
                kept.append(lot)
            else:
                expired_total += lot[1]
        lots[:] = kept

    for ev in events:
        if ev[0] == "earn":
            _, pts, day = ev
            sweep(day)
            lots.append([day, lot_size(pts)])
        else:
            _, pts, day = ev
            sweep(day)
            if pts > 2000:
                rejected += 1
                continue
            need = pts + 25
            if sum(lot[1] for lot in lots) < need:
                rejected += 1
                continue
            for lot in lots:
                take = min(lot[1], need)
                lot[1] -= take
                need -= take
            lots[:] = [lot for lot in lots if lot[1] > 0]
    balance = sum(lot[1] for lot in lots)
    return f"{balance}|{rejected}|{expired_total}"
''',
    },
    "x_spot_power": {
        "band_utils.py": '''
def hour_rate(hour: int) -> float:
    if 17 <= hour < 21:
        return 0.5236
    if 10 <= hour < 18:
        return 0.0913
    return 0.2147
''',
        "demand_utils.py": '''
def demand_fee(max_kwh: float) -> float:
    return max_kwh * 3.41
''',
        "solution.py": '''
from band_utils import hour_rate
from demand_utils import demand_fee


def bill(usage):
    if not usage:
        return 0.0
    energy = 0.0
    peak = 0.0
    for hour, kwh in usage:
        energy += kwh * hour_rate(hour)
        if kwh > peak:
            peak = kwh
    return round(energy + demand_fee(peak), 2)
''',
    },
}


def test_pool_has_20_tasks():
    assert len(TASKS) == 20


def test_ids_unique_and_prefixed():
    assert len(set(TASK_IDS)) == 20
    assert all(tid.startswith("x_") for tid in TASK_IDS)


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
        get_task("x_nao_existe")


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
