"""Família expressoes do pool mini-SWE (pré-registro 29).

Avaliador de expressões aritméticas inteiras: tokenizador, parser
descendente recursivo com precedência e avaliação com divisão truncada.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 tokens.py    — constante errada (operador '%' sumiu do tokenizador)
  v2 sintaxe.py   — operandos trocados (subtração deixa de associar à esquerda)
  v3 avaliador.py — condição errada (sinal do quociente errado em sinais mistos)
  v4 api.py       — teste enfraquecido (linha só de espaços não é ignorada)
"""

_TOKENS = '''\
"""Tokenizador de expressões aritméticas inteiras.

Tokens: ('num', inteiro), ('op', caractere) e ('pont', parêntese).
Espaços são ignorados; qualquer outro caractere é erro.
"""

OPERADORES = "+-*/%"
PONTUACAO = "()"


def tokeniza(texto):
    """Lista de tokens da expressão; ValueError em caractere inesperado."""
    tokens = []
    i = 0
    while i < len(texto):
        caractere = texto[i]
        if caractere == " ":
            i += 1
            continue
        if caractere.isdigit():
            fim = i
            while fim < len(texto) and texto[fim].isdigit():
                fim += 1
            tokens.append(("num", int(texto[i:fim])))
            i = fim
            continue
        if caractere in OPERADORES:
            tokens.append(("op", caractere))
            i += 1
            continue
        if caractere in PONTUACAO:
            tokens.append(("pont", caractere))
            i += 1
            continue
        raise ValueError(f"caractere inesperado: {caractere!r}")
    return tokens
'''

_TOKENS_BUG = _TOKENS.replace(
    'OPERADORES = "+-*/%"\n',
    'OPERADORES = "+-*/"\n')

_ARVORE = '''\
"""Nós da árvore sintática: ('num', n) e ('bin', op, esquerda, direita)."""


def numero(n):
    """Nó folha com valor inteiro."""
    return ("num", n)


def binario(op, esquerda, direita):
    """Nó de operação binária."""
    return ("bin", op, esquerda, direita)


def conta_nos(no):
    """Total de nós da árvore (folhas + operações)."""
    if no[0] == "num":
        return 1
    return 1 + conta_nos(no[2]) + conta_nos(no[3])
'''

_SINTAXE = '''\
"""Parser descendente recursivo com precedência usual.

Gramática (todos os operadores associam à ESQUERDA):
    expressao := termo (('+' | '-') termo)*
    termo     := fator (('*' | '/' | '%') fator)*
    fator     := NUMERO | '(' expressao ')'
"""
from arvore import binario, numero
from tokens import tokeniza


class Parser:
    """Consome a lista de tokens produzindo a árvore sintática."""

    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def _atual(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return (None, None)

    def _consome(self):
        token = self._atual()
        self._pos += 1
        return token

    def terminou(self):
        """True se todos os tokens foram consumidos."""
        return self._pos >= len(self._tokens)

    def expressao(self):
        """expressao := termo (('+' | '-') termo)*"""
        no = self.termo()
        while self._atual()[0] == "op" and self._atual()[1] in "+-":
            _, op = self._consome()
            no = binario(op, no, self.termo())
        return no

    def termo(self):
        """termo := fator (('*' | '/' | '%') fator)*"""
        no = self.fator()
        while self._atual()[0] == "op" and self._atual()[1] in "*/%":
            _, op = self._consome()
            no = binario(op, no, self.fator())
        return no

    def fator(self):
        """fator := NUMERO | '(' expressao ')'"""
        tipo, valor = self._consome()
        if tipo == "num":
            return numero(valor)
        if (tipo, valor) == ("pont", "("):
            no = self.expressao()
            if self._consome() != ("pont", ")"):
                raise ValueError("esperado ')'")
            return no
        raise ValueError(f"token inesperado: {(tipo, valor)!r}")


def analisa(texto):
    """Árvore sintática da expressão; ValueError se malformada."""
    parser = Parser(tokeniza(texto))
    no = parser.expressao()
    if not parser.terminou():
        raise ValueError("tokens sobrando apos a expressao")
    return no
'''

_SINTAXE_BUG = _SINTAXE.replace(
    "            no = binario(op, no, self.termo())\n",
    "            no = binario(op, self.termo(), no)\n")

_AVALIADOR = '''\
"""Avaliação da árvore com aritmética inteira.

A divisão trunca em direção a zero (como em C), diferente do // de
Python para operandos negativos. O resto segue a identidade
a == (a/b)*b + a%b com essa divisão truncada.
"""


def divide_truncando(a, b):
    """Quociente inteiro truncado em direção a zero; erro se b == 0."""
    if b == 0:
        raise ZeroDivisionError("divisao por zero")
    quociente = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        quociente = -quociente
    return quociente


def resto_truncando(a, b):
    """Resto coerente com a divisão truncada: a - (a/b)*b."""
    return a - divide_truncando(a, b) * b


def avalia(no):
    """Valor inteiro da árvore sintática."""
    if no[0] == "num":
        return no[1]
    _, op, esquerda, direita = no
    a = avalia(esquerda)
    b = avalia(direita)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return divide_truncando(a, b)
    if op == "%":
        return resto_truncando(a, b)
    raise ValueError(f"operador desconhecido: {op!r}")
'''

_AVALIADOR_BUG = _AVALIADOR.replace(
    "    if (a < 0) != (b < 0):\n",
    "    if (a < 0) and (b < 0):\n")

_API = '''\
"""Interface de alto nível: calcula(texto) -> inteiro."""
from avaliador import avalia
from sintaxe import analisa


def calcula(texto):
    """Avalia a expressão aritmética inteira contida no texto."""
    if not texto.strip():
        raise ValueError("expressao vazia")
    return avalia(analisa(texto))


def calcula_varias(linhas):
    """Avalia cada linha não vazia (ignora linhas em branco)."""
    resultados = []
    for linha in linhas.splitlines():
        if linha.strip():
            resultados.append(calcula(linha))
    return resultados
'''

_API_BUG = _API.replace(
    "        if linha.strip():\n",
    "        if linha:\n")

_TEST = '''\
import pytest
from api import calcula, calcula_varias
from arvore import conta_nos
from avaliador import divide_truncando
from sintaxe import analisa
from tokens import tokeniza


def test_tokeniza_numero_longo():
    assert tokeniza("12+345") == [("num", 12), ("op", "+"), ("num", 345)]


def test_tokeniza_modulo():
    assert tokeniza("10%3") == [("num", 10), ("op", "%"), ("num", 3)]


def test_caractere_invalido():
    with pytest.raises(ValueError):
        tokeniza("2^3")


def test_soma_e_precedencia():
    assert calcula("2+3*4") == 14


def test_parenteses():
    assert calcula("(2+3)*4") == 20


def test_subtracao_associa_a_esquerda():
    assert calcula("10-2-3") == 5
    assert calcula("10-4") == 6


def test_divisao_trunca_positivos():
    assert calcula("7/2") == 3


def test_divisao_trunca_negativos():
    assert calcula("(0-7)/2") == -3
    assert divide_truncando(-7, 2) == -3


def test_modulo():
    assert calcula("10%3") == 1


def test_calcula_varias_ignora_em_branco():
    assert calcula_varias("1+1\\n \\n2*3") == [2, 6]


def test_erro_sintaxe():
    with pytest.raises(ValueError):
        calcula("2+")
    with pytest.raises(ValueError):
        calcula("2 3")


def test_conta_nos():
    assert conta_nos(analisa("2+3*4")) == 5
'''

_PROMPT = (
    "Este repositório implementa um avaliador de expressões aritméticas\n"
    "inteiras: tokens.py tokeniza o texto, arvore.py define os nós da\n"
    "árvore sintática, sintaxe.py é o parser descendente recursivo com\n"
    "precedência, avaliador.py avalia a árvore (divisão trunca em direção\n"
    "a zero) e api.py expõe calcula(texto). Há testes falhando por causa\n"
    "de um bug em um dos arquivos. Use list_files e read_file para\n"
    "explorar o código, run_tests para ver quais testes falham (a suite\n"
    "está em test_app.py), localize o bug e corrija reescrevendo o\n"
    "arquivo INTEIRO com write_file."
)

_BASE = {
    "tokens.py": _TOKENS,
    "arvore.py": _ARVORE,
    "sintaxe.py": _SINTAXE,
    "avaliador.py": _AVALIADOR,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_expressoes_v{n}",
        "family": "expressoes",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "tokens.py", _TOKENS_BUG),
    _monta(2, "sintaxe.py", _SINTAXE_BUG),
    _monta(3, "avaliador.py", _AVALIADOR_BUG),
    _monta(4, "api.py", _API_BUG),
]
