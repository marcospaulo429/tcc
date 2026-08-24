"""Pool fixo de 20 tasks v5 (estrato H, prefixo x_) para o D4b (pré-registro 18).

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
"""

TASKS: list[dict] = [
    {
        "task_id": 'x_vault_lock',
        "prompt": (
            'You are asked to implement a vault keypad controller for a private banking depot.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. pin_utils.py must define `pin_ok(pin: str) -> bool` returning True iff\n'
            '   len(pin) is exactly 6, every character of pin is a digit, and the\n'
            '   integer value of pin modulo 73 equals 21.\n'
            '2. alarm_utils.py must define `alarm_level(total_fails: int) -> str`\n'
            "   returning 'AL-RED' when total_fails is at least 5, 'AL-AMB' when it is\n"
            "   at least 3, and 'AL-OFF' otherwise.\n"
            '3. solution.py must define `operate(events: list) -> str`. The vault\n'
            '   starts LOCKED with zero opens, a consecutive-failure counter at zero, a\n'
            '   total-failure counter at zero and no lockout. Events are tuples\n'
            "   ('enter', pin) or ('close',), processed in order:\n"
            '   - While a lockout is active, the current event is consumed and fully\n'
            '     ignored (whatever its kind) and the lockout counter decreases by one.\n'
            "   - 'enter' while OPEN is ignored entirely (no counters change).\n"
            "   - 'enter' while LOCKED: if pin_ok(pin) the vault becomes OPEN and the\n"
            '     consecutive counter resets to zero; otherwise BOTH failure counters\n'
            '     increase by one, and when the consecutive counter reaches exactly 3 a\n'
            '     lockout covering the NEXT 4 events begins and the consecutive counter\n'
            '     resets to zero.\n'
            "   - 'close' while OPEN: the vault becomes LOCKED and opens increases by\n"
            "     one. 'close' while LOCKED is ignored.\n"
            "   - Return f'{state}|{opens}|{alarm_level(total_fails)}' where state is\n"
            "     'LOCKED' or 'OPEN'.\n"
        ),
        "starter_code": (
            'def operate(events: list) -> str:\n'
            '    """Run the vault keypad controller over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_pin_valid():\n'
            '    from pin_utils import pin_ok\n'
            "    assert pin_ok('000021') == True\n"
            '\n'
            '\n'
            'def test_helper_pin_wrong_mod():\n'
            '    from pin_utils import pin_ok\n'
            "    assert pin_ok('000022') == False\n"
            '\n'
            '\n'
            'def test_helper_pin_wrong_length():\n'
            '    from pin_utils import pin_ok\n'
            "    assert pin_ok('00021') == False\n"
            '\n'
            '\n'
            'def test_helper_pin_non_digit():\n'
            '    from pin_utils import pin_ok\n'
            "    assert pin_ok('00002a') == False\n"
            '\n'
            '\n'
            'def test_helper_alarm_off():\n'
            '    from alarm_utils import alarm_level\n'
            "    assert alarm_level(2) == 'AL-OFF'\n"
            '\n'
            '\n'
            'def test_helper_alarm_amber():\n'
            '    from alarm_utils import alarm_level\n'
            "    assert alarm_level(3) == 'AL-AMB'\n"
            '\n'
            '\n'
            'def test_helper_alarm_red():\n'
            '    from alarm_utils import alarm_level\n'
            "    assert alarm_level(5) == 'AL-RED'\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import operate\n'
            "    assert operate([]) == 'LOCKED|0|AL-OFF'\n"
            '\n'
            '\n'
            'def test_open_and_close():\n'
            '    from solution import operate\n'
            "    assert operate([('enter', '000021'), ('close',)]) == 'LOCKED|1|AL-OFF'\n"
            '\n'
            '\n'
            'def test_lockout_swallows_valid_pin():\n'
            '    from solution import operate\n'
            "    assert operate([('enter', '111111'), ('enter', '111111'), ('enter', '111111'), ('enter', '000021'), ('close',), ('enter', '000021'), ('close',), ('enter', '000021')]) == 'OPEN|0|AL-AMB'\n"
            '\n'
            '\n'
            'def test_enter_while_open_ignored():\n'
            '    from solution import operate\n'
            "    assert operate([('enter', '000021'), ('enter', '111111')]) == 'OPEN|0|AL-OFF'\n"
            '\n'
            '\n'
            'def test_close_while_locked_ignored():\n'
            '    from solution import operate\n'
            "    assert operate([('close',), ('close',)]) == 'LOCKED|0|AL-OFF'\n"
            '\n'
            '\n'
            'def test_red_alarm_across_lockout():\n'
            '    from solution import operate\n'
            "    assert operate([('enter', '111111')] * 3 + [('close',)] * 4 + [('enter', '111111')] * 2) == 'LOCKED|0|AL-RED'\n"
        ),
    },
    {
        "task_id": 'x_vending_fsm',
        "prompt": (
            'You are asked to implement a vending machine controller for a snack distribution firm.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. coin_utils.py must define `coin_value(code: str) -> int` returning 7\n'
            "   for 'CN-A', 13 for 'CN-B', 28 for 'CN-C' and 0 for any other code.\n"
            '2. price_utils.py must define `price(slot: str) -> int` returning 41 for\n'
            "   slot 'KA', 67 for slot 'KB' and 89 for any other slot.\n"
            '3. solution.py must define `vend(events: list) -> str`. The machine starts\n'
            '   ON with an empty escrow and zero vended, rejected and refund counters.\n'
            "   Events are ('coin', code), ('select', slot) or ('refund',):\n"
            "   - 'coin': if coin_value(code) is 0 the coin is rejected (counter goes\n"
            '     up by one); when the rejected counter reaches exactly 4 the machine\n'
            '     goes OUT and every later event is ignored entirely. Otherwise the\n'
            '     value is added to the escrow.\n'
            "   - 'select': if the escrow is at least price(slot), one item is vended\n"
            '     and the price is subtracted (any change STAYS in the escrow);\n'
            '     otherwise nothing happens at all.\n'
            "   - 'refund': the refund counter goes up by one ONLY when the escrow is\n"
            '     STRICTLY greater than zero; the escrow becomes zero either way.\n'
            "   - Return f'{state}|{vended}|{escrow}|{rejected}|{refunds}' where state\n"
            "     is 'ON' or 'OUT'.\n"
        ),
        "starter_code": (
            'def vend(events: list) -> str:\n'
            '    """Run the vending machine controller over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_coin_a():\n'
            '    from coin_utils import coin_value\n'
            "    assert coin_value('CN-A') == 7\n"
            '\n'
            '\n'
            'def test_helper_coin_b():\n'
            '    from coin_utils import coin_value\n'
            "    assert coin_value('CN-B') == 13\n"
            '\n'
            '\n'
            'def test_helper_coin_c():\n'
            '    from coin_utils import coin_value\n'
            "    assert coin_value('CN-C') == 28\n"
            '\n'
            '\n'
            'def test_helper_coin_bad():\n'
            '    from coin_utils import coin_value\n'
            "    assert coin_value('XX-Z') == 0\n"
            '\n'
            '\n'
            'def test_helper_price_ka():\n'
            '    from price_utils import price\n'
            "    assert price('KA') == 41\n"
            '\n'
            '\n'
            'def test_helper_price_kb():\n'
            '    from price_utils import price\n'
            "    assert price('KB') == 67\n"
            '\n'
            '\n'
            'def test_helper_price_other():\n'
            '    from price_utils import price\n'
            "    assert price('ZZ') == 89\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import vend\n'
            "    assert vend([]) == 'ON|0|0|0|0'\n"
            '\n'
            '\n'
            'def test_buy_exact():\n'
            '    from solution import vend\n'
            "    assert vend([('coin', 'CN-C'), ('coin', 'CN-B'), ('select', 'KA')]) == 'ON|1|0|0|0'\n"
            '\n'
            '\n'
            'def test_underpaid_select_noop():\n'
            '    from solution import vend\n'
            "    assert vend([('coin', 'CN-A'), ('select', 'KA')]) == 'ON|0|7|0|0'\n"
            '\n'
            '\n'
            'def test_refund_counts():\n'
            '    from solution import vend\n'
            "    assert vend([('coin', 'CN-A'), ('refund',)]) == 'ON|0|0|0|1'\n"
            '\n'
            '\n'
            'def test_refund_empty_does_not_count():\n'
            '    from solution import vend\n'
            "    assert vend([('refund',)]) == 'ON|0|0|0|0'\n"
            '\n'
            '\n'
            'def test_out_after_four_rejections():\n'
            '    from solution import vend\n'
            "    assert vend([('coin', 'BAD')] * 4 + [('coin', 'CN-C'), ('select', 'ZZ')]) == 'OUT|0|0|4|0'\n"
            '\n'
            '\n'
            'def test_change_stays_in_escrow():\n'
            '    from solution import vend\n'
            "    assert vend([('coin', 'CN-C'), ('coin', 'CN-C'), ('select', 'KA')]) == 'ON|1|15|0|0'\n"
        ),
    },
    {
        "task_id": 'x_badge_gate',
        "prompt": (
            'You are asked to implement a badge gate controller for a secure research campus.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. badge_utils.py must define `clearance(badge: str) -> int` returning 4\n'
            "   when badge starts with 'GV-', 2 when it starts with 'CT-', else 1.\n"
            '2. zone_utils.py must define `required(zone: str) -> int` returning 4 for\n'
            "   zone 'Z-CORE', 2 for zone 'Z-LAB' and 1 for any other zone.\n"
            '3. solution.py must define `gate(events: list) -> str`. The gate starts\n'
            '   OPEN with zero entries, escorts and denials. Events are\n'
            "   ('scan', badge, zone) or ('escort', host, guest, zone):\n"
            "   - 'scan': entry is granted (entries up by one) when clearance(badge) is\n"
            '     at least required(zone); otherwise it is a denial.\n'
            "   - 'escort': the guest enters (entries AND escorts each up by one) only\n"
            '     when ALL hold: clearance(host) is at least required(zone),\n'
            '     clearance(host) is STRICTLY greater than clearance(guest), and the\n'
            '     host has escorted fewer than 2 times so far in this run. Otherwise it\n'
            "     is a denial (the host's escort count does not change).\n"
            '   - After any event, once denials reach 5 the gate enters LOCKDOWN and\n'
            '     every later event is ignored entirely.\n'
            "   - Return f'{state}|{entries}|{escorts}|{denials}' where state is 'OPEN'\n"
            "     or 'LOCKDOWN'.\n"
        ),
        "starter_code": (
            'def gate(events: list) -> str:\n'
            '    """Run the badge gate controller over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_clearance_gv():\n'
            '    from badge_utils import clearance\n'
            "    assert clearance('GV-001') == 4\n"
            '\n'
            '\n'
            'def test_helper_clearance_ct():\n'
            '    from badge_utils import clearance\n'
            "    assert clearance('CT-077') == 2\n"
            '\n'
            '\n'
            'def test_helper_clearance_other():\n'
            '    from badge_utils import clearance\n'
            "    assert clearance('XX-001') == 1\n"
            '\n'
            '\n'
            'def test_helper_required_core():\n'
            '    from zone_utils import required\n'
            "    assert required('Z-CORE') == 4\n"
            '\n'
            '\n'
            'def test_helper_required_lab():\n'
            '    from zone_utils import required\n'
            "    assert required('Z-LAB') == 2\n"
            '\n'
            '\n'
            'def test_helper_required_other():\n'
            '    from zone_utils import required\n'
            "    assert required('Z-YARD') == 1\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import gate\n'
            "    assert gate([]) == 'OPEN|0|0|0'\n"
            '\n'
            '\n'
            'def test_scan_granted():\n'
            '    from solution import gate\n'
            "    assert gate([('scan', 'GV-A', 'Z-CORE')]) == 'OPEN|1|0|0'\n"
            '\n'
            '\n'
            'def test_scan_denied():\n'
            '    from solution import gate\n'
            "    assert gate([('scan', 'CT-A', 'Z-CORE')]) == 'OPEN|0|0|1'\n"
            '\n'
            '\n'
            'def test_escort_granted():\n'
            '    from solution import gate\n'
            "    assert gate([('escort', 'GV-A', 'CT-B', 'Z-LAB')]) == 'OPEN|1|1|0'\n"
            '\n'
            '\n'
            'def test_escort_equal_clearance_denied():\n'
            '    from solution import gate\n'
            "    assert gate([('escort', 'CT-A', 'CT-B', 'Z-LAB')]) == 'OPEN|0|0|1'\n"
            '\n'
            '\n'
            'def test_escort_cap_per_host():\n'
            '    from solution import gate\n'
            "    assert gate([('escort', 'GV-A', 'XX-B', 'Z-YARD')] * 3) == 'OPEN|2|2|1'\n"
            '\n'
            '\n'
            'def test_lockdown_after_five_denials():\n'
            '    from solution import gate\n'
            "    assert gate([('scan', 'XX-A', 'Z-CORE')] * 5 + [('scan', 'GV-A', 'Z-LAB')]) == 'LOCKDOWN|0|0|5'\n"
        ),
    },
    {
        "task_id": 'x_reactor_protocol',
        "prompt": (
            'You are asked to implement a reactor event protocol for an industrial plant operator.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. prio_utils.py must define `rank(kind: str) -> int` returning 0 for\n'
            "   'ESTOP', 1 for 'VENT', 2 for 'FUEL' and 9 for anything else.\n"
            '2. vent_utils.py must define `vent_drop(pressure: int) -> int` returning\n'
            '   pressure minus 258, floored at 0.\n'
            '3. trip_utils.py must define `overpressure(pressure: int) -> bool`\n'
            '   returning True iff pressure is STRICTLY greater than 700.\n'
            '4. solution.py must define `run(events: list) -> str` where each event is\n'
            '   a tuple (timestamp, kind). First sort the events by timestamp; events\n'
            "   sharing the SAME timestamp are ordered by rank(kind) (so 'ESTOP' beats\n"
            "   'VENT' beats 'FUEL'). The reactor starts OFF with pressure 0 and a\n"
            '   waste counter at 0. Then, for each event in that order:\n'
            '   - Once the state is TRIP, every remaining event is ignored.\n'
            "   - 'ESTOP': the state becomes TRIP.\n"
            "   - 'FUEL' while VENTING: one waste is counted, nothing else changes.\n"
            "     'FUEL' otherwise: the state becomes RUN and pressure rises by 164;\n"
            '     if overpressure(pressure) the state immediately becomes TRIP.\n'
            "   - 'VENT' while RUN or VENTING: pressure becomes vent_drop(pressure);\n"
            '     the state becomes OFF when the new pressure is exactly 0, else\n'
            "     VENTING. 'VENT' while OFF: one waste is counted.\n"
            '   - After any event, when the waste counter reaches 3 the state becomes\n'
            '     TRIP.\n'
            "   - Return f'{state}|{pressure}|{waste}'.\n"
        ),
        "starter_code": (
            'def run(events: list) -> str:\n'
            '    """Run the reactor protocol over a list of timestamped events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rank_estop():\n'
            '    from prio_utils import rank\n'
            "    assert rank('ESTOP') == 0\n"
            '\n'
            '\n'
            'def test_helper_rank_vent():\n'
            '    from prio_utils import rank\n'
            "    assert rank('VENT') == 1\n"
            '\n'
            '\n'
            'def test_helper_rank_fuel():\n'
            '    from prio_utils import rank\n'
            "    assert rank('FUEL') == 2\n"
            '\n'
            '\n'
            'def test_helper_rank_other():\n'
            '    from prio_utils import rank\n'
            "    assert rank('X') == 9\n"
            '\n'
            '\n'
            'def test_helper_vent_drop():\n'
            '    from vent_utils import vent_drop\n'
            '    assert vent_drop(300) == 42\n'
            '\n'
            '\n'
            'def test_helper_vent_drop_floor():\n'
            '    from vent_utils import vent_drop\n'
            '    assert vent_drop(100) == 0\n'
            '\n'
            '\n'
            'def test_helper_overpressure_edge():\n'
            '    from trip_utils import overpressure\n'
            '    assert overpressure(700) == False\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import run\n'
            "    assert run([]) == 'OFF|0|0'\n"
            '\n'
            '\n'
            'def test_single_fuel():\n'
            '    from solution import run\n'
            "    assert run([(1, 'FUEL')]) == 'RUN|164|0'\n"
            '\n'
            '\n'
            'def test_trip_on_overpressure():\n'
            '    from solution import run\n'
            "    assert run([(i, 'FUEL') for i in range(5)]) == 'TRIP|820|0'\n"
            '\n'
            '\n'
            'def test_vent_to_off():\n'
            '    from solution import run\n'
            "    assert run([(1, 'FUEL'), (2, 'VENT')]) == 'OFF|0|0'\n"
            '\n'
            '\n'
            'def test_venting_state():\n'
            '    from solution import run\n'
            "    assert run([(1, 'FUEL'), (2, 'FUEL'), (3, 'FUEL'), (4, 'VENT')]) == 'VENTING|234|0'\n"
            '\n'
            '\n'
            'def test_simultaneous_estop_wins():\n'
            '    from solution import run\n'
            "    assert run([(5, 'FUEL'), (5, 'ESTOP')]) == 'TRIP|0|0'\n"
            '\n'
            '\n'
            'def test_waste_trips_reactor():\n'
            '    from solution import run\n'
            "    assert run([(1, 'VENT'), (2, 'VENT'), (3, 'VENT'), (4, 'FUEL')]) == 'TRIP|0|3'\n"
        ),
    },
    {
        "task_id": 'x_parcel_locker',
        "prompt": (
            'You are asked to implement a parcel locker controller for a neighborhood delivery hub.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. code_utils.py must define `code_ok(code: str) -> bool` returning True\n'
            "   iff code starts with 'PX-' and len(code) is exactly 8.\n"
            '2. age_utils.py must define `is_expired(age: int) -> bool` returning True\n'
            '   iff age is at least 4.\n'
            '3. solution.py must define `run(events: list) -> str`. The locker starts\n'
            '   ONLINE and empty, with zero picked, depot and error counters. Events\n'
            "   are ('drop', code), ('pick', code) or ('tick',):\n"
            "   - 'drop': it is an error when code_ok(code) is False, OR the code is\n"
            '     already stored, OR the locker already holds 5 parcels; otherwise the\n'
            '     parcel is stored with age 0.\n'
            "   - 'pick': removes the parcel and counts one pick when the code is\n"
            '     stored; otherwise it is an error.\n'
            "   - 'tick': FIRST every stored parcel ages by one, THEN every parcel\n"
            '     whose age satisfies is_expired is removed and counted into the depot\n'
            '     counter.\n'
            '   - After any event, once the error counter reaches 3 the locker goes\n'
            '     OFFLINE and every later event is ignored entirely.\n'
            "   - Return f'{state}|{stored}|{picked}|{depot}|{errors}' where stored is\n"
            "     the number of parcels currently held and state is 'ONLINE' or\n"
            "     'OFFLINE'.\n"
        ),
        "starter_code": (
            'def run(events: list) -> str:\n'
            '    """Run the parcel locker controller over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_code_ok():\n'
            '    from code_utils import code_ok\n'
            "    assert code_ok('PX-12345') == True\n"
            '\n'
            '\n'
            'def test_helper_code_short():\n'
            '    from code_utils import code_ok\n'
            "    assert code_ok('PX-1234') == False\n"
            '\n'
            '\n'
            'def test_helper_code_prefix():\n'
            '    from code_utils import code_ok\n'
            "    assert code_ok('QX-12345') == False\n"
            '\n'
            '\n'
            'def test_helper_expired_edge():\n'
            '    from age_utils import is_expired\n'
            '    assert is_expired(4) == True\n'
            '\n'
            '\n'
            'def test_helper_not_expired():\n'
            '    from age_utils import is_expired\n'
            '    assert is_expired(3) == False\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import run\n'
            "    assert run([]) == 'ONLINE|0|0|0|0'\n"
            '\n'
            '\n'
            'def test_drop_and_pick():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'PX-11111'), ('pick', 'PX-11111')]) == 'ONLINE|0|1|0|0'\n"
            '\n'
            '\n'
            'def test_expires_after_four_ticks():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'PX-11111')] + [('tick',)] * 4) == 'ONLINE|0|0|1|0'\n"
            '\n'
            '\n'
            'def test_survives_three_ticks():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'PX-11111')] + [('tick',)] * 3) == 'ONLINE|1|0|0|0'\n"
            '\n'
            '\n'
            'def test_duplicate_drop_error():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'PX-11111'), ('drop', 'PX-11111')]) == 'ONLINE|1|0|0|1'\n"
            '\n'
            '\n'
            'def test_capacity_overflow_error():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'PX-11111'), ('drop', 'PX-11112'), ('drop', 'PX-11113'), ('drop', 'PX-11114'), ('drop', 'PX-11115'), ('drop', 'PX-11116')]) == 'ONLINE|5|0|0|1'\n"
            '\n'
            '\n'
            'def test_offline_after_three_errors():\n'
            '    from solution import run\n'
            "    assert run([('pick', 'PX-99999')] * 3 + [('drop', 'PX-11111')]) == 'OFFLINE|0|0|0|3'\n"
            '\n'
            '\n'
            'def test_invalid_code_drop_error():\n'
            '    from solution import run\n'
            "    assert run([('drop', 'BAD')]) == 'ONLINE|0|0|0|1'\n"
        ),
    },
    {
        "task_id": 'x_berth_scheduler',
        "prompt": (
            'You are asked to implement a berth scheduler for a busy river port authority.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. fit_utils.py must define `fits(draft: float, depth: float) -> bool`\n'
            '   returning True iff draft plus a safety clearance of 0.7500 is less than\n'
            '   or equal to depth (the exact boundary fits).\n'
            '2. order_utils.py must define `ship_key(ship: tuple) -> tuple` where ship\n'
            '   is (name, draft, priority), returning (-priority, -draft, name) so that\n'
            '   sorting processes higher priority first, then deeper draft, then name\n'
            '   in ascending order.\n'
            '3. solution.py must define `assign(ships: list) -> list`. The port has\n'
            '   three berths tried in this fixed order, from shallowest to deepest:\n'
            "   'BS' with depth 6.2500, 'BR' with depth 8.5000 and 'BQ' with depth\n"
            '   11.7500. Each berth holds at most 2 ships. Process the ships sorted by\n'
            '   ship_key; each ship takes the FIRST berth in the order above that both\n'
            '   fits (per fit_utils) and still has space; a ship that fits nowhere gets\n'
            "   'ANCHOR'. Return the list of (name, berth) tuples in processing order.\n"
        ),
        "starter_code": (
            'def assign(ships: list) -> list:\n'
            '    """Assign each ship to a berth and return (name, berth) tuples."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_fits_exact_boundary():\n'
            '    from fit_utils import fits\n'
            '    assert fits(5.5, 6.25) == True\n'
            '\n'
            '\n'
            'def test_helper_fits_over_boundary():\n'
            '    from fit_utils import fits\n'
            '    assert fits(5.51, 6.25) == False\n'
            '\n'
            '\n'
            'def test_helper_ship_key():\n'
            '    from order_utils import ship_key\n'
            "    assert ship_key(('X', 4.0, 2)) == (-2, -4.0, 'X')\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import assign\n'
            '    assert assign([]) == []\n'
            '\n'
            '\n'
            'def test_small_ship_gets_shallowest():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 5.0, 1)]) == [('a', 'BS')]\n"
            '\n'
            '\n'
            'def test_deep_draft_gets_deepest():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 9.5, 1)]) == [('a', 'BQ')]\n"
            '\n'
            '\n'
            'def test_too_deep_anchors():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 11.5, 1)]) == [('a', 'ANCHOR')]\n"
            '\n'
            '\n'
            'def test_capacity_spillover():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 5.0, 1), ('b', 5.0, 1), ('c', 5.0, 1)]) == [('a', 'BS'), ('b', 'BS'), ('c', 'BR')]\n"
            '\n'
            '\n'
            'def test_priority_first():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 5.0, 1), ('b', 5.0, 9)]) == [('b', 'BS'), ('a', 'BS')]\n"
            '\n'
            '\n'
            'def test_draft_tiebreak():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 5.0, 1), ('b', 5.4, 1)]) == [('b', 'BS'), ('a', 'BS')]\n"
            '\n'
            '\n'
            'def test_boundary_fit_in_solution():\n'
            '    from solution import assign\n'
            "    assert assign([('a', 5.5, 1)]) == [('a', 'BS')]\n"
            '\n'
            '\n'
            'def test_name_tiebreak():\n'
            '    from solution import assign\n'
            "    assert assign([('b', 5.0, 1), ('a', 5.0, 1)]) == [('a', 'BS'), ('b', 'BS')]\n"
        ),
    },
    {
        "task_id": 'x_courier_dispatch',
        "prompt": (
            'You are asked to implement a courier dispatch planner for a same-day logistics firm.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. job_utils.py must define `job_key(job: tuple) -> tuple` where job is\n'
            '   (jid, kg, urgent), returning (0 if urgent else 1, -kg, jid) so that\n'
            '   sorting processes urgent jobs first, then heavier jobs, then jid in\n'
            '   ascending order.\n'
            '2. pay_utils.py must define `base_fee(kg: float) -> float` returning\n'
            '   6.2500 plus kg times 0.4100.\n'
            '3. solution.py must define `dispatch(jobs: list, couriers: list) -> tuple`\n'
            '   where each courier is (cid, capacity_kg, rating). Process the jobs\n'
            '   sorted by job_key. For each job, a courier is eligible when ALL hold:\n'
            '   - it has been assigned fewer than 3 jobs so far;\n'
            '   - if the job is urgent, its rating is NOT strictly below 2.1500;\n'
            "   - its remaining capacity covers the job's kg — except that an URGENT\n"
            '     job may exceed the remaining capacity by at most 3.5000 kg, only if\n'
            '     the job weighs at most 87 kg and that courier has never used the\n'
            '     overload before in this run (the overload is spent only when the\n'
            '     remaining capacity alone was insufficient).\n'
            '   Among eligible couriers pick the highest rating; break ties by the most\n'
            '   remaining capacity, then by cid ascending. Assign the job (remaining\n'
            '   capacity drops by kg, possibly below zero on an overload) and add\n'
            '   base_fee(kg) to the total fee. A job with no eligible courier is paired\n'
            "   with 'HOLD' and costs nothing. Return (assignments, round(fee, 2))\n"
            "   where assignments is the list of (jid, cid-or-'HOLD') in processing\n"
            '   order.\n'
        ),
        "starter_code": (
            'def dispatch(jobs: list, couriers: list) -> tuple:\n'
            '    """Assign jobs to couriers and return (assignments, total_fee)."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_job_key_urgent():\n'
            '    from job_utils import job_key\n'
            "    assert job_key(('j1', 10.0, True)) == (0, -10.0, 'j1')\n"
            '\n'
            '\n'
            'def test_helper_job_key_normal():\n'
            '    from job_utils import job_key\n'
            "    assert job_key(('j1', 10.0, False)) == (1, -10.0, 'j1')\n"
            '\n'
            '\n'
            'def test_helper_base_fee():\n'
            '    from pay_utils import base_fee\n'
            '    assert base_fee(10.0) == 10.35\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([], [('c1', 50.0, 4.0)]) == ([], 0.0)\n"
            '\n'
            '\n'
            'def test_simple_assign():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 10.0, False)], [('c1', 50.0, 4.0)]) == ([('j1', 'c1')], 10.35)\n"
            '\n'
            '\n'
            'def test_hold_when_over_capacity():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 60.0, False)], [('c1', 50.0, 4.0)]) == ([('j1', 'HOLD')], 0.0)\n"
            '\n'
            '\n'
            'def test_urgent_overload_allowed():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 53.0, True)], [('c1', 50.0, 4.0)]) == ([('j1', 'c1')], 27.98)\n"
            '\n'
            '\n'
            'def test_overload_only_once():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 53.0, True), ('j2', 53.0, True), ('j3', 53.0, True)], [('c1', 105.0, 4.0)]) == ([('j1', 'c1'), ('j2', 'c1'), ('j3', 'HOLD')], 55.96)\n"
            '\n'
            '\n'
            'def test_heavy_urgent_no_overload():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 90.0, True)], [('c1', 88.0, 4.0)]) == ([('j1', 'HOLD')], 0.0)\n"
            '\n'
            '\n'
            'def test_low_rating_rejects_urgent():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 10.0, True)], [('c1', 50.0, 2.0)]) == ([('j1', 'HOLD')], 0.0)\n"
            '\n'
            '\n'
            'def test_rating_tiebreak():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 10.0, False)], [('c1', 50.0, 3.0), ('c2', 50.0, 4.0)]) == ([('j1', 'c2')], 10.35)\n"
            '\n'
            '\n'
            'def test_capacity_tiebreak():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 10.0, False)], [('c1', 50.0, 4.0), ('c2', 60.0, 4.0)]) == ([('j1', 'c2')], 10.35)\n"
            '\n'
            '\n'
            'def test_job_limit_three():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j1', 1.0, False), ('j2', 1.0, False), ('j3', 1.0, False), ('j4', 1.0, False)], [('c1', 50.0, 4.0)]) == ([('j1', 'c1'), ('j2', 'c1'), ('j3', 'c1'), ('j4', 'HOLD')], 19.98)\n"
            '\n'
            '\n'
            'def test_urgent_processed_first():\n'
            '    from solution import dispatch\n'
            "    assert dispatch([('j2', 10.0, False), ('j1', 5.0, True)], [('c1', 50.0, 4.0)]) == ([('j1', 'c1'), ('j2', 'c1')], 18.65)\n"
        ),
    },
    {
        "task_id": 'x_grant_allocator',
        "prompt": (
            'You are asked to implement a grant allocation engine for a community foundation.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. score_utils.py must define `adj_score(org: str, score: int) -> int`\n'
            "   returning score plus a bonus of 7 when org starts with 'NG-', else the\n"
            '   raw score.\n'
            '2. cap_utils.py must define `capped(amount: float) -> float` returning the\n'
            '   amount clamped at a ceiling of 12500.0.\n'
            '3. solution.py must define `allocate(requests: list, budget: float) ->\n'
            '   tuple` where each request is (org, amount, score). Sort the requests by\n'
            '   adj_score descending, then amount ascending, then org ascending, and\n'
            '   process in that order:\n'
            '   - Requests whose adj_score is STRICTLY below 41 are skipped entirely.\n'
            '   - Let amt = capped(amount). Paying a grant g also costs a processing\n'
            '     fee of round(g * 0.0180, 2) taken from the same budget.\n'
            '   - Full funding: pay amt when amt is at least 750 and the budget covers\n'
            '     amt plus its fee.\n'
            '   - Otherwise, a ONE-TIME partial option (usable at most once per whole\n'
            '     run, and CONSUMED whenever this branch is attempted): pay\n'
            '     round(amt * 0.6200, 2) if that value is at least 750 and the budget\n'
            '     covers it plus its fee; if not, the request gets nothing.\n'
            '   - Requests reached after the partial option was consumed and that\n'
            '     cannot be fully funded get nothing.\n'
            '   - Return (funded, round(budget, 2)) where funded lists (org, grant) in\n'
            '     payment order.\n'
        ),
        "starter_code": (
            'def allocate(requests: list, budget: float) -> tuple:\n'
            '    """Allocate the budget across grant requests."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_bonus_applied():\n'
            '    from score_utils import adj_score\n'
            "    assert adj_score('NG-X', 40) == 47\n"
            '\n'
            '\n'
            'def test_helper_bonus_not_applied():\n'
            '    from score_utils import adj_score\n'
            "    assert adj_score('AC-X', 40) == 40\n"
            '\n'
            '\n'
            'def test_helper_cap_applied():\n'
            '    from cap_utils import capped\n'
            '    assert capped(20000.0) == 12500.0\n'
            '\n'
            '\n'
            'def test_helper_cap_not_applied():\n'
            '    from cap_utils import capped\n'
            '    assert capped(1000.0) == 1000.0\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import allocate\n'
            '    assert allocate([], 5000.0) == ([], 5000.0)\n'
            '\n'
            '\n'
            'def test_simple_full_funding():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 1000.0, 80)], 5000.0) == ([('AC-A', 1000.0)], 3982.0)\n"
            '\n'
            '\n'
            'def test_low_score_skipped():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 1000.0, 40)], 5000.0) == ([], 5000.0)\n"
            '\n'
            '\n'
            'def test_bonus_crosses_threshold():\n'
            '    from solution import allocate\n'
            "    assert allocate([('NG-A', 1000.0, 36)], 5000.0) == ([('NG-A', 1000.0)], 3982.0)\n"
            '\n'
            '\n'
            'def test_ceiling_applied():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 20000.0, 80)], 20000.0) == ([('AC-A', 12500.0)], 7275.0)\n"
            '\n'
            '\n'
            'def test_partial_funding():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 2000.0, 80)], 1500.0) == ([('AC-A', 1240.0)], 237.68)\n"
            '\n'
            '\n'
            'def test_partial_only_once():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 2000.0, 80), ('AC-B', 2000.0, 80)], 2600.0) == ([('AC-A', 2000.0)], 564.0)\n"
            '\n'
            '\n'
            'def test_minimum_grant():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-A', 600.0, 80)], 5000.0) == ([], 5000.0)\n"
            '\n'
            '\n'
            'def test_sort_order():\n'
            '    from solution import allocate\n'
            "    assert allocate([('AC-B', 800.0, 80), ('AC-A', 900.0, 90), ('AC-C', 800.0, 80)], 10000.0) == ([('AC-A', 900.0), ('AC-B', 800.0), ('AC-C', 800.0)], 7455.0)\n"
        ),
    },
    {
        "task_id": 'x_court_scheduler',
        "prompt": (
            'You are asked to implement a courtroom scheduler for a district judicial office.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. room_utils.py must define `room_cap(room: str) -> int` returning 300\n'
            "   for room 'RA', 195 for room 'RB' and 0 for anything else.\n"
            '2. case_utils.py must define `case_key(case: tuple) -> tuple` where case\n'
            '   is (cid, minutes, custody), returning (0 if custody else 1, -minutes,\n'
            '   cid) so that sorting processes custody cases first, then longer cases,\n'
            '   then cid ascending.\n'
            '3. solution.py must define `schedule(cases: list) -> tuple`. Both rooms\n'
            '   start with their full capacity in minutes. Process the cases sorted by\n'
            '   case_key:\n'
            '   - A custody case consumes its minutes PLUS a security buffer of 15\n'
            '     minutes of room capacity.\n'
            "   - A case STRICTLY longer than 120 minutes may only sit in room 'RA'.\n"
            '   - Among the allowed rooms with enough remaining capacity, pick the one\n'
            "     with the MOST remaining minutes; on an exact tie pick 'RA'.\n"
            "   - A case that fits nowhere is paired with 'DEFER'.\n"
            '   - Return (assignments, remaining_RA, remaining_RB) where assignments is\n'
            "     the list of (cid, room-or-'DEFER') in processing order.\n"
        ),
        "starter_code": (
            'def schedule(cases: list) -> tuple:\n'
            '    """Schedule hearings into courtrooms and return the plan."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_cap_ra():\n'
            '    from room_utils import room_cap\n'
            "    assert room_cap('RA') == 300\n"
            '\n'
            '\n'
            'def test_helper_cap_rb():\n'
            '    from room_utils import room_cap\n'
            "    assert room_cap('RB') == 195\n"
            '\n'
            '\n'
            'def test_helper_cap_other():\n'
            '    from room_utils import room_cap\n'
            "    assert room_cap('RC') == 0\n"
            '\n'
            '\n'
            'def test_helper_case_key():\n'
            '    from case_utils import case_key\n'
            "    assert case_key(('c1', 60, True)) == (0, -60, 'c1')\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import schedule\n'
            '    assert schedule([]) == ([], 300, 195)\n'
            '\n'
            '\n'
            'def test_single_case_prefers_ra():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 60, False)]) == ([('c1', 'RA')], 240, 195)\n"
            '\n'
            '\n'
            'def test_three_cases_balance():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 60, False), ('c2', 60, False), ('c3', 60, False)]) == ([('c1', 'RA'), ('c2', 'RA'), ('c3', 'RB')], 180, 135)\n"
            '\n'
            '\n'
            'def test_long_case_only_ra():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 130, False)]) == ([('c1', 'RA')], 170, 195)\n"
            '\n'
            '\n'
            'def test_long_case_defers_when_ra_full():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c0', 250, False), ('c1', 130, False)]) == ([('c0', 'RA'), ('c1', 'DEFER')], 50, 195)\n"
            '\n'
            '\n'
            'def test_custody_buffer_exact_fit():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 285, True)]) == ([('c1', 'RA')], 0, 195)\n"
            '\n'
            '\n'
            'def test_custody_buffer_defer():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 290, True)]) == ([('c1', 'DEFER')], 300, 195)\n"
            '\n'
            '\n'
            'def test_custody_processed_first():\n'
            '    from solution import schedule\n'
            "    assert schedule([('c1', 60, False), ('c2', 50, True)]) == ([('c2', 'RA'), ('c1', 'RA')], 175, 195)\n"
        ),
    },
    {
        "task_id": 'x_plate_validator',
        "prompt": (
            'You are asked to implement a license plate validator for a vehicle registry bureau.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. norm_utils.py must define `normalize(raw: str) -> str` applying these\n'
            '   steps in this exact order: first remove every space and every hyphen,\n'
            "   then uppercase the string, then replace every 'O' with '0' and every\n"
            "   'I' with '1' (the order matters: lowercase letters must be uppercased\n"
            '   BEFORE the digit substitution).\n'
            '2. rank_utils.py must define `rank(ch: str) -> int` returning the index of\n'
            "   ch in the restricted alphabet 'BCDFGHJKLMNPQRSTVWXZ', or the value\n"
            '   negative one when ch is not in it.\n'
            '3. solution.py must define `validate(raw: str) -> str`. Let s be\n'
            '   normalize(raw); apply the checks in this exact order, returning at the\n'
            '   FIRST failure:\n'
            "   - len(s) must be exactly 7, else return 'E_LEN'.\n"
            '   - Characters at positions two through five (0-based) must all be\n'
            "     digits, else return 'E_DIG'.\n"
            '   - The first, second and last characters must all be in the restricted\n'
            "     alphabet (rank not negative), else return 'E_ALPHA'.\n"
            '   - Checksum: (rank of first + rank of second) * 5 plus (sum of the four\n'
            '     digits) * 11, taken modulo 20, must equal the rank of the LAST\n'
            "     character, else return 'E_CHK'.\n"
            "   - Otherwise return 'OK-' followed by s.\n"
        ),
        "starter_code": (
            'def validate(raw: str) -> str:\n'
            '    """Validate a raw license plate string and return a status code."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_normalize_strips():\n'
            '    from norm_utils import normalize\n'
            "    assert normalize('ab - c') == 'ABC'\n"
            '\n'
            '\n'
            'def test_helper_normalize_order_matters():\n'
            '    from norm_utils import normalize\n'
            "    assert normalize('go1') == 'G01'\n"
            '\n'
            '\n'
            'def test_helper_rank_first():\n'
            '    from rank_utils import rank\n'
            "    assert rank('B') == 0\n"
            '\n'
            '\n'
            'def test_helper_rank_last():\n'
            '    from rank_utils import rank\n'
            "    assert rank('Z') == 19\n"
            '\n'
            '\n'
            'def test_helper_rank_missing():\n'
            '    from rank_utils import rank\n'
            "    assert rank('A') == -1\n"
            '\n'
            '\n'
            'def test_valid_plate():\n'
            '    from solution import validate\n'
            "    assert validate('BC2345Z') == 'OK-BC2345Z'\n"
            '\n'
            '\n'
            'def test_valid_after_normalization():\n'
            '    from solution import validate\n'
            "    assert validate('bc 2345z') == 'OK-BC2345Z'\n"
            '\n'
            '\n'
            'def test_valid_with_letter_o():\n'
            '    from solution import validate\n'
            "    assert validate('bco245j') == 'OK-BC0245J'\n"
            '\n'
            '\n'
            'def test_length_error():\n'
            '    from solution import validate\n'
            "    assert validate('BC234Z') == 'E_LEN'\n"
            '\n'
            '\n'
            'def test_digit_error():\n'
            '    from solution import validate\n'
            "    assert validate('BCX345Z') == 'E_DIG'\n"
            '\n'
            '\n'
            'def test_alpha_error_head():\n'
            '    from solution import validate\n'
            "    assert validate('AC2345Z') == 'E_ALPHA'\n"
            '\n'
            '\n'
            'def test_checksum_error():\n'
            '    from solution import validate\n'
            "    assert validate('BC2345X') == 'E_CHK'\n"
            '\n'
            '\n'
            'def test_alpha_error_tail():\n'
            '    from solution import validate\n'
            "    assert validate('BC23450') == 'E_ALPHA'\n"
        ),
    },
    {
        "task_id": 'x_voucher_parser',
        "prompt": (
            'You are asked to implement a voucher code parser for a retail promotions platform.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. kind_utils.py must define `base(kind: str) -> int` returning 250 for\n'
            "   'VXA', 475 for 'VXB', 60 for 'VXQ' and negative one otherwise.\n"
            '2. char_utils.py must define `char_index(ch: str) -> int` returning the\n'
            "   index of ch in the restricted alphabet '2346789ACDEFGH', or negative\n"
            '   one when ch is not in it.\n'
            '3. solution.py must define `parse(code: str) -> str`, applying the checks\n'
            '   in this exact order and returning at the FIRST failure:\n'
            "   - Split code on '-': there must be exactly three segments, else return\n"
            "     'BAD_SEG'.\n"
            '   - The first segment must have a known base (per kind_utils), else\n'
            "     return 'BAD_KIND'.\n"
            '   - The second segment must have exactly 4 characters, all from the\n'
            "     restricted alphabet, else return 'BAD_CHAR'.\n"
            '   - Let idxsum be the sum of the char_index values of the body. The third\n'
            "     segment must be EXACTLY the string f'{(idxsum * 13) % 89:02d}' (two\n"
            "     characters, zero-padded), else return 'BAD_SUM'.\n"
            "   - Otherwise return f'{kind}:{amount}' where amount = base(kind) plus\n"
            '     idxsum times 3.\n'
        ),
        "starter_code": (
            'def parse(code: str) -> str:\n'
            '    """Parse a voucher code and return its value or an error code."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_base_vxa():\n'
            '    from kind_utils import base\n'
            "    assert base('VXA') == 250\n"
            '\n'
            '\n'
            'def test_helper_base_vxb():\n'
            '    from kind_utils import base\n'
            "    assert base('VXB') == 475\n"
            '\n'
            '\n'
            'def test_helper_base_vxq():\n'
            '    from kind_utils import base\n'
            "    assert base('VXQ') == 60\n"
            '\n'
            '\n'
            'def test_helper_base_unknown():\n'
            '    from kind_utils import base\n'
            "    assert base('XXX') == -1\n"
            '\n'
            '\n'
            'def test_helper_index_first():\n'
            '    from char_utils import char_index\n'
            "    assert char_index('2') == 0\n"
            '\n'
            '\n'
            'def test_helper_index_last():\n'
            '    from char_utils import char_index\n'
            "    assert char_index('H') == 13\n"
            '\n'
            '\n'
            'def test_helper_index_excluded():\n'
            '    from char_utils import char_index\n'
            "    assert char_index('B') == -1\n"
            '\n'
            '\n'
            'def test_valid_voucher():\n'
            '    from solution import parse\n'
            "    assert parse('VXA-2346-78') == 'VXA:268'\n"
            '\n'
            '\n'
            'def test_valid_voucher_high_sum():\n'
            '    from solution import parse\n'
            "    assert parse('VXQ-HH99-49') == 'VXQ:174'\n"
            '\n'
            '\n'
            'def test_missing_segment():\n'
            '    from solution import parse\n'
            "    assert parse('VXA-2346') == 'BAD_SEG'\n"
            '\n'
            '\n'
            'def test_unknown_kind():\n'
            '    from solution import parse\n'
            "    assert parse('VXZ-2346-78') == 'BAD_KIND'\n"
            '\n'
            '\n'
            'def test_bad_body_char():\n'
            '    from solution import parse\n'
            "    assert parse('VXA-23B6-78') == 'BAD_CHAR'\n"
            '\n'
            '\n'
            'def test_bad_checksum():\n'
            '    from solution import parse\n'
            "    assert parse('VXA-2346-77') == 'BAD_SUM'\n"
            '\n'
            '\n'
            'def test_checksum_must_be_zero_padded():\n'
            '    from solution import parse\n'
            "    assert parse('VXB-2347-2') == 'BAD_SUM'\n"
        ),
    },
    {
        "task_id": 'x_scale_barcode',
        "prompt": (
            'You are asked to implement a scale barcode parser for a grocery point of sale system.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. digit_utils.py must define `digit_sum(s: str) -> int` returning the sum\n'
            '   of the integer values of the digits of s.\n'
            '2. chk_utils.py must define `price_check(price_digits: str) -> int`\n'
            '   returning digit_sum(price_digits) times 7, taken modulo 10.\n'
            '3. solution.py must define `parse(barcode: str)`, applying the checks in\n'
            '   this exact order and returning at the FIRST failure:\n'
            '   - Remove every space, then the result must have exactly 13 characters,\n'
            "     all digits, else return 'B_LEN'.\n"
            "   - It must start with the prefix '27', else return 'B_PFX'.\n"
            '   - The five characters starting at position 7 (0-based) encode the price\n'
            '     in cents; the character at position 12 must equal\n'
            "     price_check(those five characters), else return 'B_CHK'.\n"
            '   - Otherwise return the tuple (item, price) where item is the five\n'
            '     characters starting at position 2 (kept as a string) and price is\n'
            '     round(cents / 100, 2).\n'
        ),
        "starter_code": (
            'def parse(barcode: str):\n'
            '    """Parse a variable-weight barcode into (item, price) or an error."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_digit_sum():\n'
            '    from digit_utils import digit_sum\n'
            "    assert digit_sum('123') == 6\n"
            '\n'
            '\n'
            'def test_helper_price_check():\n'
            '    from chk_utils import price_check\n'
            "    assert price_check('01995') == 8\n"
            '\n'
            '\n'
            'def test_helper_price_check_zero():\n'
            '    from chk_utils import price_check\n'
            "    assert price_check('00000') == 0\n"
            '\n'
            '\n'
            'def test_valid_barcode():\n'
            '    from solution import parse\n'
            "    assert parse('2712345019958') == ('12345', 19.95)\n"
            '\n'
            '\n'
            'def test_spaces_are_stripped():\n'
            '    from solution import parse\n'
            "    assert parse('27 12345 01995 8') == ('12345', 19.95)\n"
            '\n'
            '\n'
            'def test_short_barcode():\n'
            '    from solution import parse\n'
            "    assert parse('271234501995') == 'B_LEN'\n"
            '\n'
            '\n'
            'def test_non_digit_barcode():\n'
            '    from solution import parse\n'
            "    assert parse('27123450199a8') == 'B_LEN'\n"
            '\n'
            '\n'
            'def test_wrong_prefix():\n'
            '    from solution import parse\n'
            "    assert parse('2812345019958') == 'B_PFX'\n"
            '\n'
            '\n'
            'def test_wrong_check_digit():\n'
            '    from solution import parse\n'
            "    assert parse('2712345019957') == 'B_CHK'\n"
            '\n'
            '\n'
            'def test_zero_price():\n'
            '    from solution import parse\n'
            "    assert parse('2754321000000') == ('54321', 0.0)\n"
            '\n'
            '\n'
            'def test_small_price_cents():\n'
            '    from solution import parse\n'
            "    assert parse('2704242000422') == ('04242', 0.42)\n"
        ),
    },
    {
        "task_id": 'x_chem_batch',
        "prompt": (
            'You are asked to implement a batch code validator for a chemical laboratory network.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. clean_utils.py must define `clean(code: str) -> str` applying these\n'
            '   steps in this exact order: strip leading and trailing whitespace, then\n'
            '   uppercase the string, then remove every hyphen.\n'
            '2. sig_utils.py must define `sig_char(digit_total: int) -> str` returning\n'
            '   the character at position digit_total modulo 10 of the signature\n'
            "   alphabet 'ABCDEFGHJK'.\n"
            '3. solution.py must define `validate(code: str) -> str`. Let s be\n'
            '   clean(code); apply the checks in this exact order, returning at the\n'
            '   FIRST failure:\n'
            "   - len(s) must be exactly 10 and s must start with 'LB', else return\n"
            "     'C_FMT'.\n"
            "   - The two characters after the prefix name the lab and must be 'QN',\n"
            "     'TR' or 'VX', else return 'C_LAB'.\n"
            "   - The next five characters must all be digits, else return 'C_DIG'.\n"
            '   - The final character must equal sig_char(sum of those five digits),\n'
            "     else return 'C_SIG'.\n"
            "   - Otherwise return 'OK/' followed by the lab and the five digits.\n"
        ),
        "starter_code": (
            'def validate(code: str) -> str:\n'
            '    """Validate a chemical batch code and return a status string."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_clean_order():\n'
            '    from clean_utils import clean\n'
            "    assert clean(' lb-qn ') == 'LBQN'\n"
            '\n'
            '\n'
            'def test_helper_sig_mid():\n'
            '    from sig_utils import sig_char\n'
            "    assert sig_char(15) == 'F'\n"
            '\n'
            '\n'
            'def test_helper_sig_zero():\n'
            '    from sig_utils import sig_char\n'
            "    assert sig_char(0) == 'A'\n"
            '\n'
            '\n'
            'def test_helper_sig_wraps():\n'
            '    from sig_utils import sig_char\n'
            "    assert sig_char(23) == 'D'\n"
            '\n'
            '\n'
            'def test_valid_code():\n'
            '    from solution import validate\n'
            "    assert validate('LBQN12345F') == 'OK/QN12345'\n"
            '\n'
            '\n'
            'def test_valid_after_cleaning():\n'
            '    from solution import validate\n'
            "    assert validate(' lb-qn-12345f ') == 'OK/QN12345'\n"
            '\n'
            '\n'
            'def test_short_code():\n'
            '    from solution import validate\n'
            "    assert validate('LBQN1234F') == 'C_FMT'\n"
            '\n'
            '\n'
            'def test_wrong_prefix():\n'
            '    from solution import validate\n'
            "    assert validate('XBQN12345F') == 'C_FMT'\n"
            '\n'
            '\n'
            'def test_unknown_lab():\n'
            '    from solution import validate\n'
            "    assert validate('LBZZ12345F') == 'C_LAB'\n"
            '\n'
            '\n'
            'def test_non_digit_block():\n'
            '    from solution import validate\n'
            "    assert validate('LBQN12a45F') == 'C_DIG'\n"
            '\n'
            '\n'
            'def test_wrong_signature():\n'
            '    from solution import validate\n'
            "    assert validate('LBQN12345G') == 'C_SIG'\n"
        ),
    },
    {
        "task_id": 'x_loyalty_ledger',
        "prompt": (
            'You are asked to implement a loyalty points ledger for an airline rewards program.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. bonus_utils.py must define `bonus(pts: int) -> int` returning\n'
            '   int(pts * 0.1500) (truncated) when pts is STRICTLY greater than 500,\n'
            '   else 0.\n'
            '2. lot_utils.py must define `lot_size(pts: int) -> int` returning\n'
            '   pts plus bonus(pts), clamped at a ceiling of 3000.\n'
            '3. expiry_utils.py must define `usable(earn_day: int, day: int) -> bool`\n'
            '   returning True iff day minus earn_day is STRICTLY less than 90.\n'
            '4. solution.py must define `settle(events: list) -> str`. The ledger keeps\n'
            '   a FIFO list of point lots, each remembering its earn day. Events are\n'
            "   ('earn', pts, day) or ('spend', pts, day), already in chronological\n"
            '   order. BEFORE processing each event, sweep the lots: every lot that is\n'
            "   no longer usable at the event's day is removed and its remaining points\n"
            '   are added to an expired counter. Then:\n'
            "   - 'earn': append a new lot of lot_size(pts) points.\n"
            "   - 'spend': a spend of STRICTLY more than 2000 points is rejected\n"
            '     outright. Otherwise the total cost is pts plus a redemption fee of\n'
            '     25 points; if the usable balance cannot cover the whole cost the\n'
            '     spend is rejected (nothing is consumed); otherwise consume the cost\n'
            '     from the OLDEST lots first.\n'
            "   - Return f'{balance}|{rejected}|{expired}' where balance is the sum of\n"
            '     the remaining lots after the last event.\n'
        ),
        "starter_code": (
            'def settle(events: list) -> str:\n'
            '    """Settle a chronological list of loyalty ledger events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_bonus_applied():\n'
            '    from bonus_utils import bonus\n'
            '    assert bonus(600) == 90\n'
            '\n'
            '\n'
            'def test_helper_bonus_edge():\n'
            '    from bonus_utils import bonus\n'
            '    assert bonus(500) == 0\n'
            '\n'
            '\n'
            'def test_helper_lot_size():\n'
            '    from lot_utils import lot_size\n'
            '    assert lot_size(600) == 690\n'
            '\n'
            '\n'
            'def test_helper_lot_ceiling():\n'
            '    from lot_utils import lot_size\n'
            '    assert lot_size(4000) == 3000\n'
            '\n'
            '\n'
            'def test_helper_usable_edge_in():\n'
            '    from expiry_utils import usable\n'
            '    assert usable(0, 89) == True\n'
            '\n'
            '\n'
            'def test_helper_usable_edge_out():\n'
            '    from expiry_utils import usable\n'
            '    assert usable(0, 90) == False\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import settle\n'
            "    assert settle([]) == '0|0|0'\n"
            '\n'
            '\n'
            'def test_earn_and_spend():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 100, 0), ('spend', 50, 10)]) == '25|0|0'\n"
            '\n'
            '\n'
            'def test_fee_blocks_spend():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 100, 0), ('spend', 80, 10)]) == '100|1|0'\n"
            '\n'
            '\n'
            'def test_expiry_before_spend():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 100, 0), ('spend', 10, 90)]) == '0|1|100'\n"
            '\n'
            '\n'
            'def test_fifo_consumption():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 100, 0), ('earn', 100, 50), ('spend', 80, 60)]) == '95|0|0'\n"
            '\n'
            '\n'
            'def test_expiry_keeps_younger_lot():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 100, 0), ('earn', 100, 50), ('spend', 50, 95)]) == '25|0|100'\n"
            '\n'
            '\n'
            'def test_oversize_spend_rejected():\n'
            '    from solution import settle\n'
            "    assert settle([('earn', 2500, 0), ('spend', 2001, 1)]) == '2875|1|0'\n"
        ),
    },
    {
        "task_id": 'x_prepaid_meter',
        "prompt": (
            'You are asked to implement a prepaid meter controller for an electricity utility.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. tariff_utils.py must define `energy_cost(kwh: float) -> float`: within\n'
            '   a single use, the first 45 kWh cost 0.8342 per kWh and every kWh above\n'
            '   that costs 1.1074 per kWh.\n'
            '2. credit_utils.py must define `can_serve(balance: float, cost: float) ->\n'
            '   bool` returning True iff balance minus cost is greater than or equal to\n'
            '   -15.0 (the emergency credit floor; the exact floor is allowed).\n'
            '3. solution.py must define `run(events: list) -> str`. The meter starts ON\n'
            "   with balance 0.0 and zero cuts. Events are ('topup', amount) or\n"
            "   ('use', kwh):\n"
            "   - 'use' while OFF is ignored entirely.\n"
            "   - 'use' while ON: let cost = energy_cost(kwh). If can_serve(balance,\n"
            '     cost), subtract the cost (the balance may go negative down to the\n'
            '     emergency floor). Otherwise the use is rejected in full, the meter\n'
            '     goes OFF and one cut is counted.\n'
            "   - 'topup': the amount is always added to the balance. If the meter is\n"
            '     OFF and this single top-up is at least 20.0, the meter turns back ON\n'
            '     and a reconnection fee of 11.35 is subtracted (smaller top-ups never\n'
            '     restore power, no matter the accumulated balance).\n'
            "   - Return f'{state}|{balance:.2f}|{cuts}' where state is 'ON' or 'OFF'.\n"
        ),
        "starter_code": (
            'def run(events: list) -> str:\n'
            '    """Run the prepaid meter controller over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_cost_low_tier():\n'
            '    from tariff_utils import energy_cost\n'
            '    assert energy_cost(10) == 8.342\n'
            '\n'
            '\n'
            'def test_helper_cost_tier_edge():\n'
            '    from tariff_utils import energy_cost\n'
            '    assert energy_cost(45) == 37.539\n'
            '\n'
            '\n'
            'def test_helper_cost_two_tiers():\n'
            '    from tariff_utils import energy_cost\n'
            '    assert energy_cost(50) == 43.076\n'
            '\n'
            '\n'
            'def test_helper_can_serve_floor():\n'
            '    from credit_utils import can_serve\n'
            '    assert can_serve(0.0, 15.0) == True\n'
            '\n'
            '\n'
            'def test_helper_cannot_serve_past_floor():\n'
            '    from credit_utils import can_serve\n'
            '    assert can_serve(0.0, 15.01) == False\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import run\n'
            "    assert run([]) == 'ON|0.00|0'\n"
            '\n'
            '\n'
            'def test_topup_then_use():\n'
            '    from solution import run\n'
            "    assert run([('topup', 50.0), ('use', 10)]) == 'ON|41.66|0'\n"
            '\n'
            '\n'
            'def test_emergency_credit():\n'
            '    from solution import run\n'
            "    assert run([('use', 10)]) == 'ON|-8.34|0'\n"
            '\n'
            '\n'
            'def test_cut_when_past_floor():\n'
            '    from solution import run\n'
            "    assert run([('use', 20)]) == 'OFF|0.00|1'\n"
            '\n'
            '\n'
            'def test_use_while_off_ignored():\n'
            '    from solution import run\n'
            "    assert run([('use', 20), ('use', 1)]) == 'OFF|0.00|1'\n"
            '\n'
            '\n'
            'def test_small_topup_never_restores():\n'
            '    from solution import run\n'
            "    assert run([('use', 20), ('topup', 10.0)]) == 'OFF|10.00|1'\n"
            '\n'
            '\n'
            'def test_restore_charges_fee():\n'
            '    from solution import run\n'
            "    assert run([('use', 20), ('topup', 30.0)]) == 'ON|18.65|1'\n"
            '\n'
            '\n'
            'def test_cumulative_topups_do_not_restore():\n'
            '    from solution import run\n'
            "    assert run([('use', 20), ('topup', 10.0), ('topup', 10.0)]) == 'OFF|20.00|1'\n"
        ),
    },
    {
        "task_id": 'x_escrow_ledger',
        "prompt": (
            'You are asked to implement an escrow ledger reconciler for a payments processor.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. fee_utils.py must define `capture_fee(amount: float) -> float`\n'
            '   returning round(amount * 0.0290, 2).\n'
            '2. hold_utils.py must define `trim(amount: float) -> float` returning the\n'
            '   amount clamped at a ceiling of 2500.0.\n'
            '3. solution.py must define `reconcile(entries: list) -> str`. Entries are\n'
            "   ('hold', hid, amount), ('capture', hid, amount) or ('void', hid):\n"
            "   - 'hold': registering an id that already exists is an error; otherwise\n"
            '     the hold opens with a remaining amount of trim(amount) and zero\n'
            '     captures.\n'
            "   - 'capture': it is an error when the hold id is unknown, OR the hold\n"
            '     was voided, OR the amount is STRICTLY below the minimum of 5.0, OR\n'
            "     the amount exceeds the hold's remaining amount. Otherwise the\n"
            '     remaining amount drops by the captured amount, the captured total\n'
            '     rises by it, and capture_fee(amount) is added to the fee total\n'
            '     (several captures may hit the same hold).\n'
            "   - 'void': it is an error when the hold id is unknown or already voided.\n"
            '     Otherwise the hold is voided, its remaining amount becomes 0.0, and\n'
            '     when the hold had ZERO captures a flat void fee of 1.4500 is added to\n'
            '     the fee total.\n'
            '   - After any entry, once the error counter reaches 4 the ledger becomes\n'
            '     FROZEN and every later entry is ignored entirely.\n'
            "   - Return f'{state}|{captured:.2f}|{held_open:.2f}|{fees:.2f}|{errors}'\n"
            '     where held_open sums the remaining amounts of all holds and state is\n'
            "     'OPEN' or 'FROZEN'.\n"
        ),
        "starter_code": (
            'def reconcile(entries: list) -> str:\n'
            '    """Reconcile an escrow ledger from a list of entries."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_capture_fee():\n'
            '    from fee_utils import capture_fee\n'
            '    assert capture_fee(100.0) == 2.9\n'
            '\n'
            '\n'
            'def test_helper_capture_fee_rounds():\n'
            '    from fee_utils import capture_fee\n'
            '    assert capture_fee(33.33) == 0.97\n'
            '\n'
            '\n'
            'def test_helper_trim_applied():\n'
            '    from hold_utils import trim\n'
            '    assert trim(3000.0) == 2500.0\n'
            '\n'
            '\n'
            'def test_helper_trim_not_applied():\n'
            '    from hold_utils import trim\n'
            '    assert trim(100.0) == 100.0\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([]) == 'OPEN|0.00|0.00|0.00|0'\n"
            '\n'
            '\n'
            'def test_hold_and_capture():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 40.0)]) == 'OPEN|40.00|60.00|1.16|0'\n"
            '\n'
            '\n'
            'def test_capture_beyond_remaining_error():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 60.0), ('capture', 'h1', 40.0), ('capture', 'h1', 10.0)]) == 'OPEN|100.00|0.00|2.90|1'\n"
            '\n'
            '\n'
            'def test_minimum_capture():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 4.99)]) == 'OPEN|0.00|100.00|0.00|1'\n"
            '\n'
            '\n'
            'def test_void_after_capture_no_fee():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('capture', 'h1', 40.0), ('void', 'h1')]) == 'OPEN|40.00|0.00|1.16|0'\n"
            '\n'
            '\n'
            'def test_void_without_capture_fee():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('void', 'h1')]) == 'OPEN|0.00|0.00|1.45|0'\n"
            '\n'
            '\n'
            'def test_capture_after_void_error():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('void', 'h1'), ('capture', 'h1', 10.0)]) == 'OPEN|0.00|0.00|1.45|1'\n"
            '\n'
            '\n'
            'def test_hold_ceiling():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 3000.0), ('capture', 'h1', 2500.0)]) == 'OPEN|2500.00|0.00|72.50|0'\n"
            '\n'
            '\n'
            'def test_frozen_after_four_errors():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('capture', 'x', 10.0)] * 4 + [('hold', 'h1', 100.0)]) == 'FROZEN|0.00|0.00|0.00|4'\n"
            '\n'
            '\n'
            'def test_duplicate_hold_error():\n'
            '    from solution import reconcile\n'
            "    assert reconcile([('hold', 'h1', 100.0), ('hold', 'h1', 50.0)]) == 'OPEN|0.00|100.00|0.00|1'\n"
        ),
    },
    {
        "task_id": 'x_hours_bank',
        "prompt": (
            'You are asked to implement an hours bank ledger for a staffing agency payroll team.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. id_utils.py must define `emp_ok(emp: str) -> bool` returning True iff\n'
            "   emp starts with 'EM-'.\n"
            '2. hours_utils.py must define `credited(hours: float, night: bool) ->\n'
            '   float`: hours STRICTLY above 8 in a single shift are credited at\n'
            '   1.5000 times (the first 8 at face value); THEN, if night is True, the\n'
            '   whole credited value is multiplied by 1.2500 (the night multiplier is\n'
            '   applied AFTER the overtime split).\n'
            '3. solution.py must define `bank(events: list) -> tuple`. Events are\n'
            "   ('work', emp, hours, night) or ('claim', emp, hours):\n"
            '   - Any event whose emp fails emp_ok is counted as invalid and otherwise\n'
            '     ignored.\n'
            "   - 'work': add credited(hours, night) to the employee's balance; any\n"
            '     excess above the bank ceiling of 120.0 hours is LOST (added to a lost\n'
            '     counter, balance capped).\n'
            "   - 'claim': the claim is rejected when hours is not a multiple of 4 or\n"
            "     the employee's balance cannot cover it in full; otherwise the balance\n"
            '     drops by the claimed hours.\n'
            '   - Return (balances, round(lost, 2), rejected, invalid) where balances\n'
            '     is the sorted list of (emp, balance) pairs.\n'
        ),
        "starter_code": (
            'def bank(events: list) -> tuple:\n'
            '    """Run the hours bank ledger over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_emp_ok():\n'
            '    from id_utils import emp_ok\n'
            "    assert emp_ok('EM-77') == True\n"
            '\n'
            '\n'
            'def test_helper_emp_bad():\n'
            '    from id_utils import emp_ok\n'
            "    assert emp_ok('XX-77') == False\n"
            '\n'
            '\n'
            'def test_helper_credited_plain():\n'
            '    from hours_utils import credited\n'
            '    assert credited(8.0, False) == 8.0\n'
            '\n'
            '\n'
            'def test_helper_credited_overtime():\n'
            '    from hours_utils import credited\n'
            '    assert credited(10.0, False) == 11.0\n'
            '\n'
            '\n'
            'def test_helper_credited_night_after_overtime():\n'
            '    from hours_utils import credited\n'
            '    assert credited(10.0, True) == 13.75\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import bank\n'
            '    assert bank([]) == ([], 0.0, 0, 0)\n'
            '\n'
            '\n'
            'def test_simple_work():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'EM-A', 10.0, False)]) == ([('EM-A', 11.0)], 0.0, 0, 0)\n"
            '\n'
            '\n'
            'def test_ceiling_loses_excess():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'EM-A', 80.0, False), ('work', 'EM-A', 80.0, False)]) == ([('EM-A', 120.0)], 112.0, 0, 0)\n"
            '\n'
            '\n'
            'def test_claim_ok():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 8)]) == ([('EM-A', 3.0)], 0.0, 0, 0)\n"
            '\n'
            '\n'
            'def test_claim_not_multiple_rejected():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 6)]) == ([('EM-A', 11.0)], 0.0, 1, 0)\n"
            '\n'
            '\n'
            'def test_claim_insufficient_rejected():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'EM-A', 10.0, False), ('claim', 'EM-A', 12)]) == ([('EM-A', 11.0)], 0.0, 1, 0)\n"
            '\n'
            '\n'
            'def test_invalid_employee():\n'
            '    from solution import bank\n'
            "    assert bank([('work', 'XX-A', 10.0, False)]) == ([], 0.0, 0, 1)\n"
        ),
    },
    {
        "task_id": 'x_night_surcharge',
        "prompt": (
            'You are asked to implement a minute-based surcharge rater for a taxi network.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. window_utils.py must define `band(minute: int) -> str` for minutes of\n'
            "   the day. The peak band 'P' covers minutes 300 (inclusive) to 540\n"
            "   (exclusive). The night band 'N' covers minutes 1290 (inclusive) to the\n"
            '   end of the day AND minutes before 330. The two windows OVERLAP between\n'
            '   minutes 300 and 330: there the peak band takes precedence. Every other\n'
            "   minute is the day band 'D'.\n"
            '2. mult_utils.py must define `mult(band_code: str) -> float` returning\n'
            "   1.7500 for 'N', 2.2500 for 'P' and 1.0 otherwise.\n"
            '3. solution.py must define `charge(intervals: list) -> float` where each\n'
            '   interval is (start_minute, end_minute), end exclusive. Every minute\n'
            '   costs a base of 0.0410 times the multiplier of its band. Sum over all\n'
            '   minutes of all intervals and return round(total, 2).\n'
        ),
        "starter_code": (
            'def charge(intervals: list) -> float:\n'
            '    """Charge a list of half-open minute intervals."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_band_peak_start():\n'
            '    from window_utils import band\n'
            "    assert band(300) == 'P'\n"
            '\n'
            '\n'
            'def test_helper_band_overlap_is_peak():\n'
            '    from window_utils import band\n'
            "    assert band(329) == 'P'\n"
            '\n'
            '\n'
            'def test_helper_band_night_before_peak():\n'
            '    from window_utils import band\n'
            "    assert band(299) == 'N'\n"
            '\n'
            '\n'
            'def test_helper_band_peak_end():\n'
            '    from window_utils import band\n'
            "    assert band(539) == 'P'\n"
            '\n'
            '\n'
            'def test_helper_band_day_after_peak():\n'
            '    from window_utils import band\n'
            "    assert band(540) == 'D'\n"
            '\n'
            '\n'
            'def test_helper_band_night_start():\n'
            '    from window_utils import band\n'
            "    assert band(1290) == 'N'\n"
            '\n'
            '\n'
            'def test_helper_band_day_before_night():\n'
            '    from window_utils import band\n'
            "    assert band(1289) == 'D'\n"
            '\n'
            '\n'
            'def test_helper_mult_night():\n'
            '    from mult_utils import mult\n'
            "    assert mult('N') == 1.75\n"
            '\n'
            '\n'
            'def test_helper_mult_peak():\n'
            '    from mult_utils import mult\n'
            "    assert mult('P') == 2.25\n"
            '\n'
            '\n'
            'def test_helper_mult_day():\n'
            '    from mult_utils import mult\n'
            "    assert mult('D') == 1.0\n"
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import charge\n'
            '    assert charge([]) == 0.0\n'
            '\n'
            '\n'
            'def test_day_interval():\n'
            '    from solution import charge\n'
            '    assert charge([(600, 660)]) == 2.46\n'
            '\n'
            '\n'
            'def test_crosses_night_peak_boundary():\n'
            '    from solution import charge\n'
            '    assert charge([(290, 310)]) == 1.64\n'
            '\n'
            '\n'
            'def test_crosses_day_night_boundary():\n'
            '    from solution import charge\n'
            '    assert charge([(1280, 1300)]) == 1.13\n'
        ),
    },
    {
        "task_id": 'x_freight_zones',
        "prompt": (
            'You are asked to implement a freight corridor rater for an overland haulage company.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. rate_utils.py must define `zone_rate(zone: str) -> float` returning\n'
            "   1.2400 per km for zone 'ZN-A', 0.8800 for zone 'ZN-B' and 1.9100 for\n"
            '   any other zone.\n'
            '2. corridor_utils.py must define `corridor_split(cum_before, km)`\n'
            '   returning the tuple (normal_km, corridor_km): of the km driven in a\n'
            '   leg, the part that keeps the CUMULATIVE route distance at or below the\n'
            '   corridor threshold of 250 km is normal, the rest is corridor (a leg may\n'
            '   split in the middle; when cum_before already exceeds the threshold the\n'
            '   whole leg is corridor).\n'
            '3. solution.py must define `quote(legs: list) -> float` where each leg is\n'
            '   (zone, km), in route order. Normal km are billed at the zone rate;\n'
            '   corridor km are ALWAYS billed at the flat corridor rate of 0.6200\n'
            '   regardless of zone (the corridor rate takes precedence). An empty route\n'
            '   costs 0.0; any non-empty route is billed at least the minimum charge of\n'
            '   68.0. Return round(total, 2).\n'
        ),
        "starter_code": (
            'def quote(legs: list) -> float:\n'
            '    """Quote a freight route given its legs."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_a():\n'
            '    from rate_utils import zone_rate\n'
            "    assert zone_rate('ZN-A') == 1.24\n"
            '\n'
            '\n'
            'def test_helper_rate_b():\n'
            '    from rate_utils import zone_rate\n'
            "    assert zone_rate('ZN-B') == 0.88\n"
            '\n'
            '\n'
            'def test_helper_rate_other():\n'
            '    from rate_utils import zone_rate\n'
            "    assert zone_rate('ZN-X') == 1.91\n"
            '\n'
            '\n'
            'def test_helper_split_all_normal():\n'
            '    from corridor_utils import corridor_split\n'
            '    assert corridor_split(0, 100) == (100, 0)\n'
            '\n'
            '\n'
            'def test_helper_split_middle():\n'
            '    from corridor_utils import corridor_split\n'
            '    assert corridor_split(200, 100) == (50, 50)\n'
            '\n'
            '\n'
            'def test_helper_split_all_corridor():\n'
            '    from corridor_utils import corridor_split\n'
            '    assert corridor_split(300, 100) == (0, 100)\n'
            '\n'
            '\n'
            'def test_empty_route():\n'
            '    from solution import quote\n'
            '    assert quote([]) == 0.0\n'
            '\n'
            '\n'
            'def test_minimum_charge():\n'
            '    from solution import quote\n'
            "    assert quote([('ZN-B', 10)]) == 68.0\n"
            '\n'
            '\n'
            'def test_simple_leg():\n'
            '    from solution import quote\n'
            "    assert quote([('ZN-A', 100)]) == 124.0\n"
            '\n'
            '\n'
            'def test_split_mid_leg():\n'
            '    from solution import quote\n'
            "    assert quote([('ZN-A', 200), ('ZN-A', 100)]) == 341.0\n"
            '\n'
            '\n'
            'def test_exact_threshold_boundary():\n'
            '    from solution import quote\n'
            "    assert quote([('ZN-A', 250), ('ZN-B', 10)]) == 316.2\n"
            '\n'
            '\n'
            'def test_unknown_zone_rate():\n'
            '    from solution import quote\n'
            "    assert quote([('ZN-Q', 100)]) == 191.0\n"
        ),
    },
    {
        "task_id": 'x_spot_power',
        "prompt": (
            'You are asked to implement a spot power biller for an industrial energy retailer.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. band_utils.py must define `hour_rate(hour: int) -> float`. The critical\n'
            '   band covers hours 17 (inclusive) to 21 (exclusive) at 0.5236 per kWh.\n'
            '   The green band covers hours 10 (inclusive) to 18 (exclusive) at 0.0913\n'
            '   per kWh. The two bands OVERLAP at hour 17: there the critical band\n'
            '   takes precedence. Every other hour is billed at the base rate of\n'
            '   0.2147 per kWh.\n'
            '2. demand_utils.py must define `demand_fee(max_kwh: float) -> float`\n'
            '   returning max_kwh times 3.4100.\n'
            '3. solution.py must define `bill(usage: list) -> float` where each reading\n'
            '   is (hour, kwh). The energy charge sums kwh times hour_rate(hour) over\n'
            '   all readings. The demand charge is demand_fee of the LARGEST single\n'
            "   reading's kwh. An empty usage list costs 0.0. Otherwise return\n"
            '   round(energy + demand, 2).\n'
        ),
        "starter_code": (
            'def bill(usage: list) -> float:\n'
            '    """Bill a list of hourly power readings."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_overlap_is_critical():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(17) == 0.5236\n'
            '\n'
            '\n'
            'def test_helper_rate_critical_end():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(20) == 0.5236\n'
            '\n'
            '\n'
            'def test_helper_rate_base_after_critical():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(21) == 0.2147\n'
            '\n'
            '\n'
            'def test_helper_rate_green_start():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(10) == 0.0913\n'
            '\n'
            '\n'
            'def test_helper_rate_base_before_green():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(9) == 0.2147\n'
            '\n'
            '\n'
            'def test_helper_rate_green_mid():\n'
            '    from band_utils import hour_rate\n'
            '    assert hour_rate(16) == 0.0913\n'
            '\n'
            '\n'
            'def test_helper_demand_fee():\n'
            '    from demand_utils import demand_fee\n'
            '    assert demand_fee(10.0) == 34.1\n'
            '\n'
            '\n'
            'def test_empty_usage():\n'
            '    from solution import bill\n'
            '    assert bill([]) == 0.0\n'
            '\n'
            '\n'
            'def test_single_green_reading():\n'
            '    from solution import bill\n'
            '    assert bill([(12, 10.0)]) == 35.01\n'
            '\n'
            '\n'
            'def test_mixed_bands():\n'
            '    from solution import bill\n'
            '    assert bill([(18, 5.0), (3, 5.0)]) == 20.74\n'
            '\n'
            '\n'
            'def test_peak_is_single_largest():\n'
            '    from solution import bill\n'
            '    assert bill([(12, 2.0), (12, 7.0)]) == 24.69\n'
            '\n'
            '\n'
            'def test_boundary_hour_base():\n'
            '    from solution import bill\n'
            '    assert bill([(21, 1.0)]) == 3.62\n'
        ),
    },
]

STRATA: dict[str, str] = {
    'x_vault_lock': "H",
    'x_vending_fsm': "H",
    'x_badge_gate': "H",
    'x_reactor_protocol': "H",
    'x_parcel_locker': "H",
    'x_berth_scheduler': "H",
    'x_courier_dispatch': "H",
    'x_grant_allocator': "H",
    'x_court_scheduler': "H",
    'x_plate_validator': "H",
    'x_voucher_parser': "H",
    'x_scale_barcode': "H",
    'x_chem_batch': "H",
    'x_loyalty_ledger': "H",
    'x_prepaid_meter': "H",
    'x_escrow_ledger': "H",
    'x_hours_bank': "H",
    'x_night_surcharge': "H",
    'x_freight_zones': "H",
    'x_spot_power': "H",
}

CRITICAL_CONSTANTS: dict[str, list[str]] = {
    'x_vault_lock': [
        '6',
        '73',
        '21',
        "'AL-RED'",
        "'AL-AMB'",
        "'AL-OFF'",
        '3',
        '4',
        '5',
    ],
    'x_vending_fsm': [
        "'CN-A'",
        "'CN-B'",
        "'CN-C'",
        '7',
        '13',
        '28',
        "'KA'",
        "'KB'",
        '41',
        '67',
        '89',
        '4',
    ],
    'x_badge_gate': [
        "'GV-'",
        "'CT-'",
        "'Z-CORE'",
        "'Z-LAB'",
        '4',
        '2',
        '5',
        "'LOCKDOWN'",
    ],
    'x_reactor_protocol': [
        "'ESTOP'",
        "'VENT'",
        "'FUEL'",
        '9',
        '258',
        '700',
        '164',
        '3',
    ],
    'x_parcel_locker': [
        "'PX-'",
        '8',
        '5',
        '4',
        '3',
        "'OFFLINE'",
    ],
    'x_berth_scheduler': [
        '0.7500',
        "'BS'",
        '6.2500',
        "'BR'",
        '8.5000',
        "'BQ'",
        '11.7500',
        '2',
        "'ANCHOR'",
    ],
    'x_courier_dispatch': [
        '6.2500',
        '0.4100',
        '3.5000',
        '87',
        '2.1500',
        '3',
        "'HOLD'",
    ],
    'x_grant_allocator': [
        "'NG-'",
        '7',
        '12500',
        '41',
        '0.0180',
        '750',
        '0.6200',
    ],
    'x_court_scheduler': [
        "'RA'",
        "'RB'",
        '300',
        '195',
        '15',
        '120',
        "'DEFER'",
    ],
    'x_plate_validator': [
        "'BCDFGHJKLMNPQRSTVWXZ'",
        '7',
        '5',
        '11',
        '20',
        "'E_LEN'",
        "'E_DIG'",
        "'E_ALPHA'",
        "'E_CHK'",
        "'OK-'",
    ],
    'x_voucher_parser': [
        "'VXA'",
        "'VXB'",
        "'VXQ'",
        '250',
        '475',
        '60',
        "'2346789ACDEFGH'",
        '13',
        '89',
        '3',
        "'BAD_KIND'",
        "'BAD_SUM'",
    ],
    'x_scale_barcode': [
        '13',
        "'27'",
        '7',
        '10',
        '12',
        '100',
        "'B_LEN'",
        "'B_PFX'",
        "'B_CHK'",
    ],
    'x_chem_batch': [
        "'LB'",
        "'QN'",
        "'TR'",
        "'VX'",
        "'ABCDEFGHJK'",
        '10',
        "'C_FMT'",
        "'C_LAB'",
        "'C_DIG'",
        "'C_SIG'",
        "'OK/'",
    ],
    'x_loyalty_ledger': [
        '0.1500',
        '500',
        '3000',
        '90',
        '2000',
        '25',
    ],
    'x_prepaid_meter': [
        '0.8342',
        '1.1074',
        '45',
        '15.0',
        '20.0',
        '11.35',
    ],
    'x_escrow_ledger': [
        '0.0290',
        '2500.0',
        '5.0',
        '1.4500',
        '4',
        "'FROZEN'",
    ],
    'x_hours_bank': [
        "'EM-'",
        '8',
        '1.5000',
        '1.2500',
        '120',
        '4',
    ],
    'x_night_surcharge': [
        '300',
        '540',
        '1290',
        '330',
        '1.7500',
        '2.2500',
        '0.0410',
    ],
    'x_freight_zones': [
        "'ZN-A'",
        "'ZN-B'",
        '1.2400',
        '0.8800',
        '1.9100',
        '250',
        '0.6200',
        '68.0',
    ],
    'x_spot_power': [
        '17',
        '21',
        '0.5236',
        '10',
        '18',
        '0.0913',
        '0.2147',
        '3.4100',
    ],
}


def get_task(task_id: str) -> dict:
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise KeyError(task_id)
