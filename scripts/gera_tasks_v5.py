"""Gera environment/tasks_v5.py (pré-registro 18, pool x_, perfil fracionário).

Método idêntico ao v4: cada task tem solução canônica embutida aqui; os valores
esperados dos asserts são obtidos EXECUTANDO a canônica (repr(), zero aritmética
manual). Depois valida no environment.sandbox: canônica reward 1.0, starter 0.0,
constantes após char 240, preâmbulo sem dígitos, contagens de arquivos/testes.

Uso: uv run python scripts/gera_tasks_v5.py
"""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from environment.sandbox import Sandbox  # noqa: E402

# ---------------------------------------------------------------------------
# Especificações das 20 tasks. files: helpers primeiro, solution.py por último.
# tests: (nome, linha de import, expressão avaliada na canônica).
# ---------------------------------------------------------------------------

SPECS: list[dict] = [
    # ------------------------------------------------------------- FSM (5)
    {
        "tid": "x_vault_lock",
        "opening": "You are asked to implement a vault keypad controller for a private banking depot.",
        "files": {
            "pin_utils.py": '''\
def pin_ok(pin: str) -> bool:
    return len(pin) == 6 and pin.isdigit() and int(pin) % 73 == 21
''',
            "alarm_utils.py": '''\
def alarm_level(total_fails: int) -> str:
    if total_fails >= 5:
        return "AL-RED"
    if total_fails >= 3:
        return "AL-AMB"
    return "AL-OFF"
''',
            "solution.py": '''\
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
        "rules": """\
1. pin_utils.py must define `pin_ok(pin: str) -> bool` returning True iff
   len(pin) is exactly 6, every character of pin is a digit, and the
   integer value of pin modulo 73 equals 21.
2. alarm_utils.py must define `alarm_level(total_fails: int) -> str`
   returning 'AL-RED' when total_fails is at least 5, 'AL-AMB' when it is
   at least 3, and 'AL-OFF' otherwise.
3. solution.py must define `operate(events: list) -> str`. The vault
   starts LOCKED with zero opens, a consecutive-failure counter at zero, a
   total-failure counter at zero and no lockout. Events are tuples
   ('enter', pin) or ('close',), processed in order:
   - While a lockout is active, the current event is consumed and fully
     ignored (whatever its kind) and the lockout counter decreases by one.
   - 'enter' while OPEN is ignored entirely (no counters change).
   - 'enter' while LOCKED: if pin_ok(pin) the vault becomes OPEN and the
     consecutive counter resets to zero; otherwise BOTH failure counters
     increase by one, and when the consecutive counter reaches exactly 3 a
     lockout covering the NEXT 4 events begins and the consecutive counter
     resets to zero.
   - 'close' while OPEN: the vault becomes LOCKED and opens increases by
     one. 'close' while LOCKED is ignored.
   - Return f'{state}|{opens}|{alarm_level(total_fails)}' where state is
     'LOCKED' or 'OPEN'.
""",
        "starter": '''\
def operate(events: list) -> str:
    """Run the vault keypad controller over a list of events."""
    raise NotImplementedError
''',
        "constants": ["6", "73", "21", "'AL-RED'", "'AL-AMB'", "'AL-OFF'", "3", "4", "5"],
        "tests": [
            ("test_helper_pin_valid", "from pin_utils import pin_ok", "pin_ok('000021')"),
            ("test_helper_pin_wrong_mod", "from pin_utils import pin_ok", "pin_ok('000022')"),
            ("test_helper_pin_wrong_length", "from pin_utils import pin_ok", "pin_ok('00021')"),
            ("test_helper_pin_non_digit", "from pin_utils import pin_ok", "pin_ok('00002a')"),
            ("test_helper_alarm_off", "from alarm_utils import alarm_level", "alarm_level(2)"),
            ("test_helper_alarm_amber", "from alarm_utils import alarm_level", "alarm_level(3)"),
            ("test_helper_alarm_red", "from alarm_utils import alarm_level", "alarm_level(5)"),
            ("test_empty_run", "from solution import operate", "operate([])"),
            ("test_open_and_close", "from solution import operate",
             "operate([('enter', '000021'), ('close',)])"),
            ("test_lockout_swallows_valid_pin", "from solution import operate",
             "operate([('enter', '111111'), ('enter', '111111'), ('enter', '111111'),"
             " ('enter', '000021'), ('close',), ('enter', '000021'), ('close',),"
             " ('enter', '000021')])"),
            ("test_enter_while_open_ignored", "from solution import operate",
             "operate([('enter', '000021'), ('enter', '111111')])"),
            ("test_close_while_locked_ignored", "from solution import operate",
             "operate([('close',), ('close',)])"),
            ("test_red_alarm_across_lockout", "from solution import operate",
             "operate([('enter', '111111')] * 3 + [('close',)] * 4 + [('enter', '111111')] * 2)"),
        ],
    },
    {
        "tid": "x_vending_fsm",
        "opening": "You are asked to implement a vending machine controller for a snack distribution firm.",
        "files": {
            "coin_utils.py": '''\
def coin_value(code: str) -> int:
    values = {"CN-A": 7, "CN-B": 13, "CN-C": 28}
    return values.get(code, 0)
''',
            "price_utils.py": '''\
def price(slot: str) -> int:
    if slot == "KA":
        return 41
    if slot == "KB":
        return 67
    return 89
''',
            "solution.py": '''\
from coin_utils import coin_value
from price_utils import price


def vend(events):
    state = "ON"
    escrow = 0
    vended = 0
    rejected = 0
    refunds = 0
    for ev in events:
        if state == "OUT":
            break
        if ev[0] == "coin":
            value = coin_value(ev[1])
            if value == 0:
                rejected += 1
                if rejected == 4:
                    state = "OUT"
            else:
                escrow += value
        elif ev[0] == "select":
            cost = price(ev[1])
            if escrow >= cost:
                vended += 1
                escrow -= cost
        elif ev[0] == "refund":
            if escrow > 0:
                refunds += 1
            escrow = 0
    return f"{state}|{vended}|{escrow}|{rejected}|{refunds}"
''',
        },
        "rules": """\
1. coin_utils.py must define `coin_value(code: str) -> int` returning 7
   for 'CN-A', 13 for 'CN-B', 28 for 'CN-C' and 0 for any other code.
2. price_utils.py must define `price(slot: str) -> int` returning 41 for
   slot 'KA', 67 for slot 'KB' and 89 for any other slot.
3. solution.py must define `vend(events: list) -> str`. The machine starts
   ON with an empty escrow and zero vended, rejected and refund counters.
   Events are ('coin', code), ('select', slot) or ('refund',):
   - 'coin': if coin_value(code) is 0 the coin is rejected (counter goes
     up by one); when the rejected counter reaches exactly 4 the machine
     goes OUT and every later event is ignored entirely. Otherwise the
     value is added to the escrow.
   - 'select': if the escrow is at least price(slot), one item is vended
     and the price is subtracted (any change STAYS in the escrow);
     otherwise nothing happens at all.
   - 'refund': the refund counter goes up by one ONLY when the escrow is
     STRICTLY greater than zero; the escrow becomes zero either way.
   - Return f'{state}|{vended}|{escrow}|{rejected}|{refunds}' where state
     is 'ON' or 'OUT'.
""",
        "starter": '''\
def vend(events: list) -> str:
    """Run the vending machine controller over a list of events."""
    raise NotImplementedError
''',
        "constants": ["'CN-A'", "'CN-B'", "'CN-C'", "7", "13", "28",
                      "'KA'", "'KB'", "41", "67", "89", "4"],
        "tests": [
            ("test_helper_coin_a", "from coin_utils import coin_value", "coin_value('CN-A')"),
            ("test_helper_coin_b", "from coin_utils import coin_value", "coin_value('CN-B')"),
            ("test_helper_coin_c", "from coin_utils import coin_value", "coin_value('CN-C')"),
            ("test_helper_coin_bad", "from coin_utils import coin_value", "coin_value('XX-Z')"),
            ("test_helper_price_ka", "from price_utils import price", "price('KA')"),
            ("test_helper_price_kb", "from price_utils import price", "price('KB')"),
            ("test_helper_price_other", "from price_utils import price", "price('ZZ')"),
            ("test_empty_run", "from solution import vend", "vend([])"),
            ("test_buy_exact", "from solution import vend",
             "vend([('coin', 'CN-C'), ('coin', 'CN-B'), ('select', 'KA')])"),
            ("test_underpaid_select_noop", "from solution import vend",
             "vend([('coin', 'CN-A'), ('select', 'KA')])"),
            ("test_refund_counts", "from solution import vend",
             "vend([('coin', 'CN-A'), ('refund',)])"),
            ("test_refund_empty_does_not_count", "from solution import vend",
             "vend([('refund',)])"),
            ("test_out_after_four_rejections", "from solution import vend",
             "vend([('coin', 'BAD')] * 4 + [('coin', 'CN-C'), ('select', 'ZZ')])"),
            ("test_change_stays_in_escrow", "from solution import vend",
             "vend([('coin', 'CN-C'), ('coin', 'CN-C'), ('select', 'KA')])"),
        ],
    },
    {
        "tid": "x_badge_gate",
        "opening": "You are asked to implement a badge gate controller for a secure research campus.",
        "files": {
            "badge_utils.py": '''\
def clearance(badge: str) -> int:
    if badge.startswith("GV-"):
        return 4
    if badge.startswith("CT-"):
        return 2
    return 1
''',
            "zone_utils.py": '''\
def required(zone: str) -> int:
    if zone == "Z-CORE":
        return 4
    if zone == "Z-LAB":
        return 2
    return 1
''',
            "solution.py": '''\
from badge_utils import clearance
from zone_utils import required


def gate(events):
    state = "OPEN"
    entries = 0
    escorts = 0
    denials = 0
    escort_used = {}
    for ev in events:
        if state == "LOCKDOWN":
            break
        if ev[0] == "scan":
            _, badge, zone = ev
            if clearance(badge) >= required(zone):
                entries += 1
            else:
                denials += 1
        elif ev[0] == "escort":
            _, host, guest, zone = ev
            used = escort_used.get(host, 0)
            if (clearance(host) >= required(zone)
                    and clearance(host) > clearance(guest)
                    and used < 2):
                entries += 1
                escorts += 1
                escort_used[host] = used + 1
            else:
                denials += 1
        if denials >= 5:
            state = "LOCKDOWN"
    return f"{state}|{entries}|{escorts}|{denials}"
''',
        },
        "rules": """\
1. badge_utils.py must define `clearance(badge: str) -> int` returning 4
   when badge starts with 'GV-', 2 when it starts with 'CT-', else 1.
2. zone_utils.py must define `required(zone: str) -> int` returning 4 for
   zone 'Z-CORE', 2 for zone 'Z-LAB' and 1 for any other zone.
3. solution.py must define `gate(events: list) -> str`. The gate starts
   OPEN with zero entries, escorts and denials. Events are
   ('scan', badge, zone) or ('escort', host, guest, zone):
   - 'scan': entry is granted (entries up by one) when clearance(badge) is
     at least required(zone); otherwise it is a denial.
   - 'escort': the guest enters (entries AND escorts each up by one) only
     when ALL hold: clearance(host) is at least required(zone),
     clearance(host) is STRICTLY greater than clearance(guest), and the
     host has escorted fewer than 2 times so far in this run. Otherwise it
     is a denial (the host's escort count does not change).
   - After any event, once denials reach 5 the gate enters LOCKDOWN and
     every later event is ignored entirely.
   - Return f'{state}|{entries}|{escorts}|{denials}' where state is 'OPEN'
     or 'LOCKDOWN'.
""",
        "starter": '''\
def gate(events: list) -> str:
    """Run the badge gate controller over a list of events."""
    raise NotImplementedError
''',
        "constants": ["'GV-'", "'CT-'", "'Z-CORE'", "'Z-LAB'", "4", "2", "5", "'LOCKDOWN'"],
        "tests": [
            ("test_helper_clearance_gv", "from badge_utils import clearance", "clearance('GV-001')"),
            ("test_helper_clearance_ct", "from badge_utils import clearance", "clearance('CT-077')"),
            ("test_helper_clearance_other", "from badge_utils import clearance", "clearance('XX-001')"),
            ("test_helper_required_core", "from zone_utils import required", "required('Z-CORE')"),
            ("test_helper_required_lab", "from zone_utils import required", "required('Z-LAB')"),
            ("test_helper_required_other", "from zone_utils import required", "required('Z-YARD')"),
            ("test_empty_run", "from solution import gate", "gate([])"),
            ("test_scan_granted", "from solution import gate",
             "gate([('scan', 'GV-A', 'Z-CORE')])"),
            ("test_scan_denied", "from solution import gate",
             "gate([('scan', 'CT-A', 'Z-CORE')])"),
            ("test_escort_granted", "from solution import gate",
             "gate([('escort', 'GV-A', 'CT-B', 'Z-LAB')])"),
            ("test_escort_equal_clearance_denied", "from solution import gate",
             "gate([('escort', 'CT-A', 'CT-B', 'Z-LAB')])"),
            ("test_escort_cap_per_host", "from solution import gate",
             "gate([('escort', 'GV-A', 'XX-B', 'Z-YARD')] * 3)"),
            ("test_lockdown_after_five_denials", "from solution import gate",
             "gate([('scan', 'XX-A', 'Z-CORE')] * 5 + [('scan', 'GV-A', 'Z-LAB')])"),
        ],
    },
    {
        "tid": "x_reactor_protocol",
        "opening": "You are asked to implement a reactor event protocol for an industrial plant operator.",
        "files": {
            "prio_utils.py": '''\
def rank(kind: str) -> int:
    order = {"ESTOP": 0, "VENT": 1, "FUEL": 2}
    return order.get(kind, 9)
''',
            "vent_utils.py": '''\
def vent_drop(pressure: int) -> int:
    return max(pressure - 258, 0)
''',
            "trip_utils.py": '''\
def overpressure(pressure: int) -> bool:
    return pressure > 700
''',
            "solution.py": '''\
from prio_utils import rank
from trip_utils import overpressure
from vent_utils import vent_drop


def run(events):
    state = "OFF"
    pressure = 0
    waste = 0
    for _, kind in sorted(events, key=lambda e: (e[0], rank(e[1]))):
        if state == "TRIP":
            break
        if kind == "ESTOP":
            state = "TRIP"
        elif kind == "FUEL":
            if state == "VENTING":
                waste += 1
            else:
                state = "RUN"
                pressure += 164
                if overpressure(pressure):
                    state = "TRIP"
        elif kind == "VENT":
            if state in ("RUN", "VENTING"):
                pressure = vent_drop(pressure)
                state = "OFF" if pressure == 0 else "VENTING"
            else:
                waste += 1
        if waste >= 3:
            state = "TRIP"
    return f"{state}|{pressure}|{waste}"
''',
        },
        "rules": """\
1. prio_utils.py must define `rank(kind: str) -> int` returning 0 for
   'ESTOP', 1 for 'VENT', 2 for 'FUEL' and 9 for anything else.
2. vent_utils.py must define `vent_drop(pressure: int) -> int` returning
   pressure minus 258, floored at 0.
3. trip_utils.py must define `overpressure(pressure: int) -> bool`
   returning True iff pressure is STRICTLY greater than 700.
4. solution.py must define `run(events: list) -> str` where each event is
   a tuple (timestamp, kind). First sort the events by timestamp; events
   sharing the SAME timestamp are ordered by rank(kind) (so 'ESTOP' beats
   'VENT' beats 'FUEL'). The reactor starts OFF with pressure 0 and a
   waste counter at 0. Then, for each event in that order:
   - Once the state is TRIP, every remaining event is ignored.
   - 'ESTOP': the state becomes TRIP.
   - 'FUEL' while VENTING: one waste is counted, nothing else changes.
     'FUEL' otherwise: the state becomes RUN and pressure rises by 164;
     if overpressure(pressure) the state immediately becomes TRIP.
   - 'VENT' while RUN or VENTING: pressure becomes vent_drop(pressure);
     the state becomes OFF when the new pressure is exactly 0, else
     VENTING. 'VENT' while OFF: one waste is counted.
   - After any event, when the waste counter reaches 3 the state becomes
     TRIP.
   - Return f'{state}|{pressure}|{waste}'.
""",
        "starter": '''\
def run(events: list) -> str:
    """Run the reactor protocol over a list of timestamped events."""
    raise NotImplementedError
''',
        "constants": ["'ESTOP'", "'VENT'", "'FUEL'", "9", "258", "700", "164", "3"],
        "tests": [
            ("test_helper_rank_estop", "from prio_utils import rank", "rank('ESTOP')"),
            ("test_helper_rank_vent", "from prio_utils import rank", "rank('VENT')"),
            ("test_helper_rank_fuel", "from prio_utils import rank", "rank('FUEL')"),
            ("test_helper_rank_other", "from prio_utils import rank", "rank('X')"),
            ("test_helper_vent_drop", "from vent_utils import vent_drop", "vent_drop(300)"),
            ("test_helper_vent_drop_floor", "from vent_utils import vent_drop", "vent_drop(100)"),
            ("test_helper_overpressure_edge", "from trip_utils import overpressure", "overpressure(700)"),
            ("test_empty_run", "from solution import run", "run([])"),
            ("test_single_fuel", "from solution import run", "run([(1, 'FUEL')])"),
            ("test_trip_on_overpressure", "from solution import run",
             "run([(i, 'FUEL') for i in range(5)])"),
            ("test_vent_to_off", "from solution import run",
             "run([(1, 'FUEL'), (2, 'VENT')])"),
            ("test_venting_state", "from solution import run",
             "run([(1, 'FUEL'), (2, 'FUEL'), (3, 'FUEL'), (4, 'VENT')])"),
            ("test_simultaneous_estop_wins", "from solution import run",
             "run([(5, 'FUEL'), (5, 'ESTOP')])"),
            ("test_waste_trips_reactor", "from solution import run",
             "run([(1, 'VENT'), (2, 'VENT'), (3, 'VENT'), (4, 'FUEL')])"),
        ],
    },
    {
        "tid": "x_parcel_locker",
        "opening": "You are asked to implement a parcel locker controller for a neighborhood delivery hub.",
        "files": {
            "code_utils.py": '''\
def code_ok(code: str) -> bool:
    return code.startswith("PX-") and len(code) == 8
''',
            "age_utils.py": '''\
def is_expired(age: int) -> bool:
    return age >= 4
''',
            "solution.py": '''\
from age_utils import is_expired
from code_utils import code_ok


def run(events):
    stored = {}
    depot = 0
    picked = 0
    errors = 0
    state = "ONLINE"
    for ev in events:
        if state == "OFFLINE":
            break
        if ev[0] == "drop":
            code = ev[1]
            if not code_ok(code) or code in stored or len(stored) >= 5:
                errors += 1
            else:
                stored[code] = 0
        elif ev[0] == "pick":
            code = ev[1]
            if code in stored:
                del stored[code]
                picked += 1
            else:
                errors += 1
        elif ev[0] == "tick":
            for code in list(stored):
                stored[code] += 1
            for code in list(stored):
                if is_expired(stored[code]):
                    del stored[code]
                    depot += 1
        if errors >= 3:
            state = "OFFLINE"
    return f"{state}|{len(stored)}|{picked}|{depot}|{errors}"
''',
        },
        "rules": """\
1. code_utils.py must define `code_ok(code: str) -> bool` returning True
   iff code starts with 'PX-' and len(code) is exactly 8.
2. age_utils.py must define `is_expired(age: int) -> bool` returning True
   iff age is at least 4.
3. solution.py must define `run(events: list) -> str`. The locker starts
   ONLINE and empty, with zero picked, depot and error counters. Events
   are ('drop', code), ('pick', code) or ('tick',):
   - 'drop': it is an error when code_ok(code) is False, OR the code is
     already stored, OR the locker already holds 5 parcels; otherwise the
     parcel is stored with age 0.
   - 'pick': removes the parcel and counts one pick when the code is
     stored; otherwise it is an error.
   - 'tick': FIRST every stored parcel ages by one, THEN every parcel
     whose age satisfies is_expired is removed and counted into the depot
     counter.
   - After any event, once the error counter reaches 3 the locker goes
     OFFLINE and every later event is ignored entirely.
   - Return f'{state}|{stored}|{picked}|{depot}|{errors}' where stored is
     the number of parcels currently held and state is 'ONLINE' or
     'OFFLINE'.
""",
        "starter": '''\
def run(events: list) -> str:
    """Run the parcel locker controller over a list of events."""
    raise NotImplementedError
''',
        "constants": ["'PX-'", "8", "5", "4", "3", "'OFFLINE'"],
        "tests": [
            ("test_helper_code_ok", "from code_utils import code_ok", "code_ok('PX-12345')"),
            ("test_helper_code_short", "from code_utils import code_ok", "code_ok('PX-1234')"),
            ("test_helper_code_prefix", "from code_utils import code_ok", "code_ok('QX-12345')"),
            ("test_helper_expired_edge", "from age_utils import is_expired", "is_expired(4)"),
            ("test_helper_not_expired", "from age_utils import is_expired", "is_expired(3)"),
            ("test_empty_run", "from solution import run", "run([])"),
            ("test_drop_and_pick", "from solution import run",
             "run([('drop', 'PX-11111'), ('pick', 'PX-11111')])"),
            ("test_expires_after_four_ticks", "from solution import run",
             "run([('drop', 'PX-11111')] + [('tick',)] * 4)"),
            ("test_survives_three_ticks", "from solution import run",
             "run([('drop', 'PX-11111')] + [('tick',)] * 3)"),
            ("test_duplicate_drop_error", "from solution import run",
             "run([('drop', 'PX-11111'), ('drop', 'PX-11111')])"),
            ("test_capacity_overflow_error", "from solution import run",
             "run([('drop', 'PX-11111'), ('drop', 'PX-11112'), ('drop', 'PX-11113'),"
             " ('drop', 'PX-11114'), ('drop', 'PX-11115'), ('drop', 'PX-11116')])"),
            ("test_offline_after_three_errors", "from solution import run",
             "run([('pick', 'PX-99999')] * 3 + [('drop', 'PX-11111')])"),
            ("test_invalid_code_drop_error", "from solution import run",
             "run([('drop', 'BAD')])"),
        ],
    },
    # ---------------------------------------------------- matching (4)
    {
        "tid": "x_berth_scheduler",
        "opening": "You are asked to implement a berth scheduler for a busy river port authority.",
        "files": {
            "fit_utils.py": '''\
def fits(draft: float, depth: float) -> bool:
    return draft + 0.75 <= depth
''',
            "order_utils.py": '''\
def ship_key(ship: tuple) -> tuple:
    return (-ship[2], -ship[1], ship[0])
''',
            "solution.py": '''\
from fit_utils import fits
from order_utils import ship_key

BERTHS = [("BS", 6.25), ("BR", 8.5), ("BQ", 11.75)]


def assign(ships):
    counts = {"BS": 0, "BR": 0, "BQ": 0}
    out = []
    for name, draft, priority in sorted(ships, key=ship_key):
        chosen = "ANCHOR"
        for berth, depth in BERTHS:
            if counts[berth] < 2 and fits(draft, depth):
                chosen = berth
                counts[berth] += 1
                break
        out.append((name, chosen))
    return out
''',
        },
        "rules": """\
1. fit_utils.py must define `fits(draft: float, depth: float) -> bool`
   returning True iff draft plus a safety clearance of 0.7500 is less than
   or equal to depth (the exact boundary fits).
2. order_utils.py must define `ship_key(ship: tuple) -> tuple` where ship
   is (name, draft, priority), returning (-priority, -draft, name) so that
   sorting processes higher priority first, then deeper draft, then name
   in ascending order.
3. solution.py must define `assign(ships: list) -> list`. The port has
   three berths tried in this fixed order, from shallowest to deepest:
   'BS' with depth 6.2500, 'BR' with depth 8.5000 and 'BQ' with depth
   11.7500. Each berth holds at most 2 ships. Process the ships sorted by
   ship_key; each ship takes the FIRST berth in the order above that both
   fits (per fit_utils) and still has space; a ship that fits nowhere gets
   'ANCHOR'. Return the list of (name, berth) tuples in processing order.
""",
        "starter": '''\
def assign(ships: list) -> list:
    """Assign each ship to a berth and return (name, berth) tuples."""
    raise NotImplementedError
''',
        "constants": ["0.7500", "'BS'", "6.2500", "'BR'", "8.5000",
                      "'BQ'", "11.7500", "2", "'ANCHOR'"],
        "tests": [
            ("test_helper_fits_exact_boundary", "from fit_utils import fits", "fits(5.5, 6.25)"),
            ("test_helper_fits_over_boundary", "from fit_utils import fits", "fits(5.51, 6.25)"),
            ("test_helper_ship_key", "from order_utils import ship_key", "ship_key(('X', 4.0, 2))"),
            ("test_empty_run", "from solution import assign", "assign([])"),
            ("test_small_ship_gets_shallowest", "from solution import assign",
             "assign([('a', 5.0, 1)])"),
            ("test_deep_draft_gets_deepest", "from solution import assign",
             "assign([('a', 9.5, 1)])"),
            ("test_too_deep_anchors", "from solution import assign",
             "assign([('a', 11.5, 1)])"),
            ("test_capacity_spillover", "from solution import assign",
             "assign([('a', 5.0, 1), ('b', 5.0, 1), ('c', 5.0, 1)])"),
            ("test_priority_first", "from solution import assign",
             "assign([('a', 5.0, 1), ('b', 5.0, 9)])"),
            ("test_draft_tiebreak", "from solution import assign",
             "assign([('a', 5.0, 1), ('b', 5.4, 1)])"),
            ("test_boundary_fit_in_solution", "from solution import assign",
             "assign([('a', 5.5, 1)])"),
            ("test_name_tiebreak", "from solution import assign",
             "assign([('b', 5.0, 1), ('a', 5.0, 1)])"),
        ],
    },
    {
        "tid": "x_courier_dispatch",
        "opening": "You are asked to implement a courier dispatch planner for a same-day logistics firm.",
        "files": {
            "job_utils.py": '''\
def job_key(job: tuple) -> tuple:
    jid, kg, urgent = job
    return (0 if urgent else 1, -kg, jid)
''',
            "pay_utils.py": '''\
def base_fee(kg: float) -> float:
    return 6.25 + kg * 0.41
''',
            "solution.py": '''\
from job_utils import job_key
from pay_utils import base_fee


def dispatch(jobs, couriers):
    state = {}
    order = []
    for cid, cap, rating in couriers:
        state[cid] = {"rem": cap, "rating": rating, "jobs": 0, "over": False}
        order.append(cid)
    assignments = []
    fee = 0.0
    for jid, kg, urgent in sorted(jobs, key=job_key):
        cands = []
        for cid in order:
            st = state[cid]
            if st["jobs"] >= 3:
                continue
            if urgent and st["rating"] < 2.15:
                continue
            if st["rem"] >= kg:
                cands.append((cid, False))
            elif urgent and not st["over"] and kg <= 87 and st["rem"] + 3.5 >= kg:
                cands.append((cid, True))
        if not cands:
            assignments.append((jid, "HOLD"))
            continue
        cid, over = min(
            cands,
            key=lambda c: (-state[c[0]]["rating"], -state[c[0]]["rem"], c[0]),
        )
        st = state[cid]
        st["rem"] -= kg
        st["jobs"] += 1
        if over:
            st["over"] = True
        fee += base_fee(kg)
        assignments.append((jid, cid))
    return (assignments, round(fee, 2))
''',
        },
        "rules": """\
1. job_utils.py must define `job_key(job: tuple) -> tuple` where job is
   (jid, kg, urgent), returning (0 if urgent else 1, -kg, jid) so that
   sorting processes urgent jobs first, then heavier jobs, then jid in
   ascending order.
2. pay_utils.py must define `base_fee(kg: float) -> float` returning
   6.2500 plus kg times 0.4100.
3. solution.py must define `dispatch(jobs: list, couriers: list) -> tuple`
   where each courier is (cid, capacity_kg, rating). Process the jobs
   sorted by job_key. For each job, a courier is eligible when ALL hold:
   - it has been assigned fewer than 3 jobs so far;
   - if the job is urgent, its rating is NOT strictly below 2.1500;
   - its remaining capacity covers the job's kg — except that an URGENT
     job may exceed the remaining capacity by at most 3.5000 kg, only if
     the job weighs at most 87 kg and that courier has never used the
     overload before in this run (the overload is spent only when the
     remaining capacity alone was insufficient).
   Among eligible couriers pick the highest rating; break ties by the most
   remaining capacity, then by cid ascending. Assign the job (remaining
   capacity drops by kg, possibly below zero on an overload) and add
   base_fee(kg) to the total fee. A job with no eligible courier is paired
   with 'HOLD' and costs nothing. Return (assignments, round(fee, 2))
   where assignments is the list of (jid, cid-or-'HOLD') in processing
   order.
""",
        "starter": '''\
def dispatch(jobs: list, couriers: list) -> tuple:
    """Assign jobs to couriers and return (assignments, total_fee)."""
    raise NotImplementedError
''',
        "constants": ["6.2500", "0.4100", "3.5000", "87", "2.1500", "3", "'HOLD'"],
        "tests": [
            ("test_helper_job_key_urgent", "from job_utils import job_key",
             "job_key(('j1', 10.0, True))"),
            ("test_helper_job_key_normal", "from job_utils import job_key",
             "job_key(('j1', 10.0, False))"),
            ("test_helper_base_fee", "from pay_utils import base_fee", "base_fee(10.0)"),
            ("test_empty_run", "from solution import dispatch",
             "dispatch([], [('c1', 50.0, 4.0)])"),
            ("test_simple_assign", "from solution import dispatch",
             "dispatch([('j1', 10.0, False)], [('c1', 50.0, 4.0)])"),
            ("test_hold_when_over_capacity", "from solution import dispatch",
             "dispatch([('j1', 60.0, False)], [('c1', 50.0, 4.0)])"),
            ("test_urgent_overload_allowed", "from solution import dispatch",
             "dispatch([('j1', 53.0, True)], [('c1', 50.0, 4.0)])"),
            ("test_overload_only_once", "from solution import dispatch",
             "dispatch([('j1', 53.0, True), ('j2', 53.0, True), ('j3', 53.0, True)],"
             " [('c1', 105.0, 4.0)])"),
            ("test_heavy_urgent_no_overload", "from solution import dispatch",
             "dispatch([('j1', 90.0, True)], [('c1', 88.0, 4.0)])"),
            ("test_low_rating_rejects_urgent", "from solution import dispatch",
             "dispatch([('j1', 10.0, True)], [('c1', 50.0, 2.0)])"),
            ("test_rating_tiebreak", "from solution import dispatch",
             "dispatch([('j1', 10.0, False)], [('c1', 50.0, 3.0), ('c2', 50.0, 4.0)])"),
            ("test_capacity_tiebreak", "from solution import dispatch",
             "dispatch([('j1', 10.0, False)], [('c1', 50.0, 4.0), ('c2', 60.0, 4.0)])"),
            ("test_job_limit_three", "from solution import dispatch",
             "dispatch([('j1', 1.0, False), ('j2', 1.0, False), ('j3', 1.0, False),"
             " ('j4', 1.0, False)], [('c1', 50.0, 4.0)])"),
            ("test_urgent_processed_first", "from solution import dispatch",
             "dispatch([('j2', 10.0, False), ('j1', 5.0, True)], [('c1', 50.0, 4.0)])"),
        ],
    },
    {
        "tid": "x_grant_allocator",
        "opening": "You are asked to implement a grant allocation engine for a community foundation.",
        "files": {
            "score_utils.py": '''\
def adj_score(org: str, score: int) -> int:
    if org.startswith("NG-"):
        return score + 7
    return score
''',
            "cap_utils.py": '''\
def capped(amount: float) -> float:
    return min(amount, 12500.0)
''',
            "solution.py": '''\
from cap_utils import capped
from score_utils import adj_score


def _fee(grant):
    return round(grant * 0.018, 2)


def allocate(requests, budget):
    funded = []
    partial_used = False
    ordered = sorted(
        requests, key=lambda r: (-adj_score(r[0], r[2]), r[1], r[0])
    )
    for org, amount, score in ordered:
        if adj_score(org, score) < 41:
            continue
        amt = capped(amount)
        if amt >= 750 and budget >= amt + _fee(amt):
            grant = amt
        elif not partial_used:
            partial_used = True
            part = round(amt * 0.62, 2)
            if part >= 750 and budget >= part + _fee(part):
                grant = part
            else:
                continue
        else:
            continue
        budget -= grant + _fee(grant)
        funded.append((org, grant))
    return (funded, round(budget, 2))
''',
        },
        "rules": """\
1. score_utils.py must define `adj_score(org: str, score: int) -> int`
   returning score plus a bonus of 7 when org starts with 'NG-', else the
   raw score.
2. cap_utils.py must define `capped(amount: float) -> float` returning the
   amount clamped at a ceiling of 12500.0.
3. solution.py must define `allocate(requests: list, budget: float) ->
   tuple` where each request is (org, amount, score). Sort the requests by
   adj_score descending, then amount ascending, then org ascending, and
   process in that order:
   - Requests whose adj_score is STRICTLY below 41 are skipped entirely.
   - Let amt = capped(amount). Paying a grant g also costs a processing
     fee of round(g * 0.0180, 2) taken from the same budget.
   - Full funding: pay amt when amt is at least 750 and the budget covers
     amt plus its fee.
   - Otherwise, a ONE-TIME partial option (usable at most once per whole
     run, and CONSUMED whenever this branch is attempted): pay
     round(amt * 0.6200, 2) if that value is at least 750 and the budget
     covers it plus its fee; if not, the request gets nothing.
   - Requests reached after the partial option was consumed and that
     cannot be fully funded get nothing.
   - Return (funded, round(budget, 2)) where funded lists (org, grant) in
     payment order.
""",
        "starter": '''\
def allocate(requests: list, budget: float) -> tuple:
    """Allocate the budget across grant requests."""
    raise NotImplementedError
''',
        "constants": ["'NG-'", "7", "12500", "41", "0.0180", "750", "0.6200"],
        "tests": [
            ("test_helper_bonus_applied", "from score_utils import adj_score",
             "adj_score('NG-X', 40)"),
            ("test_helper_bonus_not_applied", "from score_utils import adj_score",
             "adj_score('AC-X', 40)"),
            ("test_helper_cap_applied", "from cap_utils import capped", "capped(20000.0)"),
            ("test_helper_cap_not_applied", "from cap_utils import capped", "capped(1000.0)"),
            ("test_empty_run", "from solution import allocate", "allocate([], 5000.0)"),
            ("test_simple_full_funding", "from solution import allocate",
             "allocate([('AC-A', 1000.0, 80)], 5000.0)"),
            ("test_low_score_skipped", "from solution import allocate",
             "allocate([('AC-A', 1000.0, 40)], 5000.0)"),
            ("test_bonus_crosses_threshold", "from solution import allocate",
             "allocate([('NG-A', 1000.0, 36)], 5000.0)"),
            ("test_ceiling_applied", "from solution import allocate",
             "allocate([('AC-A', 20000.0, 80)], 20000.0)"),
            ("test_partial_funding", "from solution import allocate",
             "allocate([('AC-A', 2000.0, 80)], 1500.0)"),
            ("test_partial_only_once", "from solution import allocate",
             "allocate([('AC-A', 2000.0, 80), ('AC-B', 2000.0, 80)], 2600.0)"),
            ("test_minimum_grant", "from solution import allocate",
             "allocate([('AC-A', 600.0, 80)], 5000.0)"),
            ("test_sort_order", "from solution import allocate",
             "allocate([('AC-B', 800.0, 80), ('AC-A', 900.0, 90), ('AC-C', 800.0, 80)],"
             " 10000.0)"),
        ],
    },
    {
        "tid": "x_court_scheduler",
        "opening": "You are asked to implement a courtroom scheduler for a district judicial office.",
        "files": {
            "room_utils.py": '''\
def room_cap(room: str) -> int:
    if room == "RA":
        return 300
    if room == "RB":
        return 195
    return 0
''',
            "case_utils.py": '''\
def case_key(case: tuple) -> tuple:
    cid, minutes, custody = case
    return (0 if custody else 1, -minutes, cid)
''',
            "solution.py": '''\
from case_utils import case_key
from room_utils import room_cap


def schedule(cases):
    rem = {"RA": room_cap("RA"), "RB": room_cap("RB")}
    out = []
    for cid, minutes, custody in sorted(cases, key=case_key):
        need = minutes + (15 if custody else 0)
        rooms = ["RA"] if minutes > 120 else ["RA", "RB"]
        best = None
        for room in rooms:
            if rem[room] >= need and (best is None or rem[room] > rem[best]):
                best = room
        if best is None:
            out.append((cid, "DEFER"))
        else:
            rem[best] -= need
            out.append((cid, best))
    return (out, rem["RA"], rem["RB"])
''',
        },
        "rules": """\
1. room_utils.py must define `room_cap(room: str) -> int` returning 300
   for room 'RA', 195 for room 'RB' and 0 for anything else.
2. case_utils.py must define `case_key(case: tuple) -> tuple` where case
   is (cid, minutes, custody), returning (0 if custody else 1, -minutes,
   cid) so that sorting processes custody cases first, then longer cases,
   then cid ascending.
3. solution.py must define `schedule(cases: list) -> tuple`. Both rooms
   start with their full capacity in minutes. Process the cases sorted by
   case_key:
   - A custody case consumes its minutes PLUS a security buffer of 15
     minutes of room capacity.
   - A case STRICTLY longer than 120 minutes may only sit in room 'RA'.
   - Among the allowed rooms with enough remaining capacity, pick the one
     with the MOST remaining minutes; on an exact tie pick 'RA'.
   - A case that fits nowhere is paired with 'DEFER'.
   - Return (assignments, remaining_RA, remaining_RB) where assignments is
     the list of (cid, room-or-'DEFER') in processing order.
""",
        "starter": '''\
def schedule(cases: list) -> tuple:
    """Schedule hearings into courtrooms and return the plan."""
    raise NotImplementedError
''',
        "constants": ["'RA'", "'RB'", "300", "195", "15", "120", "'DEFER'"],
        "tests": [
            ("test_helper_cap_ra", "from room_utils import room_cap", "room_cap('RA')"),
            ("test_helper_cap_rb", "from room_utils import room_cap", "room_cap('RB')"),
            ("test_helper_cap_other", "from room_utils import room_cap", "room_cap('RC')"),
            ("test_helper_case_key", "from case_utils import case_key",
             "case_key(('c1', 60, True))"),
            ("test_empty_run", "from solution import schedule", "schedule([])"),
            ("test_single_case_prefers_ra", "from solution import schedule",
             "schedule([('c1', 60, False)])"),
            ("test_three_cases_balance", "from solution import schedule",
             "schedule([('c1', 60, False), ('c2', 60, False), ('c3', 60, False)])"),
            ("test_long_case_only_ra", "from solution import schedule",
             "schedule([('c1', 130, False)])"),
            ("test_long_case_defers_when_ra_full", "from solution import schedule",
             "schedule([('c0', 250, False), ('c1', 130, False)])"),
            ("test_custody_buffer_exact_fit", "from solution import schedule",
             "schedule([('c1', 285, True)])"),
            ("test_custody_buffer_defer", "from solution import schedule",
             "schedule([('c1', 290, True)])"),
            ("test_custody_processed_first", "from solution import schedule",
             "schedule([('c1', 60, False), ('c2', 50, True)])"),
        ],
    },
    # --------------------------------------------------- validators (4)
    {
        "tid": "x_plate_validator",
        "opening": "You are asked to implement a license plate validator for a vehicle registry bureau.",
        "files": {
            "norm_utils.py": '''\
def normalize(raw: str) -> str:
    s = raw.replace(" ", "").replace("-", "")
    s = s.upper()
    return s.replace("O", "0").replace("I", "1")
''',
            "rank_utils.py": '''\
ALPHABET = "BCDFGHJKLMNPQRSTVWXZ"


def rank(ch: str) -> int:
    return ALPHABET.find(ch)
''',
            "solution.py": '''\
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
        "rules": """\
1. norm_utils.py must define `normalize(raw: str) -> str` applying these
   steps in this exact order: first remove every space and every hyphen,
   then uppercase the string, then replace every 'O' with '0' and every
   'I' with '1' (the order matters: lowercase letters must be uppercased
   BEFORE the digit substitution).
2. rank_utils.py must define `rank(ch: str) -> int` returning the index of
   ch in the restricted alphabet 'BCDFGHJKLMNPQRSTVWXZ', or the value
   negative one when ch is not in it.
3. solution.py must define `validate(raw: str) -> str`. Let s be
   normalize(raw); apply the checks in this exact order, returning at the
   FIRST failure:
   - len(s) must be exactly 7, else return 'E_LEN'.
   - Characters at positions two through five (0-based) must all be
     digits, else return 'E_DIG'.
   - The first, second and last characters must all be in the restricted
     alphabet (rank not negative), else return 'E_ALPHA'.
   - Checksum: (rank of first + rank of second) * 5 plus (sum of the four
     digits) * 11, taken modulo 20, must equal the rank of the LAST
     character, else return 'E_CHK'.
   - Otherwise return 'OK-' followed by s.
""",
        "starter": '''\
def validate(raw: str) -> str:
    """Validate a raw license plate string and return a status code."""
    raise NotImplementedError
''',
        "constants": ["'BCDFGHJKLMNPQRSTVWXZ'", "7", "5", "11", "20",
                      "'E_LEN'", "'E_DIG'", "'E_ALPHA'", "'E_CHK'", "'OK-'"],
        "tests": [
            ("test_helper_normalize_strips", "from norm_utils import normalize",
             "normalize('ab - c')"),
            ("test_helper_normalize_order_matters", "from norm_utils import normalize",
             "normalize('go1')"),
            ("test_helper_rank_first", "from rank_utils import rank", "rank('B')"),
            ("test_helper_rank_last", "from rank_utils import rank", "rank('Z')"),
            ("test_helper_rank_missing", "from rank_utils import rank", "rank('A')"),
            ("test_valid_plate", "from solution import validate", "validate('BC2345Z')"),
            ("test_valid_after_normalization", "from solution import validate",
             "validate('bc 2345z')"),
            ("test_valid_with_letter_o", "from solution import validate",
             "validate('bco245j')"),
            ("test_length_error", "from solution import validate", "validate('BC234Z')"),
            ("test_digit_error", "from solution import validate", "validate('BCX345Z')"),
            ("test_alpha_error_head", "from solution import validate", "validate('AC2345Z')"),
            ("test_checksum_error", "from solution import validate", "validate('BC2345X')"),
            ("test_alpha_error_tail", "from solution import validate", "validate('BC23450')"),
        ],
    },
    {
        "tid": "x_voucher_parser",
        "opening": "You are asked to implement a voucher code parser for a retail promotions platform.",
        "files": {
            "kind_utils.py": '''\
def base(kind: str) -> int:
    values = {"VXA": 250, "VXB": 475, "VXQ": 60}
    return values.get(kind, -1)
''',
            "char_utils.py": '''\
ALPHABET = "2346789ACDEFGH"


def char_index(ch: str) -> int:
    return ALPHABET.find(ch)
''',
            "solution.py": '''\
from char_utils import char_index
from kind_utils import base


def parse(code):
    parts = code.split("-")
    if len(parts) != 3:
        return "BAD_SEG"
    kind, body, chk = parts
    value = base(kind)
    if value < 0:
        return "BAD_KIND"
    if len(body) != 4 or any(char_index(c) < 0 for c in body):
        return "BAD_CHAR"
    idxsum = sum(char_index(c) for c in body)
    if chk != f"{(idxsum * 13) % 89:02d}":
        return "BAD_SUM"
    return f"{kind}:{value + idxsum * 3}"
''',
        },
        "rules": """\
1. kind_utils.py must define `base(kind: str) -> int` returning 250 for
   'VXA', 475 for 'VXB', 60 for 'VXQ' and negative one otherwise.
2. char_utils.py must define `char_index(ch: str) -> int` returning the
   index of ch in the restricted alphabet '2346789ACDEFGH', or negative
   one when ch is not in it.
3. solution.py must define `parse(code: str) -> str`, applying the checks
   in this exact order and returning at the FIRST failure:
   - Split code on '-': there must be exactly three segments, else return
     'BAD_SEG'.
   - The first segment must have a known base (per kind_utils), else
     return 'BAD_KIND'.
   - The second segment must have exactly 4 characters, all from the
     restricted alphabet, else return 'BAD_CHAR'.
   - Let idxsum be the sum of the char_index values of the body. The third
     segment must be EXACTLY the string f'{(idxsum * 13) % 89:02d}' (two
     characters, zero-padded), else return 'BAD_SUM'.
   - Otherwise return f'{kind}:{amount}' where amount = base(kind) plus
     idxsum times 3.
""",
        "starter": '''\
def parse(code: str) -> str:
    """Parse a voucher code and return its value or an error code."""
    raise NotImplementedError
''',
        "constants": ["'VXA'", "'VXB'", "'VXQ'", "250", "475", "60",
                      "'2346789ACDEFGH'", "13", "89", "3", "'BAD_KIND'", "'BAD_SUM'"],
        "tests": [
            ("test_helper_base_vxa", "from kind_utils import base", "base('VXA')"),
            ("test_helper_base_vxb", "from kind_utils import base", "base('VXB')"),
            ("test_helper_base_vxq", "from kind_utils import base", "base('VXQ')"),
            ("test_helper_base_unknown", "from kind_utils import base", "base('XXX')"),
            ("test_helper_index_first", "from char_utils import char_index", "char_index('2')"),
            ("test_helper_index_last", "from char_utils import char_index", "char_index('H')"),
            ("test_helper_index_excluded", "from char_utils import char_index", "char_index('B')"),
            ("test_valid_voucher", "from solution import parse", "parse('VXA-2346-78')"),
            ("test_valid_voucher_high_sum", "from solution import parse", "parse('VXQ-HH99-49')"),
            ("test_missing_segment", "from solution import parse", "parse('VXA-2346')"),
            ("test_unknown_kind", "from solution import parse", "parse('VXZ-2346-78')"),
            ("test_bad_body_char", "from solution import parse", "parse('VXA-23B6-78')"),
            ("test_bad_checksum", "from solution import parse", "parse('VXA-2346-77')"),
            ("test_checksum_must_be_zero_padded", "from solution import parse",
             "parse('VXB-2347-2')"),
        ],
    },
    {
        "tid": "x_scale_barcode",
        "opening": "You are asked to implement a scale barcode parser for a grocery point of sale system.",
        "files": {
            "digit_utils.py": '''\
def digit_sum(s: str) -> int:
    return sum(int(ch) for ch in s)
''',
            "chk_utils.py": '''\
from digit_utils import digit_sum


def price_check(price_digits: str) -> int:
    return (digit_sum(price_digits) * 7) % 10
''',
            "solution.py": '''\
from chk_utils import price_check


def parse(barcode):
    s = barcode.replace(" ", "")
    if len(s) != 13 or not s.isdigit():
        return "B_LEN"
    if not s.startswith("27"):
        return "B_PFX"
    if price_check(s[7:12]) != int(s[12]):
        return "B_CHK"
    return (s[2:7], round(int(s[7:12]) / 100, 2))
''',
        },
        "rules": """\
1. digit_utils.py must define `digit_sum(s: str) -> int` returning the sum
   of the integer values of the digits of s.
2. chk_utils.py must define `price_check(price_digits: str) -> int`
   returning digit_sum(price_digits) times 7, taken modulo 10.
3. solution.py must define `parse(barcode: str)`, applying the checks in
   this exact order and returning at the FIRST failure:
   - Remove every space, then the result must have exactly 13 characters,
     all digits, else return 'B_LEN'.
   - It must start with the prefix '27', else return 'B_PFX'.
   - The five characters starting at position 7 (0-based) encode the price
     in cents; the character at position 12 must equal
     price_check(those five characters), else return 'B_CHK'.
   - Otherwise return the tuple (item, price) where item is the five
     characters starting at position 2 (kept as a string) and price is
     round(cents / 100, 2).
""",
        "starter": '''\
def parse(barcode: str):
    """Parse a variable-weight barcode into (item, price) or an error."""
    raise NotImplementedError
''',
        "constants": ["13", "'27'", "7", "10", "12", "100",
                      "'B_LEN'", "'B_PFX'", "'B_CHK'"],
        "tests": [
            ("test_helper_digit_sum", "from digit_utils import digit_sum", "digit_sum('123')"),
            ("test_helper_price_check", "from chk_utils import price_check",
             "price_check('01995')"),
            ("test_helper_price_check_zero", "from chk_utils import price_check",
             "price_check('00000')"),
            ("test_valid_barcode", "from solution import parse", "parse('2712345019958')"),
            ("test_spaces_are_stripped", "from solution import parse",
             "parse('27 12345 01995 8')"),
            ("test_short_barcode", "from solution import parse", "parse('271234501995')"),
            ("test_non_digit_barcode", "from solution import parse", "parse('27123450199a8')"),
            ("test_wrong_prefix", "from solution import parse", "parse('2812345019958')"),
            ("test_wrong_check_digit", "from solution import parse", "parse('2712345019957')"),
            ("test_zero_price", "from solution import parse", "parse('2754321000000')"),
            ("test_small_price_cents", "from solution import parse", "parse('2704242000422')"),
        ],
    },
    {
        "tid": "x_chem_batch",
        "opening": "You are asked to implement a batch code validator for a chemical laboratory network.",
        "files": {
            "clean_utils.py": '''\
def clean(code: str) -> str:
    s = code.strip()
    s = s.upper()
    return s.replace("-", "")
''',
            "sig_utils.py": '''\
LETTERS = "ABCDEFGHJK"


def sig_char(digit_total: int) -> str:
    return LETTERS[digit_total % 10]
''',
            "solution.py": '''\
from clean_utils import clean
from sig_utils import sig_char


def validate(code):
    s = clean(code)
    if len(s) != 10 or not s.startswith("LB"):
        return "C_FMT"
    lab = s[2:4]
    if lab not in ("QN", "TR", "VX"):
        return "C_LAB"
    digits = s[4:9]
    if not digits.isdigit():
        return "C_DIG"
    total = sum(int(ch) for ch in digits)
    if s[9] != sig_char(total):
        return "C_SIG"
    return "OK/" + lab + digits
''',
        },
        "rules": """\
1. clean_utils.py must define `clean(code: str) -> str` applying these
   steps in this exact order: strip leading and trailing whitespace, then
   uppercase the string, then remove every hyphen.
2. sig_utils.py must define `sig_char(digit_total: int) -> str` returning
   the character at position digit_total modulo 10 of the signature
   alphabet 'ABCDEFGHJK'.
3. solution.py must define `validate(code: str) -> str`. Let s be
   clean(code); apply the checks in this exact order, returning at the
   FIRST failure:
   - len(s) must be exactly 10 and s must start with 'LB', else return
     'C_FMT'.
   - The two characters after the prefix name the lab and must be 'QN',
     'TR' or 'VX', else return 'C_LAB'.
   - The next five characters must all be digits, else return 'C_DIG'.
   - The final character must equal sig_char(sum of those five digits),
     else return 'C_SIG'.
   - Otherwise return 'OK/' followed by the lab and the five digits.
""",
        "starter": '''\
def validate(code: str) -> str:
    """Validate a chemical batch code and return a status string."""
    raise NotImplementedError
''',
        "constants": ["'LB'", "'QN'", "'TR'", "'VX'", "'ABCDEFGHJK'", "10",
                      "'C_FMT'", "'C_LAB'", "'C_DIG'", "'C_SIG'", "'OK/'"],
        "tests": [
            ("test_helper_clean_order", "from clean_utils import clean", "clean(' lb-qn ')"),
            ("test_helper_sig_mid", "from sig_utils import sig_char", "sig_char(15)"),
            ("test_helper_sig_zero", "from sig_utils import sig_char", "sig_char(0)"),
            ("test_helper_sig_wraps", "from sig_utils import sig_char", "sig_char(23)"),
            ("test_valid_code", "from solution import validate", "validate('LBQN12345F')"),
            ("test_valid_after_cleaning", "from solution import validate",
             "validate(' lb-qn-12345f ')"),
            ("test_short_code", "from solution import validate", "validate('LBQN1234F')"),
            ("test_wrong_prefix", "from solution import validate", "validate('XBQN12345F')"),
            ("test_unknown_lab", "from solution import validate", "validate('LBZZ12345F')"),
            ("test_non_digit_block", "from solution import validate", "validate('LBQN12a45F')"),
            ("test_wrong_signature", "from solution import validate", "validate('LBQN12345G')"),
        ],
    },
    # ------------------------------------------------------ ledgers (4)
    {
        "tid": "x_loyalty_ledger",
        "opening": "You are asked to implement a loyalty points ledger for an airline rewards program.",
        "files": {
            "bonus_utils.py": '''\
def bonus(pts: int) -> int:
    if pts > 500:
        return int(pts * 0.15)
    return 0
''',
            "lot_utils.py": '''\
from bonus_utils import bonus


def lot_size(pts: int) -> int:
    return min(pts + bonus(pts), 3000)
''',
            "expiry_utils.py": '''\
def usable(earn_day: int, day: int) -> bool:
    return day - earn_day < 90
''',
            "solution.py": '''\
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
        "rules": """\
1. bonus_utils.py must define `bonus(pts: int) -> int` returning
   int(pts * 0.1500) (truncated) when pts is STRICTLY greater than 500,
   else 0.
2. lot_utils.py must define `lot_size(pts: int) -> int` returning
   pts plus bonus(pts), clamped at a ceiling of 3000.
3. expiry_utils.py must define `usable(earn_day: int, day: int) -> bool`
   returning True iff day minus earn_day is STRICTLY less than 90.
4. solution.py must define `settle(events: list) -> str`. The ledger keeps
   a FIFO list of point lots, each remembering its earn day. Events are
   ('earn', pts, day) or ('spend', pts, day), already in chronological
   order. BEFORE processing each event, sweep the lots: every lot that is
   no longer usable at the event's day is removed and its remaining points
   are added to an expired counter. Then:
   - 'earn': append a new lot of lot_size(pts) points.
   - 'spend': a spend of STRICTLY more than 2000 points is rejected
     outright. Otherwise the total cost is pts plus a redemption fee of
     25 points; if the usable balance cannot cover the whole cost the
     spend is rejected (nothing is consumed); otherwise consume the cost
     from the OLDEST lots first.
   - Return f'{balance}|{rejected}|{expired}' where balance is the sum of
     the remaining lots after the last event.
""",
        "starter": '''\
def settle(events: list) -> str:
    """Settle a chronological list of loyalty ledger events."""
    raise NotImplementedError
''',
        "constants": ["0.1500", "500", "3000", "90", "2000", "25"],
        "tests": [
            ("test_helper_bonus_applied", "from bonus_utils import bonus", "bonus(600)"),
            ("test_helper_bonus_edge", "from bonus_utils import bonus", "bonus(500)"),
            ("test_helper_lot_size", "from lot_utils import lot_size", "lot_size(600)"),
            ("test_helper_lot_ceiling", "from lot_utils import lot_size", "lot_size(4000)"),
            ("test_helper_usable_edge_in", "from expiry_utils import usable", "usable(0, 89)"),
            ("test_helper_usable_edge_out", "from expiry_utils import usable", "usable(0, 90)"),
            ("test_empty_run", "from solution import settle", "settle([])"),
            ("test_earn_and_spend", "from solution import settle",
             "settle([('earn', 100, 0), ('spend', 50, 10)])"),
            ("test_fee_blocks_spend", "from solution import settle",
             "settle([('earn', 100, 0), ('spend', 80, 10)])"),
            ("test_expiry_before_spend", "from solution import settle",
             "settle([('earn', 100, 0), ('spend', 10, 90)])"),
            ("test_fifo_consumption", "from solution import settle",
             "settle([('earn', 100, 0), ('earn', 100, 50), ('spend', 80, 60)])"),
            ("test_expiry_keeps_younger_lot", "from solution import settle",
             "settle([('earn', 100, 0), ('earn', 100, 50), ('spend', 50, 95)])"),
            ("test_oversize_spend_rejected", "from solution import settle",
             "settle([('earn', 2500, 0), ('spend', 2001, 1)])"),
        ],
    },
    {
        "tid": "x_prepaid_meter",
        "opening": "You are asked to implement a prepaid meter controller for an electricity utility.",
        "files": {
            "tariff_utils.py": '''\
def energy_cost(kwh: float) -> float:
    if kwh <= 45:
        return kwh * 0.8342
    return 45 * 0.8342 + (kwh - 45) * 1.1074
''',
            "credit_utils.py": '''\
def can_serve(balance: float, cost: float) -> bool:
    return balance - cost >= -15.0
''',
            "solution.py": '''\
from credit_utils import can_serve
from tariff_utils import energy_cost


def run(events):
    balance = 0.0
    state = "ON"
    cuts = 0
    for ev in events:
        if ev[0] == "topup":
            balance += ev[1]
            if state == "OFF" and ev[1] >= 20.0:
                state = "ON"
                balance -= 11.35
        else:
            if state == "OFF":
                continue
            cost = energy_cost(ev[1])
            if can_serve(balance, cost):
                balance -= cost
            else:
                state = "OFF"
                cuts += 1
    return f"{state}|{balance:.2f}|{cuts}"
''',
        },
        "rules": """\
1. tariff_utils.py must define `energy_cost(kwh: float) -> float`: within
   a single use, the first 45 kWh cost 0.8342 per kWh and every kWh above
   that costs 1.1074 per kWh.
2. credit_utils.py must define `can_serve(balance: float, cost: float) ->
   bool` returning True iff balance minus cost is greater than or equal to
   -15.0 (the emergency credit floor; the exact floor is allowed).
3. solution.py must define `run(events: list) -> str`. The meter starts ON
   with balance 0.0 and zero cuts. Events are ('topup', amount) or
   ('use', kwh):
   - 'use' while OFF is ignored entirely.
   - 'use' while ON: let cost = energy_cost(kwh). If can_serve(balance,
     cost), subtract the cost (the balance may go negative down to the
     emergency floor). Otherwise the use is rejected in full, the meter
     goes OFF and one cut is counted.
   - 'topup': the amount is always added to the balance. If the meter is
     OFF and this single top-up is at least 20.0, the meter turns back ON
     and a reconnection fee of 11.35 is subtracted (smaller top-ups never
     restore power, no matter the accumulated balance).
   - Return f'{state}|{balance:.2f}|{cuts}' where state is 'ON' or 'OFF'.
""",
        "starter": '''\
def run(events: list) -> str:
    """Run the prepaid meter controller over a list of events."""
    raise NotImplementedError
''',
        "constants": ["0.8342", "1.1074", "45", "15.0", "20.0", "11.35"],
        "tests": [
            ("test_helper_cost_low_tier", "from tariff_utils import energy_cost",
             "energy_cost(10)"),
            ("test_helper_cost_tier_edge", "from tariff_utils import energy_cost",
             "energy_cost(45)"),
            ("test_helper_cost_two_tiers", "from tariff_utils import energy_cost",
             "energy_cost(50)"),
            ("test_helper_can_serve_floor", "from credit_utils import can_serve",
             "can_serve(0.0, 15.0)"),
            ("test_helper_cannot_serve_past_floor", "from credit_utils import can_serve",
             "can_serve(0.0, 15.01)"),
            ("test_empty_run", "from solution import run", "run([])"),
            ("test_topup_then_use", "from solution import run",
             "run([('topup', 50.0), ('use', 10)])"),
            ("test_emergency_credit", "from solution import run", "run([('use', 10)])"),
            ("test_cut_when_past_floor", "from solution import run", "run([('use', 20)])"),
            ("test_use_while_off_ignored", "from solution import run",
             "run([('use', 20), ('use', 1)])"),
            ("test_small_topup_never_restores", "from solution import run",
             "run([('use', 20), ('topup', 10.0)])"),
            ("test_restore_charges_fee", "from solution import run",
             "run([('use', 20), ('topup', 30.0)])"),
            ("test_cumulative_topups_do_not_restore", "from solution import run",
             "run([('use', 20), ('topup', 10.0), ('topup', 10.0)])"),
        ],
    },
    {
        "tid": "x_escrow_ledger",
        "opening": "You are asked to implement an escrow ledger reconciler for a payments processor.",
        "files": {
            "fee_utils.py": '''\
def capture_fee(amount: float) -> float:
    return round(amount * 0.029, 2)
''',
            "hold_utils.py": '''\
def trim(amount: float) -> float:
    return min(amount, 2500.0)
''',
            "solution.py": '''\
from fee_utils import capture_fee
from hold_utils import trim


def reconcile(entries):
    holds = {}
    captured = 0.0
    fees = 0.0
    errors = 0
    state = "OPEN"
    for entry in entries:
        if state == "FROZEN":
            break
        if entry[0] == "hold":
            _, hid, amount = entry
            if hid in holds:
                errors += 1
            else:
                holds[hid] = {"rem": trim(amount), "captures": 0, "void": False}
        elif entry[0] == "capture":
            _, hid, amount = entry
            hold = holds.get(hid)
            if (hold is None or hold["void"] or amount < 5.0
                    or amount > hold["rem"]):
                errors += 1
            else:
                hold["rem"] -= amount
                hold["captures"] += 1
                captured += amount
                fees += capture_fee(amount)
        elif entry[0] == "void":
            _, hid = entry
            hold = holds.get(hid)
            if hold is None or hold["void"]:
                errors += 1
            else:
                hold["void"] = True
                if hold["captures"] == 0:
                    fees += 1.45
                hold["rem"] = 0.0
        if errors >= 4:
            state = "FROZEN"
    held_open = sum(h["rem"] for h in holds.values())
    return f"{state}|{captured:.2f}|{held_open:.2f}|{fees:.2f}|{errors}"
''',
        },
        "rules": """\
1. fee_utils.py must define `capture_fee(amount: float) -> float`
   returning round(amount * 0.0290, 2).
2. hold_utils.py must define `trim(amount: float) -> float` returning the
   amount clamped at a ceiling of 2500.0.
3. solution.py must define `reconcile(entries: list) -> str`. Entries are
   ('hold', hid, amount), ('capture', hid, amount) or ('void', hid):
   - 'hold': registering an id that already exists is an error; otherwise
     the hold opens with a remaining amount of trim(amount) and zero
     captures.
   - 'capture': it is an error when the hold id is unknown, OR the hold
     was voided, OR the amount is STRICTLY below the minimum of 5.0, OR
     the amount exceeds the hold's remaining amount. Otherwise the
     remaining amount drops by the captured amount, the captured total
     rises by it, and capture_fee(amount) is added to the fee total
     (several captures may hit the same hold).
   - 'void': it is an error when the hold id is unknown or already voided.
     Otherwise the hold is voided, its remaining amount becomes 0.0, and
     when the hold had ZERO captures a flat void fee of 1.4500 is added to
     the fee total.
   - After any entry, once the error counter reaches 4 the ledger becomes
     FROZEN and every later entry is ignored entirely.
   - Return f'{state}|{captured:.2f}|{held_open:.2f}|{fees:.2f}|{errors}'
     where held_open sums the remaining amounts of all holds and state is
     'OPEN' or 'FROZEN'.
""",
        "starter": '''\
def reconcile(entries: list) -> str:
    """Reconcile an escrow ledger from a list of entries."""
    raise NotImplementedError
''',
        "constants": ["0.0290", "2500.0", "5.0", "1.4500", "4", "'FROZEN'"],
        "tests": [
            ("test_helper_capture_fee", "from fee_utils import capture_fee",
             "capture_fee(100.0)"),
            ("test_helper_capture_fee_rounds", "from fee_utils import capture_fee",
             "capture_fee(33.33)"),
            ("test_helper_trim_applied", "from hold_utils import trim", "trim(3000.0)"),
            ("test_helper_trim_not_applied", "from hold_utils import trim", "trim(100.0)"),
            ("test_empty_run", "from solution import reconcile", "reconcile([])"),
            ("test_hold_and_capture", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 40.0)])"),
            ("test_capture_beyond_remaining_error", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 60.0),"
             " ('capture', 'h1', 40.0), ('capture', 'h1', 10.0)])"),
            ("test_minimum_capture", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 4.99)])"),
            ("test_void_after_capture_no_fee", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 40.0), ('void', 'h1')])"),
            ("test_void_without_capture_fee", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('void', 'h1')])"),
            ("test_capture_after_void_error", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('void', 'h1'), ('capture', 'h1', 10.0)])"),
            ("test_hold_ceiling", "from solution import reconcile",
             "reconcile([('hold', 'h1', 3000.0), ('capture', 'h1', 2500.0)])"),
            ("test_frozen_after_four_errors", "from solution import reconcile",
             "reconcile([('capture', 'x', 10.0)] * 4 + [('hold', 'h1', 100.0)])"),
            ("test_duplicate_hold_error", "from solution import reconcile",
             "reconcile([('hold', 'h1', 100.0), ('hold', 'h1', 50.0)])"),
        ],
    },
    {
        "tid": "x_hours_bank",
        "opening": "You are asked to implement an hours bank ledger for a staffing agency payroll team.",
        "files": {
            "id_utils.py": '''\
def emp_ok(emp: str) -> bool:
    return emp.startswith("EM-")
''',
            "hours_utils.py": '''\
def credited(hours: float, night: bool) -> float:
    if hours > 8:
        base = 8 + (hours - 8) * 1.5
    else:
        base = hours
    if night:
        base = base * 1.25
    return base
''',
            "solution.py": '''\
from hours_utils import credited
from id_utils import emp_ok


def bank(events):
    balances = {}
    lost = 0.0
    rejected = 0
    invalid = 0
    for ev in events:
        if ev[0] == "work":
            _, emp, hours, night = ev
            if not emp_ok(emp):
                invalid += 1
                continue
            new = balances.get(emp, 0.0) + credited(hours, night)
            if new > 120.0:
                lost += new - 120.0
                new = 120.0
            balances[emp] = new
        else:
            _, emp, hours = ev
            if not emp_ok(emp):
                invalid += 1
                continue
            if hours % 4 != 0 or balances.get(emp, 0.0) < hours:
                rejected += 1
            else:
                balances[emp] -= hours
    return (sorted(balances.items()), round(lost, 2), rejected, invalid)
''',
        },
        "rules": """\
1. id_utils.py must define `emp_ok(emp: str) -> bool` returning True iff
   emp starts with 'EM-'.
2. hours_utils.py must define `credited(hours: float, night: bool) ->
   float`: hours STRICTLY above 8 in a single shift are credited at
   1.5000 times (the first 8 at face value); THEN, if night is True, the
   whole credited value is multiplied by 1.2500 (the night multiplier is
   applied AFTER the overtime split).
3. solution.py must define `bank(events: list) -> tuple`. Events are
   ('work', emp, hours, night) or ('claim', emp, hours):
   - Any event whose emp fails emp_ok is counted as invalid and otherwise
     ignored.
   - 'work': add credited(hours, night) to the employee's balance; any
     excess above the bank ceiling of 120.0 hours is LOST (added to a lost
     counter, balance capped).
   - 'claim': the claim is rejected when hours is not a multiple of 4 or
     the employee's balance cannot cover it in full; otherwise the balance
     drops by the claimed hours.
   - Return (balances, round(lost, 2), rejected, invalid) where balances
     is the sorted list of (emp, balance) pairs.
""",
        "starter": '''\
def bank(events: list) -> tuple:
    """Run the hours bank ledger over a list of events."""
    raise NotImplementedError
''',
        "constants": ["'EM-'", "8", "1.5000", "1.2500", "120", "4"],
        "tests": [
            ("test_helper_emp_ok", "from id_utils import emp_ok", "emp_ok('EM-77')"),
            ("test_helper_emp_bad", "from id_utils import emp_ok", "emp_ok('XX-77')"),
            ("test_helper_credited_plain", "from hours_utils import credited",
             "credited(8.0, False)"),
            ("test_helper_credited_overtime", "from hours_utils import credited",
             "credited(10.0, False)"),
            ("test_helper_credited_night_after_overtime", "from hours_utils import credited",
             "credited(10.0, True)"),
            ("test_empty_run", "from solution import bank", "bank([])"),
            ("test_simple_work", "from solution import bank",
             "bank([('work', 'EM-A', 10.0, False)])"),
            ("test_ceiling_loses_excess", "from solution import bank",
             "bank([('work', 'EM-A', 80.0, False), ('work', 'EM-A', 80.0, False)])"),
            ("test_claim_ok", "from solution import bank",
             "bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 8)])"),
            ("test_claim_not_multiple_rejected", "from solution import bank",
             "bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 6)])"),
            ("test_claim_insufficient_rejected", "from solution import bank",
             "bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 12)])"),
            ("test_invalid_employee", "from solution import bank",
             "bank([('work', 'XX-A', 10.0, False)])"),
        ],
    },
    # ------------------------------------------------------- rating (3)
    {
        "tid": "x_night_surcharge",
        "opening": "You are asked to implement a minute-based surcharge rater for a taxi network.",
        "files": {
            "window_utils.py": '''\
def band(minute: int) -> str:
    if 300 <= minute < 540:
        return "P"
    if minute >= 1290 or minute < 330:
        return "N"
    return "D"
''',
            "mult_utils.py": '''\
def mult(band_code: str) -> float:
    if band_code == "N":
        return 1.75
    if band_code == "P":
        return 2.25
    return 1.0
''',
            "solution.py": '''\
from mult_utils import mult
from window_utils import band


def charge(intervals):
    total = 0.0
    for start, end in intervals:
        for minute in range(start, end):
            total += 0.041 * mult(band(minute))
    return round(total, 2)
''',
        },
        "rules": """\
1. window_utils.py must define `band(minute: int) -> str` for minutes of
   the day. The peak band 'P' covers minutes 300 (inclusive) to 540
   (exclusive). The night band 'N' covers minutes 1290 (inclusive) to the
   end of the day AND minutes before 330. The two windows OVERLAP between
   minutes 300 and 330: there the peak band takes precedence. Every other
   minute is the day band 'D'.
2. mult_utils.py must define `mult(band_code: str) -> float` returning
   1.7500 for 'N', 2.2500 for 'P' and 1.0 otherwise.
3. solution.py must define `charge(intervals: list) -> float` where each
   interval is (start_minute, end_minute), end exclusive. Every minute
   costs a base of 0.0410 times the multiplier of its band. Sum over all
   minutes of all intervals and return round(total, 2).
""",
        "starter": '''\
def charge(intervals: list) -> float:
    """Charge a list of half-open minute intervals."""
    raise NotImplementedError
''',
        "constants": ["300", "540", "1290", "330", "1.7500", "2.2500", "0.0410"],
        "tests": [
            ("test_helper_band_peak_start", "from window_utils import band", "band(300)"),
            ("test_helper_band_overlap_is_peak", "from window_utils import band", "band(329)"),
            ("test_helper_band_night_before_peak", "from window_utils import band", "band(299)"),
            ("test_helper_band_peak_end", "from window_utils import band", "band(539)"),
            ("test_helper_band_day_after_peak", "from window_utils import band", "band(540)"),
            ("test_helper_band_night_start", "from window_utils import band", "band(1290)"),
            ("test_helper_band_day_before_night", "from window_utils import band", "band(1289)"),
            ("test_helper_mult_night", "from mult_utils import mult", "mult('N')"),
            ("test_helper_mult_peak", "from mult_utils import mult", "mult('P')"),
            ("test_helper_mult_day", "from mult_utils import mult", "mult('D')"),
            ("test_empty_run", "from solution import charge", "charge([])"),
            ("test_day_interval", "from solution import charge", "charge([(600, 660)])"),
            ("test_crosses_night_peak_boundary", "from solution import charge",
             "charge([(290, 310)])"),
            ("test_crosses_day_night_boundary", "from solution import charge",
             "charge([(1280, 1300)])"),
        ],
    },
    {
        "tid": "x_freight_zones",
        "opening": "You are asked to implement a freight corridor rater for an overland haulage company.",
        "files": {
            "rate_utils.py": '''\
def zone_rate(zone: str) -> float:
    if zone == "ZN-A":
        return 1.24
    if zone == "ZN-B":
        return 0.88
    return 1.91
''',
            "corridor_utils.py": '''\
def corridor_split(cum_before, km):
    normal = max(0, min(km, 250 - cum_before))
    return (normal, km - normal)
''',
            "solution.py": '''\
from corridor_utils import corridor_split
from rate_utils import zone_rate


def quote(legs):
    if not legs:
        return 0.0
    cum = 0
    total = 0.0
    for zone, km in legs:
        normal, corridor = corridor_split(cum, km)
        total += normal * zone_rate(zone) + corridor * 0.62
        cum += km
    if total < 68.0:
        total = 68.0
    return round(total, 2)
''',
        },
        "rules": """\
1. rate_utils.py must define `zone_rate(zone: str) -> float` returning
   1.2400 per km for zone 'ZN-A', 0.8800 for zone 'ZN-B' and 1.9100 for
   any other zone.
2. corridor_utils.py must define `corridor_split(cum_before, km)`
   returning the tuple (normal_km, corridor_km): of the km driven in a
   leg, the part that keeps the CUMULATIVE route distance at or below the
   corridor threshold of 250 km is normal, the rest is corridor (a leg may
   split in the middle; when cum_before already exceeds the threshold the
   whole leg is corridor).
3. solution.py must define `quote(legs: list) -> float` where each leg is
   (zone, km), in route order. Normal km are billed at the zone rate;
   corridor km are ALWAYS billed at the flat corridor rate of 0.6200
   regardless of zone (the corridor rate takes precedence). An empty route
   costs 0.0; any non-empty route is billed at least the minimum charge of
   68.0. Return round(total, 2).
""",
        "starter": '''\
def quote(legs: list) -> float:
    """Quote a freight route given its legs."""
    raise NotImplementedError
''',
        "constants": ["'ZN-A'", "'ZN-B'", "1.2400", "0.8800", "1.9100",
                      "250", "0.6200", "68.0"],
        "tests": [
            ("test_helper_rate_a", "from rate_utils import zone_rate", "zone_rate('ZN-A')"),
            ("test_helper_rate_b", "from rate_utils import zone_rate", "zone_rate('ZN-B')"),
            ("test_helper_rate_other", "from rate_utils import zone_rate", "zone_rate('ZN-X')"),
            ("test_helper_split_all_normal", "from corridor_utils import corridor_split",
             "corridor_split(0, 100)"),
            ("test_helper_split_middle", "from corridor_utils import corridor_split",
             "corridor_split(200, 100)"),
            ("test_helper_split_all_corridor", "from corridor_utils import corridor_split",
             "corridor_split(300, 100)"),
            ("test_empty_route", "from solution import quote", "quote([])"),
            ("test_minimum_charge", "from solution import quote", "quote([('ZN-B', 10)])"),
            ("test_simple_leg", "from solution import quote", "quote([('ZN-A', 100)])"),
            ("test_split_mid_leg", "from solution import quote",
             "quote([('ZN-A', 200), ('ZN-A', 100)])"),
            ("test_exact_threshold_boundary", "from solution import quote",
             "quote([('ZN-A', 250), ('ZN-B', 10)])"),
            ("test_unknown_zone_rate", "from solution import quote", "quote([('ZN-Q', 100)])"),
        ],
    },
    {
        "tid": "x_spot_power",
        "opening": "You are asked to implement a spot power biller for an industrial energy retailer.",
        "files": {
            "band_utils.py": '''\
def hour_rate(hour: int) -> float:
    if 17 <= hour < 21:
        return 0.5236
    if 10 <= hour < 18:
        return 0.0913
    return 0.2147
''',
            "demand_utils.py": '''\
def demand_fee(max_kwh: float) -> float:
    return max_kwh * 3.41
''',
            "solution.py": '''\
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
        "rules": """\
1. band_utils.py must define `hour_rate(hour: int) -> float`. The critical
   band covers hours 17 (inclusive) to 21 (exclusive) at 0.5236 per kWh.
   The green band covers hours 10 (inclusive) to 18 (exclusive) at 0.0913
   per kWh. The two bands OVERLAP at hour 17: there the critical band
   takes precedence. Every other hour is billed at the base rate of
   0.2147 per kWh.
2. demand_utils.py must define `demand_fee(max_kwh: float) -> float`
   returning max_kwh times 3.4100.
3. solution.py must define `bill(usage: list) -> float` where each reading
   is (hour, kwh). The energy charge sums kwh times hour_rate(hour) over
   all readings. The demand charge is demand_fee of the LARGEST single
   reading's kwh. An empty usage list costs 0.0. Otherwise return
   round(energy + demand, 2).
""",
        "starter": '''\
def bill(usage: list) -> float:
    """Bill a list of hourly power readings."""
    raise NotImplementedError
''',
        "constants": ["17", "21", "0.5236", "10", "18", "0.0913", "0.2147", "3.4100"],
        "tests": [
            ("test_helper_rate_overlap_is_critical", "from band_utils import hour_rate",
             "hour_rate(17)"),
            ("test_helper_rate_critical_end", "from band_utils import hour_rate",
             "hour_rate(20)"),
            ("test_helper_rate_base_after_critical", "from band_utils import hour_rate",
             "hour_rate(21)"),
            ("test_helper_rate_green_start", "from band_utils import hour_rate",
             "hour_rate(10)"),
            ("test_helper_rate_base_before_green", "from band_utils import hour_rate",
             "hour_rate(9)"),
            ("test_helper_rate_green_mid", "from band_utils import hour_rate",
             "hour_rate(16)"),
            ("test_helper_demand_fee", "from demand_utils import demand_fee",
             "demand_fee(10.0)"),
            ("test_empty_usage", "from solution import bill", "bill([])"),
            ("test_single_green_reading", "from solution import bill",
             "bill([(12, 10.0)])"),
            ("test_mixed_bands", "from solution import bill",
             "bill([(18, 5.0), (3, 5.0)])"),
            ("test_peak_is_single_largest", "from solution import bill",
             "bill([(12, 2.0), (12, 7.0)])"),
            ("test_boundary_hour_base", "from solution import bill",
             "bill([(21, 1.0)])"),
        ],
    },
]

# ---------------------------------------------------------------------------
# Construção: executa a canônica para gerar os asserts, valida e emite o pool.
# ---------------------------------------------------------------------------

PREAMBLE_3 = (
    "The work is split across three files that you must create in the\n"
    "workspace: two small helper files plus the main entry point file\n"
    "solution.py that the tests call. Read every numbered rule below\n"
    "carefully and apply the rules in the exact order stated; the business\n"
    "constants are arbitrary and cannot be guessed or derived from anything\n"
    "else.\n"
    "\n"
    "Files and functions:\n"
)
PREAMBLE_4 = PREAMBLE_3.replace("three files", "four files").replace(
    "two small helper files", "three small helper files"
)


def eval_expected(spec: dict) -> list[str]:
    """Executa a solução canônica e devolve os blocos das funções de teste."""
    tmp = Path(tempfile.mkdtemp(prefix="v5gen_"))
    mod_names = [fn[:-3] for fn in spec["files"]]
    try:
        for fn, code in spec["files"].items():
            (tmp / fn).write_text(code, encoding="utf-8")
        for name in mod_names:
            sys.modules.pop(name, None)
        sys.path.insert(0, str(tmp))
        importlib.invalidate_caches()
        blocks = []
        for name, imp, expr in spec["tests"]:
            ns: dict = {}
            exec(imp, ns)
            value = eval(expr, ns)
            blocks.append(f"def {name}():\n    {imp}\n    assert {expr} == {value!r}\n")
        return blocks
    finally:
        sys.path.remove(str(tmp))
        for name in mod_names:
            sys.modules.pop(name, None)
        shutil.rmtree(tmp)


def build_task(spec: dict) -> dict:
    preamble = PREAMBLE_4 if len(spec["files"]) == 4 else PREAMBLE_3
    prompt = spec["opening"] + "\n" + preamble + spec["rules"]
    test_code = "\n\n".join(eval_expected(spec))
    return {
        "task_id": spec["tid"],
        "prompt": prompt,
        "starter_code": spec["starter"],
        "test_code": test_code,
    }


def validate_task(spec: dict, task: dict) -> None:
    tid = task["task_id"]
    prompt = task["prompt"]
    import re

    assert 3 <= len(spec["files"]) <= 4, f"{tid}: nº de arquivos"
    assert 6 <= len(spec["constants"]) <= 12, f"{tid}: nº de constantes"
    n_tests = len(re.findall(r"^def test_", task["test_code"], flags=re.M))
    assert 10 <= n_tests <= 14, f"{tid}: {n_tests} testes"
    n_asserts = len(re.findall(r"^    assert ", task["test_code"], flags=re.M))
    assert n_tests == n_asserts, f"{tid}: asserts != testes"
    assert not re.search(r"\d", prompt[:240]), f"{tid}: dígito no preâmbulo"
    for const in spec["constants"]:
        assert const in prompt[240:], f"{tid}: {const} ausente de prompt[240:]"
        assert const not in prompt[:240], f"{tid}: {const} no preâmbulo"
        assert const not in task["starter_code"], f"{tid}: {const} no starter"
    assert "NotImplementedError" in task["starter_code"], tid

    # canônica -> reward 1.0
    sandbox = Sandbox()
    try:
        for relpath, content in spec["files"].items():
            sandbox.write_file(relpath, content)
        result = sandbox.run_tests(task["test_code"])
    finally:
        sandbox.cleanup()
    assert result["reward"] == 1.0, f"{tid}: canônica reward {result['reward']}\n{result['output']}"

    # starter -> reward 0.0
    sandbox = Sandbox()
    try:
        sandbox.write_file("solution.py", task["starter_code"])
        result = sandbox.run_tests(task["test_code"])
    finally:
        sandbox.cleanup()
    assert result["reward"] == 0.0, f"{tid}: starter reward {result['reward']}"


def _fmt_block(text: str, indent: str = "            ") -> str:
    lines = text.split("\n")
    assert lines[-1] == "", "bloco deve terminar em \\n"
    return "\n".join(indent + repr(line + "\n") for line in lines[:-1])


def emit(tasks: list[dict]) -> str:
    out = []
    out.append('"""Pool fixo de 20 tasks v5 (estrato H, prefixo x_) para o D4b (pré-registro 18).\n')
    out.append("""
Perfil calcado nas 7 tasks fracionárias do v4 no Qwen3-8B (máquinas de estado,
matching com tie-breaks, validadores com checksum, ledgers com estado e rating
por intervalos com precedência), evitando pipelines aritméticos puros:

- 5 máquinas de estado/protocolos (contadores, lockouts, prioridade de eventos
  simultâneos); 4 matching/alocação com tie-breaks encadeados e capacidades;
  4 validadores/parsers com checksums customizados e normalização em ordem
  específica; 4 ledgers/estado acumulado (FIFO, reconciliação); 3 rating por
  intervalos sobrepostos com precedência.
- 3-4 arquivos por task (2-3 helpers + solution.py); 6-12 constantes de
  negócio arbitrárias, TODAS após o char 240 do prompt (preâmbulo sem dígitos);
- 10-14 funções de teste por task, 1 assert cada, cada constante crítica
  exercida por >=1 teste, com casos de borda adversariais.
- starter_code: assinatura + NotImplementedError, sem nenhuma constante.

Gerado por scripts/gera_tasks_v5.py com solução canônica validada a 100% no
sandbox (tests/test_tasks_v5.py re-executa a validação para uma amostra
determinística).
\"\"\"

TASKS: list[dict] = [
""")
    for task in tasks:
        out.append("    {\n")
        out.append(f'        "task_id": {task["task_id"]!r},\n')
        out.append('        "prompt": (\n')
        out.append(_fmt_block(task["prompt"]) + "\n")
        out.append("        ),\n")
        out.append('        "starter_code": (\n')
        out.append(_fmt_block(task["starter_code"]) + "\n")
        out.append("        ),\n")
        out.append('        "test_code": (\n')
        out.append(_fmt_block(task["test_code"]) + "\n")
        out.append("        ),\n")
        out.append("    },\n")
    out.append("]\n\n")
    out.append("STRATA: dict[str, str] = {\n")
    for task in tasks:
        out.append(f'    {task["task_id"]!r}: "H",\n')
    out.append("}\n\n")
    out.append("CRITICAL_CONSTANTS: dict[str, list[str]] = {\n")
    for spec in SPECS:
        out.append(f'    {spec["tid"]!r}: [\n')
        for const in spec["constants"]:
            out.append(f"        {const!r},\n")
        out.append("    ],\n")
    out.append("}\n\n\n")
    out.append(
        "def get_task(task_id: str) -> dict:\n"
        "    for task in TASKS:\n"
        '        if task["task_id"] == task_id:\n'
        "            return task\n"
        "    raise KeyError(task_id)\n"
    )
    return "".join(out)


def main() -> None:
    assert len(SPECS) == 20, len(SPECS)
    ids = [s["tid"] for s in SPECS]
    assert len(set(ids)) == 20 and all(t.startswith("x_") for t in ids)
    tasks = []
    for spec in SPECS:
        task = build_task(spec)
        validate_task(spec, task)
        tasks.append(task)
        print(f"ok {task['task_id']}: {len(spec['files'])} arquivos, "
              f"{len(spec['constants'])} constantes, "
              f"{task['test_code'].count('def test_')} testes")
    dest = ROOT / "environment" / "tasks_v5.py"
    dest.write_text(emit(tasks), encoding="utf-8")
    print(f"\nEscrito {dest} ({len(tasks)} tasks validadas 20/20)")


if __name__ == "__main__":
    main()
