"""Família planilha do pool mini-SWE (pré-registro 29).

Planilha em memória: células com números ou fórmulas '=A1+B2-3',
recálculo automático em ordem de dependências e detecção de ciclo.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 formulas.py     — subtração soma em vez de subtrair (operador)
  v2 celulas.py      — regex só aceita 'A1'..'Z9' (constante errada)
  v3 dependencias.py — ordem topológica devolvida invertida
  v4 planilha.py     — definir() não recalcula a planilha (chamada omitida)
"""

_CELULAS = '''\
"""Endereços de célula (coluna em letras + linha em números)."""
import re

RE_ENDERECO = re.compile(r"^[A-Z]+[1-9][0-9]*$")


def e_endereco(texto):
    """True se o texto é um endereço válido como 'A1' ou 'BC12'."""
    return isinstance(texto, str) and RE_ENDERECO.match(texto) is not None


def valida_endereco(texto):
    """ValueError se o endereço não é válido."""
    if not e_endereco(texto):
        raise ValueError(f"endereco invalido: {texto!r}")


def e_formula(conteudo):
    """True se o conteúdo da célula é uma fórmula (começa com '=')."""
    return isinstance(conteudo, str) and conteudo.startswith("=")


def e_numero(conteudo):
    """True se o conteúdo representa um número inteiro literal."""
    if isinstance(conteudo, int):
        return True
    return isinstance(conteudo, str) and conteudo.lstrip("-").isdigit()
'''

_CELULAS_BUG = _CELULAS.replace(
    'RE_ENDERECO = re.compile(r"^[A-Z]+[1-9][0-9]*$")\n',
    'RE_ENDERECO = re.compile(r"^[A-Z][1-9]$")\n')

_FORMULAS = '''\
"""Fórmulas de célula: '=A1+B2-3', somas e subtrações de termos.

Um termo é uma referência de célula ou um inteiro literal.
"""
from celulas import e_endereco


def termos(formula):
    """Lista de (sinal, termo) da fórmula, na ordem em que aparecem."""
    corpo = formula[1:].replace(" ", "")
    if not corpo:
        raise ValueError(f"formula vazia: {formula!r}")
    resultado = []
    sinal = "+"
    atual = ""
    for caractere in corpo:
        if caractere in "+-":
            if not atual:
                raise ValueError(f"formula malformada: {formula!r}")
            resultado.append((sinal, atual))
            sinal = caractere
            atual = ""
        else:
            atual += caractere
    if not atual:
        raise ValueError(f"formula malformada: {formula!r}")
    resultado.append((sinal, atual))
    return resultado


def referencias(formula):
    """Endereços de célula citados pela fórmula, na ordem."""
    return [termo for _, termo in termos(formula) if e_endereco(termo)]


def avalia(formula, valores):
    """Valor numérico da fórmula; referência sem valor conta como 0."""
    total = 0
    for sinal, termo in termos(formula):
        if e_endereco(termo):
            numero = valores.get(termo, 0)
        elif termo.isdigit():
            numero = int(termo)
        else:
            raise ValueError(f"termo invalido: {termo!r}")
        if sinal == "+":
            total += numero
        else:
            total -= numero
    return total
'''

_FORMULAS_BUG = _FORMULAS.replace(
    "        else:\n            total -= numero\n",
    "        else:\n            total += numero\n")

_DEPENDENCIAS = '''\
"""Ordem de recálculo por ordenação topológica determinística."""


def ordem_recalculo(grafo):
    """Ordena endereços com dependências antes dos dependentes.

    grafo: endereco -> lista de endereços referenciados. Referências a
    células fora do grafo são ignoradas. Empates são resolvidos por
    ordem alfabética. ValueError se existe ciclo.
    """
    nos = sorted(grafo)
    graus = {no: 0 for no in nos}
    dependentes = {no: [] for no in nos}
    for no in nos:
        for ref in grafo[no]:
            if ref in graus:
                graus[no] += 1
                dependentes[ref].append(no)
    prontos = sorted(no for no in nos if graus[no] == 0)
    ordem = []
    while prontos:
        no = prontos.pop(0)
        ordem.append(no)
        liberados = []
        for dep in dependentes[no]:
            graus[dep] -= 1
            if graus[dep] == 0:
                liberados.append(dep)
        prontos = sorted(prontos + liberados)
    if len(ordem) != len(nos):
        raise ValueError("ciclo de dependencias entre celulas")
    return ordem


def tem_ciclo(grafo):
    """True se o grafo contém ciclo de dependências."""
    try:
        ordem_recalculo(grafo)
    except ValueError:
        return True
    return False
'''

_DEPENDENCIAS_BUG = _DEPENDENCIAS.replace(
    '        raise ValueError("ciclo de dependencias entre celulas")\n    return ordem\n',
    '        raise ValueError("ciclo de dependencias entre celulas")\n'
    '    return list(reversed(ordem))\n')

_PLANILHA = '''\
"""Planilha em memória: números ou fórmulas, recálculo automático."""
from celulas import e_formula, e_numero, valida_endereco
from dependencias import ordem_recalculo
from formulas import avalia, referencias


class Planilha:
    """Guarda conteúdo e valores calculados de cada célula."""

    def __init__(self):
        self._conteudo = {}
        self._valores = {}

    def definir(self, endereco, conteudo):
        """Define número ou fórmula na célula e recalcula a planilha."""
        valida_endereco(endereco)
        if not e_formula(conteudo) and not e_numero(conteudo):
            raise ValueError(f"conteudo invalido: {conteudo!r}")
        self._conteudo[endereco] = conteudo
        self.recalcular()

    def valor(self, endereco):
        """Valor calculado da célula, ou None se não definida."""
        return self._valores.get(endereco)

    def recalcular(self):
        """Recalcula todas as células em ordem de dependências."""
        grafo = {}
        for endereco, conteudo in self._conteudo.items():
            if e_formula(conteudo):
                grafo[endereco] = referencias(conteudo)
            else:
                grafo[endereco] = []
        ordem = ordem_recalculo(grafo)
        self._valores = {}
        for endereco in ordem:
            conteudo = self._conteudo[endereco]
            if e_formula(conteudo):
                self._valores[endereco] = avalia(conteudo, self._valores)
            else:
                self._valores[endereco] = int(conteudo)

    def enderecos(self):
        """Endereços definidos, em ordem alfabética."""
        return sorted(self._conteudo)

    def valores(self):
        """Dicionário endereço -> valor calculado, em ordem alfabética."""
        return {e: self._valores.get(e) for e in self.enderecos()}
'''

_PLANILHA_BUG = _PLANILHA.replace(
    "        self._conteudo[endereco] = conteudo\n        self.recalcular()\n",
    "        self._conteudo[endereco] = conteudo\n")

_TEST = '''\
import pytest
from celulas import e_endereco, e_formula, valida_endereco
from dependencias import ordem_recalculo, tem_ciclo
from formulas import avalia, referencias, termos
from planilha import Planilha


def test_enderecos_validos():
    assert e_endereco("A1") is True
    assert e_endereco("A10") is True
    assert e_endereco("BC12") is True
    assert e_endereco("a1") is False
    assert e_endereco("1A") is False
    assert e_endereco("A0") is False
    with pytest.raises(ValueError):
        valida_endereco("Z 9")


def test_termos_e_referencias():
    assert termos("=A1+B2-3") == [("+", "A1"), ("+", "B2"), ("-", "3")]
    assert referencias("=A1+B2-3") == ["A1", "B2"]
    assert e_formula("=A1") is True
    assert e_formula("A1") is False


def test_formula_malformada():
    with pytest.raises(ValueError):
        termos("=A1++B2")
    with pytest.raises(ValueError):
        termos("=")


def test_avalia_soma_e_subtracao():
    valores = {"A1": 10, "B1": 4}
    assert avalia("=A1-B1", valores) == 6
    assert avalia("=A1+B1-2", valores) == 12
    assert avalia("=5-A1", valores) == -5


def test_avalia_referencia_ausente_vale_zero():
    assert avalia("=A9+5", {}) == 5


def test_ordem_recalculo_cadeia():
    grafo = {"C1": ["B1"], "B1": ["A1"], "A1": []}
    assert ordem_recalculo(grafo) == ["A1", "B1", "C1"]


def test_ciclo_detectado():
    assert tem_ciclo({"A1": ["B1"], "B1": ["A1"]}) is True
    assert tem_ciclo({"A1": [], "B1": ["A1"]}) is False
    with pytest.raises(ValueError):
        ordem_recalculo({"A1": ["A1"]})


def test_planilha_literais_e_formula():
    pl = Planilha()
    pl.definir("A1", "2")
    pl.definir("B1", "=A1+3")
    assert pl.valor("A1") == 2
    assert pl.valor("B1") == 5


def test_planilha_cadeia_e_atualizacao():
    pl = Planilha()
    pl.definir("A1", 2)
    pl.definir("B1", "=A1+3")
    pl.definir("C1", "=B1+A1")
    assert pl.valor("C1") == 7
    pl.definir("A1", 10)
    assert pl.valor("B1") == 13
    assert pl.valor("C1") == 23


def test_planilha_ciclo_levanta():
    pl = Planilha()
    pl.definir("A1", "=B1+1")
    assert pl.valor("A1") == 1
    with pytest.raises(ValueError):
        pl.definir("B1", "=A1+1")
'''

_PROMPT = (
    "Este repositório implementa uma planilha em memória com fórmulas:\n"
    "celulas.py valida endereços e classifica conteúdo, formulas.py\n"
    "interpreta e avalia '=A1+B2-3', dependencias.py calcula a ordem de\n"
    "recálculo (topológica, com detecção de ciclo) e planilha.py guarda\n"
    "as células e recalcula tudo a cada definição. Há testes falhando\n"
    "por causa de um bug em um dos arquivos. Use list_files e read_file\n"
    "para explorar o código, run_tests para ver quais testes falham (a\n"
    "suite está em test_app.py), localize o bug e corrija reescrevendo o\n"
    "arquivo INTEIRO com write_file."
)

_BASE = {
    "celulas.py": _CELULAS,
    "formulas.py": _FORMULAS,
    "dependencias.py": _DEPENDENCIAS,
    "planilha.py": _PLANILHA,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_planilha_v{n}",
        "family": "planilha",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "formulas.py", _FORMULAS_BUG),
    _monta(2, "celulas.py", _CELULAS_BUG),
    _monta(3, "dependencias.py", _DEPENDENCIAS_BUG),
    _monta(4, "planilha.py", _PLANILHA_BUG),
]
