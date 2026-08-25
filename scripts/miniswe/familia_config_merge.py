"""Família config_merge do pool mini-SWE (pré-registro 28).

Carregador de configuração em camadas: parse INI-like, deep merge com
precedência, interpolação de referências ${secao.chave} e validação.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 merge.py     — precedência invertida (base vence conflito escalar)
  v2 parse.py     — "false" parseado como True (condição errada)
  v3 resolve.py   — off-by-one no slice da referência (inclui '}')
  v4 validate.py  — condição invertida na checagem de obrigatórias
"""

_PARSE = '''\
"""Parser de configuração em formato INI-like simples.

Sintaxe aceita:
    [secao]
    chave = valor
    # comentário

Valores são convertidos: "true"/"false" para bool, dígitos para int,
o restante permanece string. Chaves com pontos criam sub-dicionários.
"""


def _converte(bruto):
    """Converte o texto de um valor para bool, int ou string."""
    texto = bruto.strip()
    if texto == "true":
        return True
    if texto == "false":
        return False
    if texto.lstrip("-").isdigit():
        return int(texto)
    return texto


def _insere(destino, caminho, valor):
    """Insere valor em destino seguindo o caminho pontilhado."""
    partes = caminho.split(".")
    atual = destino
    for parte in partes[:-1]:
        atual = atual.setdefault(parte, {})
    atual[partes[-1]] = valor


def parse(texto):
    """Converte texto INI-like em dict aninhado {secao: {chave: valor}}."""
    config = {}
    secao = None
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("[") and linha.endswith("]"):
            secao = linha[1:-1].strip()
            config.setdefault(secao, {})
            continue
        if secao is None:
            raise ValueError(f"chave fora de secao: {linha!r}")
        if "=" not in linha:
            raise ValueError(f"linha invalida: {linha!r}")
        chave, _, bruto = linha.partition("=")
        _insere(config[secao], chave.strip(), _converte(bruto))
    return config
'''

_PARSE_BUG = _PARSE.replace(
    '''    if texto == "true":
        return True
    if texto == "false":
        return False
''',
    '''    if texto in ("true", "false"):
        return True
''')

_MERGE = '''\
"""Deep merge de dicionários de configuração com precedência.

deep_merge(base, override): override tem precedência sobre base.
Dicionários aninhados são mesclados recursivamente; qualquer outro
tipo em override substitui integralmente o valor de base.
"""


def deep_merge(base, override):
    """Mescla override sobre base sem modificar os argumentos."""
    resultado = dict(base)
    for chave, valor in override.items():
        anterior = resultado.get(chave)
        if isinstance(anterior, dict) and isinstance(valor, dict):
            resultado[chave] = deep_merge(anterior, valor)
        else:
            resultado[chave] = valor
    return resultado


def merge_camadas(camadas):
    """Mescla uma lista de dicts, da menor para a maior precedência."""
    resultado = {}
    for camada in camadas:
        resultado = deep_merge(resultado, camada)
    return resultado
'''

_MERGE_BUG = _MERGE.replace(
    '''        else:
            resultado[chave] = valor
''',
    '''        elif chave not in resultado:
            resultado[chave] = valor
''')

_RESOLVE = '''\
"""Interpolação de referências ${secao.chave} em valores string.

Referências apontam para caminhos pontilhados do próprio config e
podem aparecer em qualquer posição da string, inclusive várias vezes
na mesma string.
"""


def _busca(config, caminho):
    """Resolve um caminho pontilhado; KeyError se não existir."""
    atual = config
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            raise KeyError(f"referencia nao encontrada: {caminho}")
        atual = atual[parte]
    return atual


def _resolve_valor(config, valor):
    """Substitui todas as referências ${...} de uma string."""
    if not isinstance(valor, str):
        return valor
    while "${" in valor:
        inicio = valor.index("${")
        fim = valor.index("}", inicio)
        caminho = valor[inicio + 2:fim]
        alvo = _busca(config, caminho)
        valor = valor[:inicio] + str(alvo) + valor[fim + 1:]
    return valor


def resolve(config):
    """Retorna cópia do config com as referências resolvidas."""
    def _anda(no):
        if isinstance(no, dict):
            return {chave: _anda(valor) for chave, valor in no.items()}
        return _resolve_valor(config, no)

    return _anda(config)
'''

_RESOLVE_BUG = _RESOLVE.replace(
    "        caminho = valor[inicio + 2:fim]\n",
    "        caminho = valor[inicio + 2:fim + 1]\n")

_VALIDATE = '''\
"""Validação de chaves obrigatórias e tipos esperados.

Caminhos são pontilhados, ex.: "app.porta". A validação retorna a
lista de erros encontrados; lista vazia significa configuração válida.
"""


def _presente(config, caminho):
    """True se o caminho pontilhado existe no config."""
    atual = config
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return False
        atual = atual[parte]
    return True


def _le(config, caminho):
    """Lê o valor de um caminho pontilhado (assume que existe)."""
    atual = config
    for parte in caminho.split("."):
        atual = atual[parte]
    return atual


def valida(config, obrigatorias=(), tipos=None):
    """Valida chaves obrigatórias e tipos; retorna lista de erros."""
    erros = []
    for caminho in obrigatorias:
        if not _presente(config, caminho):
            erros.append(f"obrigatoria ausente: {caminho}")
    for caminho, tipo in (tipos or {}).items():
        if _presente(config, caminho) and not isinstance(_le(config, caminho), tipo):
            erros.append(f"tipo invalido em {caminho}")
    return erros
'''

_VALIDATE_BUG = _VALIDATE.replace(
    '''        if not _presente(config, caminho):
            erros.append(f"obrigatoria ausente: {caminho}")
''',
    '''        if _presente(config, caminho):
            erros.append(f"obrigatoria ausente: {caminho}")
''')

_API = '''\
"""API de alto nível do carregador de configuração em camadas."""
from merge import merge_camadas
from parse import parse
from resolve import resolve
from validate import valida


def load_config(textos, obrigatorias=(), tipos=None):
    """Carrega camadas de texto INI-like e retorna o config final.

    Passos: parse de cada camada, merge (a última camada tem a maior
    precedência), resolução de referências ${secao.chave} e validação.
    Levanta ValueError se a validação encontrar erros.
    """
    camadas = [parse(texto) for texto in textos]
    config = resolve(merge_camadas(camadas))
    erros = valida(config, obrigatorias, tipos)
    if erros:
        raise ValueError("; ".join(erros))
    return config


def load_config_texto(texto):
    """Atalho para carregar uma única camada, sem validação extra."""
    return load_config([texto])
'''

_TEST = '''\
import pytest
from api import load_config
from merge import deep_merge, merge_camadas
from parse import parse
from resolve import resolve
from validate import valida


def test_parse_tipos_basicos():
    cfg = parse("[app]\\nporta = 8080\\ndebug = false\\nnome = servidor")
    assert cfg["app"]["porta"] == 8080
    assert cfg["app"]["debug"] is False
    assert cfg["app"]["nome"] == "servidor"


def test_parse_chave_pontilhada():
    cfg = parse("[db]\\npool.max = 10")
    assert cfg["db"]["pool"]["max"] == 10


def test_merge_override_escalar():
    assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_merge_aninhado_preserva_base():
    base = {"db": {"host": "x", "porta": 1}}
    over = {"db": {"porta": 2}}
    assert deep_merge(base, over) == {"db": {"host": "x", "porta": 2}}


def test_merge_camadas_ultima_vence():
    assert merge_camadas([{"a": 1}, {"a": 2}, {"a": 3}]) == {"a": 3}


def test_resolve_referencia_simples():
    cfg = {"app": {"host": "web", "url": "http://${app.host}/"}}
    assert resolve(cfg)["app"]["url"] == "http://web/"


def test_resolve_referencia_aninhada():
    cfg = {"db": {"pool": {"max": 5}}, "log": {"msg": "pool=${db.pool.max}"}}
    assert resolve(cfg)["log"]["msg"] == "pool=5"


def test_valida_ok():
    assert valida({"app": {"porta": 1}}, obrigatorias=["app.porta"]) == []


def test_valida_ausente():
    erros = valida({"app": {}}, obrigatorias=["app.porta"])
    assert erros == ["obrigatoria ausente: app.porta"]


def test_api_fim_a_fim():
    base = "[app]\\nporta = 8000\\nhost = local"
    prod = "[app]\\nporta = 9000\\nurl = http://${app.host}:${app.porta}"
    cfg = load_config([base, prod], obrigatorias=["app.url"])
    assert cfg["app"]["porta"] == 9000
    assert cfg["app"]["url"] == "http://local:9000"
'''

_PROMPT = (
    "Este repositório implementa um carregador de configuração em camadas:\n"
    "parse.py lê um formato INI-like, merge.py faz deep merge com precedência,\n"
    "resolve.py interpola referências ${secao.chave}, validate.py checa chaves\n"
    "obrigatórias e api.py expõe load_config. Há testes falhando por causa de\n"
    "um bug em um dos arquivos. Use list_files e read_file para explorar o\n"
    "código, run_tests para ver quais testes falham (a suite está em\n"
    "test_app.py), localize o bug e corrija reescrevendo o arquivo INTEIRO\n"
    "com write_file."
)

_BASE = {
    "parse.py": _PARSE,
    "merge.py": _MERGE,
    "resolve.py": _RESOLVE,
    "validate.py": _VALIDATE,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_config_merge_v{n}",
        "family": "config_merge",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "merge.py", _MERGE_BUG),
    _monta(2, "parse.py", _PARSE_BUG),
    _monta(3, "resolve.py", _RESOLVE_BUG),
    _monta(4, "validate.py", _VALIDATE_BUG),
]
