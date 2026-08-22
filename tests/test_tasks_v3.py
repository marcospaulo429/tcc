"""Testes de referência para environment/tasks_v3.py.

Para cada task v3: a solução de referência dá reward 1.0; o starter_code puro
dá reward 0.0. Testes estruturais garantem os invariantes dos estratos:
- S (sinergia): constantes críticas ausentes de prompt[:240], presentes em
  prompt[240:] e ausentes do test_code (asserts não vazam constantes isoladas);
- C (controle): constantes críticas presentes em prompt[:240].
"""

import pytest

from environment.sandbox import Sandbox
from environment.tasks import TASKS as TASKS_V1
from environment.tasks_v2 import TASKS as TASKS_V2
from environment.tasks_v3 import CRITICAL_CONSTANTS, STRATA, TASKS, get_task

# solução de referência por task: {relpath: conteúdo}
REFERENCE_SOLUTIONS: dict[str, dict[str, str]] = {
    "s_freight_quote": {
        "shipping_utils.py": '''
def round2(x: float) -> float:
    return round(x, 2)
''',
        "solution.py": '''
from shipping_utils import round2


def freight_quote(weight_kg, express):
    quote = 14.75 + weight_kg * 3.85
    if weight_kg > 22.5:
        quote *= 1.12
    if express:
        quote *= 1.45
    return round2(quote)
''',
    },
    "s_ticket_pricer": {
        "calendar_utils.py": '''
def is_weekend(day: str) -> bool:
    return day in ("sat", "sun")
''',
        "solution.py": '''
from calendar_utils import is_weekend


def ticket_price(age, day):
    price = 48.20
    if age < 12:
        price *= 0.35
    elif age >= 65:
        price *= 0.55
    price += 4.15
    if is_weekend(day):
        price += 6.60
    return round(price, 2)
''',
    },
    "s_sensor_alarm": {
        "readings_utils.py": '''
def mean(values):
    return sum(values) / len(values)
''',
        "solution.py": '''
from readings_utils import mean


def alarm_level(values):
    m = mean(values)
    if m > 71.4:
        return round(m * 1.65 + 4.35, 2)
    if m > 33.8:
        return round((m + 15.9) * 1.15, 2)
    return round(m * 0.25 + 8.2, 2)
''',
    },
    "s_commission_calc": {
        "sales_utils.py": '''
def total(sales):
    return float(sum(sales))
''',
        "solution.py": '''
from sales_utils import total


def commission(sales):
    t = total(sales)
    rate = 0.083 if t > 5400 else 0.047
    c = t * rate + 62.5
    if t > 9100:
        c += 175.0
    return round(c, 2)
''',
    },
    "s_energy_bill": {
        "meter_utils.py": '''
def usage(start, end):
    return end - start
''',
        "solution.py": '''
from meter_utils import usage


def bill(start, end, night):
    u = usage(start, end)
    cost = u * 0.6175 + 21.45
    if u > 240:
        cost += (u - 240) * 0.29
    if night:
        cost *= 0.93
    return round(cost, 2)
''',
    },
    "c_temp_label": {
        "solution.py": '''
def label(c):
    if c < 8.5:
        s = "COLD"
    elif c < 27.0:
        s = "MILD"
    else:
        s = "HOT"
    if c > 39.5:
        s += "!"
    return s
''',
    },
    "c_late_fee": {
        "solution.py": '''
def late_fee(days):
    if days <= 0:
        return 0.0
    fee = days * 2.75 + 8.0
    if days > 30:
        fee += 55.0
    return round(fee, 2)
''',
    },
    "c_username_check": {
        "solution.py": '''
def check(u):
    if len(u) < 5 or len(u) > 14:
        return "ERR_LEN"
    if not all(ch == "_" or ch.isdigit() or "a" <= ch <= "z" for ch in u):
        return "ERR_CHAR"
    return "OK:" + u
''',
    },
    "c_parcel_cost": {
        "solution.py": '''
def cost(kg):
    c = kg * 4.6 + 12.25
    if kg > 18.0:
        c *= 1.3
    return round(c, 2)
''',
    },
    "c_vote_tally": {
        "solution.py": '''
def tally(votes):
    y = votes.count("yes")
    n = votes.count("no")
    verdict = "APPROVED" if y >= n + 3 else "REJECTED"
    return f"{verdict}({y}-{n})"
''',
    },
}

TASK_IDS = [t["task_id"] for t in TASKS]
S_IDS = [tid for tid in TASK_IDS if STRATA[tid] == "S"]
C_IDS = [tid for tid in TASK_IDS if STRATA[tid] == "C"]


@pytest.fixture
def sandbox():
    sb = Sandbox()
    yield sb
    sb.cleanup()


class TestTasksV3Schema:
    def test_has_exactly_ten_tasks(self):
        assert len(TASKS) == 10

    def test_task_ids_unique(self):
        assert len(set(TASK_IDS)) == 10

    def test_task_ids_disjoint_from_v1_and_v2(self):
        other_ids = {t["task_id"] for t in TASKS_V1} | {t["task_id"] for t in TASKS_V2}
        assert not other_ids & set(TASK_IDS)

    def test_five_per_stratum(self):
        assert len(S_IDS) == 5 and len(C_IDS) == 5

    def test_strata_values_valid(self):
        assert set(STRATA.values()) <= {"S", "C", "L"}

    def test_strata_covers_exactly_task_ids(self):
        assert set(STRATA) == set(TASK_IDS)

    def test_critical_constants_covers_exactly_task_ids(self):
        assert set(CRITICAL_CONSTANTS) == set(TASK_IDS)

    def test_prefix_matches_stratum(self):
        for tid in TASK_IDS:
            assert tid.startswith(STRATA[tid].lower() + "_")

    def test_all_fields_present_and_nonempty(self):
        for task in TASKS:
            for field in ("task_id", "prompt", "test_code", "starter_code"):
                assert isinstance(task[field], str) and task[field].strip(), (
                    f"{task.get('task_id')}: campo {field} vazio ou ausente"
                )

    def test_starter_code_raises_not_implemented(self):
        for task in TASKS:
            assert "raise NotImplementedError" in task["starter_code"]

    def test_get_task_returns_task(self):
        task = get_task("s_freight_quote")
        assert task["task_id"] == "s_freight_quote"

    def test_get_task_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_task("nao_existe")


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_prompt_long_enough(task_id):
    assert len(get_task(task_id)["prompt"]) > 600


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_at_least_eight_test_functions(task_id):
    assert get_task(task_id)["test_code"].count("def test_") >= 8


@pytest.mark.parametrize("task_id", S_IDS)
def test_s_constants_only_after_first_240_chars(task_id):
    prompt = get_task(task_id)["prompt"]
    head, tail = prompt[:240], prompt[240:]
    for literal in CRITICAL_CONSTANTS[task_id]:
        assert literal not in head, (
            f"{task_id}: literal crítico {literal!r} nos primeiros 240 chars"
        )
        assert literal in tail, f"{task_id}: literal {literal!r} ausente após char 240"


@pytest.mark.parametrize("task_id", S_IDS)
def test_s_constants_never_leak_into_test_code(task_id):
    test_code = get_task(task_id)["test_code"]
    for literal in CRITICAL_CONSTANTS[task_id]:
        assert literal not in test_code, (
            f"{task_id}: literal crítico {literal!r} vaza no test_code"
        )


@pytest.mark.parametrize("task_id", S_IDS)
def test_s_tasks_have_exactly_two_files(task_id):
    assert len(REFERENCE_SOLUTIONS[task_id]) == 2
    assert "solution.py" in REFERENCE_SOLUTIONS[task_id]


@pytest.mark.parametrize("task_id", C_IDS)
def test_c_constants_inside_first_240_chars(task_id):
    head = get_task(task_id)["prompt"][:240]
    for literal in CRITICAL_CONSTANTS[task_id]:
        assert literal in head, (
            f"{task_id}: literal crítico {literal!r} fora dos primeiros 240 chars"
        )


@pytest.mark.parametrize("task_id", C_IDS)
def test_c_tasks_are_single_file(task_id):
    assert set(REFERENCE_SOLUTIONS[task_id]) == {"solution.py"}


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_gets_full_reward(task_id, sandbox):
    task = get_task(task_id)
    for relpath, content in REFERENCE_SOLUTIONS[task_id].items():
        sandbox.write_file(relpath, content)
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 1.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is True
    assert result["failed"] == 0 and result["errors"] == 0
    assert result["total"] == result["passed"] >= 8
    assert result["timed_out"] is False


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_starter_code_gets_zero_reward(task_id, sandbox):
    task = get_task(task_id)
    sandbox.write_file("solution.py", task["starter_code"])
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 0.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is False
    assert result["passed"] == 0


@pytest.mark.parametrize("task_id", S_IDS)
def test_s_partial_reward_without_helper_file(task_id, sandbox):
    """Só solution.py de referência (sem o helper): falhas individuais com
    reward parcial <1.0, sem colapso da coleta do pytest."""
    task = get_task(task_id)
    sandbox.write_file("solution.py", REFERENCE_SOLUTIONS[task_id]["solution.py"])
    result = sandbox.run_tests(task["test_code"])
    assert result["total"] >= 8, f"{task_id}: coleta colapsou:\n{result['output']}"
    assert result["reward"] < 1.0
