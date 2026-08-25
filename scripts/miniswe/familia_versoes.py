"""Família versoes do pool mini-SWE (pré-registro 29).

Comparação de versões semânticas e resolução de faixas: interpretação
de 'maior.menor.correcao', comparação, faixas (>=, <, ^, ~), escolha
da melhor candidata e decisões de atualização.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 versao.py  — componente ausente completado com 1 (constante errada)
  v2 compara.py — sinais da comparação trocados (operador invertido)
  v3 faixas.py  — til '~' usa o teto da próxima MAIOR (limite errado)
  v4 resolve.py — resolver escolhe a menor candidata (condição invertida)
"""

_VERSAO = '''\
"""Interpretação de números de versão semânticos (semver simplificado).

Uma versão tem até três componentes numéricos 'maior.menor.correcao'.
Componentes ausentes são completados com zero.
"""


def interpreta(texto):
    """'1.2.3' -> (1, 2, 3); ValueError se o texto não é uma versão."""
    partes = texto.strip().split(".")
    if not 1 <= len(partes) <= 3:
        raise ValueError(f"versao invalida: {texto!r}")
    numeros = []
    for parte in partes:
        if not parte.isdigit():
            raise ValueError(f"versao invalida: {texto!r}")
        numeros.append(int(parte))
    while len(numeros) < 3:
        numeros.append(0)
    return tuple(numeros)


def formata(versao):
    """(1, 2, 3) -> '1.2.3'."""
    return ".".join(str(n) for n in versao)


def e_valida(texto):
    """True se o texto pode ser interpretado como versão."""
    try:
        interpreta(texto)
    except ValueError:
        return False
    return True


def proxima_maior(texto):
    """Menor versão da próxima linha maior: '1.4.2' -> '2.0.0'."""
    versao = interpreta(texto)
    return formata((versao[0] + 1, 0, 0))
'''

_VERSAO_BUG = _VERSAO.replace(
    "        numeros.append(0)\n",
    "        numeros.append(1)\n")

_COMPARA = '''\
"""Comparação entre versões."""
from versao import interpreta


def compara(a, b):
    """-1 se a < b, 0 se iguais, 1 se a > b."""
    va = interpreta(a)
    vb = interpreta(b)
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def maior(a, b):
    """A mais nova das duas versões (texto original)."""
    return a if compara(a, b) >= 0 else b


def menor(a, b):
    """A mais antiga das duas versões (texto original)."""
    return a if compara(a, b) <= 0 else b


def em_ordem(versoes):
    """Versões em ordem crescente, comparando numericamente."""
    return sorted(versoes, key=interpreta)


def mais_nova(versoes):
    """A maior versão da lista; ValueError se a lista está vazia."""
    if not versoes:
        raise ValueError("lista de versoes vazia")
    return em_ordem(versoes)[-1]
'''

_COMPARA_BUG = _COMPARA.replace(
    '''    if va < vb:
        return -1
    if va > vb:
        return 1
''',
    '''    if va < vb:
        return 1
    if va > vb:
        return -1
''')

_FAIXAS = '''\
"""Faixas de versão: exata, '>=', '<', circunflexo '^' e til '~'."""
from versao import interpreta


def satisfaz(texto_versao, faixa):
    """True se a versão pertence à faixa.

    Formas aceitas: '1.2.3' (exata), '>=1.2.0', '<2.0.0',
    '^1.2.3' (mesma linha maior) e '~1.2.3' (mesma maior.menor).
    """
    versao = interpreta(texto_versao)
    faixa = faixa.strip()
    if faixa.startswith(">="):
        return versao >= interpreta(faixa[2:])
    if faixa.startswith("<"):
        return versao < interpreta(faixa[1:])
    if faixa.startswith("^"):
        base = interpreta(faixa[1:])
        teto = (base[0] + 1, 0, 0)
        return base <= versao < teto
    if faixa.startswith("~"):
        base = interpreta(faixa[1:])
        teto = (base[0], base[1] + 1, 0)
        return base <= versao < teto
    return versao == interpreta(faixa)


def filtra(versoes, faixa):
    """Versões da lista que satisfazem a faixa, preservando a ordem."""
    return [v for v in versoes if satisfaz(v, faixa)]
'''

_FAIXAS_BUG = _FAIXAS.replace(
    "        teto = (base[0], base[1] + 1, 0)\n",
    "        teto = (base[0] + 1, 0, 0)\n")

_RESOLVE = '''\
"""Escolha da melhor versão dentro de uma faixa."""
from compara import compara
from faixas import satisfaz


def resolver(candidatas, faixa):
    """Maior versão da lista que satisfaz a faixa; None se nenhuma."""
    melhor = None
    for candidata in candidatas:
        if not satisfaz(candidata, faixa):
            continue
        if melhor is None or compara(candidata, melhor) > 0:
            melhor = candidata
    return melhor


def resolver_varias(candidatas, faixas):
    """Resolve cada faixa; dicionário faixa -> versão escolhida."""
    return {faixa: resolver(candidatas, faixa) for faixa in faixas}


def existe_compativel(candidatas, faixa):
    """True se alguma candidata da lista satisfaz a faixa."""
    return resolver(candidatas, faixa) is not None
'''

_RESOLVE_BUG = _RESOLVE.replace(
    "        if melhor is None or compara(candidata, melhor) > 0:\n",
    "        if melhor is None or compara(candidata, melhor) < 0:\n")

_API = '''\
"""Operações de alto nível: decidir atualizações de dependências."""
from compara import compara
from resolve import resolver


def melhor_atualizacao(atual, candidatas, faixa):
    """Maior candidata da faixa que seja mais nova que a versão atual."""
    escolhida = resolver(candidatas, faixa)
    if escolhida is None or compara(escolhida, atual) <= 0:
        return None
    return escolhida


def desatualizada(atual, candidatas, faixa):
    """True se existe atualização melhor que a versão atual."""
    return melhor_atualizacao(atual, candidatas, faixa) is not None


def relatorio(atual, candidatas, faixa):
    """Resumo textual da decisão de atualização."""
    escolhida = melhor_atualizacao(atual, candidatas, faixa)
    if escolhida is None:
        return f"{atual}: ja atualizada para a faixa {faixa}"
    return f"{atual}: atualizar para {escolhida}"
'''

_TEST = '''\
import pytest
from api import desatualizada, melhor_atualizacao
from compara import compara, em_ordem, maior
from faixas import filtra, satisfaz
from resolve import resolver
from versao import e_valida, formata, interpreta


def test_interpreta_completa():
    assert interpreta("1.2.3") == (1, 2, 3)
    assert interpreta("10.0.7") == (10, 0, 7)


def test_interpreta_incompleta_completa_com_zero():
    assert interpreta("1.2") == (1, 2, 0)
    assert interpreta("2") == (2, 0, 0)


def test_interpreta_invalida():
    for texto in ("", "1.a.0", "1.2.3.4", "v1.0"):
        with pytest.raises(ValueError):
            interpreta(texto)
    assert e_valida("1.0.0") is True
    assert e_valida("abc") is False


def test_formata():
    assert formata((3, 1, 4)) == "3.1.4"


def test_compara_basico():
    assert compara("1.0.0", "2.0.0") == -1
    assert compara("2.0.0", "1.9.9") == 1
    assert compara("1.2.3", "1.2.3") == 0
    assert maior("1.2.0", "1.10.0") == "1.10.0"


def test_em_ordem_numerica():
    versoes = ["1.10.0", "1.2.0", "0.9.9"]
    assert em_ordem(versoes) == ["0.9.9", "1.2.0", "1.10.0"]


def test_satisfaz_limites():
    assert satisfaz("1.5.0", ">=1.2.0") is True
    assert satisfaz("1.1.9", ">=1.2.0") is False
    assert satisfaz("1.9.9", "<2.0.0") is True
    assert satisfaz("2.0.0", "<2.0.0") is False


def test_satisfaz_circunflexo():
    assert satisfaz("1.9.9", "^1.2.3") is True
    assert satisfaz("1.2.2", "^1.2.3") is False
    assert satisfaz("2.0.0", "^1.2.3") is False


def test_satisfaz_til():
    assert satisfaz("1.2.9", "~1.2.0") is True
    assert satisfaz("1.3.0", "~1.2.0") is False
    assert filtra(["1.2.1", "1.3.0", "1.2.5"], "~1.2.0") == ["1.2.1", "1.2.5"]


def test_resolver_escolhe_a_maior():
    candidatas = ["1.2.0", "1.4.2", "1.3.9", "2.0.0"]
    assert resolver(candidatas, "^1.2.0") == "1.4.2"
    assert resolver(candidatas, ">=3.0.0") is None
    assert melhor_atualizacao("1.4.2", candidatas, "^1.2.0") is None
    assert desatualizada("1.2.0", candidatas, "^1.2.0") is True
'''

_PROMPT = (
    "Este repositório implementa comparação de versões semânticas e\n"
    "resolução de faixas: versao.py interpreta 'maior.menor.correcao',\n"
    "compara.py compara versões, faixas.py decide se uma versão satisfaz\n"
    "uma faixa (>=, <, ^, ~), resolve.py escolhe a melhor candidata e\n"
    "api.py decide atualizações. Há testes falhando por causa de um bug\n"
    "em um dos arquivos. Use list_files e read_file para explorar o\n"
    "código, run_tests para ver quais testes falham (a suite está em\n"
    "test_app.py), localize o bug e corrija reescrevendo o arquivo\n"
    "INTEIRO com write_file."
)

_BASE = {
    "versao.py": _VERSAO,
    "compara.py": _COMPARA,
    "faixas.py": _FAIXAS,
    "resolve.py": _RESOLVE,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_versoes_v{n}",
        "family": "versoes",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "versao.py", _VERSAO_BUG),
    _monta(2, "compara.py", _COMPARA_BUG),
    _monta(3, "faixas.py", _FAIXAS_BUG),
    _monta(4, "resolve.py", _RESOLVE_BUG),
]
