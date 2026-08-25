"""Família csvtable do pool mini-SWE (pré-registro 29).

Tabelas CSV-like (separador ';'): parse com validação, filtro por
comparação, ordenação estável e junção interna por coluna comum.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 tabela.py    — validação frouxa (aceita linha com campos extras)
  v2 filtro.py    — operador '>=' se comporta como '>'
  v3 ordenacao.py — flag de ordem invertida (reverse=not decrescente)
  v4 juncao.py    — em colisão de coluna, mantém o valor da esquerda
"""

_TABELA = '''\
"""Parse de tabelas CSV-like: separador ';', primeira linha = cabeçalho.

Cada linha vira um dict coluna -> valor (sempre string; a conversão
numérica é feita sob demanda por como_numero).
"""


def parse_tabela(texto):
    """Converte o texto em (colunas, linhas); ValueError se malformado."""
    brutas = [linha for linha in texto.splitlines() if linha.strip()]
    if not brutas:
        raise ValueError("tabela vazia")
    colunas = [c.strip() for c in brutas[0].split(";")]
    if len(set(colunas)) != len(colunas):
        raise ValueError("colunas duplicadas no cabecalho")
    linhas = []
    for bruta in brutas[1:]:
        valores = [v.strip() for v in bruta.split(";")]
        if len(valores) != len(colunas):
            raise ValueError(
                f"linha com {len(valores)} campos, esperado {len(colunas)}")
        linhas.append(dict(zip(colunas, valores)))
    return colunas, linhas


def como_numero(valor):
    """Converte para int quando possível; senão devolve a própria string."""
    try:
        return int(valor)
    except ValueError:
        return valor


def largura_colunas(colunas, linhas):
    """Largura máxima (em caracteres) de cada coluna, para exibição."""
    larguras = {c: len(c) for c in colunas}
    for linha in linhas:
        for c in colunas:
            larguras[c] = max(larguras[c], len(linha[c]))
    return larguras
'''

_TABELA_BUG = _TABELA.replace(
    "        if len(valores) != len(colunas):\n",
    "        if len(valores) < len(colunas):\n")

_FILTRO = '''\
"""Filtro de linhas por comparação em uma coluna."""
from tabela import como_numero

OPERADORES = ("==", "!=", ">=", "<=", ">", "<")


def compara(a, op, b):
    """Aplica o operador; tipos mistos (int vs str) comparam como string."""
    if isinstance(a, int) != isinstance(b, int):
        a, b = str(a), str(b)
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if op == ">":
        return a > b
    if op == ">=":
        return a >= b
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    raise ValueError(f"operador desconhecido: {op!r}")


def filtra(linhas, coluna, op, alvo):
    """Linhas cujo valor na coluna satisfaz `valor op alvo`."""
    if op not in OPERADORES:
        raise ValueError(f"operador desconhecido: {op!r}")
    alvo_num = como_numero(alvo)
    resultado = []
    for linha in linhas:
        if coluna not in linha:
            raise KeyError(coluna)
        if compara(como_numero(linha[coluna]), op, alvo_num):
            resultado.append(linha)
    return resultado
'''

_FILTRO_BUG = _FILTRO.replace(
    '''    if op == ">=":
        return a >= b
''',
    '''    if op == ">=":
        return a > b
''')

_ORDENACAO = '''\
"""Ordenação estável de linhas por coluna (numérica quando possível)."""
from tabela import como_numero


def chave_ordenacao(valor):
    """Chave que ordena ints antes de strings, cada grupo em ordem natural."""
    numero = como_numero(valor)
    if isinstance(numero, int):
        return (0, numero, "")
    return (1, 0, numero)


def ordena(linhas, coluna, decrescente=False):
    """Nova lista ordenada pela coluna; empates preservam a ordem original."""
    return sorted(
        linhas,
        key=lambda linha: chave_ordenacao(linha[coluna]),
        reverse=decrescente,
    )


def primeiro(linhas, coluna):
    """Linha com o menor valor na coluna; ValueError se lista vazia."""
    if not linhas:
        raise ValueError("nenhuma linha para ordenar")
    return ordena(linhas, coluna)[0]
'''

_ORDENACAO_BUG = _ORDENACAO.replace(
    "        reverse=decrescente,\n",
    "        reverse=not decrescente,\n")

_JUNCAO = '''\
"""Junção interna de duas listas de linhas por coluna comum.

Em colisão de nomes de coluna (fora a chave), o valor da tabela da
DIREITA prevalece. A ordem do resultado segue a tabela da esquerda.
"""


def junta(linhas_a, linhas_b, coluna):
    """Junção interna por igualdade na coluna dada."""
    resultado = []
    for linha_a in linhas_a:
        if coluna not in linha_a:
            raise KeyError(coluna)
        for linha_b in linhas_b:
            if coluna not in linha_b:
                raise KeyError(coluna)
            if linha_a[coluna] != linha_b[coluna]:
                continue
            combinada = dict(linha_a)
            for chave, valor in linha_b.items():
                if chave != coluna:
                    combinada[chave] = valor
            resultado.append(combinada)
    return resultado
'''

_JUNCAO_BUG = _JUNCAO.replace(
    "                if chave != coluna:\n",
    "                if chave not in combinada:\n")

_API = '''\
"""Consulta composta sobre tabelas CSV-like: parse -> filtro -> ordenação."""
from filtro import filtra
from juncao import junta
from ordenacao import ordena
from tabela import parse_tabela


def consulta(texto, coluna=None, op=None, alvo=None,
             ordenar_por=None, decrescente=False):
    """Parse do texto, filtro opcional e ordenação opcional, nessa ordem."""
    _, linhas = parse_tabela(texto)
    if coluna is not None:
        linhas = filtra(linhas, coluna, op, alvo)
    if ordenar_por is not None:
        linhas = ordena(linhas, ordenar_por, decrescente)
    return linhas


def junta_textos(texto_a, texto_b, coluna):
    """Parse das duas tabelas e junção interna pela coluna."""
    _, linhas_a = parse_tabela(texto_a)
    _, linhas_b = parse_tabela(texto_b)
    return junta(linhas_a, linhas_b, coluna)


def projeta(linhas, colunas):
    """Restringe cada linha às colunas pedidas, na ordem dada."""
    return [{c: linha[c] for c in colunas} for linha in linhas]


def como_texto(colunas, linhas):
    """Reconstrói o texto CSV-like (cabeçalho + linhas)."""
    saida = [";".join(colunas)]
    for linha in linhas:
        saida.append(";".join(linha[c] for c in colunas))
    return "\\n".join(saida)
'''

_TEST = '''\
import pytest
from api import consulta, junta_textos
from filtro import filtra
from juncao import junta
from ordenacao import ordena
from tabela import como_numero, parse_tabela

PESSOAS = "nome;idade\\nana;30\\nbia;25\\ncaio;30"
TIMES = "nome;time\\nana;azul\\ncaio;verde"


def test_parse_basico():
    colunas, linhas = parse_tabela(PESSOAS)
    assert colunas == ["nome", "idade"]
    assert linhas[1] == {"nome": "bia", "idade": "25"}


def test_parse_campo_extra_rejeitado():
    with pytest.raises(ValueError):
        parse_tabela("a;b\\n1;2;3")


def test_parse_campo_faltando_rejeitado():
    with pytest.raises(ValueError):
        parse_tabela("a;b\\n1")


def test_como_numero():
    assert como_numero("42") == 42
    assert como_numero("x1") == "x1"


def test_filtra_maior():
    _, linhas = parse_tabela(PESSOAS)
    nomes = [linha["nome"] for linha in filtra(linhas, "idade", ">", "25")]
    assert nomes == ["ana", "caio"]


def test_filtra_maior_igual_inclui_limite():
    _, linhas = parse_tabela(PESSOAS)
    nomes = [linha["nome"] for linha in filtra(linhas, "idade", ">=", "30")]
    assert nomes == ["ana", "caio"]


def test_ordena_crescente_estavel():
    _, linhas = parse_tabela(PESSOAS)
    nomes = [linha["nome"] for linha in ordena(linhas, "idade")]
    assert nomes == ["bia", "ana", "caio"]


def test_ordena_decrescente():
    _, linhas = parse_tabela(PESSOAS)
    nomes = [linha["nome"] for linha in ordena(linhas, "idade", decrescente=True)]
    assert nomes == ["ana", "caio", "bia"]


def test_junta_basica():
    assert junta_textos(PESSOAS, TIMES, "nome") == [
        {"nome": "ana", "idade": "30", "time": "azul"},
        {"nome": "caio", "idade": "30", "time": "verde"},
    ]


def test_junta_direita_prevalece():
    a = [{"id": "1", "nota": "antiga"}]
    b = [{"id": "1", "nota": "nova"}]
    assert junta(a, b, "id") == [{"id": "1", "nota": "nova"}]


def test_consulta_composta():
    linhas = consulta(PESSOAS, "idade", ">=", "30", ordenar_por="nome")
    assert [linha["nome"] for linha in linhas] == ["ana", "caio"]
'''

_PROMPT = (
    "Este repositório implementa consultas sobre tabelas CSV-like\n"
    "(separador ';'): tabela.py faz parse/validação, filtro.py filtra\n"
    "linhas por comparação, ordenacao.py ordena de forma estável,\n"
    "juncao.py faz junção interna por coluna comum e api.py compõe as\n"
    "operações. Há testes falhando por causa de um bug em um dos arquivos.\n"
    "Use list_files e read_file para explorar o código, run_tests para ver\n"
    "quais testes falham (a suite está em test_app.py), localize o bug e\n"
    "corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "tabela.py": _TABELA,
    "filtro.py": _FILTRO,
    "ordenacao.py": _ORDENACAO,
    "juncao.py": _JUNCAO,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_csvtable_v{n}",
        "family": "csvtable",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "tabela.py", _TABELA_BUG),
    _monta(2, "filtro.py", _FILTRO_BUG),
    _monta(3, "ordenacao.py", _ORDENACAO_BUG),
    _monta(4, "juncao.py", _JUNCAO_BUG),
]
