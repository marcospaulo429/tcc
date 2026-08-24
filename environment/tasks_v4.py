"""Pool fixo de 24 tasks v4 (estrato H, prefixo h_) para o D4 (pré-registro 17).

Tasks estilo v3 endurecidas para o Qwen3-8B ficar em regime fracionário:

- 3-4 arquivos por task (2-3 helpers + solution.py), cada helper com regra
  própria; imports DENTRO das funções de teste para reward gradual.
- 6-12 constantes de negócio arbitrárias por task (floats de 4 decimais,
  thresholds inteiros estranhos, strings-código), TODAS aparecendo APÓS o
  char 240 do prompt — os primeiros ~240 chars são preâmbulo genérico, de modo
  que um summarize que trunque em 240 chars destrói as constantes.
- 10-14 funções de teste por task, 1 assert cada, cobrindo caminhos distintos:
  cada constante crítica é exercida por >=1 teste, com casos de borda
  adversariais (limites exatos inclusive/exclusive, listas vazias, empates,
  arredondamento half-up em pontos específicos do pipeline).
- starter_code: assinatura + NotImplementedError, sem nenhuma constante.

Gerado com solução canônica validada a 100% no sandbox (tests/test_tasks_v4.py
re-executa a validação para uma amostra determinística).
"""

TASKS: list[dict] = [
    {
        "task_id": 'h_customs_clearance',
        "prompt": (
            'You are asked to implement a customs clearance module for a freight forwarding firm.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. fx_utils.py must define `to_local(amount: float, currency: str) -> float`\n'
            "   returning amount * 5.2731 for 'EUR', amount * 6.1408 for 'GBP',\n"
            "   amount * 4.9377 for 'USD' and amount * 1.0 for 'LOC'.\n"
            '2. round_utils.py must define `half_up2(x: float) -> float` returning\n'
            '   math.floor(x * 100 + 0.5) / 100 (half-up rounding to two decimals).\n'
            '3. solution.py must define `clearance(items: list) -> float` where each\n'
            '   item is a tuple (category, amount, currency), computed in this exact\n'
            '   order:\n'
            '   - For each item: local = to_local(amount, currency).\n'
            "   - Duty rate by category prefix: 0.1873 if category starts with 'QX-',\n"
            "     0.0942 if it starts with 'RM-', otherwise 0.2417.\n"
            '   - Exemption: if local is STRICTLY less than 683 the item pays no duty\n'
            '     (at exactly 683 the duty applies).\n'
            '   - The cost of one item is half_up2(local + local * duty_rate),\n'
            '     rounded per item BEFORE summing.\n'
            '   - total = sum of the item costs plus a flat handling fee of 41.85\n'
            '     (the fee applies even for an empty list).\n'
            '   - Bulk rebate: if the list has STRICTLY more than 7 items, multiply\n'
            '     total by 0.9315 (at exactly 7 items there is no rebate).\n'
            '   - Return half_up2(total).\n'
        ),
        "starter_code": (
            'def clearance(items: list) -> float:\n'
            '    """Compute the customs clearance total for a list of items."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_half_up2_basic():\n'
            '    from round_utils import half_up2\n'
            '    assert half_up2(3.14159) == 3.14\n'
            '\n'
            '\n'
            'def test_helper_half_up2_half_cent():\n'
            '    from round_utils import half_up2\n'
            '    assert half_up2(2.005) == 2.01\n'
            '\n'
            '\n'
            'def test_helper_fx_eur():\n'
            '    from fx_utils import to_local\n'
            "    assert to_local(10.0, 'EUR') == 52.731\n"
            '\n'
            '\n'
            'def test_helper_fx_gbp():\n'
            '    from fx_utils import to_local\n'
            "    assert to_local(10.0, 'GBP') == 61.407999999999994\n"
            '\n'
            '\n'
            'def test_helper_fx_usd():\n'
            '    from fx_utils import to_local\n'
            "    assert to_local(100.0, 'USD') == 493.77000000000004\n"
            '\n'
            '\n'
            'def test_exempt_item_below_threshold():\n'
            '    from solution import clearance\n'
            "    assert clearance([('QX-A', 100.0, 'LOC')]) == 141.85\n"
            '\n'
            '\n'
            'def test_duty_at_exact_threshold():\n'
            '    from solution import clearance\n'
            "    assert clearance([('ZZ-A', 683.0, 'LOC')]) == 889.93\n"
            '\n'
            '\n'
            'def test_qx_rate():\n'
            '    from solution import clearance\n'
            "    assert clearance([('QX-B', 700.0, 'LOC')]) == 872.96\n"
            '\n'
            '\n'
            'def test_rm_rate():\n'
            '    from solution import clearance\n'
            "    assert clearance([('RM-C', 700.0, 'LOC')]) == 807.79\n"
            '\n'
            '\n'
            'def test_default_rate_eur():\n'
            '    from solution import clearance\n'
            "    assert clearance([('AA-D', 150.0, 'EUR')]) == 1023.99\n"
            '\n'
            '\n'
            'def test_empty_list_pays_handling():\n'
            '    from solution import clearance\n'
            '    assert clearance([]) == 41.85\n'
            '\n'
            '\n'
            'def test_bulk_rebate_eight_items():\n'
            '    from solution import clearance\n'
            "    assert clearance([('QX-A', 10.0, 'LOC')] * 8) == 113.5\n"
            '\n'
            '\n'
            'def test_no_rebate_at_seven_items():\n'
            '    from solution import clearance\n'
            "    assert clearance([('QX-A', 10.0, 'LOC')] * 7) == 111.85\n"
        ),
    },
    {
        "task_id": 'h_hotel_folio',
        "prompt": (
            'You are asked to implement a hotel folio calculator for a boutique hotel chain.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. season_utils.py must define `room_rate(month: int) -> float`\n'
            '   returning 412.60 for months 6, 7 and 8; 388.45 for months 12 and 1;\n'
            '   and 297.30 for every other month.\n'
            '2. fee_utils.py must define\n'
            '   `city_tax(rate: float, taxed_nights: int) -> float` returning\n'
            '   rate * taxed_nights * 0.0685.\n'
            '3. solution.py must define\n'
            '   `folio(nights: int, month: int, breakfast: bool) -> float` computed\n'
            '   in this exact order, where half_up(x) means\n'
            '   math.floor(x * 100 + 0.5) / 100:\n'
            '   - rate = room_rate(month); room = rate * nights.\n'
            '   - Long-stay: if nights is STRICTLY greater than 13, multiply room by\n'
            '     0.8823 (at exactly 13 nights there is no discount).\n'
            '   - meals = 23.4 * nights if breakfast is True, otherwise 0.0.\n'
            '   - City tax is charged on the UNDISCOUNTED nightly rate and for at\n'
            '     most 9 nights: tax = city_tax(rate, min(nights, 9)).\n'
            '   - Return round(half_up(room) + half_up(meals) + half_up(tax), 2).\n'
        ),
        "starter_code": (
            'def folio(nights: int, month: int, breakfast: bool) -> float:\n'
            '    """Compute the total hotel folio for a stay."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_summer():\n'
            '    from season_utils import room_rate\n'
            '    assert room_rate(7) == 412.6\n'
            '\n'
            '\n'
            'def test_helper_rate_december():\n'
            '    from season_utils import room_rate\n'
            '    assert room_rate(12) == 388.45\n'
            '\n'
            '\n'
            'def test_helper_rate_january():\n'
            '    from season_utils import room_rate\n'
            '    assert room_rate(1) == 388.45\n'
            '\n'
            '\n'
            'def test_helper_rate_shoulder():\n'
            '    from season_utils import room_rate\n'
            '    assert room_rate(4) == 297.3\n'
            '\n'
            '\n'
            'def test_helper_city_tax():\n'
            '    from fee_utils import city_tax\n'
            '    assert city_tax(100.0, 9) == 61.650000000000006\n'
            '\n'
            '\n'
            'def test_short_stay_no_breakfast():\n'
            '    from solution import folio\n'
            '    assert folio(3, 4, False) == 953.0\n'
            '\n'
            '\n'
            'def test_short_stay_with_breakfast():\n'
            '    from solution import folio\n'
            '    assert folio(3, 4, True) == 1023.2\n'
            '\n'
            '\n'
            'def test_long_stay_discount():\n'
            '    from solution import folio\n'
            '    assert folio(14, 4, False) == 3855.6\n'
            '\n'
            '\n'
            'def test_thirteen_nights_no_discount():\n'
            '    from solution import folio\n'
            '    assert folio(13, 4, False) == 4048.19\n'
            '\n'
            '\n'
            'def test_tax_capped_at_nine_nights():\n'
            '    from solution import folio\n'
            '    assert folio(10, 4, False) == 3156.29\n'
            '\n'
            '\n'
            'def test_exactly_nine_nights():\n'
            '    from solution import folio\n'
            '    assert folio(9, 4, False) == 2858.99\n'
            '\n'
            '\n'
            'def test_long_summer_tax_undiscounted():\n'
            '    from solution import folio\n'
            '    assert folio(14, 6, False) == 5350.89\n'
        ),
    },
    {
        "task_id": 'h_freight_ladder',
        "prompt": (
            'You are asked to implement a tiered freight pricing module for a cargo airline.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. band_utils.py must define `band_charge(kg: float) -> float` using\n'
            '   cumulative bands: the first 137 kg cost 2.3146 per kg, the portion\n'
            '   above 137 and up to 415 kg costs 1.9072 per kg, and the portion\n'
            '   above 415 kg costs 1.4381 per kg.\n'
            '2. surcharge_utils.py must define `fuel(amount: float) -> float`\n'
            '   returning amount * 0.1176.\n'
            '3. solution.py must define `quote(kg: float, insured: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - c = band_charge(kg).\n'
            '   - Add fuel(c) to c.\n'
            '   - Minimum charge: if c is STRICTLY less than 89, set c to 89\n'
            '     (applied after the fuel surcharge).\n'
            '   - If insured is True, add a flat insurance fee of 27.55 (the\n'
            '     insurance fee is never subject to fuel and never counts toward\n'
            '     the minimum).\n'
            '   - Return round(c, 2).\n'
        ),
        "starter_code": (
            'def quote(kg: float, insured: bool) -> float:\n'
            '    """Compute the freight quote for a shipment weight."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_band_first():\n'
            '    from band_utils import band_charge\n'
            '    assert band_charge(100) == 231.46\n'
            '\n'
            '\n'
            'def test_helper_band_exact_first_edge():\n'
            '    from band_utils import band_charge\n'
            '    assert band_charge(137) == 317.1002\n'
            '\n'
            '\n'
            'def test_helper_band_second():\n'
            '    from band_utils import band_charge\n'
            '    assert band_charge(200) == 437.25379999999996\n'
            '\n'
            '\n'
            'def test_helper_band_exact_second_edge():\n'
            '    from band_utils import band_charge\n'
            '    assert band_charge(415) == 847.3018\n'
            '\n'
            '\n'
            'def test_helper_band_third():\n'
            '    from band_utils import band_charge\n'
            '    assert band_charge(500) == 969.5402999999999\n'
            '\n'
            '\n'
            'def test_helper_fuel():\n'
            '    from surcharge_utils import fuel\n'
            '    assert fuel(100.0) == 11.76\n'
            '\n'
            '\n'
            'def test_minimum_applies_small_load():\n'
            '    from solution import quote\n'
            '    assert quote(10, False) == 89\n'
            '\n'
            '\n'
            'def test_above_minimum_no_bump():\n'
            '    from solution import quote\n'
            '    assert quote(40, False) == 103.47\n'
            '\n'
            '\n'
            'def test_insured_small_load():\n'
            '    from solution import quote\n'
            '    assert quote(10, True) == 116.55\n'
            '\n'
            '\n'
            'def test_zero_kg_minimum():\n'
            '    from solution import quote\n'
            '    assert quote(0, False) == 89\n'
            '\n'
            '\n'
            'def test_large_insured():\n'
            '    from solution import quote\n'
            '    assert quote(500, True) == 1111.11\n'
            '\n'
            '\n'
            'def test_mid_band_quote():\n'
            '    from solution import quote\n'
            '    assert quote(200, False) == 488.67\n'
        ),
    },
    {
        "task_id": 'h_parking_tariff',
        "prompt": (
            'You are asked to implement a parking garage tariff module for an airport operator.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. time_utils.py must define `blocks(minutes: int) -> int`: the first\n'
            '   45 minutes are free; beyond that, every STARTED block of 30 minutes\n'
            '   counts as one block (so any minutes <= 45 gives no block at all and\n'
            '   one minute past the free window already counts one full block).\n'
            '2. plate_utils.py must define `is_ev(plate: str) -> bool` returning\n'
            "   True iff plate starts with 'EV-'.\n"
            '3. solution.py must define\n'
            '   `fee(minutes: int, plate: str, lost_ticket: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - Lost ticket: if lost_ticket is True, return the flat penalty 61.0\n'
            '     immediately (no other rule applies, not even the EV discount).\n'
            '   - f = blocks(minutes) * 4.35.\n'
            '   - Daily cap: if f is STRICTLY greater than 38.7, set f to 38.7.\n'
            '   - EV discount: if is_ev(plate), multiply f by 0.85 (applied AFTER\n'
            '     the cap).\n'
            '   - Return round(f, 2).\n'
        ),
        "starter_code": (
            'def fee(minutes: int, plate: str, lost_ticket: bool) -> float:\n'
            '    """Compute the parking fee for a stay."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_blocks_free_window():\n'
            '    from time_utils import blocks\n'
            '    assert blocks(45) == 0\n'
            '\n'
            '\n'
            'def test_helper_blocks_one_minute_over():\n'
            '    from time_utils import blocks\n'
            '    assert blocks(46) == 1\n'
            '\n'
            '\n'
            'def test_helper_blocks_two():\n'
            '    from time_utils import blocks\n'
            '    assert blocks(105) == 2\n'
            '\n'
            '\n'
            'def test_helper_blocks_started_third():\n'
            '    from time_utils import blocks\n'
            '    assert blocks(106) == 3\n'
            '\n'
            '\n'
            'def test_helper_is_ev_true():\n'
            '    from plate_utils import is_ev\n'
            "    assert is_ev('EV-1234') == True\n"
            '\n'
            '\n'
            'def test_helper_is_ev_false():\n'
            '    from plate_utils import is_ev\n'
            "    assert is_ev('EX-1234') == False\n"
            '\n'
            '\n'
            'def test_lost_ticket_overrides_ev():\n'
            '    from solution import fee\n'
            "    assert fee(30, 'EV-9999', True) == 61.0\n"
            '\n'
            '\n'
            'def test_small_fee():\n'
            '    from solution import fee\n'
            "    assert fee(76, 'AB-1111', False) == 8.7\n"
            '\n'
            '\n'
            'def test_cap_reached():\n'
            '    from solution import fee\n'
            "    assert fee(600, 'AB-1111', False) == 38.7\n"
            '\n'
            '\n'
            'def test_cap_then_ev_discount():\n'
            '    from solution import fee\n'
            "    assert fee(600, 'EV-1234', False) == 32.9\n"
            '\n'
            '\n'
            'def test_below_cap_many_blocks():\n'
            '    from solution import fee\n'
            "    assert fee(256, 'AB-1111', False) == 34.8\n"
            '\n'
            '\n'
            'def test_zero_minutes():\n'
            '    from solution import fee\n'
            "    assert fee(0, 'AB-1111', False) == 0.0\n"
        ),
    },
    {
        "task_id": 'h_payslip_deductions',
        "prompt": (
            'You are asked to implement a payslip deduction pipeline for a staffing agency.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. pension_utils.py must define `pension(gross: float) -> float`\n'
            '   returning 0.0537 * min(gross, 9250).\n'
            '2. tax_utils.py must define `income_tax(taxable: float) -> float`: the\n'
            '   first 3178 of taxable is taxed at 0.11 and any amount above 3178 is\n'
            '   taxed at 0.23.\n'
            '3. levy_utils.py must define `health_levy(gross: float) -> float`\n'
            '   returning 118.6 when gross is STRICTLY greater than 2140, else 0.0.\n'
            '4. solution.py must define `net(gross: float, insured: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - p = pension(gross); taxable = gross - p.\n'
            '   - t = income_tax(taxable); h = health_levy(gross).\n'
            '   - n = gross - p - t - h.\n'
            '   - If insured is True subtract a flat premium of 34.75.\n'
            '   - Return round(n, 2).\n'
        ),
        "starter_code": (
            'def net(gross: float, insured: bool) -> float:\n'
            '    """Compute the net pay after all deductions."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_pension_small():\n'
            '    from pension_utils import pension\n'
            '    assert pension(1000.0) == 53.699999999999996\n'
            '\n'
            '\n'
            'def test_helper_pension_capped():\n'
            '    from pension_utils import pension\n'
            '    assert pension(20000.0) == 496.72499999999997\n'
            '\n'
            '\n'
            'def test_helper_tax_low_band():\n'
            '    from tax_utils import income_tax\n'
            '    assert income_tax(1000.0) == 110.0\n'
            '\n'
            '\n'
            'def test_helper_tax_exact_edge():\n'
            '    from tax_utils import income_tax\n'
            '    assert income_tax(3178.0) == 349.58\n'
            '\n'
            '\n'
            'def test_helper_tax_high_band():\n'
            '    from tax_utils import income_tax\n'
            '    assert income_tax(5000.0) == 768.64\n'
            '\n'
            '\n'
            'def test_helper_levy_above():\n'
            '    from levy_utils import health_levy\n'
            '    assert health_levy(2140.5) == 118.6\n'
            '\n'
            '\n'
            'def test_helper_levy_exact_threshold():\n'
            '    from levy_utils import health_levy\n'
            '    assert health_levy(2140.0) == 0.0\n'
            '\n'
            '\n'
            'def test_net_low_gross():\n'
            '    from solution import net\n'
            '    assert net(1500.0, False) == 1263.31\n'
            '\n'
            '\n'
            'def test_net_high_gross():\n'
            '    from solution import net\n'
            '    assert net(6000.0, False) == 4634.67\n'
            '\n'
            '\n'
            'def test_net_insured():\n'
            '    from solution import net\n'
            '    assert net(6000.0, True) == 4599.92\n'
            '\n'
            '\n'
            'def test_net_zero_gross():\n'
            '    from solution import net\n'
            '    assert net(0.0, False) == 0.0\n'
            '\n'
            '\n'
            'def test_net_pension_capped_path():\n'
            '    from solution import net\n'
            '    assert net(12000.0, False) == 9120.28\n'
        ),
    },
    {
        "task_id": 'h_bookstore_order',
        "prompt": (
            'You are asked to implement an order pricing module for an online bookstore.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. line_utils.py must define\n'
            '   `line_total(price: float, qty: int) -> float`, where half_up(x)\n'
            '   means math.floor(x * 100 + 0.5) / 100: t = price * qty; if qty is\n'
            '   greater than or equal to 17 multiply t by 0.9264 (a qty one below\n'
            '   that gets no discount); return half_up(t).\n'
            '2. gift_utils.py must define `wrap_fee(code: str, units: int) -> float`\n'
            "   returning 3.15 * units when code starts with 'GF-', else 0.0.\n"
            '3. solution.py must define\n'
            '   `order_total(lines: list, code: str) -> float` where each line is a\n'
            '   tuple (price, qty), computed in this exact order:\n'
            '   - subtotal = sum of line_total(price, qty) over the lines.\n'
            '   - Volume rebate: if subtotal is STRICTLY greater than 923, multiply\n'
            '     subtotal by 0.9588 (at exactly 923 there is no rebate).\n'
            '   - Shipping: add 12.85 unless the subtotal AFTER the rebate step is\n'
            '     greater than or equal to 618.\n'
            '   - Gift wrap: add wrap_fee(code, units) where units is the sum of\n'
            '     all qty values in the order.\n'
            '   - Return half_up(the final amount).\n'
        ),
        "starter_code": (
            'def order_total(lines: list, code: str) -> float:\n'
            '    """Compute the total price of a bookstore order."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_line_no_discount():\n'
            '    from line_utils import line_total\n'
            '    assert line_total(10.0, 5) == 50.0\n'
            '\n'
            '\n'
            'def test_helper_line_bulk_discount():\n'
            '    from line_utils import line_total\n'
            '    assert line_total(10.0, 17) == 157.49\n'
            '\n'
            '\n'
            'def test_helper_line_just_below_bulk():\n'
            '    from line_utils import line_total\n'
            '    assert line_total(10.0, 16) == 160.0\n'
            '\n'
            '\n'
            'def test_helper_wrap_gift():\n'
            '    from gift_utils import wrap_fee\n'
            "    assert wrap_fee('GF-X', 4) == 12.6\n"
            '\n'
            '\n'
            'def test_helper_wrap_other():\n'
            '    from gift_utils import wrap_fee\n'
            "    assert wrap_fee('ZZ-X', 4) == 0.0\n"
            '\n'
            '\n'
            'def test_empty_order_ships():\n'
            '    from solution import order_total\n'
            "    assert order_total([], 'NONE') == 12.85\n"
            '\n'
            '\n'
            'def test_rebate_applied():\n'
            '    from solution import order_total\n'
            "    assert order_total([(500.0, 2)], 'NONE') == 958.8\n"
            '\n'
            '\n'
            'def test_no_rebate_at_exact_edge():\n'
            '    from solution import order_total\n'
            "    assert order_total([(923.0, 1)], 'NONE') == 923.0\n"
            '\n'
            '\n'
            'def test_shipping_waived_at_edge():\n'
            '    from solution import order_total\n'
            "    assert order_total([(618.0, 1)], 'NONE') == 618.0\n"
            '\n'
            '\n'
            'def test_shipping_charged_below_edge():\n'
            '    from solution import order_total\n'
            "    assert order_total([(617.99, 1)], 'NONE') == 630.84\n"
            '\n'
            '\n'
            'def test_gift_wrap_counts_units():\n'
            '    from solution import order_total\n'
            "    assert order_total([(10.0, 3), (5.0, 2)], 'GF-A') == 68.6\n"
            '\n'
            '\n'
            'def test_combined_bulk_rebate_gift():\n'
            '    from solution import order_total\n'
            "    assert order_total([(60.0, 17)], 'GF-B') == 959.55\n"
        ),
    },
    {
        "task_id": 'h_sku_validator',
        "prompt": (
            'You are asked to implement a SKU validation module for a wholesale marketplace.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. checksum_utils.py must define `checksum(digits: str) -> int`\n'
            '   returning the sum of the integer digits, where digits in EVEN\n'
            '   positions (0-based) are tripled before summing, all taken modulo 43.\n'
            '2. prefix_utils.py must define `prefix_ok(sku: str) -> bool` returning\n'
            "   True iff sku starts with 'KP-' or 'VN-'.\n"
            '3. solution.py must define `validate(sku: str) -> str`, applying the\n'
            '   checks in this exact order and returning at the FIRST failure:\n'
            "   - If len(sku) is not exactly 11, return 'ERR_74'.\n"
            "   - If prefix_ok(sku) is False, return 'ERR_29'.\n"
            "   - The last 8 characters must all be digits, else return 'ERR_50'.\n"
            "   - If checksum(those 8 digits) is not exactly 19, return 'ERR_88'.\n"
            "   - Otherwise return 'OK:' followed by the last 8 characters.\n"
        ),
        "starter_code": (
            'def validate(sku: str) -> str:\n'
            '    """Validate a SKU string and return a status code."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_checksum_simple():\n'
            '    from checksum_utils import checksum\n'
            "    assert checksum('11111111') == 16\n"
            '\n'
            '\n'
            'def test_helper_checksum_modulo():\n'
            '    from checksum_utils import checksum\n'
            "    assert checksum('99999999') == 15\n"
            '\n'
            '\n'
            'def test_helper_checksum_positions():\n'
            '    from checksum_utils import checksum\n'
            "    assert checksum('10101010') == 12\n"
            '\n'
            '\n'
            'def test_helper_prefix_kp():\n'
            '    from prefix_utils import prefix_ok\n'
            "    assert prefix_ok('KP-1') == True\n"
            '\n'
            '\n'
            'def test_helper_prefix_vn():\n'
            '    from prefix_utils import prefix_ok\n'
            "    assert prefix_ok('VN-1') == True\n"
            '\n'
            '\n'
            'def test_helper_prefix_bad():\n'
            '    from prefix_utils import prefix_ok\n'
            "    assert prefix_ok('XX-1') == False\n"
            '\n'
            '\n'
            'def test_too_short():\n'
            '    from solution import validate\n'
            "    assert validate('KP-1234') == 'ERR_74'\n"
            '\n'
            '\n'
            'def test_too_long():\n'
            '    from solution import validate\n'
            "    assert validate('KP-123456789') == 'ERR_74'\n"
            '\n'
            '\n'
            'def test_bad_prefix_right_length():\n'
            '    from solution import validate\n'
            "    assert validate('XX-12345678') == 'ERR_29'\n"
            '\n'
            '\n'
            'def test_non_digit_tail():\n'
            '    from solution import validate\n'
            "    assert validate('KP-1234567a') == 'ERR_50'\n"
            '\n'
            '\n'
            'def test_bad_checksum():\n'
            '    from solution import validate\n'
            "    assert validate('KP-11111111') == 'ERR_88'\n"
            '\n'
            '\n'
            'def test_valid_sku():\n'
            '    from solution import validate\n'
            "    assert validate('KP-10201021') == 'OK:10201021'\n"
            '\n'
            '\n'
            'def test_length_checked_before_prefix():\n'
            '    from solution import validate\n'
            "    assert validate('XX-1') == 'ERR_74'\n"
        ),
    },
    {
        "task_id": 'h_water_billing',
        "prompt": (
            'You are asked to implement a water utility billing module for a municipal utility.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. usage_utils.py must define `consumption(prev: int, curr: int) -> int`\n'
            '   returning curr - prev, but if curr is STRICTLY less than prev the\n'
            '   meter rolled over at 10000 and it returns (10000 - prev) + curr.\n'
            '2. tier_utils.py must define `tier_cost(m3: int) -> float` with\n'
            '   cumulative tiers: the first 12 cubic meters cost 1.8354 each, the\n'
            '   portion above 12 and up to 31 costs 3.2417 each, and the portion\n'
            '   above 31 costs 5.9126 each.\n'
            '3. sewer_utils.py must define `sewer(m3: int) -> float` returning\n'
            '   m3 * 0.7238.\n'
            '4. solution.py must define\n'
            '   `bill(prev: int, curr: int, social: bool) -> float` computed in this\n'
            '   exact order:\n'
            '   - m3 = consumption(prev, curr).\n'
            '   - total = tier_cost(m3) + sewer(m3) + a fixed meter fee of 14.2.\n'
            '   - Social tariff: if social is True, multiply total by 0.6471.\n'
            '   - Return round(total, 2).\n'
        ),
        "starter_code": (
            'def bill(prev: int, curr: int, social: bool) -> float:\n'
            '    """Compute the water bill from two meter readings."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_consumption_normal():\n'
            '    from usage_utils import consumption\n'
            '    assert consumption(100, 130) == 30\n'
            '\n'
            '\n'
            'def test_helper_consumption_rollover():\n'
            '    from usage_utils import consumption\n'
            '    assert consumption(9990, 25) == 35\n'
            '\n'
            '\n'
            'def test_helper_tier_first_only():\n'
            '    from tier_utils import tier_cost\n'
            '    assert tier_cost(10) == 18.354\n'
            '\n'
            '\n'
            'def test_helper_tier_exact_first_edge():\n'
            '    from tier_utils import tier_cost\n'
            '    assert tier_cost(12) == 22.0248\n'
            '\n'
            '\n'
            'def test_helper_tier_second():\n'
            '    from tier_utils import tier_cost\n'
            '    assert tier_cost(20) == 47.9584\n'
            '\n'
            '\n'
            'def test_helper_tier_exact_second_edge():\n'
            '    from tier_utils import tier_cost\n'
            '    assert tier_cost(31) == 83.6171\n'
            '\n'
            '\n'
            'def test_helper_tier_third():\n'
            '    from tier_utils import tier_cost\n'
            '    assert tier_cost(40) == 136.8305\n'
            '\n'
            '\n'
            'def test_helper_sewer():\n'
            '    from sewer_utils import sewer\n'
            '    assert sewer(10) == 7.2379999999999995\n'
            '\n'
            '\n'
            'def test_bill_small_usage():\n'
            '    from solution import bill\n'
            '    assert bill(0, 10, False) == 39.79\n'
            '\n'
            '\n'
            'def test_bill_social():\n'
            '    from solution import bill\n'
            '    assert bill(0, 10, True) == 25.75\n'
            '\n'
            '\n'
            'def test_bill_rollover_heavy():\n'
            '    from solution import bill\n'
            '    assert bill(9980, 30, False) == 246.35\n'
            '\n'
            '\n'
            'def test_bill_zero_usage():\n'
            '    from solution import bill\n'
            '    assert bill(500, 500, False) == 14.2\n'
        ),
    },
    {
        "task_id": 'h_triage_queue',
        "prompt": (
            'You are asked to implement a triage scoring and queueing module for an urgent-care clinic.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. score_utils.py must define\n'
            '   `severity(hr: int, temp: float) -> int` computed as: s = 0; add 34\n'
            '   points if hr is STRICTLY greater than 118; add 27 points if temp is\n'
            '   STRICTLY greater than 38.6; add 12 more points if BOTH conditions\n'
            '   hold; return s.\n'
            '2. age_utils.py must define `age_boost(age: int) -> int` returning 21\n'
            '   when age >= 77 or age <= 4, else 0.\n'
            '3. solution.py must define `order(patients: list) -> list` where each\n'
            '   patient is a tuple (name, hr, temp, age):\n'
            "   - Each patient's score is severity(hr, temp) + age_boost(age).\n"
            '   - Return the list of names sorted by score DESCENDING; ties are\n'
            '     broken by name ASCENDING (plain string order).\n'
            '   - Patients whose score is STRICTLY below 21 are dropped from the\n'
            '     result entirely.\n'
        ),
        "starter_code": (
            'def order(patients: list) -> list:\n'
            '    """Return patient names in triage order."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_severity_hr_only():\n'
            '    from score_utils import severity\n'
            '    assert severity(119, 37.0) == 34\n'
            '\n'
            '\n'
            'def test_helper_severity_temp_only():\n'
            '    from score_utils import severity\n'
            '    assert severity(80, 38.7) == 27\n'
            '\n'
            '\n'
            'def test_helper_severity_both():\n'
            '    from score_utils import severity\n'
            '    assert severity(119, 38.7) == 73\n'
            '\n'
            '\n'
            'def test_helper_severity_exact_edges():\n'
            '    from score_utils import severity\n'
            '    assert severity(118, 38.6) == 0\n'
            '\n'
            '\n'
            'def test_helper_boost_elderly():\n'
            '    from age_utils import age_boost\n'
            '    assert age_boost(77) == 21\n'
            '\n'
            '\n'
            'def test_helper_boost_infant():\n'
            '    from age_utils import age_boost\n'
            '    assert age_boost(4) == 21\n'
            '\n'
            '\n'
            'def test_helper_boost_adult():\n'
            '    from age_utils import age_boost\n'
            '    assert age_boost(40) == 0\n'
            '\n'
            '\n'
            'def test_order_by_score():\n'
            '    from solution import order\n'
            "    assert order([('ana', 119, 37.0, 30), ('bob', 119, 38.7, 30)]) == ['bob', 'ana']\n"
            '\n'
            '\n'
            'def test_tie_broken_by_name():\n'
            '    from solution import order\n'
            "    assert order([('zed', 119, 37.0, 30), ('amy', 119, 37.0, 30)]) == ['amy', 'zed']\n"
            '\n'
            '\n'
            'def test_low_scores_dropped():\n'
            '    from solution import order\n'
            "    assert order([('lia', 80, 37.0, 30), ('max', 119, 37.0, 30)]) == ['max']\n"
            '\n'
            '\n'
            'def test_boost_rescues_patient():\n'
            '    from solution import order\n'
            "    assert order([('eva', 80, 37.0, 80)]) == ['eva']\n"
            '\n'
            '\n'
            'def test_exact_cutoff_kept():\n'
            '    from solution import order\n'
            "    assert order([('kid', 80, 37.0, 4)]) == ['kid']\n"
            '\n'
            '\n'
            'def test_empty_list():\n'
            '    from solution import order\n'
            '    assert order([]) == []\n'
        ),
    },
    {
        "task_id": 'h_gym_membership',
        "prompt": (
            'You are asked to implement a gym membership billing module for a fitness franchise.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. plan_utils.py must define `plan_fee(plan: str) -> float` returning\n'
            "   67.90 for 'FLEX', 54.35 for 'CORE' and 41.20 for 'OFFPEAK'.\n"
            '2. visit_utils.py must define `overage(visits: int, plan: str) -> float`:\n'
            "   only plan 'OFFPEAK' has a visit allowance, of 11 visits per month;\n"
            '   each visit beyond it costs 6.45; other plans always return 0.0.\n'
            '3. solution.py must define\n'
            '   `invoice(plan: str, visits: int, months_active: int) -> float`\n'
            '   computed in this exact order:\n'
            '   - total = plan_fee(plan) + overage(visits, plan).\n'
            '   - Loyalty: if months_active is STRICTLY greater than 23, multiply\n'
            '     total by 0.9137 (at exactly 23 there is no discount).\n'
            '   - Inactivity penalty: if visits is exactly 0, add 15.9 AFTER the\n'
            '     loyalty step (the penalty is never discounted).\n'
            '   - Return round(total, 2).\n'
        ),
        "starter_code": (
            'def invoice(plan: str, visits: int, months_active: int) -> float:\n'
            '    """Compute the monthly gym invoice."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_fee_flex():\n'
            '    from plan_utils import plan_fee\n'
            "    assert plan_fee('FLEX') == 67.9\n"
            '\n'
            '\n'
            'def test_helper_fee_core():\n'
            '    from plan_utils import plan_fee\n'
            "    assert plan_fee('CORE') == 54.35\n"
            '\n'
            '\n'
            'def test_helper_fee_offpeak():\n'
            '    from plan_utils import plan_fee\n'
            "    assert plan_fee('OFFPEAK') == 41.2\n"
            '\n'
            '\n'
            'def test_helper_overage_within_allowance():\n'
            '    from visit_utils import overage\n'
            "    assert overage(11, 'OFFPEAK') == 0.0\n"
            '\n'
            '\n'
            'def test_helper_overage_beyond():\n'
            '    from visit_utils import overage\n'
            "    assert overage(14, 'OFFPEAK') == 19.35\n"
            '\n'
            '\n'
            'def test_helper_overage_flex_free():\n'
            '    from visit_utils import overage\n'
            "    assert overage(50, 'FLEX') == 0.0\n"
            '\n'
            '\n'
            'def test_invoice_core_plain():\n'
            '    from solution import invoice\n'
            "    assert invoice('CORE', 8, 5) == 54.35\n"
            '\n'
            '\n'
            'def test_invoice_loyalty():\n'
            '    from solution import invoice\n'
            "    assert invoice('CORE', 8, 24) == 49.66\n"
            '\n'
            '\n'
            'def test_invoice_no_loyalty_at_edge():\n'
            '    from solution import invoice\n'
            "    assert invoice('CORE', 8, 23) == 54.35\n"
            '\n'
            '\n'
            'def test_invoice_offpeak_overage():\n'
            '    from solution import invoice\n'
            "    assert invoice('OFFPEAK', 14, 5) == 60.55\n"
            '\n'
            '\n'
            'def test_invoice_inactive_penalty():\n'
            '    from solution import invoice\n'
            "    assert invoice('FLEX', 0, 5) == 83.8\n"
            '\n'
            '\n'
            'def test_invoice_penalty_after_loyalty():\n'
            '    from solution import invoice\n'
            "    assert invoice('FLEX', 0, 24) == 77.94\n"
        ),
    },
    {
        "task_id": 'h_grade_curve',
        "prompt": (
            'You are asked to implement an exam grading and curving module for a certification board.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. raw_utils.py must define\n'
            '   `raw_score(correct: int, wrong: int) -> float` returning\n'
            '   correct * 4.25 - wrong * 1.75 (blank answers count nothing), with\n'
            '   a floor at 0.0 (never negative).\n'
            '2. curve_utils.py must define `curved(score: float) -> float`\n'
            '   returning min(score * 1.0842, 100.0).\n'
            '3. solution.py must define\n'
            '   `grade(correct: int, wrong: int, retake: bool) -> str` computed in\n'
            '   this exact order:\n'
            '   - s = curved(raw_score(correct, wrong)).\n'
            '   - Retake cap: if retake is True and s is STRICTLY greater than\n'
            '     84.5, set s to 84.5.\n'
            "   - Band: 'DIST' if s >= 91.3, else 'PASS' if s >= 68.7, else\n"
            "     'FAIL'.\n"
            "   - Return the band, then ':', then s formatted with exactly two\n"
            "     decimals (e.g. 'PASS:84.50').\n"
        ),
        "starter_code": (
            'def grade(correct: int, wrong: int, retake: bool) -> str:\n'
            '    """Compute the curved exam grade label."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_raw_basic():\n'
            '    from raw_utils import raw_score\n'
            '    assert raw_score(10, 4) == 35.5\n'
            '\n'
            '\n'
            'def test_helper_raw_floor():\n'
            '    from raw_utils import raw_score\n'
            '    assert raw_score(1, 10) == 0.0\n'
            '\n'
            '\n'
            'def test_helper_curve_normal():\n'
            '    from curve_utils import curved\n'
            '    assert curved(50.0) == 54.21\n'
            '\n'
            '\n'
            'def test_helper_curve_capped():\n'
            '    from curve_utils import curved\n'
            '    assert curved(99.0) == 100.0\n'
            '\n'
            '\n'
            'def test_grade_fail():\n'
            '    from solution import grade\n'
            "    assert grade(10, 0, False) == 'FAIL:46.08'\n"
            '\n'
            '\n'
            'def test_grade_pass():\n'
            '    from solution import grade\n'
            "    assert grade(16, 0, False) == 'PASS:73.73'\n"
            '\n'
            '\n'
            'def test_grade_dist():\n'
            '    from solution import grade\n'
            "    assert grade(21, 0, False) == 'DIST:96.76'\n"
            '\n'
            '\n'
            'def test_retake_capped():\n'
            '    from solution import grade\n'
            "    assert grade(21, 0, True) == 'PASS:84.50'\n"
            '\n'
            '\n'
            'def test_retake_below_cap_untouched():\n'
            '    from solution import grade\n'
            "    assert grade(16, 0, True) == 'PASS:73.73'\n"
            '\n'
            '\n'
            'def test_zero_answers():\n'
            '    from solution import grade\n'
            "    assert grade(0, 0, False) == 'FAIL:0.00'\n"
            '\n'
            '\n'
            'def test_wrong_answers_penalize():\n'
            '    from solution import grade\n'
            "    assert grade(20, 10, False) == 'PASS:73.18'\n"
            '\n'
            '\n'
            'def test_curve_cap_then_dist():\n'
            '    from solution import grade\n'
            "    assert grade(24, 0, False) == 'DIST:100.00'\n"
        ),
    },
    {
        "task_id": 'h_cargo_manifest',
        "prompt": (
            'You are asked to implement a cargo manifest checker for a container terminal.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. weight_utils.py must define `chargeable(kg: float) -> float`\n'
            '   returning kg * 1.0637 when kg is STRICTLY greater than 740, else kg.\n'
            '2. code_utils.py must define `hazard_class(code: str) -> int` returning\n'
            "   3 when code starts with 'HZ-', 2 when it starts with 'CH-', else 1.\n"
            '3. slot_utils.py must define `slots(kg: float) -> int` returning the\n'
            '   number of 325-kg slots needed, any remainder counting as one more\n'
            '   full slot (0 kg needs 0 slots).\n'
            '4. solution.py must define `manifest_fee(containers: list) -> float`\n'
            '   where each container is a tuple (code, kg), in this exact order:\n'
            '   - fee for one container = chargeable(kg) * 0.5218 multiplied by\n'
            '     hazard_class(code), then rounded with round(x, 2) per container.\n'
            '   - total = sum of the container fees.\n'
            '   - Add a berth fee of 9.75 for each slot, counting slots(kg) on the\n'
            '     RAW kg of every container (not the chargeable weight).\n'
            '   - Return round(total, 2).\n'
        ),
        "starter_code": (
            'def manifest_fee(containers: list) -> float:\n'
            '    """Compute the total manifest fee for a list of containers."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_chargeable_light():\n'
            '    from weight_utils import chargeable\n'
            '    assert chargeable(740.0) == 740.0\n'
            '\n'
            '\n'
            'def test_helper_chargeable_heavy():\n'
            '    from weight_utils import chargeable\n'
            '    assert chargeable(800.0) == 850.96\n'
            '\n'
            '\n'
            'def test_helper_hazard_hz():\n'
            '    from code_utils import hazard_class\n'
            "    assert hazard_class('HZ-1') == 3\n"
            '\n'
            '\n'
            'def test_helper_hazard_ch():\n'
            '    from code_utils import hazard_class\n'
            "    assert hazard_class('CH-1') == 2\n"
            '\n'
            '\n'
            'def test_helper_hazard_plain():\n'
            '    from code_utils import hazard_class\n'
            "    assert hazard_class('XX-1') == 1\n"
            '\n'
            '\n'
            'def test_helper_slots_exact():\n'
            '    from slot_utils import slots\n'
            '    assert slots(650) == 2\n'
            '\n'
            '\n'
            'def test_helper_slots_remainder():\n'
            '    from slot_utils import slots\n'
            '    assert slots(651) == 3\n'
            '\n'
            '\n'
            'def test_helper_slots_zero():\n'
            '    from slot_utils import slots\n'
            '    assert slots(0) == 0\n'
            '\n'
            '\n'
            'def test_single_plain_container():\n'
            '    from solution import manifest_fee\n'
            "    assert manifest_fee([('XX-1', 100.0)]) == 61.93\n"
            '\n'
            '\n'
            'def test_single_hazard_container():\n'
            '    from solution import manifest_fee\n'
            "    assert manifest_fee([('HZ-1', 100.0)]) == 166.29\n"
            '\n'
            '\n'
            'def test_heavy_chemical():\n'
            '    from solution import manifest_fee\n'
            "    assert manifest_fee([('CH-1', 800.0)]) == 917.31\n"
            '\n'
            '\n'
            'def test_empty_manifest():\n'
            '    from solution import manifest_fee\n'
            '    assert manifest_fee([]) == 0.0\n'
            '\n'
            '\n'
            'def test_mixed_manifest():\n'
            '    from solution import manifest_fee\n'
            "    assert manifest_fee([('XX-1', 100.0), ('HZ-2', 800.0)]) == 1423.27\n"
        ),
    },
    {
        "task_id": 'h_turnstile_fsm',
        "prompt": (
            'You are asked to implement a turnstile controller state machine for a metro operator.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. card_utils.py must define `card_ok(card: str) -> bool` returning\n'
            "   True iff card starts with 'MT-' and len(card) is exactly 9.\n"
            '2. fare_utils.py must define `fare(zone: int) -> float` returning\n'
            '   2.85 for zone 1, 4.6 for zone 2 and 7.15 for any other zone.\n'
            '3. solution.py must define `run(events: list) -> str`. The machine\n'
            '   starts LOCKED with a collected total of 0.0. Each event is a tuple:\n'
            "   ('tap', card, zone) or ('push',). Processing rules in order:\n"
            "   - 'tap' while LOCKED: if card_ok(card) is False, count one error;\n"
            '     otherwise add fare(zone) to the total and become UNLOCKED.\n'
            "   - 'tap' while UNLOCKED: count one error (state unchanged, no fare).\n"
            "   - 'push' while UNLOCKED: become LOCKED (a successful passage).\n"
            "   - 'push' while LOCKED: count one error.\n"
            '   - After 3 errors in total the machine JAMS: ignore every later\n'
            '     event entirely.\n'
            "   - Return f'{state}|{passages}|{total:.2f}' where state is 'JAMMED',\n"
            "     'LOCKED' or 'UNLOCKED'.\n"
        ),
        "starter_code": (
            'def run(events: list) -> str:\n'
            '    """Run the turnstile state machine over a list of events."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_card_ok():\n'
            '    from card_utils import card_ok\n'
            "    assert card_ok('MT-123456') == True\n"
            '\n'
            '\n'
            'def test_helper_card_bad_prefix():\n'
            '    from card_utils import card_ok\n'
            "    assert card_ok('XX-123456') == False\n"
            '\n'
            '\n'
            'def test_helper_card_bad_length():\n'
            '    from card_utils import card_ok\n'
            "    assert card_ok('MT-12345') == False\n"
            '\n'
            '\n'
            'def test_helper_fare_zone1():\n'
            '    from fare_utils import fare\n'
            '    assert fare(1) == 2.85\n'
            '\n'
            '\n'
            'def test_helper_fare_zone2():\n'
            '    from fare_utils import fare\n'
            '    assert fare(2) == 4.6\n'
            '\n'
            '\n'
            'def test_helper_fare_other():\n'
            '    from fare_utils import fare\n'
            '    assert fare(5) == 7.15\n'
            '\n'
            '\n'
            'def test_empty_run():\n'
            '    from solution import run\n'
            "    assert run([]) == 'LOCKED|0|0.00'\n"
            '\n'
            '\n'
            'def test_single_passage():\n'
            '    from solution import run\n'
            "    assert run([('tap', 'MT-123456', 1), ('push',)]) == 'LOCKED|1|2.85'\n"
            '\n'
            '\n'
            'def test_tap_while_unlocked_is_error():\n'
            '    from solution import run\n'
            "    assert run([('tap', 'MT-123456', 1), ('tap', 'MT-123456', 1)]) == 'UNLOCKED|0|2.85'\n"
            '\n'
            '\n'
            'def test_push_locked_error():\n'
            '    from solution import run\n'
            "    assert run([('push',)]) == 'LOCKED|0|0.00'\n"
            '\n'
            '\n'
            'def test_bad_card_no_fare():\n'
            '    from solution import run\n'
            "    assert run([('tap', 'XX-123456', 1)]) == 'LOCKED|0|0.00'\n"
            '\n'
            '\n'
            'def test_jam_after_three_errors():\n'
            '    from solution import run\n'
            "    assert run([('push',), ('push',), ('push',), ('tap', 'MT-123456', 1)]) == 'JAMMED|0|0.00'\n"
            '\n'
            '\n'
            'def test_two_zones_two_passages():\n'
            '    from solution import run\n'
            "    assert run([('tap', 'MT-123456', 1), ('push',), ('tap', 'MT-654321', 2), ('push',)]) == 'LOCKED|2|7.45'\n"
        ),
    },
    {
        "task_id": 'h_expense_audit',
        "prompt": (
            'You are asked to implement an expense report auditing module for a corporate finance team.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. cap_utils.py must define `cap_for(kind: str) -> float` returning\n'
            "   84.0 for 'MEAL', 173.5 for 'HOTEL' and 46.25 for 'TAXI' (these are\n"
            '   the only kinds that exist).\n'
            '2. flag_utils.py must define `is_weekend_date(day: int) -> bool`\n'
            '   returning True iff day % 7 is 0 or 6 (days are numbered from 0).\n'
            '3. solution.py must define `audit(expenses: list) -> tuple` where each\n'
            '   expense is a tuple (kind, amount, day). For each expense in order:\n'
            '   - The reimbursable part is min(amount, cap_for(kind)).\n'
            '   - Weekend penalty: if is_weekend_date(day), the reimbursable part\n'
            '     is further multiplied by 0.55 (applied after the cap).\n'
            '   - An expense is FLAGGED when amount is STRICTLY greater than\n'
            "     1.4 times its cap, or when it is a weekend 'TAXI'.\n"
            '   - Return (round(total_reimbursed, 2), flagged_count).\n'
        ),
        "starter_code": (
            'def audit(expenses: list) -> tuple:\n'
            '    """Audit an expense report; return (total_reimbursed, flagged_count)."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_cap_meal():\n'
            '    from cap_utils import cap_for\n'
            "    assert cap_for('MEAL') == 84.0\n"
            '\n'
            '\n'
            'def test_helper_cap_hotel():\n'
            '    from cap_utils import cap_for\n'
            "    assert cap_for('HOTEL') == 173.5\n"
            '\n'
            '\n'
            'def test_helper_cap_taxi():\n'
            '    from cap_utils import cap_for\n'
            "    assert cap_for('TAXI') == 46.25\n"
            '\n'
            '\n'
            'def test_helper_weekend_day6():\n'
            '    from flag_utils import is_weekend_date\n'
            '    assert is_weekend_date(6) == True\n'
            '\n'
            '\n'
            'def test_helper_weekend_day7():\n'
            '    from flag_utils import is_weekend_date\n'
            '    assert is_weekend_date(7) == True\n'
            '\n'
            '\n'
            'def test_helper_weekday():\n'
            '    from flag_utils import is_weekend_date\n'
            '    assert is_weekend_date(3) == False\n'
            '\n'
            '\n'
            'def test_meal_under_cap():\n'
            '    from solution import audit\n'
            "    assert audit([('MEAL', 50.0, 1)]) == (50.0, 0)\n"
            '\n'
            '\n'
            'def test_meal_capped():\n'
            '    from solution import audit\n'
            "    assert audit([('MEAL', 100.0, 1)]) == (84.0, 0)\n"
            '\n'
            '\n'
            'def test_flag_over_140pct():\n'
            '    from solution import audit\n'
            "    assert audit([('MEAL', 120.0, 1)]) == (84.0, 1)\n"
            '\n'
            '\n'
            'def test_exact_140pct_not_flagged():\n'
            '    from solution import audit\n'
            "    assert audit([('MEAL', 117.6, 1)]) == (84.0, 0)\n"
            '\n'
            '\n'
            'def test_weekend_penalty():\n'
            '    from solution import audit\n'
            "    assert audit([('HOTEL', 100.0, 6)]) == (55.0, 0)\n"
            '\n'
            '\n'
            'def test_weekend_taxi_flagged():\n'
            '    from solution import audit\n'
            "    assert audit([('TAXI', 20.0, 6)]) == (11.0, 1)\n"
            '\n'
            '\n'
            'def test_empty_report():\n'
            '    from solution import audit\n'
            '    assert audit([]) == (0.0, 0)\n'
            '\n'
            '\n'
            'def test_mixed_report():\n'
            '    from solution import audit\n'
            "    assert audit([('MEAL', 100.0, 1), ('TAXI', 30.0, 7), ('HOTEL', 300.0, 2)]) == (274.0, 2)\n"
        ),
    },
    {
        "task_id": 'h_seed_lot_grader',
        "prompt": (
            'You are asked to implement a seed lot quality grading module for an agricultural cooperative.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. purity_utils.py must define\n'
            '   `purity(clean_g: float, total_g: float) -> float` returning\n'
            '   clean_g / total_g * 100.0 (total_g of 0 returns 0.0).\n'
            '2. germ_utils.py must define\n'
            '   `germination(sprouted: int, tested: int) -> float` returning\n'
            '   sprouted / tested * 100.0 (tested of 0 returns 0.0).\n'
            '3. solution.py must define\n'
            '   `grade_lot(clean_g: float, total_g: float, sprouted: int,\n'
            '   tested: int) -> str` computed in this exact order:\n'
            '   - p = purity(...); g = germination(...).\n'
            '   - index = p * 0.42 + g * 0.58, rounded with round(index, 1) BEFORE\n'
            '     comparing to any threshold below.\n'
            "   - Grade 'PRIME' needs index >= 92.4 AND p >= 96.0.\n"
            "   - Otherwise grade 'FAIR' needs index >= 71.8.\n"
            "   - Otherwise the grade is 'CULL'.\n"
            "   - Return f'{grade}/{index}' with index shown via str(index).\n"
        ),
        "starter_code": (
            'def grade_lot(clean_g: float, total_g: float, sprouted: int, tested: int) -> str:\n'
            '    """Grade a seed lot from purity and germination measurements."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_purity():\n'
            '    from purity_utils import purity\n'
            '    assert purity(96.0, 100.0) == 96.0\n'
            '\n'
            '\n'
            'def test_helper_purity_zero_total():\n'
            '    from purity_utils import purity\n'
            '    assert purity(5.0, 0.0) == 0.0\n'
            '\n'
            '\n'
            'def test_helper_germination():\n'
            '    from germ_utils import germination\n'
            '    assert germination(90, 100) == 90.0\n'
            '\n'
            '\n'
            'def test_helper_germination_zero_tested():\n'
            '    from germ_utils import germination\n'
            '    assert germination(5, 0) == 0.0\n'
            '\n'
            '\n'
            'def test_prime_lot():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(98.0, 100.0, 95, 100) == 'PRIME/96.3'\n"
            '\n'
            '\n'
            'def test_high_index_low_purity_not_prime():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(90.0, 100.0, 100, 100) == 'FAIR/95.8'\n"
            '\n'
            '\n'
            'def test_fair_lot():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(80.0, 100.0, 70, 100) == 'FAIR/74.2'\n"
            '\n'
            '\n'
            'def test_cull_lot():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(50.0, 100.0, 40, 100) == 'CULL/44.2'\n"
            '\n'
            '\n'
            'def test_exact_fair_edge():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(71.8, 100.0, 718, 1000) == 'FAIR/71.8'\n"
            '\n'
            '\n'
            'def test_zero_everything():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(0.0, 0.0, 0, 0) == 'CULL/0.0'\n"
            '\n'
            '\n'
            'def test_prime_exact_purity_edge():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(96.0, 100.0, 95, 100) == 'PRIME/95.4'\n"
            '\n'
            '\n'
            'def test_rounding_decides_band():\n'
            '    from solution import grade_lot\n'
            "    assert grade_lot(96.0, 100.0, 89, 100) == 'FAIR/91.9'\n"
        ),
    },
    {
        "task_id": 'h_car_lease_quote',
        "prompt": (
            'You are asked to implement a car lease quoting module for a vehicle leasing company.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. depr_utils.py must define\n'
            '   `residual(msrp: float, months: int) -> float` returning\n'
            '   msrp * (0.6412 if months >= 36 else 0.7871).\n'
            '2. money_utils.py must define `money_factor(tier: int) -> float`\n'
            '   returning 0.00291 for tier 1, 0.00418 for tier 2, and 0.00655 for\n'
            '   any other tier.\n'
            '3. fee_utils.py must define `acquisition_fee() -> float` returning\n'
            '   642.0.\n'
            '4. solution.py must define\n'
            '   `monthly(msrp: float, months: int, tier: int) -> float` computed\n'
            '   in this exact order:\n'
            '   - r = residual(msrp, months).\n'
            '   - depreciation part = (msrp - r) / months.\n'
            '   - finance part = (msrp + r) * money_factor(tier).\n'
            '   - base = depreciation part + finance part, rounded round(base, 2)\n'
            '     BEFORE the next step.\n'
            '   - Spread the acquisition_fee() evenly: add\n'
            '     round(acquisition_fee() / months, 2).\n'
            '   - Return round(the sum, 2).\n'
        ),
        "starter_code": (
            'def monthly(msrp: float, months: int, tier: int) -> float:\n'
            '    """Compute the monthly lease payment."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_residual_long():\n'
            '    from depr_utils import residual\n'
            '    assert residual(10000.0, 36) == 6412.0\n'
            '\n'
            '\n'
            'def test_helper_residual_short():\n'
            '    from depr_utils import residual\n'
            '    assert residual(10000.0, 24) == 7871.0\n'
            '\n'
            '\n'
            'def test_helper_mf_tier1():\n'
            '    from money_utils import money_factor\n'
            '    assert money_factor(1) == 0.00291\n'
            '\n'
            '\n'
            'def test_helper_mf_tier2():\n'
            '    from money_utils import money_factor\n'
            '    assert money_factor(2) == 0.00418\n'
            '\n'
            '\n'
            'def test_helper_mf_tier3():\n'
            '    from money_utils import money_factor\n'
            '    assert money_factor(3) == 0.00655\n'
            '\n'
            '\n'
            'def test_helper_acquisition():\n'
            '    from fee_utils import acquisition_fee\n'
            '    assert acquisition_fee() == 642.0\n'
            '\n'
            '\n'
            'def test_monthly_36_tier1():\n'
            '    from solution import monthly\n'
            '    assert monthly(30000.0, 36, 1) == 460.11\n'
            '\n'
            '\n'
            'def test_monthly_24_tier1():\n'
            '    from solution import monthly\n'
            '    assert monthly(30000.0, 24, 1) == 448.89\n'
            '\n'
            '\n'
            'def test_monthly_36_tier2():\n'
            '    from solution import monthly\n'
            '    assert monthly(30000.0, 36, 2) == 522.64\n'
            '\n'
            '\n'
            'def test_monthly_36_tier5():\n'
            '    from solution import monthly\n'
            '    assert monthly(30000.0, 36, 5) == 639.33\n'
            '\n'
            '\n'
            'def test_monthly_exact_36_edge():\n'
            '    from solution import monthly\n'
            '    assert monthly(20000.0, 36, 1) == 312.68\n'
            '\n'
            '\n'
            'def test_monthly_short_lease_tier3():\n'
            '    from solution import monthly\n'
            '    assert monthly(20000.0, 12, 3) == 642.44\n'
        ),
    },
    {
        "task_id": 'h_return_merchandise',
        "prompt": (
            'You are asked to implement a merchandise return processing module for an electronics retailer.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. window_utils.py must define\n'
            '   `refund_rate(days_since: int) -> float`: 1.0 up to 14 days\n'
            '   (inclusive), 0.8259 up to 42 days (inclusive), 0.5117 up to 77\n'
            '   days (inclusive), 0.0 afterwards.\n'
            '2. restock_utils.py must define `restock_fee(opened: bool) -> float`\n'
            '   returning 24.65 when opened is True, else 0.0.\n'
            '3. solution.py must define\n'
            '   `refund(price: float, days_since: int, opened: bool,\n'
            '   defective: bool) -> float` computed in this exact order:\n'
            '   - Defective items ALWAYS refund the full price, regardless of the\n'
            '     window or opening: return round(price, 2) at once.\n'
            '   - r = price * refund_rate(days_since).\n'
            '   - If r is 0.0 the window has closed: return 0.0 (no fee applies).\n'
            '   - Subtract restock_fee(opened); if the result is negative,\n'
            '     clamp to 0.0.\n'
            '   - Return round(the result, 2).\n'
        ),
        "starter_code": (
            'def refund(price: float, days_since: int, opened: bool, defective: bool) -> float:\n'
            '    """Compute the refund amount for a returned item."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_full_window():\n'
            '    from window_utils import refund_rate\n'
            '    assert refund_rate(14) == 1.0\n'
            '\n'
            '\n'
            'def test_helper_rate_partial_window():\n'
            '    from window_utils import refund_rate\n'
            '    assert refund_rate(15) == 0.8259\n'
            '\n'
            '\n'
            'def test_helper_rate_last_partial_day():\n'
            '    from window_utils import refund_rate\n'
            '    assert refund_rate(42) == 0.8259\n'
            '\n'
            '\n'
            'def test_helper_rate_last_late_day():\n'
            '    from window_utils import refund_rate\n'
            '    assert refund_rate(77) == 0.5117\n'
            '\n'
            '\n'
            'def test_helper_rate_closed():\n'
            '    from window_utils import refund_rate\n'
            '    assert refund_rate(78) == 0.0\n'
            '\n'
            '\n'
            'def test_helper_restock_opened():\n'
            '    from restock_utils import restock_fee\n'
            '    assert restock_fee(True) == 24.65\n'
            '\n'
            '\n'
            'def test_full_refund_sealed():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 10, False, False) == 100.0\n'
            '\n'
            '\n'
            'def test_opened_pays_fee():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 10, True, False) == 75.35\n'
            '\n'
            '\n'
            'def test_partial_window():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 20, False, False) == 82.59\n'
            '\n'
            '\n'
            'def test_defective_ignores_window():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 90, True, True) == 100.0\n'
            '\n'
            '\n'
            'def test_late_window_refund():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 60, False, False) == 51.17\n'
            '\n'
            '\n'
            'def test_closed_window_zero():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 90, True, False) == 0.0\n'
            '\n'
            '\n'
            'def test_fee_clamped_to_zero():\n'
            '    from solution import refund\n'
            '    assert refund(20.0, 10, True, False) == 0.0\n'
            '\n'
            '\n'
            'def test_partial_and_fee():\n'
            '    from solution import refund\n'
            '    assert refund(100.0, 42, True, False) == 57.94\n'
        ),
    },
    {
        "task_id": 'h_print_shop',
        "prompt": (
            'You are asked to implement a print job pricing module for a commercial print shop.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. paper_utils.py must define `sheet_cost(stock: str) -> float`\n'
            "   returning 0.0842 for 'BOND', 0.1937 for 'GLOSS' and 0.3164 for\n"
            "   'CARD'.\n"
            '2. setup_utils.py must define `setup_fee(color: bool) -> float`\n'
            '   returning 31.4 when color is True, else 17.8.\n'
            '3. solution.py must define\n'
            '   `job_price(pages: int, copies: int, stock: str, color: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - sheets = pages * copies.\n'
            '   - run = sheets * sheet_cost(stock); color jobs multiply run by 2.6\n'
            '     (mono jobs leave it unchanged).\n'
            '   - Volume break: if sheets is STRICTLY greater than 1850, multiply\n'
            '     run by 0.8118 (at exactly 1850 there is no break).\n'
            '   - price = run + setup_fee(color).\n'
            '   - Rush minimum: if price is STRICTLY less than 52.3, return 52.3\n'
            '     exactly; otherwise return round(price, 2).\n'
        ),
        "starter_code": (
            'def job_price(pages: int, copies: int, stock: str, color: bool) -> float:\n'
            '    """Compute the price of a print job."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_sheet_bond():\n'
            '    from paper_utils import sheet_cost\n'
            "    assert sheet_cost('BOND') == 0.0842\n"
            '\n'
            '\n'
            'def test_helper_sheet_gloss():\n'
            '    from paper_utils import sheet_cost\n'
            "    assert sheet_cost('GLOSS') == 0.1937\n"
            '\n'
            '\n'
            'def test_helper_sheet_card():\n'
            '    from paper_utils import sheet_cost\n'
            "    assert sheet_cost('CARD') == 0.3164\n"
            '\n'
            '\n'
            'def test_helper_setup_color():\n'
            '    from setup_utils import setup_fee\n'
            '    assert setup_fee(True) == 31.4\n'
            '\n'
            '\n'
            'def test_helper_setup_mono():\n'
            '    from setup_utils import setup_fee\n'
            '    assert setup_fee(False) == 17.8\n'
            '\n'
            '\n'
            'def test_minimum_small_job():\n'
            '    from solution import job_price\n'
            "    assert job_price(1, 1, 'BOND', False) == 52.3\n"
            '\n'
            '\n'
            'def test_mono_mid_job():\n'
            '    from solution import job_price\n'
            "    assert job_price(100, 5, 'BOND', False) == 59.9\n"
            '\n'
            '\n'
            'def test_color_multiplier():\n'
            '    from solution import job_price\n'
            "    assert job_price(100, 5, 'BOND', True) == 140.86\n"
            '\n'
            '\n'
            'def test_volume_break():\n'
            '    from solution import job_price\n'
            "    assert job_price(100, 20, 'BOND', False) == 154.51\n"
            '\n'
            '\n'
            'def test_exact_volume_edge_no_break():\n'
            '    from solution import job_price\n'
            "    assert job_price(74, 25, 'BOND', False) == 173.57\n"
            '\n'
            '\n'
            'def test_gloss_color_job():\n'
            '    from solution import job_price\n'
            "    assert job_price(50, 10, 'GLOSS', True) == 283.21\n"
            '\n'
            '\n'
            'def test_card_stock_job():\n'
            '    from solution import job_price\n'
            "    assert job_price(200, 4, 'CARD', False) == 270.92\n"
        ),
    },
    {
        "task_id": 'h_donation_matcher',
        "prompt": (
            'You are asked to implement a donation matching module for a charitable foundation.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. match_utils.py must define `match_rate(employer: str) -> float`\n'
            "   returning 1.75 when employer starts with 'PL-', 0.65 when it starts\n"
            "   with 'ST-', else 0.0.\n"
            '2. cap_utils.py must define `annual_cap(employer: str) -> float`\n'
            "   returning 5230.0 for 'PL-' employers and 1980.0 for 'ST-' employers\n"
            '   (0.0 for anyone else).\n'
            '3. solution.py must define\n'
            '   `matched(donations: list, employer: str) -> float` where donations\n'
            '   is a list of floats, computed in this exact order:\n'
            '   - Each donation is matched at match_rate(employer), but any single\n'
            '     donation STRICTLY greater than 940 only has its first 940\n'
            '     matched.\n'
            '   - Sum the matches, then clamp the sum at annual_cap(employer).\n'
            '   - Add a fixed processing credit of 12.4 whenever the clamped sum is\n'
            '     STRICTLY greater than 0.\n'
            '   - Return round(the result, 2).\n'
        ),
        "starter_code": (
            'def matched(donations: list, employer: str) -> float:\n'
            '    """Compute the total employer-matched amount."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_pl():\n'
            '    from match_utils import match_rate\n'
            "    assert match_rate('PL-ACME') == 1.75\n"
            '\n'
            '\n'
            'def test_helper_rate_st():\n'
            '    from match_utils import match_rate\n'
            "    assert match_rate('ST-GOV') == 0.65\n"
            '\n'
            '\n'
            'def test_helper_rate_none():\n'
            '    from match_utils import match_rate\n'
            "    assert match_rate('XX-Q') == 0.0\n"
            '\n'
            '\n'
            'def test_helper_cap_pl():\n'
            '    from cap_utils import annual_cap\n'
            "    assert annual_cap('PL-ACME') == 5230.0\n"
            '\n'
            '\n'
            'def test_helper_cap_st():\n'
            '    from cap_utils import annual_cap\n'
            "    assert annual_cap('ST-GOV') == 1980.0\n"
            '\n'
            '\n'
            'def test_helper_cap_none():\n'
            '    from cap_utils import annual_cap\n'
            "    assert annual_cap('XX-Q') == 0.0\n"
            '\n'
            '\n'
            'def test_simple_match():\n'
            '    from solution import matched\n'
            "    assert matched([100.0], 'PL-ACME') == 187.4\n"
            '\n'
            '\n'
            'def test_large_donation_clipped():\n'
            '    from solution import matched\n'
            "    assert matched([1000.0], 'PL-ACME') == 1657.4\n"
            '\n'
            '\n'
            'def test_exact_clip_edge():\n'
            '    from solution import matched\n'
            "    assert matched([940.0], 'PL-ACME') == 1657.4\n"
            '\n'
            '\n'
            'def test_cap_reached():\n'
            '    from solution import matched\n'
            "    assert matched([940.0, 940.0, 940.0, 940.0], 'PL-ACME') == 5242.4\n"
            '\n'
            '\n'
            'def test_st_employer():\n'
            '    from solution import matched\n'
            "    assert matched([200.0], 'ST-GOV') == 142.4\n"
            '\n'
            '\n'
            'def test_no_match_no_credit():\n'
            '    from solution import matched\n'
            "    assert matched([500.0], 'XX-Q') == 0.0\n"
            '\n'
            '\n'
            'def test_empty_list():\n'
            '    from solution import matched\n'
            "    assert matched([], 'PL-ACME') == 0\n"
        ),
    },
    {
        "task_id": 'h_wind_turbine_pay',
        "prompt": (
            'You are asked to implement a wind farm settlement module for a renewable energy trader.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. output_utils.py must define `mwh(readings: list) -> float`\n'
            '   returning the sum of the readings divided by 1000.0 (readings are\n'
            '   in kWh).\n'
            '2. price_utils.py must define `strike(hour_class: str) -> float`\n'
            "   returning 61.37 for 'PEAK' and 34.82 for 'OFF'.\n"
            '3. solution.py must define\n'
            '   `settle(readings: list, hour_class: str, curtailed: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - e = mwh(readings); pay = e * strike(hour_class).\n'
            '   - Curtailment: if curtailed is True the payment is reduced:\n'
            '     multiply pay by 0.71 BEFORE the bonus below.\n'
            '   - Production bonus: if e is STRICTLY greater than 8.4 MWh, add a\n'
            '     flat 96.55 (the bonus is never curtailed).\n'
            '   - Return round(pay, 2).\n'
        ),
        "starter_code": (
            'def settle(readings: list, hour_class: str, curtailed: bool) -> float:\n'
            '    """Compute the settlement payment for a set of turbine readings."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_mwh():\n'
            '    from output_utils import mwh\n'
            '    assert mwh([2500.0, 1500.0]) == 4.0\n'
            '\n'
            '\n'
            'def test_helper_mwh_empty():\n'
            '    from output_utils import mwh\n'
            '    assert mwh([]) == 0.0\n'
            '\n'
            '\n'
            'def test_helper_strike_peak():\n'
            '    from price_utils import strike\n'
            "    assert strike('PEAK') == 61.37\n"
            '\n'
            '\n'
            'def test_helper_strike_off():\n'
            '    from price_utils import strike\n'
            "    assert strike('OFF') == 34.82\n"
            '\n'
            '\n'
            'def test_settle_peak_plain():\n'
            '    from solution import settle\n'
            "    assert settle([2000.0], 'PEAK', False) == 122.74\n"
            '\n'
            '\n'
            'def test_settle_off_plain():\n'
            '    from solution import settle\n'
            "    assert settle([2000.0], 'OFF', False) == 69.64\n"
            '\n'
            '\n'
            'def test_settle_curtailed():\n'
            '    from solution import settle\n'
            "    assert settle([2000.0], 'PEAK', True) == 87.15\n"
            '\n'
            '\n'
            'def test_bonus_paid():\n'
            '    from solution import settle\n'
            "    assert settle([9000.0], 'OFF', False) == 409.93\n"
            '\n'
            '\n'
            'def test_bonus_exact_edge_no_bonus():\n'
            '    from solution import settle\n'
            "    assert settle([8400.0], 'OFF', False) == 292.49\n"
            '\n'
            '\n'
            'def test_bonus_not_curtailed():\n'
            '    from solution import settle\n'
            "    assert settle([9000.0], 'OFF', True) == 319.05\n"
            '\n'
            '\n'
            'def test_empty_readings():\n'
            '    from solution import settle\n'
            "    assert settle([], 'PEAK', False) == 0.0\n"
            '\n'
            '\n'
            'def test_many_readings_peak_bonus():\n'
            '    from solution import settle\n'
            "    assert settle([3000.0, 3000.0, 3000.0], 'PEAK', False) == 648.88\n"
        ),
    },
    {
        "task_id": 'h_apartment_deposit',
        "prompt": (
            'You are asked to implement a security deposit settlement module for a property manager.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. wear_utils.py must define `deductible(item: str, cost: float) -> float`:\n'
            "   items starting with 'WT-' (normal wear and tear) are never charged\n"
            '   (0.0); everything else is charged at cost * 0.9235.\n'
            '2. clean_utils.py must define `cleaning(rooms: int) -> float` returning\n'
            '   rooms * 43.7 with a cap at 218.5.\n'
            '3. solution.py must define\n'
            '   `settlement(deposit: float, damages: list, rooms: int,\n'
            '   late_days: int) -> float` where damages is a list of (item, cost)\n'
            '   tuples, computed in this exact order:\n'
            '   - charges = sum of deductible(item, cost) + cleaning(rooms).\n'
            '   - Late-return penalty: add 27.15 per late day for AT MOST 6 days\n'
            '     (further days add nothing).\n'
            '   - result = deposit - charges; a negative result is reported as a\n'
            '     debt: return round(result, 2) either way (may be negative).\n'
        ),
        "starter_code": (
            'def settlement(deposit: float, damages: list, rooms: int, late_days: int) -> float:\n'
            '    """Compute the deposit settlement (may be negative)."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_wear_free():\n'
            '    from wear_utils import deductible\n'
            "    assert deductible('WT-paint', 100.0) == 0.0\n"
            '\n'
            '\n'
            'def test_helper_damage_charged():\n'
            '    from wear_utils import deductible\n'
            "    assert deductible('DG-door', 100.0) == 92.35\n"
            '\n'
            '\n'
            'def test_helper_cleaning_small():\n'
            '    from clean_utils import cleaning\n'
            '    assert cleaning(2) == 87.4\n'
            '\n'
            '\n'
            'def test_helper_cleaning_capped():\n'
            '    from clean_utils import cleaning\n'
            '    assert cleaning(6) == 218.5\n'
            '\n'
            '\n'
            'def test_helper_cleaning_exact_cap():\n'
            '    from clean_utils import cleaning\n'
            '    assert cleaning(5) == 218.5\n'
            '\n'
            '\n'
            'def test_no_damages():\n'
            '    from solution import settlement\n'
            '    assert settlement(1000.0, [], 2, 0) == 912.6\n'
            '\n'
            '\n'
            'def test_wear_items_free():\n'
            '    from solution import settlement\n'
            "    assert settlement(1000.0, [('WT-wall', 500.0)], 2, 0) == 912.6\n"
            '\n'
            '\n'
            'def test_damage_charged():\n'
            '    from solution import settlement\n'
            "    assert settlement(1000.0, [('DG-door', 200.0)], 2, 0) == 727.9\n"
            '\n'
            '\n'
            'def test_late_penalty():\n'
            '    from solution import settlement\n'
            '    assert settlement(1000.0, [], 2, 3) == 831.15\n'
            '\n'
            '\n'
            'def test_late_penalty_capped():\n'
            '    from solution import settlement\n'
            '    assert settlement(1000.0, [], 2, 10) == 749.7\n'
            '\n'
            '\n'
            'def test_late_exact_six_days():\n'
            '    from solution import settlement\n'
            '    assert settlement(1000.0, [], 2, 6) == 749.7\n'
            '\n'
            '\n'
            'def test_negative_settlement():\n'
            '    from solution import settlement\n'
            "    assert settlement(100.0, [('DG-sofa', 900.0)], 6, 0) == -949.65\n"
        ),
    },
    {
        "task_id": 'h_stream_royalties',
        "prompt": (
            'You are asked to implement a streaming royalty splitter for a music rights agency.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. rate_utils.py must define `per_stream(region: str) -> float`\n'
            "   returning 0.00473 for 'NA', 0.00311 for 'EU' and 0.00187 for any\n"
            '   other region.\n'
            '2. split_utils.py must define\n'
            '   `writer_share(gross: float) -> float` returning gross * 0.3842.\n'
            '3. fee_utils.py must define `agency_fee(gross: float) -> float`\n'
            '   returning gross * 0.0917.\n'
            '4. solution.py must define\n'
            '   `payout(streams: int, region: str) -> tuple` computed in this exact\n'
            '   order, where half_up(x) = math.floor(x * 100 + 0.5) / 100:\n'
            '   - gross = streams * per_stream(region).\n'
            '   - Threshold: if gross is STRICTLY less than 25, both parties get\n'
            '     0.0 (the royalty accrues but is not paid): return (0.0, 0.0).\n'
            '   - w = half_up(writer_share(gross)).\n'
            '   - The performer gets the remainder AFTER the agency fee:\n'
            '     p = half_up(gross - w - agency_fee(gross)).\n'
            '   - Return (w, p).\n'
        ),
        "starter_code": (
            'def payout(streams: int, region: str) -> tuple:\n'
            '    """Compute (writer, performer) royalty payouts."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_rate_na():\n'
            '    from rate_utils import per_stream\n'
            "    assert per_stream('NA') == 0.00473\n"
            '\n'
            '\n'
            'def test_helper_rate_eu():\n'
            '    from rate_utils import per_stream\n'
            "    assert per_stream('EU') == 0.00311\n"
            '\n'
            '\n'
            'def test_helper_rate_row():\n'
            '    from rate_utils import per_stream\n'
            "    assert per_stream('BR') == 0.00187\n"
            '\n'
            '\n'
            'def test_helper_writer_share():\n'
            '    from split_utils import writer_share\n'
            '    assert writer_share(100.0) == 38.42\n'
            '\n'
            '\n'
            'def test_helper_agency_fee():\n'
            '    from fee_utils import agency_fee\n'
            '    assert agency_fee(100.0) == 9.17\n'
            '\n'
            '\n'
            'def test_below_threshold():\n'
            '    from solution import payout\n'
            "    assert payout(5000, 'NA') == (0.0, 0.0)\n"
            '\n'
            '\n'
            'def test_na_payout():\n'
            '    from solution import payout\n'
            "    assert payout(10000, 'NA') == (18.17, 24.79)\n"
            '\n'
            '\n'
            'def test_eu_payout():\n'
            '    from solution import payout\n'
            "    assert payout(10000, 'EU') == (11.95, 16.3)\n"
            '\n'
            '\n'
            'def test_row_payout():\n'
            '    from solution import payout\n'
            "    assert payout(20000, 'BR') == (14.37, 19.6)\n"
            '\n'
            '\n'
            'def test_zero_streams():\n'
            '    from solution import payout\n'
            "    assert payout(0, 'NA') == (0.0, 0.0)\n"
            '\n'
            '\n'
            'def test_just_above_threshold():\n'
            '    from solution import payout\n'
            "    assert payout(5300, 'NA') == (9.63, 13.14)\n"
            '\n'
            '\n'
            'def test_large_volume():\n'
            '    from solution import payout\n'
            "    assert payout(1000000, 'NA') == (1817.27, 2478.99)\n"
        ),
    },
    {
        "task_id": 'h_bakery_batch',
        "prompt": (
            'You are asked to implement a bakery production planning module for an industrial bakery.\n'
            'The work is split across three files that you must create in the\n'
            'workspace: two small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. mix_utils.py must define `flour_needed(loaves: int) -> float`\n'
            '   returning loaves * 0.4235 (kilograms of flour per loaf), plus a\n'
            '   fixed machine loss of 1.85 kg for any batch with at least one loaf\n'
            '   (a batch of zero loaves needs 0.0).\n'
            '2. oven_utils.py must define `oven_runs(loaves: int) -> int`: each run\n'
            '   bakes at most 27 loaves; return the number of runs needed.\n'
            '3. solution.py must define `batch_cost(loaves: int, rush: bool) -> float`\n'
            '   computed in this exact order:\n'
            '   - cost = flour_needed(loaves) * 2.415 (price per kg of flour).\n'
            '   - Add 18.6 for every oven run (oven_runs(loaves)).\n'
            '   - Rush order: if rush is True, multiply the whole cost by 1.3345.\n'
            '   - Round the result with round(x, 2); if the rounded value is\n'
            '     STRICTLY below 11.9 return 11.9 (minimum billing).\n'
        ),
        "starter_code": (
            'def batch_cost(loaves: int, rush: bool) -> float:\n'
            '    """Compute the production cost of a batch of loaves."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_flour_zero():\n'
            '    from mix_utils import flour_needed\n'
            '    assert flour_needed(0) == 0.0\n'
            '\n'
            '\n'
            'def test_helper_flour_one():\n'
            '    from mix_utils import flour_needed\n'
            '    assert flour_needed(1) == 2.2735000000000003\n'
            '\n'
            '\n'
            'def test_helper_flour_hundred():\n'
            '    from mix_utils import flour_needed\n'
            '    assert flour_needed(100) == 44.2\n'
            '\n'
            '\n'
            'def test_helper_runs_zero():\n'
            '    from oven_utils import oven_runs\n'
            '    assert oven_runs(0) == 0\n'
            '\n'
            '\n'
            'def test_helper_runs_exact():\n'
            '    from oven_utils import oven_runs\n'
            '    assert oven_runs(27) == 1\n'
            '\n'
            '\n'
            'def test_helper_runs_remainder():\n'
            '    from oven_utils import oven_runs\n'
            '    assert oven_runs(28) == 2\n'
            '\n'
            '\n'
            'def test_zero_loaves_minimum():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(0, False) == 11.9\n'
            '\n'
            '\n'
            'def test_small_batch():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(10, False) == 33.3\n'
            '\n'
            '\n'
            'def test_rush_batch():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(10, True) == 44.43\n'
            '\n'
            '\n'
            'def test_two_oven_runs():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(28, False) == 70.3\n'
            '\n'
            '\n'
            'def test_exact_one_run():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(27, False) == 50.68\n'
            '\n'
            '\n'
            'def test_large_rush():\n'
            '    from solution import batch_cost\n'
            '    assert batch_cost(100, True) == 241.74\n'
        ),
    },
    {
        "task_id": 'h_telco_roaming',
        "prompt": (
            'You are asked to implement a mobile roaming charges module for a telecom carrier.\n'
            'The work is split across four files that you must create in the\n'
            'workspace: three small helper files plus the main entry point file\n'
            'solution.py that the tests call. Read every numbered rule below\n'
            'carefully and apply the rules in the exact order stated; the business\n'
            'constants are arbitrary and cannot be guessed or derived from anything\n'
            'else.\n'
            '\n'
            'Files and functions:\n'
            '1. data_utils.py must define `data_charge(mb: float) -> float`: the\n'
            '   first 512 MB cost 0.0193 per MB and every MB above that costs\n'
            '   0.0072 per MB.\n'
            '2. voice_utils.py must define `voice_charge(minutes: int) -> float`\n'
            '   returning minutes * 0.4180.\n'
            '3. bundle_utils.py must define `bundle_credit(code: str) -> float`\n'
            "   returning 21.9 when code is exactly 'RM7', 9.35 when it is exactly\n"
            "   'RM3', else 0.0.\n"
            '4. solution.py must define\n'
            '   `roaming_bill(mb: float, minutes: int, code: str) -> float`\n'
            '   computed in this exact order:\n'
            '   - total = data_charge(mb) + voice_charge(minutes).\n'
            '   - Subtract bundle_credit(code); clamp a negative result to 0.0.\n'
            '   - Regulatory cap: if total is STRICTLY greater than 87.6, set\n'
            '     total to 87.6.\n'
            '   - Return round(total, 2).\n'
        ),
        "starter_code": (
            'def roaming_bill(mb: float, minutes: int, code: str) -> float:\n'
            '    """Compute the monthly roaming bill."""\n'
            '    raise NotImplementedError\n'
        ),
        "test_code": (
            'def test_helper_data_below_break():\n'
            '    from data_utils import data_charge\n'
            '    assert data_charge(100.0) == 1.9300000000000002\n'
            '\n'
            '\n'
            'def test_helper_data_exact_break():\n'
            '    from data_utils import data_charge\n'
            '    assert data_charge(512.0) == 9.8816\n'
            '\n'
            '\n'
            'def test_helper_data_above_break():\n'
            '    from data_utils import data_charge\n'
            '    assert data_charge(1000.0) == 13.3952\n'
            '\n'
            '\n'
            'def test_helper_voice():\n'
            '    from voice_utils import voice_charge\n'
            '    assert voice_charge(10) == 4.18\n'
            '\n'
            '\n'
            'def test_helper_bundle_rm7():\n'
            '    from bundle_utils import bundle_credit\n'
            "    assert bundle_credit('RM7') == 21.9\n"
            '\n'
            '\n'
            'def test_helper_bundle_rm3():\n'
            '    from bundle_utils import bundle_credit\n'
            "    assert bundle_credit('RM3') == 9.35\n"
            '\n'
            '\n'
            'def test_helper_bundle_none():\n'
            '    from bundle_utils import bundle_credit\n'
            "    assert bundle_credit('RM9') == 0.0\n"
            '\n'
            '\n'
            'def test_bill_data_only():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(100.0, 0, 'NONE') == 1.93\n"
            '\n'
            '\n'
            'def test_bill_voice_only():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(0.0, 30, 'NONE') == 12.54\n"
            '\n'
            '\n'
            'def test_bill_credit_applied():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(100.0, 30, 'RM3') == 5.12\n"
            '\n'
            '\n'
            'def test_bill_clamped_at_zero():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(50.0, 0, 'RM7') == 0.0\n"
            '\n'
            '\n'
            'def test_bill_capped():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(5000.0, 200, 'NONE') == 87.6\n"
            '\n'
            '\n'
            'def test_bill_just_under_cap():\n'
            '    from solution import roaming_bill\n'
            "    assert roaming_bill(0.0, 209, 'NONE') == 87.36\n"
        ),
    },
]

STRATA: dict[str, str] = {
    'h_customs_clearance': "H",
    'h_hotel_folio': "H",
    'h_freight_ladder': "H",
    'h_parking_tariff': "H",
    'h_payslip_deductions': "H",
    'h_bookstore_order': "H",
    'h_sku_validator': "H",
    'h_water_billing': "H",
    'h_triage_queue': "H",
    'h_gym_membership': "H",
    'h_grade_curve': "H",
    'h_cargo_manifest': "H",
    'h_turnstile_fsm': "H",
    'h_expense_audit': "H",
    'h_seed_lot_grader': "H",
    'h_car_lease_quote': "H",
    'h_return_merchandise': "H",
    'h_print_shop': "H",
    'h_donation_matcher': "H",
    'h_wind_turbine_pay': "H",
    'h_apartment_deposit': "H",
    'h_stream_royalties': "H",
    'h_bakery_batch': "H",
    'h_telco_roaming': "H",
}

CRITICAL_CONSTANTS: dict[str, list[str]] = {
    'h_customs_clearance': [
        '5.2731',
        '6.1408',
        '4.9377',
        '0.1873',
        '0.0942',
        '0.2417',
        '683',
        '41.85',
        '7',
        '0.9315',
        "'QX-'",
        "'RM-'",
    ],
    'h_hotel_folio': [
        '412.60',
        '388.45',
        '297.30',
        '0.0685',
        '13',
        '0.8823',
        '23.4',
        '9',
    ],
    'h_freight_ladder': [
        '137',
        '415',
        '2.3146',
        '1.9072',
        '1.4381',
        '0.1176',
        '89',
        '27.55',
    ],
    'h_parking_tariff': ['45', '30', "'EV-'", '61.0', '4.35', '38.7', '0.85'],
    'h_payslip_deductions': [
        '0.0537',
        '9250',
        '3178',
        '0.11',
        '0.23',
        '118.6',
        '2140',
        '34.75',
    ],
    'h_bookstore_order': [
        '17',
        '0.9264',
        '3.15',
        "'GF-'",
        '923',
        '0.9588',
        '12.85',
        '618',
    ],
    'h_sku_validator': [
        '43',
        "'KP-'",
        "'VN-'",
        '11',
        "'ERR_74'",
        "'ERR_29'",
        "'ERR_50'",
        '19',
        "'ERR_88'",
        "'OK:'",
    ],
    'h_water_billing': [
        '10000',
        '12',
        '31',
        '1.8354',
        '3.2417',
        '5.9126',
        '0.7238',
        '14.2',
        '0.6471',
    ],
    'h_triage_queue': ['34', '118', '27', '38.6', '12', '21', '77', '4'],
    'h_gym_membership': [
        '67.90',
        '54.35',
        '41.20',
        '11',
        '6.45',
        '23',
        '0.9137',
        '15.9',
    ],
    'h_grade_curve': [
        '4.25',
        '1.75',
        '1.0842',
        '84.5',
        '91.3',
        '68.7',
        "'DIST'",
        "'PASS'",
        "'FAIL'",
    ],
    'h_cargo_manifest': ['1.0637', '740', "'HZ-'", "'CH-'", '325', '0.5218', '9.75'],
    'h_turnstile_fsm': ["'MT-'", '9', '2.85', '4.6', '7.15', '3', "'JAMMED'"],
    'h_expense_audit': ['84.0', '173.5', '46.25', '0.55', '1.4', "'TAXI'"],
    'h_seed_lot_grader': [
        '0.42',
        '0.58',
        '92.4',
        '96.0',
        '71.8',
        "'PRIME'",
        "'FAIR'",
        "'CULL'",
    ],
    'h_car_lease_quote': [
        '0.6412',
        '0.7871',
        '36',
        '0.00291',
        '0.00418',
        '0.00655',
        '642.0',
    ],
    'h_return_merchandise': ['14', '0.8259', '42', '0.5117', '77', '24.65'],
    'h_print_shop': [
        '0.0842',
        '0.1937',
        '0.3164',
        '31.4',
        '17.8',
        '2.6',
        '1850',
        '0.8118',
        '52.3',
    ],
    'h_donation_matcher': [
        "'PL-'",
        "'ST-'",
        '1.75',
        '0.65',
        '5230.0',
        '1980.0',
        '940',
        '12.4',
    ],
    'h_wind_turbine_pay': ['1000.0', '61.37', '34.82', '0.71', '8.4', '96.55'],
    'h_apartment_deposit': ["'WT-'", '0.9235', '43.7', '218.5', '27.15', '6'],
    'h_stream_royalties': ['0.00473', '0.00311', '0.00187', '0.3842', '0.0917', '25'],
    'h_bakery_batch': ['0.4235', '1.85', '27', '2.415', '18.6', '1.3345', '11.9'],
    'h_telco_roaming': [
        '512',
        '0.0193',
        '0.0072',
        '0.4180',
        '21.9',
        '9.35',
        "'RM7'",
        "'RM3'",
        '87.6',
    ],
}


def get_task(task_id: str) -> dict:
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise KeyError(task_id)
