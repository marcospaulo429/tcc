"""Família templates do pool mini-SWE (pré-registro 29).

Renderizador de templates com variáveis {{var}} (caminhos com ponto),
condicionais {% se cond %}...{% fim %} e laços
{% para item em lista %}...{% fim %}: tags, valores, blocos e render.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 valores.py — formata(None) devolve 'None' (constante errada)
  v2 tags.py    — limpa() só remove espaços à esquerda (chamada errada)
  v3 blocos.py  — separa_para devolve (fonte, variavel) trocados (operandos)
  v4 render.py  — {% se %} mostra o corpo quando é falso (condição invertida)
"""

_TAGS = '''\
"""Localização de tags num template: {{variavel}} e {% comando %}."""
import re

RE_TAG = re.compile(r"\\{\\{(.*?)\\}\\}|\\{%(.*?)%\\}")


def limpa(texto):
    """Conteúdo da tag sem espaços nas pontas."""
    return texto.strip()


def proxima_tag(template, inicio):
    """Próxima tag a partir de `inicio`: (ini, fim, tipo, conteudo).

    tipo é 'var' para {{...}}; para {% ... %} é a palavra-chave
    ('se', 'para' ou 'fim') e conteudo é o restante da tag.
    Devolve None quando não há mais tags.
    """
    achado = RE_TAG.search(template, inicio)
    if achado is None:
        return None
    if achado.group(1) is not None:
        return (achado.start(), achado.end(), "var", limpa(achado.group(1)))
    bruto = limpa(achado.group(2))
    palavra, _, resto = bruto.partition(" ")
    return (achado.start(), achado.end(), palavra, limpa(resto))


def todas_tags(template):
    """Lista (tipo, conteudo) de todas as tags, na ordem do texto."""
    resultado = []
    pos = 0
    while True:
        tag = proxima_tag(template, pos)
        if tag is None:
            return resultado
        _, fim, tipo, conteudo = tag
        resultado.append((tipo, conteudo))
        pos = fim
'''

_TAGS_BUG = _TAGS.replace(
    "    return texto.strip()\n",
    "    return texto.lstrip()\n")

_VALORES = '''\
"""Busca de valores no contexto e conversão para texto de saída."""


def busca(contexto, caminho):
    """Resolve 'usuario.nome' navegando por dicionários; None se faltar."""
    atual = contexto
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def formata(valor):
    """Texto de saída de um valor; ausência (None) vira string vazia."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sim" if valor else "nao"
    return str(valor)


def e_verdadeiro(valor):
    """Regra de verdade dos blocos {% se %}: segue o bool() do Python."""
    return bool(valor)
'''

_VALORES_BUG = _VALORES.replace(
    '''    if valor is None:
        return ""
''',
    '''    if valor is None:
        return "None"
''')

_BLOCOS = '''\
"""Delimitação de blocos {% se %} / {% para %} até o {% fim %} par."""
from tags import proxima_tag

ABERTURAS = ("se", "para")


def encontra_fim(template, inicio):
    """Posição do {% fim %} que fecha o bloco aberto antes de `inicio`.

    Devolve (ini, fim): início da tag de fechamento e a posição logo
    após ela. Considera blocos aninhados. ValueError se não há fecho.
    """
    nivel = 1
    pos = inicio
    while True:
        tag = proxima_tag(template, pos)
        if tag is None:
            raise ValueError("bloco aberto sem {% fim %}")
        ini, fim, tipo, _ = tag
        if tipo in ABERTURAS:
            nivel += 1
        elif tipo == "fim":
            nivel -= 1
            if nivel == 0:
                return ini, fim
        pos = fim


def separa_para(conteudo):
    """'item em lista' -> ('item', 'lista'); ValueError se malformado."""
    partes = conteudo.split(" em ")
    if len(partes) != 2 or not partes[0].strip() or not partes[1].strip():
        raise ValueError(f"laco malformado: {conteudo!r}")
    return partes[0].strip(), partes[1].strip()
'''

_BLOCOS_BUG = _BLOCOS.replace(
    "    return partes[0].strip(), partes[1].strip()\n",
    "    return partes[1].strip(), partes[0].strip()\n")

_RENDER = '''\
"""Renderização recursiva do template com o contexto."""
from blocos import encontra_fim, separa_para
from tags import proxima_tag
from valores import busca, e_verdadeiro, formata


def renderiza(template, contexto):
    """Substitui variáveis e processa blocos; devolve o texto final."""
    saida = []
    pos = 0
    while True:
        tag = proxima_tag(template, pos)
        if tag is None:
            saida.append(template[pos:])
            break
        ini, fim, tipo, conteudo = tag
        saida.append(template[pos:ini])
        if tipo == "var":
            saida.append(formata(busca(contexto, conteudo)))
            pos = fim
        elif tipo == "se":
            fecho_ini, fecho_fim = encontra_fim(template, fim)
            corpo = template[fim:fecho_ini]
            if e_verdadeiro(busca(contexto, conteudo)):
                saida.append(renderiza(corpo, contexto))
            pos = fecho_fim
        elif tipo == "para":
            variavel, fonte = separa_para(conteudo)
            fecho_ini, fecho_fim = encontra_fim(template, fim)
            corpo = template[fim:fecho_ini]
            itens = busca(contexto, fonte)
            for item in itens if itens is not None else []:
                escopo = dict(contexto)
                escopo[variavel] = item
                saida.append(renderiza(corpo, escopo))
            pos = fecho_fim
        elif tipo == "fim":
            raise ValueError("{% fim %} sem bloco aberto")
        else:
            raise ValueError(f"comando desconhecido: {tipo!r}")
    return "".join(saida)
'''

_RENDER_BUG = _RENDER.replace(
    "            if e_verdadeiro(busca(contexto, conteudo)):\n",
    "            if not e_verdadeiro(busca(contexto, conteudo)):\n")

_API = '''\
"""API de alto nível do renderizador de templates."""
from render import renderiza


def renderizar(template, contexto=None):
    """Renderiza o template; contexto ausente vale dicionário vazio."""
    if contexto is None:
        contexto = {}
    return renderiza(template, contexto)


def renderizar_varios(template, contextos):
    """Mesmo template para vários contextos, na ordem dada."""
    return [renderizar(template, contexto) for contexto in contextos]
'''

_TEST = '''\
import pytest
from api import renderizar, renderizar_varios
from blocos import separa_para
from valores import busca, e_verdadeiro, formata


def test_texto_puro():
    assert renderizar("sem tags aqui") == "sem tags aqui"


def test_variavel_simples():
    assert renderizar("Oi, {{nome}}!", {"nome": "Ana"}) == "Oi, Ana!"


def test_variavel_com_espacos_na_tag():
    assert renderizar("Oi, {{ nome }}!", {"nome": "Ana"}) == "Oi, Ana!"


def test_variavel_ausente_vira_vazio():
    assert renderizar("[{{sumida}}]", {}) == "[]"
    assert formata(None) == ""


def test_caminho_com_pontos():
    ctx = {"usuario": {"nome": "Bia", "idade": 30}}
    saida = renderizar("{{usuario.nome}} tem {{usuario.idade}}", ctx)
    assert saida == "Bia tem 30"
    assert busca(ctx, "usuario.sobrenome") is None


def test_se_verdadeiro_mostra_corpo():
    tpl = "a{% se mostrar %}X{% fim %}b"
    assert renderizar(tpl, {"mostrar": True}) == "aXb"


def test_se_falso_esconde_corpo():
    tpl = "a{% se mostrar %}X{% fim %}b"
    assert renderizar(tpl, {"mostrar": False}) == "ab"
    assert renderizar(tpl, {}) == "ab"


def test_laco_simples():
    tpl = "{% para x em itens %}[{{x}}]{% fim %}"
    assert renderizar(tpl, {"itens": ["a", "b", "c"]}) == "[a][b][c]"


def test_blocos_aninhados():
    tpl = "{% para n em ns %}{% se n %}{{n}};{% fim %}{% fim %}"
    assert renderizar(tpl, {"ns": [1, 0, 2]}) == "1;2;"


def test_fim_solto_e_bloco_aberto_levantam():
    with pytest.raises(ValueError):
        renderizar("x{% fim %}", {})
    with pytest.raises(ValueError):
        renderizar("{% se a %}sem fecho", {"a": True})


def test_unitarios_de_apoio():
    assert separa_para("item em lista") == ("item", "lista")
    assert e_verdadeiro([]) is False
    assert e_verdadeiro("x") is True
    assert renderizar_varios("{{n}}", [{"n": 1}, {"n": 2}]) == ["1", "2"]
'''

_PROMPT = (
    "Este repositório implementa um renderizador de templates com\n"
    "variáveis {{var}}, condicionais {% se cond %}...{% fim %} e laços\n"
    "{% para item em lista %}...{% fim %}: tags.py localiza as tags,\n"
    "valores.py busca/formata valores do contexto, blocos.py delimita os\n"
    "blocos e render.py monta o texto final (api.py é a fachada). Há\n"
    "testes falhando por causa de um bug em um dos arquivos. Use\n"
    "list_files e read_file para explorar o código, run_tests para ver\n"
    "quais testes falham (a suite está em test_app.py), localize o bug e\n"
    "corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "tags.py": _TAGS,
    "valores.py": _VALORES,
    "blocos.py": _BLOCOS,
    "render.py": _RENDER,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_templates_v{n}",
        "family": "templates",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "valores.py", _VALORES_BUG),
    _monta(2, "tags.py", _TAGS_BUG),
    _monta(3, "blocos.py", _BLOCOS_BUG),
    _monta(4, "render.py", _RENDER_BUG),
]
