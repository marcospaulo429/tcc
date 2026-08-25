"""Família ledger do pool mini-SWE (pré-registro 28).

Livro-caixa com centavos inteiros: parse/validação de lançamentos,
agregação de saldos por conta, juros simples e extrato formatado.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 saldo.py      — operador trocado (débito soma em vez de subtrair)
  v2 juros.py      — divisor errado (1000 em vez de 10000, juros 10x)
  v3 extrato.py    — centavos sem zero-padding (5 -> '0,5')
  v4 transacoes.py — validação frouxa (aceita valor zero)
"""

_TRANSACOES = '''\
"""Parse e validação de lançamentos do livro-caixa.

Formato de cada linha: conta;tipo;valor_centavos
  - conta: identificador não vazio (ex.: caixa, banco)
  - tipo: "credito" ou "debito"
  - valor_centavos: inteiro estritamente positivo, em centavos

Linhas vazias e comentários iniciados por '#' são ignorados.
"""

TIPOS_VALIDOS = ("credito", "debito")


def parse_lancamento(linha):
    """Converte uma linha em dict {conta, tipo, valor}; ValueError se inválida."""
    partes = linha.strip().split(";")
    if len(partes) != 3:
        raise ValueError(f"formato invalido: {linha!r}")
    conta = partes[0].strip()
    tipo = partes[1].strip()
    bruto = partes[2].strip()
    if not conta:
        raise ValueError("conta vazia")
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    try:
        valor = int(bruto)
    except ValueError:
        raise ValueError(f"valor nao inteiro: {bruto!r}") from None
    if valor <= 0:
        raise ValueError(f"valor deve ser positivo: {valor}")
    return {"conta": conta, "tipo": tipo, "valor": valor}


def parse_lancamentos(texto):
    """Converte texto multilinha em lista de lançamentos."""
    lancamentos = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#"):
            continue
        lancamentos.append(parse_lancamento(limpa))
    return lancamentos
'''

_TRANSACOES_BUG = _TRANSACOES.replace(
    "    if valor <= 0:\n",
    "    if valor < 0:\n")

_SALDO = '''\
"""Agregação de saldos por conta, sempre em centavos inteiros."""


def saldo_conta(lancamentos, conta):
    """Saldo de uma conta: créditos somam, débitos subtraem."""
    total = 0
    for lanc in lancamentos:
        if lanc["conta"] != conta:
            continue
        if lanc["tipo"] == "credito":
            total += lanc["valor"]
        else:
            total -= lanc["valor"]
    return total


def contas_conhecidas(lancamentos):
    """Contas na ordem da primeira aparição (determinística)."""
    contas = []
    for lanc in lancamentos:
        if lanc["conta"] not in contas:
            contas.append(lanc["conta"])
    return contas


def saldos_por_conta(lancamentos):
    """Dict conta -> saldo em centavos, na ordem de primeira aparição."""
    return {conta: saldo_conta(lancamentos, conta)
            for conta in contas_conhecidas(lancamentos)}


def contas_negativas(saldos):
    """Contas com saldo negativo, em ordem alfabética."""
    return sorted(conta for conta, saldo in saldos.items() if saldo < 0)


def total_geral(lancamentos):
    """Soma dos saldos de todas as contas."""
    return sum(saldos_por_conta(lancamentos).values())
'''

_SALDO_BUG = _SALDO.replace(
    '''        else:
            total -= lanc["valor"]
''',
    '''        else:
            total += lanc["valor"]
''')

_JUROS = '''\
"""Juros simples sobre valores em centavos inteiros.

A taxa é expressa em basis points mensais (1 bps = 0,01% ao mês),
portanto o fator do período é taxa_bps * meses / 10000. O resultado
é truncado para baixo (divisão inteira), garantindo que todos os
valores permaneçam centavos inteiros — nunca float.
"""


def juros_simples(principal, taxa_bps, meses):
    """Juros simples: principal * taxa_bps * meses // 10000."""
    if principal < 0 or taxa_bps < 0 or meses < 0:
        raise ValueError("parametros devem ser nao-negativos")
    return (principal * taxa_bps * meses) // 10000


def montante(principal, taxa_bps, meses):
    """Principal acrescido dos juros simples do período."""
    return principal + juros_simples(principal, taxa_bps, meses)
'''

_JUROS_BUG = _JUROS.replace(
    "    return (principal * taxa_bps * meses) // 10000\n",
    "    return (principal * taxa_bps * meses) // 1000\n")

_EXTRATO = '''\
"""Formatação de extrato em texto puro e determinístico."""


def formata_centavos(valor):
    """Formata centavos com vírgula decimal: 1234 -> '12,34', 5 -> '0,05'."""
    sinal = "-" if valor < 0 else ""
    absoluto = abs(valor)
    reais = absoluto // 100
    centavos = absoluto % 100
    return f"{sinal}{reais},{centavos:02d}"


def linha_conta(conta, saldo):
    """Linha do extrato para uma conta."""
    return f"{conta}: R$ {formata_centavos(saldo)}"


def gera_extrato(saldos):
    """Relatório com uma linha por conta (ordem alfabética) e o total."""
    linhas = ["EXTRATO"]
    for conta in sorted(saldos):
        linhas.append(linha_conta(conta, saldos[conta]))
    total = sum(saldos.values())
    linhas.append(f"TOTAL: R$ {formata_centavos(total)}")
    return "\\n".join(linhas)
'''

_EXTRATO_BUG = _EXTRATO.replace(
    '    return f"{sinal}{reais},{centavos:02d}"\n',
    '    return f"{sinal}{reais},{centavos}"\n')

_API = '''\
"""API de alto nível do livro-caixa.

Recebe o texto bruto de lançamentos (uma linha por lançamento) e
expõe as operações compostas: saldos, extrato e projeção com juros.
"""
from extrato import gera_extrato
from juros import montante
from saldo import saldos_por_conta
from transacoes import parse_lancamentos


def processa(texto):
    """Parse do texto de lançamentos e retorna saldos por conta."""
    return saldos_por_conta(parse_lancamentos(texto))


def relatorio(texto):
    """Extrato formatado a partir do texto de lançamentos."""
    return gera_extrato(processa(texto))


def projeta_saldo(texto, conta, taxa_bps, meses):
    """Saldo futuro de uma conta com juros simples sobre o saldo atual."""
    saldos = processa(texto)
    if conta not in saldos:
        raise KeyError(conta)
    return montante(saldos[conta], taxa_bps, meses)
'''

_TEST = '''\
import pytest
from api import processa, projeta_saldo, relatorio
from extrato import formata_centavos, gera_extrato
from juros import juros_simples, montante
from saldo import saldo_conta, saldos_por_conta
from transacoes import parse_lancamento, parse_lancamentos


def test_parse_lancamento_valido():
    esperado = {"conta": "caixa", "tipo": "credito", "valor": 1500}
    assert parse_lancamento("caixa;credito;1500") == esperado


def test_parse_valor_zero_rejeitado():
    with pytest.raises(ValueError):
        parse_lancamento("caixa;credito;0")


def test_parse_tipo_invalido():
    with pytest.raises(ValueError):
        parse_lancamento("caixa;deposito;100")


def test_saldo_credito_debito():
    lancs = parse_lancamentos("caixa;credito;1000\\ncaixa;debito;300")
    assert saldo_conta(lancs, "caixa") == 700


def test_saldos_por_conta():
    lancs = parse_lancamentos("a;credito;100\\nb;credito;200\\na;debito;50")
    assert saldos_por_conta(lancs) == {"a": 50, "b": 200}


def test_juros_simples_basico():
    # 10000 centavos a 100 bps (1% a.m.) por 3 meses = 300 centavos
    assert juros_simples(10000, 100, 3) == 300


def test_montante():
    assert montante(10000, 100, 3) == 10300


def test_formata_centavos_padding():
    assert formata_centavos(5) == "0,05"
    assert formata_centavos(1234) == "12,34"
    assert formata_centavos(-70) == "-0,70"


def test_relatorio_completo():
    texto = "caixa;credito;1000\\nbanco;credito;250\\ncaixa;debito;300"
    esperado = "EXTRATO\\nbanco: R$ 2,50\\ncaixa: R$ 7,00\\nTOTAL: R$ 9,50"
    assert relatorio(texto) == esperado


def test_projeta_saldo():
    texto = "caixa;credito;10000"
    assert projeta_saldo(texto, "caixa", 200, 6) == 11200
'''

_PROMPT = (
    "Este repositório implementa um livro-caixa em centavos inteiros:\n"
    "transacoes.py faz parse/validação de lançamentos, saldo.py agrega\n"
    "saldos por conta, juros.py calcula juros simples, extrato.py formata o\n"
    "relatório e api.py expõe as operações compostas. Há testes falhando por\n"
    "causa de um bug em um dos arquivos. Use list_files e read_file para\n"
    "explorar o código, run_tests para ver quais testes falham (a suite está\n"
    "em test_app.py), localize o bug e corrija reescrevendo o arquivo\n"
    "INTEIRO com write_file."
)

_BASE = {
    "transacoes.py": _TRANSACOES,
    "saldo.py": _SALDO,
    "juros.py": _JUROS,
    "extrato.py": _EXTRATO,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_ledger_v{n}",
        "family": "ledger",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "saldo.py", _SALDO_BUG),
    _monta(2, "juros.py", _JUROS_BUG),
    _monta(3, "extrato.py", _EXTRATO_BUG),
    _monta(4, "transacoes.py", _TRANSACOES_BUG),
]
