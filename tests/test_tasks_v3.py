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
    "l_payroll_pipeline": {
        "tax_utils.py": '''
def withhold(gross: float) -> float:
    return gross * 0.2140
''',
        "bonus_utils.py": '''
def seniority_bonus(years: int) -> float:
    return years * 37.25
''',
        "solution.py": '''
from bonus_utils import seniority_bonus
from tax_utils import withhold


def net_pay(hours, rate, years):
    gross = hours * rate
    if hours > 172.0:
        gross += (hours - 172.0) * rate * 0.65
    total = gross + seniority_bonus(years)
    return round(total - withhold(total), 2)
''',
    },
    "l_loyalty_points": {
        "tier_utils.py": '''
def tier(total_spend: float) -> str:
    if total_spend > 812.40:
        return "GOLD"
    if total_spend > 296.70:
        return "SILVER"
    return "BASE"
''',
        "points_utils.py": '''
def base_points(amount: float) -> int:
    return int(amount * 3.7)
''',
        "solution.py": '''
from points_utils import base_points
from tier_utils import tier


def award(amount, total_spend):
    p = base_points(amount)
    mult = {"GOLD": 2.25, "SILVER": 1.4, "BASE": 1.0}[tier(total_spend)]
    return int(p * mult)
''',
    },
    "l_shipping_batch": {
        "box_utils.py": '''
def volumetric(l, w, h):
    return (l * w * h) / 4820.0
''',
        "rate_utils.py": '''
def zone_rate(zone: str) -> float:
    return {"A": 5.85, "B": 9.15, "C": 13.4}[zone]
''',
        "solution.py": '''
from box_utils import volumetric
from rate_utils import zone_rate


def batch_cost(boxes, zone):
    total = sum(max(kg, volumetric(l, w, h)) for l, w, h, kg in boxes)
    cost = total * zone_rate(zone) + 27.9
    if len(boxes) > 4:
        cost *= 0.94
    return round(cost, 2)
''',
    },
    "l_rental_invoice": {
        "fuel_utils.py": '''
def fuel_charge(liters: float) -> float:
    return liters * 7.35
''',
        "insure_utils.py": '''
def insurance(days: int) -> float:
    return days * 12.60
''',
        "solution.py": '''
from fuel_utils import fuel_charge
from insure_utils import insurance


def invoice(days, km, liters, insured):
    total = days * 44.90 + km * 0.37
    total += fuel_charge(liters)
    if insured:
        total += insurance(days)
    if km > 950:
        total += 88.0
    return round(total, 2)
''',
    },
    "l_grade_report": {
        "score_utils.py": '''
def weighted(exam: float, hw: float) -> float:
    return exam * 0.62 + hw * 0.38
''',
        "curve_utils.py": '''
def curve(score: float) -> float:
    return min(score + 4.7, 100.0)
''',
        "solution.py": '''
from curve_utils import curve
from score_utils import weighted


def report(exam, hw, attendance):
    s = curve(weighted(exam, hw))
    if attendance < 0.75:
        s *= 0.85
    if s >= 91.5:
        letter = "A"
    elif s >= 78.3:
        letter = "B"
    elif s >= 62.1:
        letter = "C"
    else:
        letter = "F"
    return f"{letter}:{round(s, 2)}"
''',
    },
    "l_order_validator": {
        "sku_utils.py": '''
def valid_sku(s) -> bool:
    return (
        isinstance(s, str)
        and s.startswith("ZQ-")
        and len(s) == 7
        and s[3:].isdigit()
    )
''',
        "qty_utils.py": '''
def qty_in_range(q: int) -> bool:
    return 1 <= q <= 46
''',
        "solution.py": '''
from qty_utils import qty_in_range
from sku_utils import valid_sku


def validate(order):
    if "sku" not in order:
        return "ERR_41"
    if not valid_sku(order["sku"]):
        return "ERR_17"
    if "qty" not in order:
        return "ERR_58"
    if not qty_in_range(order["qty"]):
        return "ERR_23"
    if order.get("express") and order["qty"] > 30:
        return "ERR_66"
    return "OK:" + order["sku"]
''',
    },
    "l_log_parser": {
        "level_utils.py": '''
def level_weight(level: str) -> float:
    return {"DEBUG": 0.5, "WARN": 3.25, "FATAL": 8.75}.get(level, 0.0)
''',
        "ts_utils.py": '''
def in_window(ts: int) -> bool:
    return 1200 <= ts <= 8600
''',
        "solution.py": '''
from level_utils import level_weight
from ts_utils import in_window


def severity(lines):
    total, has_fatal = 0.0, False
    for line in lines:
        parts = line.split("|")
        if len(parts) != 3:
            continue
        try:
            ts = int(parts[0])
        except ValueError:
            continue
        if not in_window(ts):
            continue
        w = level_weight(parts[1])
        if w == 0.0:
            continue
        total += w
        if parts[1] == "FATAL":
            has_fatal = True
    if has_fatal:
        total *= 1.9
    return round(total, 2)
''',
    },
    "l_vending_machine": {
        "coin_utils.py": '''
def coin_value(code: str) -> float:
    return {"T1": 0.35, "T2": 1.15, "T5": 2.6}.get(code, 0.0)
''',
        "price_utils.py": '''
def price(item: str) -> float:
    return {"cola": 3.05, "chips": 1.85}[item]
''',
        "solution.py": '''
from coin_utils import coin_value
from price_utils import price


def run(events):
    out, credit = [], 0.0
    for ev in events:
        if ev in ("T1", "T2", "T5"):
            credit = round(credit + coin_value(ev), 2)
            out.append(f"CREDIT:{credit}")
        elif ev.startswith("SEL:"):
            item = ev[4:]
            if credit >= price(item):
                change = round(credit - price(item), 2)
                out.append(f"VEND:{item}:{change}")
                credit = 0.0
            else:
                out.append("ERR_LOW")
        elif ev == "CANCEL":
            out.append(f"REFUND:{credit}")
            credit = 0.0
        else:
            out.append("ERR_EVT")
    return out
''',
    },
    "l_door_controller": {
        "badge_utils.py": '''
def badge_ok(code) -> bool:
    return isinstance(code, str) and code.startswith("BX") and len(code) == 6
''',
        "alarm_utils.py": '''
def alarm_after(fails: int) -> bool:
    return fails >= 4
''',
        "solution.py": '''
from alarm_utils import alarm_after
from badge_utils import badge_ok


def control(events):
    out, state, fails = [], "LOCKED", 0
    for ev in events:
        kind = ev[0]
        if kind == "force":
            state = "ALARM"
            out.append("ALARM_ON")
        elif state == "ALARM":
            if kind == "reset":
                if ev[1] == "7359":
                    state, fails = "LOCKED", 0
                    out.append("RESET_OK")
                else:
                    out.append("ERR_PIN")
            else:
                out.append("ERR_STATE")
        elif state == "LOCKED":
            if kind == "badge":
                if badge_ok(ev[1]):
                    state, fails = "OPEN", 0
                    out.append("OPENED")
                else:
                    fails += 1
                    if alarm_after(fails):
                        state = "ALARM"
                        out.append("ALARM_ON")
                    else:
                        out.append("DENIED")
            else:
                out.append("ERR_STATE")
        else:
            if kind == "close":
                state = "LOCKED"
                out.append("CLOSED")
            else:
                out.append("ERR_STATE")
    return out
''',
    },
    "l_discount_chain": {
        "coupon_utils.py": '''
def coupon_pct(code: str) -> float:
    return {"VX9": 0.14, "KJ4": 0.23}.get(code, 0.0)
''',
        "member_utils.py": '''
def member_rate(level: str) -> float:
    return {"plus": 0.06, "max": 0.11}.get(level, 0.0)
''',
        "solution.py": '''
from coupon_utils import coupon_pct
from member_utils import member_rate


def final_price(subtotal, code, level):
    p = subtotal * (1 - coupon_pct(code))
    p *= 1 - member_rate(level)
    if p > 480.0:
        p -= 25.5
    p += 3.95
    return round(p, 2)
''',
    },
}

TASK_IDS = [t["task_id"] for t in TASKS]
S_IDS = [tid for tid in TASK_IDS if STRATA[tid] == "S"]
C_IDS = [tid for tid in TASK_IDS if STRATA[tid] == "C"]
L_IDS = [tid for tid in TASK_IDS if STRATA[tid] == "L"]


@pytest.fixture
def sandbox():
    sb = Sandbox()
    yield sb
    sb.cleanup()


class TestTasksV3Schema:
    def test_has_exactly_twenty_tasks(self):
        assert len(TASKS) == 20

    def test_task_ids_unique(self):
        assert len(set(TASK_IDS)) == 20

    def test_task_ids_disjoint_from_v1_and_v2(self):
        other_ids = {t["task_id"] for t in TASKS_V1} | {t["task_id"] for t in TASKS_V2}
        assert not other_ids & set(TASK_IDS)

    def test_five_per_stratum(self):
        assert len(S_IDS) == 5 and len(C_IDS) == 5 and len(L_IDS) == 10

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


@pytest.mark.parametrize("task_id", L_IDS)
def test_l_prompt_longer_than_800(task_id):
    assert len(get_task(task_id)["prompt"]) > 800


@pytest.mark.parametrize("task_id", L_IDS)
def test_l_constants_only_after_first_240_chars(task_id):
    prompt = get_task(task_id)["prompt"]
    head, tail = prompt[:240], prompt[240:]
    for literal in CRITICAL_CONSTANTS[task_id]:
        assert literal not in head, (
            f"{task_id}: literal crítico {literal!r} nos primeiros 240 chars"
        )
        assert literal in tail, f"{task_id}: literal {literal!r} ausente após char 240"


@pytest.mark.parametrize("task_id", L_IDS)
def test_l_at_least_ten_test_functions(task_id):
    assert get_task(task_id)["test_code"].count("def test_") >= 10


@pytest.mark.parametrize("task_id", L_IDS)
def test_l_tasks_have_exactly_three_files(task_id):
    assert len(REFERENCE_SOLUTIONS[task_id]) == 3
    assert "solution.py" in REFERENCE_SOLUTIONS[task_id]


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
