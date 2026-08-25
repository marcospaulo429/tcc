"""Família mini-SWE "text_pipeline" (pré-registro 28, piloto V2).

Pipeline de processamento de texto multi-arquivo; 4 variantes, cada uma
com UM bug injetado em um arquivo distinto do repositório base.
"""

_TOKENIZA = '''"""Tokenizador por regras simples (stdlib puro).

Cada token e obtido separando o texto por espacos, removendo pontuacao
das bordas e convertendo para minusculas.
"""

PONTUACAO = ".,;:!?()[]{}\\"'`~<>|/\\\\"


def tokeniza(texto: str) -> list[str]:
    """Divide o texto em tokens minusculos, sem pontuacao nas bordas."""
    tokens = []
    for bruto in texto.split():
        token = bruto.strip(PONTUACAO)
        token = token.lower()
        if token:
            tokens.append(token)
    return tokens


def tokeniza_linhas(linhas: list[str]) -> list[str]:
    """Tokeniza uma lista de linhas, preservando a ordem."""
    tokens = []
    for linha in linhas:
        tokens.extend(tokeniza(linha))
    return tokens


def eh_numero(token: str) -> bool:
    """True se o token e composto apenas por digitos."""
    return token.isdigit()


def separa_numeros(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Separa tokens em (palavras, numeros), preservando a ordem."""
    palavras: list[str] = []
    numeros: list[str] = []
    for token in tokens:
        if eh_numero(token):
            numeros.append(token)
        else:
            palavras.append(token)
    return palavras, numeros
'''

_FILTROS = '''"""Filtros de tokens: stopwords, tamanho minimo e normalizacao de acentos."""

STOPWORDS = frozenset({
    "a", "o", "as", "os", "de", "do", "da", "dos", "das",
    "e", "em", "um", "uma", "uns", "umas",
    "que", "para", "com", "no", "na", "nos", "nas", "por", "se",
})

MIN_TAMANHO = 2

_MAPA_ACENTOS = {
    "\\u00e1": "a", "\\u00e0": "a", "\\u00e3": "a", "\\u00e2": "a",
    "\\u00e9": "e", "\\u00ea": "e",
    "\\u00ed": "i",
    "\\u00f3": "o", "\\u00f4": "o", "\\u00f5": "o",
    "\\u00fa": "u", "\\u00fc": "u",
    "\\u00e7": "c",
}


def remove_stopwords(tokens: list[str], stopwords=None) -> list[str]:
    """Remove tokens presentes no conjunto de stopwords."""
    ativas = STOPWORDS if stopwords is None else stopwords
    return [t for t in tokens if t not in ativas]


def filtra_curtas(tokens: list[str], minimo: int = MIN_TAMANHO) -> list[str]:
    """Mantem apenas tokens com tamanho maior ou igual a minimo."""
    return [t for t in tokens if len(t) >= minimo]


def normaliza_acentos(token: str) -> str:
    """Substitui vogais acentuadas e cedilha por equivalentes ASCII."""
    return "".join(_MAPA_ACENTOS.get(ch, ch) for ch in token)


def normaliza_tudo(tokens: list[str]) -> list[str]:
    """Aplica normalizacao de acentos a todos os tokens."""
    return [normaliza_acentos(t) for t in tokens]
'''

_CONTAGEM = '''"""Contagem de frequencias e top-k com desempate deterministico."""


def conta(tokens: list[str]) -> dict[str, int]:
    """Frequencia absoluta de cada token, em ordem de primeira ocorrencia."""
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq


def top_k(freq: dict[str, int], k: int) -> list[tuple[str, int]]:
    """Top-k por frequencia decrescente; empate resolvido em ordem alfabetica."""
    itens = sorted(freq.items(), key=lambda par: (-par[1], par[0]))
    return itens[:k]


def total_tokens(freq: dict[str, int]) -> int:
    """Soma de todas as frequencias."""
    return sum(freq.values())


def vocabulario(freq: dict[str, int]) -> list[str]:
    """Palavras distintas em ordem alfabetica."""
    return sorted(freq)


def conta_bigramas(tokens: list[str]) -> dict[tuple[str, str], int]:
    """Frequencia de pares consecutivos de tokens."""
    freq: dict[tuple[str, str], int] = {}
    for i in range(len(tokens) - 1):
        par = (tokens[i], tokens[i + 1])
        freq[par] = freq.get(par, 0) + 1
    return freq


def percentual_inteiro(freq: dict[str, int]) -> dict[str, int]:
    """Percentual (inteiro, truncado) de cada token sobre o total."""
    total = total_tokens(freq)
    if total == 0:
        return {}
    return {t: (100 * n) // total for t, n in sorted(freq.items())}
'''

_FORMATA = '''"""Formatacao de relatorios em texto puro (linhas no formato "palavra: n")."""

SEPARADOR = ": "


def linha_item(palavra: str, n: int) -> str:
    """Formata um item do relatorio como "palavra: n"."""
    return palavra + SEPARADOR + str(n)


def formata_top(itens: list[tuple[str, int]]) -> list[str]:
    """Formata a lista de itens do top-k, uma linha por item."""
    return [linha_item(palavra, n) for palavra, n in itens]


def cabecalho(titulo: str, total: int, vocab: int) -> list[str]:
    """Duas linhas de cabecalho do relatorio."""
    return [f"== {titulo} ==", f"total={total} vocab={vocab}"]


def relatorio(titulo: str, freq: dict[str, int],
              itens_top: list[tuple[str, int]]) -> str:
    """Relatorio completo: cabecalho seguido dos itens do top-k."""
    total = sum(freq.values())
    linhas = cabecalho(titulo, total, len(freq))
    linhas.extend(formata_top(itens_top))
    return "\\n".join(linhas)
'''

_API = '''"""Pipeline completo: texto bruto -> relatorio de frequencias."""
from contagem import conta, top_k
from filtros import filtra_curtas, normaliza_tudo, remove_stopwords
from formata import relatorio
from tokeniza import tokeniza


def _pipeline_tokens(texto: str) -> list[str]:
    """Tokeniza, normaliza acentos, remove stopwords e filtra curtas."""
    tokens = tokeniza(texto)
    tokens = normaliza_tudo(tokens)
    tokens = remove_stopwords(tokens)
    tokens = filtra_curtas(tokens)
    return tokens


def frequencias(texto: str) -> dict[str, int]:
    """Frequencias dos tokens apos o pipeline completo de filtros."""
    return conta(_pipeline_tokens(texto))


def processa(texto: str, k: int = 3, titulo: str = "RELATORIO") -> str:
    """Executa o pipeline e devolve o relatorio com o top-k."""
    freq = frequencias(texto)
    itens = top_k(freq, k)
    return relatorio(titulo, freq, itens)
'''

_TESTS = '''"""Suite de testes do pipeline de texto (test_app.py)."""
from api import frequencias, processa
from contagem import conta, top_k
from filtros import filtra_curtas, normaliza_acentos, remove_stopwords
from formata import linha_item
from tokeniza import separa_numeros, tokeniza


def test_tokeniza_basico():
    assert tokeniza("Ola, mundo!") == ["ola", "mundo"]


def test_tokeniza_converte_para_minusculas():
    assert tokeniza("BANANA banana; (Banana)") == ["banana", "banana", "banana"]


def test_separa_numeros():
    assert separa_numeros(["abc", "12", "x9", "7"]) == (["abc", "x9"], ["12", "7"])


def test_remove_stopwords():
    assert remove_stopwords(["a", "casa", "de", "papel"]) == ["casa", "papel"]


def test_filtra_curtas_mantem_tamanho_igual_ao_minimo():
    assert filtra_curtas(["ab", "c", "abc"], minimo=2) == ["ab", "abc"]


def test_normaliza_acentos():
    assert normaliza_acentos("cora\\u00e7\\u00e3o") == "coracao"


def test_conta():
    assert conta(["x", "y", "x"]) == {"x": 2, "y": 1}


def test_top_k_ordena_por_frequencia_decrescente():
    freq = {"raro": 1, "comum": 3, "medio": 2}
    assert top_k(freq, 2) == [("comum", 3), ("medio", 2)]


def test_top_k_desempata_em_ordem_alfabetica():
    freq = {"beta": 2, "alfa": 2, "gama": 1}
    assert top_k(freq, 2) == [("alfa", 2), ("beta", 2)]


def test_linha_item_usa_dois_pontos():
    assert linha_item("casa", 3) == "casa: 3"


def test_frequencias_fim_a_fim():
    assert frequencias("O peixe \\u00e9 um peixe") == {"peixe": 2}


def test_processa_fim_a_fim():
    texto = "A casa azul e a casa verde; casa AZUL!"
    esperado = "== RELATORIO ==\\ntotal=6 vocab=3\\ncasa: 3\\nazul: 2"
    assert processa(texto, k=2) == esperado
'''

_BASE = {
    "tokeniza.py": _TOKENIZA,
    "filtros.py": _FILTROS,
    "contagem.py": _CONTAGEM,
    "formata.py": _FORMATA,
    "api.py": _API,
}

_PROMPT = (
    "Este repositorio implementa um pipeline de processamento de texto: "
    "tokenizacao por regras (tokeniza.py), filtros de stopwords e normalizacao "
    "(filtros.py), contagem de frequencias com top-k deterministico (contagem.py), "
    "formatacao de relatorio (formata.py) e a API do pipeline completo (api.py).\n"
    "A suite de testes esta falhando: existe exatamente UM bug em UM dos arquivos.\n"
    "O arquivo test_app.py contem a suite de testes usada na avaliacao.\n"
    "Use list_files e read_file para explorar o codigo e run_tests para ver "
    "quais testes falham.\n"
    "Localize o bug e corrija-o reescrevendo o arquivo INTEIRO com write_file. "
    "Nao modifique test_app.py."
)


def _com_bug(fonte: str, antigo: str, novo: str) -> str:
    assert antigo in fonte, f"trecho nao encontrado: {antigo!r}"
    return fonte.replace(antigo, novo, 1)


def _task(n: int, bug_file: str, conteudo_bugado: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = conteudo_bugado
    repo["test_app.py"] = _TESTS
    return {
        "task_id": f"swe_text_pipeline_v{n}",
        "family": "text_pipeline",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TESTS,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    # v1: tokenizador esquece de converter para minusculas (linha omitida)
    _task(1, "tokeniza.py", _com_bug(
        _TOKENIZA,
        "        token = bruto.strip(PONTUACAO)\n        token = token.lower()\n",
        "        token = bruto.strip(PONTUACAO)\n",
    )),
    # v2: top_k ordena por frequencia CRESCENTE (sinal do criterio trocado)
    _task(2, "contagem.py", _com_bug(
        _CONTAGEM,
        "key=lambda par: (-par[1], par[0])",
        "key=lambda par: (par[1], par[0])",
    )),
    # v3: filtra_curtas com off-by-one (> em vez de >=) descarta tokens no limite
    _task(3, "filtros.py", _com_bug(
        _FILTROS,
        "return [t for t in tokens if len(t) >= minimo]",
        "return [t for t in tokens if len(t) > minimo]",
    )),
    # v4: separador do relatorio errado ("=" em vez de ": ")
    _task(4, "formata.py", _com_bug(
        _FORMATA,
        'SEPARADOR = ": "',
        'SEPARADOR = "="',
    )),
]

__all__ = ["TASKS"]
