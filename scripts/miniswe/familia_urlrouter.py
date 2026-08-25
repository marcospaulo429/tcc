"""Família urlrouter do pool mini-SWE (pré-registro 29).

Roteador de URLs com parâmetros no estilo /users/<id>: parse de
padrões, casamento de caminhos, normalização e despacho ordenado.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 padroes.py   — fatia errada (nome do parâmetro fica com o '>')
  v2 casamento.py — comparação frouxa (aceita caminho mais longo que o padrão)
  v3 normaliza.py — off-by-one (remove a barra da raiz, '/' vira '')
  v4 roteador.py  — ordem invertida (a ÚLTIMA rota registrada vence)
"""

_PADROES = '''\
"""Parse de padrões de rota como /users/<id>/posts/<post>.

Segmentos entre '<' e '>' são parâmetros nomeados; os demais são
literais que exigem igualdade exata no casamento.
"""


def divide_caminho(caminho):
    """Segmentos do caminho; ValueError se não começa com '/'."""
    if not caminho.startswith("/"):
        raise ValueError(f"caminho deve comecar com '/': {caminho!r}")
    if caminho == "/":
        return []
    return caminho[1:].split("/")


def analisa_padrao(padrao):
    """Lista de segmentos ('literal', texto) ou ('parametro', nome)."""
    segmentos = []
    for parte in divide_caminho(padrao):
        if parte.startswith("<") and parte.endswith(">"):
            nome = parte[1:-1]
            if not nome:
                raise ValueError(f"parametro sem nome em {padrao!r}")
            segmentos.append(("parametro", nome))
        else:
            if not parte:
                raise ValueError(f"segmento vazio em {padrao!r}")
            segmentos.append(("literal", parte))
    return segmentos


def nomes_parametros(padrao):
    """Nomes dos parâmetros do padrão, na ordem em que aparecem."""
    return [valor for tipo, valor in analisa_padrao(padrao)
            if tipo == "parametro"]
'''

_PADROES_BUG = _PADROES.replace(
    "            nome = parte[1:-1]\n",
    "            nome = parte[1:]\n")

_CASAMENTO = '''\
"""Casamento de um caminho concreto contra um padrão analisado."""
from padroes import analisa_padrao, divide_caminho


def casa(padrao, caminho):
    """Dict de parâmetros extraídos se o caminho casa; None caso contrário.

    O caminho só casa se tiver EXATAMENTE o mesmo número de segmentos
    do padrão; literais exigem igualdade e parâmetros capturam o valor.
    """
    segmentos = analisa_padrao(padrao)
    partes = divide_caminho(caminho)
    if len(partes) != len(segmentos):
        return None
    parametros = {}
    for (tipo, esperado), parte in zip(segmentos, partes):
        if tipo == "literal":
            if parte != esperado:
                return None
        else:
            if not parte:
                return None
            parametros[esperado] = parte
    return parametros


def casa_literalmente(padrao, caminho):
    """True se o padrão casa o caminho sem capturar nenhum parâmetro."""
    parametros = casa(padrao, caminho)
    return parametros == {}
'''

_CASAMENTO_BUG = _CASAMENTO.replace(
    "    if len(partes) != len(segmentos):\n",
    "    if len(partes) < len(segmentos):\n")

_NORMALIZA = '''\
"""Normalização de caminhos antes do roteamento."""


def normaliza(caminho):
    """Colapsa barras duplicadas e remove a barra final (exceto na raiz).

    Exemplos: '/users//7/' -> '/users/7'; '/' -> '/'; '' -> '/'.
    """
    if not caminho:
        return "/"
    while "//" in caminho:
        caminho = caminho.replace("//", "/")
    if not caminho.startswith("/"):
        caminho = "/" + caminho
    if len(caminho) > 1 and caminho.endswith("/"):
        caminho = caminho[:-1]
    return caminho


def junta(base, sufixo):
    """Concatena dois pedaços de caminho já normalizando o resultado."""
    return normaliza(base + "/" + sufixo)


def eh_raiz(caminho):
    """True se o caminho normalizado é a raiz."""
    return normaliza(caminho) == "/"
'''

_NORMALIZA_BUG = _NORMALIZA.replace(
    '    if len(caminho) > 1 and caminho.endswith("/"):\n',
    '    if len(caminho) > 0 and caminho.endswith("/"):\n')

_ROTEADOR = '''\
"""Registro e despacho de rotas: a PRIMEIRA rota registrada que casa vence."""
from casamento import casa
from normaliza import normaliza


class Roteador:
    """Tabela ordenada de rotas (padrão -> nome do handler)."""

    def __init__(self):
        self._rotas = []

    def adiciona(self, padrao, nome_handler):
        """Registra a rota; padrões duplicados são rejeitados."""
        for existente, _ in self._rotas:
            if existente == padrao:
                raise ValueError(f"padrao duplicado: {padrao!r}")
        self._rotas.append((padrao, nome_handler))

    def despacha(self, caminho):
        """(nome_handler, parametros) da primeira rota registrada que casa.

        O caminho é normalizado antes; KeyError se nenhuma rota casa.
        """
        alvo = normaliza(caminho)
        for padrao, nome_handler in self._rotas:
            parametros = casa(padrao, alvo)
            if parametros is not None:
                return nome_handler, parametros
        raise KeyError(alvo)

    def rotas(self):
        """Padrões registrados, na ordem de registro."""
        return [padrao for padrao, _ in self._rotas]
'''

_ROTEADOR_BUG = _ROTEADOR.replace(
    "        for padrao, nome_handler in self._rotas:\n",
    "        for padrao, nome_handler in reversed(self._rotas):\n")

_API = '''\
"""Montagem do roteador de exemplo da aplicação de usuários."""
from roteador import Roteador


def monta_api():
    """Roteador com as rotas da API de usuários (a ordem importa)."""
    roteador = Roteador()
    roteador.adiciona("/", "raiz")
    roteador.adiciona("/users", "lista_usuarios")
    roteador.adiciona("/users/novo", "cria_usuario")
    roteador.adiciona("/users/<id>", "mostra_usuario")
    roteador.adiciona("/users/<id>/posts/<post>", "mostra_post")
    return roteador


def resolve(caminho):
    """Despacha o caminho no roteador de exemplo."""
    return monta_api().despacha(caminho)


def resolve_todos(caminhos):
    """Resolve vários caminhos, preservando a ordem de entrada."""
    roteador = monta_api()
    return [roteador.despacha(caminho) for caminho in caminhos]
'''

_TEST = '''\
import pytest
from api import resolve
from casamento import casa
from normaliza import junta, normaliza
from padroes import analisa_padrao, divide_caminho, nomes_parametros
from roteador import Roteador


def test_divide_caminho():
    assert divide_caminho("/") == []
    assert divide_caminho("/a/b") == ["a", "b"]


def test_caminho_sem_barra_rejeitado():
    with pytest.raises(ValueError):
        divide_caminho("users/7")


def test_analisa_padrao_com_parametro():
    esperado = [("literal", "users"), ("parametro", "id")]
    assert analisa_padrao("/users/<id>") == esperado


def test_nomes_parametros():
    assert nomes_parametros("/users/<id>/posts/<post>") == ["id", "post"]


def test_casa_literal():
    assert casa("/users", "/users") == {}
    assert casa("/users", "/posts") is None


def test_casa_extrai_parametros():
    assert casa("/users/<id>", "/users/7") == {"id": "7"}


def test_casa_exige_mesmo_tamanho():
    assert casa("/users", "/users/7") is None
    assert casa("/users/<id>", "/users") is None


def test_normaliza_barras():
    assert normaliza("/users//7/") == "/users/7"
    assert junta("/users", "7") == "/users/7"


def test_normaliza_raiz():
    assert normaliza("/") == "/"
    assert normaliza("") == "/"


def test_primeira_rota_registrada_vence():
    roteador = Roteador()
    roteador.adiciona("/users/novo", "criar")
    roteador.adiciona("/users/<id>", "mostrar")
    assert roteador.despacha("/users/novo") == ("criar", {})


def test_resolve_api_exemplo():
    assert resolve("/users/7/") == ("mostra_usuario", {"id": "7"})
    assert resolve("/") == ("raiz", {})
'''

_PROMPT = (
    "Este repositório implementa um roteador de URLs com parâmetros no\n"
    "estilo /users/<id>: padroes.py analisa os padrões de rota,\n"
    "casamento.py casa caminhos concretos contra padrões, normaliza.py\n"
    "limpa os caminhos, roteador.py registra e despacha rotas e api.py\n"
    "monta o roteador de exemplo. Há testes falhando por causa de um bug\n"
    "em um dos arquivos. Use list_files e read_file para explorar o\n"
    "código, run_tests para ver quais testes falham (a suite está em\n"
    "test_app.py), localize o bug e corrija reescrevendo o arquivo\n"
    "INTEIRO com write_file."
)

_BASE = {
    "padroes.py": _PADROES,
    "casamento.py": _CASAMENTO,
    "normaliza.py": _NORMALIZA,
    "roteador.py": _ROTEADOR,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_urlrouter_v{n}",
        "family": "urlrouter",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "padroes.py", _PADROES_BUG),
    _monta(2, "casamento.py", _CASAMENTO_BUG),
    _monta(3, "normaliza.py", _NORMALIZA_BUG),
    _monta(4, "roteador.py", _ROTEADOR_BUG),
]
