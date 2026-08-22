"""Pool fixo de 10 tasks v3 estratificadas para o Teste de sinergia contexto×constantes.

Dois estratos nesta entrega (o estrato "L" será adicionado em chamada futura):

- Estrato S (sinergia, prefixo s_): prompts >600 chars cujos primeiros 240 chars
  contêm APENAS apresentação genérica (arquivos, nomes de função, propósito).
  Todas as constantes críticas aparecem APÓS o char 240 — se o summarize truncar
  o enunciado, elas se perdem. Cada task tem exatamente 2 arquivos: um helper
  trivial SEM constantes críticas e solution.py que usa todas. Todo valor
  esperado nos asserts é COMPOSTO de >=2 constantes críticas, de modo que o
  output do pytest (que vaza valores esperados) não permite recuperar nenhuma
  constante individual.

- Estrato C (controle, prefixo c_): prompts >600 chars cujas constantes críticas
  aparecem TODAS dentro dos primeiros 240 chars; o restante do enunciado é
  apenas elaboração redundante. 1 arquivo (solution.py). Truncar aos 240 chars
  não remove informação necessária.

Ambos os estratos usam imports DENTRO das funções de teste para reward gradual
(arquivos ausentes causam falhas individuais, não erro de coleta).
"""

TASKS: list[dict] = [
    # ------------------------- ESTRATO S -------------------------
    {
        "task_id": "s_freight_quote",
        "prompt": (
            "You are asked to implement a freight quoting module for a logistics\n"
            "company. The work is split across two files that you must create in the\n"
            "workspace: a small numeric helper file and the main entry point file\n"
            "solution.py that the tests call. Read every rule below carefully: the\n"
            "exact business constants matter and cannot be derived from the code.\n\n"
            "Files and functions:\n"
            "1. shipping_utils.py must define `round2(x: float) -> float` returning\n"
            "   `round(x, 2)`.\n"
            "2. solution.py must define\n"
            "   `freight_quote(weight_kg: float, express: bool) -> float` computed\n"
            "   in this exact order:\n"
            "   - Start with a flat base fee of 14.75 plus 3.85 per kilogram\n"
            "     (weight_kg * 3.85).\n"
            "   - Heavy surcharge: if weight_kg is STRICTLY greater than 22.5,\n"
            "     multiply the quote by 1.12 (at exactly 22.5 there is no surcharge).\n"
            "   - Express: if express is True, multiply the quote by 1.45 at the end.\n"
            "   Return the final quote passed through round2.\n"
        ),
        "starter_code": (
            "def freight_quote(weight_kg: float, express: bool) -> float:\n"
            '    """Compute the freight quote for a shipment."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_helper_round2():\n"
            "    from shipping_utils import round2\n"
            "    assert round2(3.14159) == 3.14\n"
            "\n"
            "\n"
            "def test_standard_ten_kg():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(10.0, False) == 53.25\n"
            "\n"
            "\n"
            "def test_standard_one_kg():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(1.0, False) == 18.6\n"
            "\n"
            "\n"
            "def test_zero_weight_express():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(0.0, True) == 21.39\n"
            "\n"
            "\n"
            "def test_heavy_shipment():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(30.0, False) == 145.88\n"
            "\n"
            "\n"
            "def test_just_above_heavy_threshold():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(23, False) == 115.7\n"
            "\n"
            "\n"
            "def test_just_below_heavy_threshold():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(22, False) == 99.45\n"
            "\n"
            "\n"
            "def test_heavy_and_express():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(23, True) == 167.76\n"
            "\n"
            "\n"
            "def test_light_express():\n"
            "    from solution import freight_quote\n"
            "    assert freight_quote(5.0, True) == 49.3\n"
        ),
    },
    {
        "task_id": "s_ticket_pricer",
        "prompt": (
            "You are asked to implement a museum ticket pricing module. The work is\n"
            "split across two files that you must create in the workspace: a small\n"
            "calendar helper file and the main entry point file solution.py that the\n"
            "tests call. The pricing constants below are arbitrary business rules\n"
            "and must be followed exactly as written, in the given order.\n\n"
            "Files and functions:\n"
            "1. calendar_utils.py must define `is_weekend(day: str) -> bool` returning\n"
            "   True iff day is 'sat' or 'sun' (lowercase three-letter codes).\n"
            "2. solution.py must define `ticket_price(age: int, day: str) -> float`\n"
            "   computed in this exact order:\n"
            "   - Start from the adult base price of 48.20.\n"
            "   - If age < 12, multiply the base by 0.35; otherwise if age >= 65,\n"
            "     multiply the base by 0.55 (only one multiplier ever applies).\n"
            "   - Add a fixed booking fee of 4.15.\n"
            "   - If is_weekend(day), add a weekend surcharge of 6.60.\n"
            "   Return the result rounded to 2 decimal places with round(x, 2).\n"
        ),
        "starter_code": (
            "def ticket_price(age: int, day: str) -> float:\n"
            '    """Compute the ticket price for a visitor age on a given day."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_helper_weekend_true():\n"
            "    from calendar_utils import is_weekend\n"
            "    assert is_weekend('sat') is True and is_weekend('sun') is True\n"
            "\n"
            "\n"
            "def test_helper_weekday_false():\n"
            "    from calendar_utils import is_weekend\n"
            "    assert is_weekend('mon') is False\n"
            "\n"
            "\n"
            "def test_adult_weekday():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(30, 'mon') == 52.35\n"
            "\n"
            "\n"
            "def test_child_weekday():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(8, 'tue') == 21.02\n"
            "\n"
            "\n"
            "def test_senior_weekday():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(70, 'wed') == 30.66\n"
            "\n"
            "\n"
            "def test_adult_weekend():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(30, 'sat') == 58.95\n"
            "\n"
            "\n"
            "def test_child_weekend():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(8, 'sun') == 27.62\n"
            "\n"
            "\n"
            "def test_senior_weekend():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(70, 'sat') == 37.26\n"
            "\n"
            "\n"
            "def test_child_boundary_ages():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(11, 'mon') == 21.02\n"
            "    assert ticket_price(12, 'mon') == 52.35\n"
            "\n"
            "\n"
            "def test_senior_boundary_ages():\n"
            "    from solution import ticket_price\n"
            "    assert ticket_price(64, 'fri') == 52.35\n"
            "    assert ticket_price(66, 'thu') == 30.66\n"
        ),
    },
    {
        "task_id": "s_sensor_alarm",
        "prompt": (
            "You are asked to implement an industrial sensor alarm scorer. The work\n"
            "is split across two files that you must create in the workspace: a tiny\n"
            "statistics helper file and the main entry point file solution.py that\n"
            "the tests call. The alarm thresholds and scaling factors given below\n"
            "are calibration constants; follow them exactly as written.\n\n"
            "Files and functions:\n"
            "1. readings_utils.py must define `mean(values: list[float]) -> float`\n"
            "   returning `sum(values) / len(values)` (input is never empty).\n"
            "2. solution.py must define `alarm_level(values: list[float]) -> float`.\n"
            "   Let m = mean(values). Then, checked from the top:\n"
            "   - if m is STRICTLY greater than 71.4, return round(m * 1.65 + 4.35, 2);\n"
            "   - otherwise, if m is STRICTLY greater than 33.8, return\n"
            "     round((m + 15.9) * 1.15, 2);\n"
            "   - otherwise return round(m * 0.25 + 8.2, 2).\n"
            "   Exactly one branch applies; the two thresholds are strict.\n"
        ),
        "starter_code": (
            "def alarm_level(values: list[float]) -> float:\n"
            '    """Score the alarm level for a window of sensor readings."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_helper_mean():\n"
            "    from readings_utils import mean\n"
            "    assert mean([2, 4]) == 3.0\n"
            "\n"
            "\n"
            "def test_high_band():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([80, 80]) == 136.35\n"
            "\n"
            "\n"
            "def test_mid_band():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([40]) == 64.28\n"
            "\n"
            "\n"
            "def test_low_band():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([10, 20]) == 11.95\n"
            "\n"
            "\n"
            "def test_just_below_high_threshold():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([71]) == 99.94\n"
            "\n"
            "\n"
            "def test_just_above_high_threshold():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([72]) == 123.15\n"
            "\n"
            "\n"
            "def test_just_below_mid_threshold():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([33]) == 16.45\n"
            "\n"
            "\n"
            "def test_just_above_mid_threshold():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([34]) == 57.38\n"
            "\n"
            "\n"
            "def test_high_band_single_reading():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([100]) == 169.35\n"
            "\n"
            "\n"
            "def test_mid_band_two_readings():\n"
            "    from solution import alarm_level\n"
            "    assert alarm_level([50, 60]) == 81.53\n"
        ),
    },
    {
        "task_id": "s_commission_calc",
        "prompt": (
            "You are asked to implement a sales commission calculator. The work is\n"
            "split across two files that you must create in the workspace: a small\n"
            "aggregation helper file and the main entry point file solution.py that\n"
            "the tests call. The commission rates, tier thresholds and bonuses given\n"
            "below are contractual constants and must be applied exactly as stated.\n\n"
            "Files and functions:\n"
            "1. sales_utils.py must define `total(sales: list[float]) -> float`\n"
            "   returning `float(sum(sales))`.\n"
            "2. solution.py must define `commission(sales: list[float]) -> float`.\n"
            "   Let t = total(sales). Then, in this exact order:\n"
            "   - Rate: use 0.083 if t is STRICTLY greater than 5400, otherwise use\n"
            "     0.047 (at exactly 5400 the lower rate applies).\n"
            "   - Commission: t times the rate, plus a fixed stipend of 62.5.\n"
            "   - Top-seller bonus: if t is STRICTLY greater than 9100, add a flat\n"
            "     175.0 on top (at exactly 9100 there is no bonus).\n"
            "   Return the result rounded to 2 decimal places with round(x, 2).\n"
        ),
        "starter_code": (
            "def commission(sales: list[float]) -> float:\n"
            '    """Compute the commission owed for a list of sale amounts."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_helper_total():\n"
            "    from sales_utils import total\n"
            "    assert total([1, 2, 3]) == 6\n"
            "\n"
            "\n"
            "def test_low_tier_small():\n"
            "    from solution import commission\n"
            "    assert commission([1000]) == 109.5\n"
            "\n"
            "\n"
            "def test_low_tier_medium():\n"
            "    from solution import commission\n"
            "    assert commission([5000]) == 297.5\n"
            "\n"
            "\n"
            "def test_high_tier():\n"
            "    from solution import commission\n"
            "    assert commission([6000]) == 560.5\n"
            "\n"
            "\n"
            "def test_just_below_rate_threshold():\n"
            "    from solution import commission\n"
            "    assert commission([5399]) == 316.25\n"
            "\n"
            "\n"
            "def test_just_above_rate_threshold():\n"
            "    from solution import commission\n"
            "    assert commission([5401]) == 510.78\n"
            "\n"
            "\n"
            "def test_just_below_bonus_threshold():\n"
            "    from solution import commission\n"
            "    assert commission([9099]) == 817.72\n"
            "\n"
            "\n"
            "def test_just_above_bonus_threshold():\n"
            "    from solution import commission\n"
            "    assert commission([9101]) == 992.88\n"
            "\n"
            "\n"
            "def test_big_seller_with_bonus():\n"
            "    from solution import commission\n"
            "    assert commission([10000]) == 1067.5\n"
            "\n"
            "\n"
            "def test_multiple_sales_summed():\n"
            "    from solution import commission\n"
            "    assert commission([2000, 500]) == 180.0\n"
        ),
    },
    {
        "task_id": "s_energy_bill",
        "prompt": (
            "You are asked to implement an electricity billing module. The work is\n"
            "split across two files that you must create in the workspace: a meter\n"
            "reading helper file and the main entry point file solution.py that the\n"
            "tests call. The tariff constants below come from the utility contract\n"
            "and must be applied exactly, in the stated order.\n\n"
            "Files and functions:\n"
            "1. meter_utils.py must define `usage(start: float, end: float) -> float`\n"
            "   returning `end - start` (the consumed units).\n"
            "2. solution.py must define\n"
            "   `bill(start: float, end: float, night: bool) -> float`.\n"
            "   Let u = usage(start, end). Then, in this exact order:\n"
            "   - Base cost: u * 0.6175 plus a fixed connection charge of 21.45.\n"
            "   - Peak surcharge: if u is STRICTLY greater than 240, add\n"
            "     (u - 240) * 0.29 for the excess units only.\n"
            "   - Night plan: if night is True, multiply the whole amount by 0.93\n"
            "     at the very end.\n"
            "   Return the result rounded to 2 decimal places with round(x, 2).\n"
        ),
        "starter_code": (
            "def bill(start: float, end: float, night: bool) -> float:\n"
            '    """Compute the electricity bill between two meter readings."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_helper_usage():\n"
            "    from meter_utils import usage\n"
            "    assert usage(10, 25) == 15\n"
            "\n"
            "\n"
            "def test_small_usage_day():\n"
            "    from solution import bill\n"
            "    assert bill(50, 150, False) == 83.2\n"
            "\n"
            "\n"
            "def test_small_usage_night():\n"
            "    from solution import bill\n"
            "    assert bill(50, 150, True) == 77.38\n"
            "\n"
            "\n"
            "def test_peak_surcharge_day():\n"
            "    from solution import bill\n"
            "    assert bill(0, 300, False) == 224.1\n"
            "\n"
            "\n"
            "def test_peak_surcharge_other_readings():\n"
            "    from solution import bill\n"
            "    assert bill(40, 300, False) == 187.8\n"
            "\n"
            "\n"
            "def test_medium_usage_day():\n"
            "    from solution import bill\n"
            "    assert bill(0, 200, False) == 144.95\n"
            "\n"
            "\n"
            "def test_medium_usage_night():\n"
            "    from solution import bill\n"
            "    assert bill(0, 200, True) == 134.8\n"
            "\n"
            "\n"
            "def test_just_above_peak_threshold():\n"
            "    from solution import bill\n"
            "    assert bill(100, 341, False) == 170.56\n"
            "\n"
            "\n"
            "def test_peak_and_night_combined():\n"
            "    from solution import bill\n"
            "    assert bill(0, 300, True) == 208.41\n"
        ),
    },
    # ------------------------- ESTRATO C -------------------------
    {
        "task_id": "c_temp_label",
        "prompt": (
            "Create solution.py defining `label(c: float) -> str`: return 'COLD' if\n"
            "c < 8.5, 'MILD' if 8.5 <= c < 27.0, otherwise 'HOT'; then append '!' to\n"
            "the label whenever c > 39.5. The constants 8.5, 27.0 and 39.5 are exact.\n\n"
            "To restate the very same rules step by step: you look at the temperature\n"
            "c and pick one of the three labels using the two cutoffs already given\n"
            "above, then independently decide whether to add the exclamation mark\n"
            "using the third cutoff already given above. For example, a temperature\n"
            "below the first cutoff yields the cold label; a temperature at or above\n"
            "the first cutoff but below the second yields the mild label; anything at\n"
            "or above the second cutoff yields the hot label. Finally, if and only if\n"
            "the temperature strictly exceeds the third cutoff, one exclamation mark\n"
            "is appended to whatever label was chosen. Nothing else is ever appended,\n"
            "and no other threshold exists beyond the three numbers stated in the\n"
            "first paragraph.\n"
        ),
        "starter_code": (
            "def label(c: float) -> str:\n"
            '    """Return the display label for a temperature in Celsius."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_cold():\n"
            "    from solution import label\n"
            "    assert label(0.0) == 'COLD'\n"
            "\n"
            "\n"
            "def test_cold_boundary():\n"
            "    from solution import label\n"
            "    assert label(8.4) == 'COLD'\n"
            "\n"
            "\n"
            "def test_mild_lower_boundary():\n"
            "    from solution import label\n"
            "    assert label(8.5) == 'MILD'\n"
            "\n"
            "\n"
            "def test_mild_upper_boundary():\n"
            "    from solution import label\n"
            "    assert label(26.9) == 'MILD'\n"
            "\n"
            "\n"
            "def test_hot_boundary():\n"
            "    from solution import label\n"
            "    assert label(27.0) == 'HOT'\n"
            "\n"
            "\n"
            "def test_no_bang_at_exact_threshold():\n"
            "    from solution import label\n"
            "    assert label(39.5) == 'HOT'\n"
            "\n"
            "\n"
            "def test_bang_above_threshold():\n"
            "    from solution import label\n"
            "    assert label(39.6) == 'HOT!'\n"
            "\n"
            "\n"
            "def test_negative_is_cold():\n"
            "    from solution import label\n"
            "    assert label(-5.0) == 'COLD'\n"
            "\n"
            "\n"
            "def test_very_hot():\n"
            "    from solution import label\n"
            "    assert label(100.0) == 'HOT!'\n"
        ),
    },
    {
        "task_id": "c_late_fee",
        "prompt": (
            "Create solution.py defining `late_fee(days: int) -> float`: return 0.0\n"
            "if days <= 0; otherwise fee = days * 2.75 + 8.0; if days > 30 add 55.0\n"
            "more; return round(fee, 2). All four constants are exact and mandatory.\n\n"
            "To walk through the very same computation again in words: when nothing\n"
            "is overdue (zero days or a negative input) the caller owes nothing at\n"
            "all, so the function returns the float zero. When at least one day is\n"
            "overdue, the fee grows linearly with the number of days at the per-day\n"
            "rate stated in the first sentence, on top of the flat handling amount\n"
            "also stated in the first sentence. When the delay is longer than the\n"
            "day-count threshold stated in the first sentence, one extra flat penalty\n"
            "(the fourth constant above) is added a single time — it is not\n"
            "multiplied by anything. The final value is always rounded to two\n"
            "decimal places before being returned, exactly as written above.\n"
        ),
        "starter_code": (
            "def late_fee(days: int) -> float:\n"
            '    """Compute the late-return fee for a rental overdue by `days`."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_zero_days():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(0) == 0.0\n"
            "\n"
            "\n"
            "def test_negative_days():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(-3) == 0.0\n"
            "\n"
            "\n"
            "def test_one_day():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(1) == 10.75\n"
            "\n"
            "\n"
            "def test_two_days():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(2) == 13.5\n"
            "\n"
            "\n"
            "def test_ten_days():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(10) == 35.5\n"
            "\n"
            "\n"
            "def test_no_penalty_at_exact_threshold():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(30) == 90.5\n"
            "\n"
            "\n"
            "def test_penalty_above_threshold():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(31) == 148.25\n"
            "\n"
            "\n"
            "def test_long_delay():\n"
            "    from solution import late_fee\n"
            "    assert late_fee(60) == 228.0\n"
        ),
    },
    {
        "task_id": "c_username_check",
        "prompt": (
            "Create solution.py defining `check(u: str) -> str`: return 'ERR_LEN' if\n"
            "len(u) < 5 or len(u) > 14; return 'ERR_CHAR' if u contains anything\n"
            "besides lowercase a-z, digits or '_'; otherwise return 'OK:' + u.\n\n"
            "Restating the exact same policy in plain words: the length rule is\n"
            "checked first, so a username that is both too short and full of illegal\n"
            "characters still gets the length error code from the first sentence.\n"
            "Only when the length is inside the inclusive range implied above does\n"
            "the character rule run: every single character must be a lowercase\n"
            "ASCII letter, a decimal digit, or the underscore; uppercase letters,\n"
            "spaces and punctuation all trigger the character error code from the\n"
            "first sentence. A username that passes both checks is echoed back with\n"
            "the two-character prefix and colon shown above glued directly in front\n"
            "of it, with no added spaces and no other transformation of any kind.\n"
        ),
        "starter_code": (
            "def check(u: str) -> str:\n"
            '    """Validate a username and return a status string."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_valid_minimal_length():\n"
            "    from solution import check\n"
            "    assert check('abcde') == 'OK:abcde'\n"
            "\n"
            "\n"
            "def test_too_short():\n"
            "    from solution import check\n"
            "    assert check('abcd') == 'ERR_LEN'\n"
            "\n"
            "\n"
            "def test_valid_maximal_length():\n"
            "    from solution import check\n"
            "    assert check('aaaaaaaaaaaaaa') == 'OK:aaaaaaaaaaaaaa'\n"
            "\n"
            "\n"
            "def test_too_long():\n"
            "    from solution import check\n"
            "    assert check('aaaaaaaaaaaaaaa') == 'ERR_LEN'\n"
            "\n"
            "\n"
            "def test_underscore_and_digit_ok():\n"
            "    from solution import check\n"
            "    assert check('user_1') == 'OK:user_1'\n"
            "\n"
            "\n"
            "def test_uppercase_rejected():\n"
            "    from solution import check\n"
            "    assert check('User1x') == 'ERR_CHAR'\n"
            "\n"
            "\n"
            "def test_space_rejected():\n"
            "    from solution import check\n"
            "    assert check('abc de') == 'ERR_CHAR'\n"
            "\n"
            "\n"
            "def test_empty_is_len_error():\n"
            "    from solution import check\n"
            "    assert check('') == 'ERR_LEN'\n"
            "\n"
            "\n"
            "def test_typical_valid_name():\n"
            "    from solution import check\n"
            "    assert check('good_name9') == 'OK:good_name9'\n"
        ),
    },
    {
        "task_id": "c_parcel_cost",
        "prompt": (
            "Create solution.py defining `cost(kg: float) -> float`: compute\n"
            "kg * 4.6 + 12.25; if kg > 18.0 multiply the whole amount by 1.3; return\n"
            "it rounded with round(x, 2). All four numeric constants are exact.\n\n"
            "Spelling out the identical procedure once more: every parcel pays a\n"
            "weight-proportional amount (the per-kilogram rate from the first\n"
            "sentence times the weight) plus the flat handling amount from the first\n"
            "sentence. Parcels whose weight strictly exceeds the bulky-parcel\n"
            "threshold from the first sentence have the ENTIRE amount so far — both\n"
            "the proportional part and the flat part — scaled by the bulky\n"
            "multiplier from the first sentence; parcels at exactly that weight are\n"
            "NOT scaled. The very last step is always the two-decimal rounding shown\n"
            "above, applied once, after any scaling. There are no other fees,\n"
            "discounts, thresholds or special cases beyond what the first sentence\n"
            "already states.\n"
        ),
        "starter_code": (
            "def cost(kg: float) -> float:\n"
            '    """Compute the delivery cost of a parcel by weight."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_zero_weight():\n"
            "    from solution import cost\n"
            "    assert cost(0.0) == 12.25\n"
            "\n"
            "\n"
            "def test_one_kg():\n"
            "    from solution import cost\n"
            "    assert cost(1.0) == 16.85\n"
            "\n"
            "\n"
            "def test_ten_kg():\n"
            "    from solution import cost\n"
            "    assert cost(10.0) == 58.25\n"
            "\n"
            "\n"
            "def test_no_scaling_at_exact_threshold():\n"
            "    from solution import cost\n"
            "    assert cost(18.0) == 95.05\n"
            "\n"
            "\n"
            "def test_scaling_just_above_threshold():\n"
            "    from solution import cost\n"
            "    assert cost(18.1) == 124.16\n"
            "\n"
            "\n"
            "def test_twenty_kg():\n"
            "    from solution import cost\n"
            "    assert cost(20.0) == 135.53\n"
            "\n"
            "\n"
            "def test_fractional_weight():\n"
            "    from solution import cost\n"
            "    assert cost(5.5) == 37.55\n"
            "\n"
            "\n"
            "def test_heavy_parcel():\n"
            "    from solution import cost\n"
            "    assert cost(100.0) == 613.92\n"
        ),
    },
    {
        "task_id": "c_vote_tally",
        "prompt": (
            "Create solution.py defining `tally(votes: list[str]) -> str`: count the\n"
            "exact strings 'yes' and 'no' (ignore everything else); return\n"
            "'APPROVED(y-n)' if yes >= no + 3, else 'REJECTED(y-n)', where y and n\n"
            "are the two counts.\n\n"
            "Describing the very same behaviour again for clarity: the function\n"
            "walks the list and keeps two counters, one for entries equal to the\n"
            "affirmative string from the first sentence and one for entries equal to\n"
            "the negative string from the first sentence; every other entry —\n"
            "including different capitalisations, abstentions or arbitrary text — is\n"
            "simply skipped and affects nothing. The motion passes only when the\n"
            "affirmative count beats the negative count by at least the margin\n"
            "stated in the first sentence. The returned string is the verdict word\n"
            "from the first sentence followed immediately by an opening parenthesis,\n"
            "the affirmative count, a hyphen, the negative count, and a closing\n"
            "parenthesis, with no spaces anywhere inside it.\n"
        ),
        "starter_code": (
            "def tally(votes: list[str]) -> str:\n"
            '    """Tally yes/no votes and return the verdict string."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "def test_unanimous_approval():\n"
            "    from solution import tally\n"
            "    assert tally(['yes', 'yes', 'yes']) == 'APPROVED(3-0)'\n"
            "\n"
            "\n"
            "def test_margin_too_small():\n"
            "    from solution import tally\n"
            "    assert tally(['yes', 'yes', 'yes', 'no']) == 'REJECTED(3-1)'\n"
            "\n"
            "\n"
            "def test_margin_exactly_three():\n"
            "    from solution import tally\n"
            "    assert tally(['yes', 'yes', 'yes', 'yes', 'no']) == 'APPROVED(4-1)'\n"
            "\n"
            "\n"
            "def test_empty_vote_list():\n"
            "    from solution import tally\n"
            "    assert tally([]) == 'REJECTED(0-0)'\n"
            "\n"
            "\n"
            "def test_only_no_votes():\n"
            "    from solution import tally\n"
            "    assert tally(['no', 'no']) == 'REJECTED(0-2)'\n"
            "\n"
            "\n"
            "def test_other_strings_ignored():\n"
            "    from solution import tally\n"
            "    assert tally(['yes', 'maybe', 'yes', 'YES', 'yes']) == 'APPROVED(3-0)'\n"
            "\n"
            "\n"
            "def test_mixed_with_margin():\n"
            "    from solution import tally\n"
            "    votes = ['yes'] * 5 + ['no'] * 2\n"
            "    assert tally(votes) == 'APPROVED(5-2)'\n"
            "\n"
            "\n"
            "def test_abstain_only():\n"
            "    from solution import tally\n"
            "    assert tally(['abstain']) == 'REJECTED(0-0)'\n"
        ),
    },
]

STRATA: dict[str, str] = {
    "s_freight_quote": "S",
    "s_ticket_pricer": "S",
    "s_sensor_alarm": "S",
    "s_commission_calc": "S",
    "s_energy_bill": "S",
    "c_temp_label": "C",
    "c_late_fee": "C",
    "c_username_check": "C",
    "c_parcel_cost": "C",
    "c_vote_tally": "C",
}

CRITICAL_CONSTANTS: dict[str, list[str]] = {
    "s_freight_quote": ["14.75", "3.85", "22.5", "1.12", "1.45"],
    "s_ticket_pricer": ["48.20", "0.35", "0.55", "4.15", "6.60"],
    "s_sensor_alarm": ["71.4", "33.8", "1.65", "4.35", "15.9", "1.15", "0.25", "8.2"],
    "s_commission_calc": ["0.083", "0.047", "5400", "9100", "175.0", "62.5"],
    "s_energy_bill": ["0.6175", "21.45", "240", "0.29", "0.93"],
    "c_temp_label": ["8.5", "27.0", "39.5", "'COLD'", "'MILD'", "'HOT'"],
    "c_late_fee": ["2.75", "8.0", "55.0", "30"],
    "c_username_check": ["'ERR_LEN'", "'ERR_CHAR'", "'OK:'", "5", "14"],
    "c_parcel_cost": ["4.6", "12.25", "18.0", "1.3"],
    "c_vote_tally": ["'yes'", "'no'", "'APPROVED", "'REJECTED", "+ 3"],
}


def get_task(task_id: str) -> dict:
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise KeyError(task_id)
