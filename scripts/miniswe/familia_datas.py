"""Família datas do pool mini-SWE (pré-registro 29).

Calendário gregoriano implementado do zero (sem datetime): bissextos,
conversão data<->ordinal, dias da semana, dias úteis e feriados fixos.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 calendario.py — condição invertida (século não múltiplo de 400 vira bissexto)
  v2 ordinal.py    — off-by-one (para_ordinal devolve um dia a menos)
  v3 uteis.py      — comparação errada (sábado deixa de ser fim de semana)
  v4 feriados.py   — constante errada (independência em 6/9 em vez de 7/9)
"""

_CALENDARIO = '''\
"""Calendário gregoriano implementado do zero — sem datetime.

Datas são tuplas (ano, mes, dia) com ano >= 1. Este módulo cuida de
anos bissextos, dias por mês e validação.
"""

DIAS_POR_MES = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def eh_bissexto(ano):
    """Regra gregoriana: múltiplo de 4, exceto séculos fora dos múltiplos de 400."""
    if ano % 400 == 0:
        return True
    if ano % 100 == 0:
        return False
    return ano % 4 == 0


def dias_no_mes(ano, mes):
    """Quantos dias tem o mês no ano dado."""
    if not 1 <= mes <= 12:
        raise ValueError(f"mes invalido: {mes}")
    if mes == 2 and eh_bissexto(ano):
        return 29
    return DIAS_POR_MES[mes - 1]


def valida_data(ano, mes, dia):
    """ValueError se (ano, mes, dia) não é uma data real."""
    if ano < 1:
        raise ValueError(f"ano invalido: {ano}")
    if not 1 <= dia <= dias_no_mes(ano, mes):
        raise ValueError(f"data invalida: {ano:04d}-{mes:02d}-{dia:02d}")
'''

_CALENDARIO_BUG = _CALENDARIO.replace(
    '''    if ano % 100 == 0:
        return False
''',
    '''    if ano % 100 == 0:
        return True
''')

_ORDINAL = '''\
"""Conversão data <-> ordinal (dias corridos desde 01/01/0001 = 1)."""
from calendario import dias_no_mes, eh_bissexto, valida_data


def _dias_antes_do_ano(ano):
    """Dias completos em todos os anos anteriores a `ano`."""
    anteriores = ano - 1
    return (anteriores * 365 + anteriores // 4
            - anteriores // 100 + anteriores // 400)


def para_ordinal(ano, mes, dia):
    """Ordinal da data: 01/01/0001 -> 1, 02/01/0001 -> 2, ..."""
    valida_data(ano, mes, dia)
    total = _dias_antes_do_ano(ano)
    for m in range(1, mes):
        total += dias_no_mes(ano, m)
    return total + dia


def de_ordinal(ordinal):
    """Data (ano, mes, dia) correspondente ao ordinal (>= 1)."""
    if ordinal < 1:
        raise ValueError(f"ordinal invalido: {ordinal}")
    ano = 1
    while True:
        dias_do_ano = 366 if eh_bissexto(ano) else 365
        if ordinal <= dias_do_ano:
            break
        ordinal -= dias_do_ano
        ano += 1
    mes = 1
    while ordinal > dias_no_mes(ano, mes):
        ordinal -= dias_no_mes(ano, mes)
        mes += 1
    return ano, mes, ordinal
'''

_ORDINAL_BUG = _ORDINAL.replace(
    "    return total + dia\n",
    "    return total + dia - 1\n")

_UTEIS = '''\
"""Dias da semana e aritmética de dias úteis sobre o ordinal.

Convenção: 0=segunda ... 5=sábado, 6=domingo. O ordinal 1
(01/01/0001) caiu numa segunda-feira.
"""
from ordinal import de_ordinal, para_ordinal

SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA, SABADO, DOMINGO = range(7)


def dia_da_semana(ano, mes, dia):
    """0=segunda ... 6=domingo."""
    return (para_ordinal(ano, mes, dia) + 6) % 7


def eh_fim_de_semana(ano, mes, dia):
    """True para sábado e domingo."""
    return dia_da_semana(ano, mes, dia) >= SABADO


def soma_dias(ano, mes, dia, n):
    """Data n dias corridos depois (n pode ser negativo)."""
    return de_ordinal(para_ordinal(ano, mes, dia) + n)


def proximo_dia_util(ano, mes, dia, eh_livre):
    """Primeira data ESTRITAMENTE depois que é dia útil.

    `eh_livre(mes, dia)` indica feriado; fins de semana nunca contam
    como dia útil.
    """
    ordinal = para_ordinal(ano, mes, dia)
    while True:
        ordinal += 1
        a, m, d = de_ordinal(ordinal)
        if eh_fim_de_semana(a, m, d):
            continue
        if eh_livre(m, d):
            continue
        return a, m, d


def soma_dias_uteis(ano, mes, dia, n, eh_livre):
    """Avança n dias úteis (n >= 0), pulando fins de semana e feriados."""
    atual = (ano, mes, dia)
    for _ in range(n):
        atual = proximo_dia_util(atual[0], atual[1], atual[2], eh_livre)
    return atual
'''

_UTEIS_BUG = _UTEIS.replace(
    "    return dia_da_semana(ano, mes, dia) >= SABADO\n",
    "    return dia_da_semana(ano, mes, dia) > SABADO\n")

_FERIADOS = '''\
"""Feriados nacionais fixos, como pares (mes, dia)."""

FERIADOS_FIXOS = (
    (1, 1),    # confraternizacao universal
    (4, 21),   # tiradentes
    (5, 1),    # dia do trabalho
    (9, 7),    # independencia
    (10, 12),  # nossa senhora aparecida
    (11, 2),   # finados
    (11, 15),  # proclamacao da republica
    (12, 25),  # natal
)


def eh_feriado(mes, dia):
    """True se (mes, dia) é feriado fixo em qualquer ano."""
    return (mes, dia) in FERIADOS_FIXOS


def feriados_do_mes(mes):
    """Dias de feriado do mês, em ordem crescente."""
    return sorted(dia for m, dia in FERIADOS_FIXOS if m == mes)
'''

_FERIADOS_BUG = _FERIADOS.replace(
    "    (9, 7),    # independencia\n",
    "    (9, 6),    # independencia\n")

_API = '''\
"""Operações compostas do calendário: prazos e distâncias."""
from feriados import eh_feriado
from ordinal import para_ordinal
from uteis import eh_fim_de_semana, soma_dias_uteis


def dias_entre(inicio, fim):
    """Dias corridos de `inicio` até `fim` (tuplas (ano, mes, dia))."""
    return para_ordinal(*fim) - para_ordinal(*inicio)


def eh_dia_util(ano, mes, dia):
    """True se a data não cai em fim de semana nem feriado fixo."""
    return not eh_fim_de_semana(ano, mes, dia) and not eh_feriado(mes, dia)


def prazo_util(ano, mes, dia, n):
    """Data após n dias úteis, pulando fins de semana e feriados fixos."""
    return soma_dias_uteis(ano, mes, dia, n, eh_feriado)
'''

_TEST = '''\
import pytest
from api import dias_entre, prazo_util
from calendario import dias_no_mes, eh_bissexto, valida_data
from feriados import eh_feriado, feriados_do_mes
from ordinal import de_ordinal, para_ordinal
from uteis import dia_da_semana, eh_fim_de_semana, soma_dias


def test_bissexto_regra_completa():
    assert eh_bissexto(2024)
    assert eh_bissexto(2000)
    assert not eh_bissexto(1900)
    assert not eh_bissexto(2023)


def test_dias_no_mes_fevereiro():
    assert dias_no_mes(2024, 2) == 29
    assert dias_no_mes(2023, 2) == 28


def test_valida_data_rejeita():
    with pytest.raises(ValueError):
        valida_data(2023, 2, 29)


def test_ordinal_base():
    assert para_ordinal(1, 1, 1) == 1
    assert de_ordinal(1) == (1, 1, 1)


def test_ordinal_ida_e_volta():
    assert de_ordinal(para_ordinal(2024, 2, 29)) == (2024, 2, 29)


def test_dia_da_semana_conhecido():
    # 01/01/2024 foi segunda-feira
    assert dia_da_semana(2024, 1, 1) == 0


def test_fim_de_semana_sabado_e_domingo():
    assert eh_fim_de_semana(2024, 1, 6)
    assert eh_fim_de_semana(2024, 1, 7)
    assert not eh_fim_de_semana(2024, 1, 8)


def test_soma_dias_vira_mes():
    assert soma_dias(2024, 1, 31, 1) == (2024, 2, 1)


def test_feriado_independencia():
    assert eh_feriado(9, 7)
    assert feriados_do_mes(11) == [2, 15]


def test_dias_entre():
    assert dias_entre((2024, 1, 1), (2024, 3, 1)) == 60


def test_prazo_util_pula_fim_de_semana():
    # 05/01/2024 foi sexta; 1 dia útil depois é segunda 08/01
    assert prazo_util(2024, 1, 5, 1) == (2024, 1, 8)


def test_prazo_util_pula_feriado():
    # 04/09/2026 foi sexta; segunda 07/09 é feriado, cai em terça 08/09
    assert prazo_util(2026, 9, 4, 1) == (2026, 9, 8)
'''

_PROMPT = (
    "Este repositório implementa um calendário gregoriano do zero, sem\n"
    "datetime: calendario.py trata bissextos e dias por mês, ordinal.py\n"
    "converte data<->ordinal, uteis.py calcula dias da semana e dias\n"
    "úteis, feriados.py lista feriados fixos e api.py compõe prazos e\n"
    "distâncias. Há testes falhando por causa de um bug em um dos\n"
    "arquivos. Use list_files e read_file para explorar o código,\n"
    "run_tests para ver quais testes falham (a suite está em test_app.py),\n"
    "localize o bug e corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "calendario.py": _CALENDARIO,
    "ordinal.py": _ORDINAL,
    "uteis.py": _UTEIS,
    "feriados.py": _FERIADOS,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_datas_v{n}",
        "family": "datas",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "calendario.py", _CALENDARIO_BUG),
    _monta(2, "ordinal.py", _ORDINAL_BUG),
    _monta(3, "uteis.py", _UTEIS_BUG),
    _monta(4, "feriados.py", _FERIADOS_BUG),
]
