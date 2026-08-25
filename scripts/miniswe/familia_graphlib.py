"""Família mini-SWE "graphlib" (pré-registro 28, piloto V2).

Biblioteca de grafos dirigidos multi-arquivo; 4 variantes, cada uma
com UM bug injetado em um arquivo distinto do repositório base.
"""

_GRAFO = '''"""Grafo dirigido com listas de adjacencia mantidas em ordem alfabetica."""


class Grafo:
    """Grafo dirigido; nos sao strings, pesos sao inteiros."""

    def __init__(self):
        self._adj: dict[str, list[str]] = {}
        self._pesos: dict[tuple[str, str], int] = {}

    def adiciona_no(self, no: str) -> None:
        """Garante a existencia do no, sem arestas."""
        if no not in self._adj:
            self._adj[no] = []

    def adiciona_aresta(self, origem: str, destino: str, peso: int = 1) -> None:
        """Adiciona aresta dirigida origem->destino com peso inteiro."""
        self.adiciona_no(origem)
        self.adiciona_no(destino)
        if destino not in self._adj[origem]:
            self._adj[origem].append(destino)
            self._adj[origem].sort()
        self._pesos[(origem, destino)] = peso

    def vizinhos(self, no: str) -> list[str]:
        """Sucessores do no em ordem alfabetica."""
        return list(self._adj.get(no, []))

    def peso(self, origem: str, destino: str) -> int:
        """Peso da aresta; KeyError se a aresta nao existir."""
        return self._pesos[(origem, destino)]

    def tem_aresta(self, origem: str, destino: str) -> bool:
        """True se a aresta dirigida origem->destino existe."""
        return (origem, destino) in self._pesos

    def nos(self) -> list[str]:
        """Todos os nos em ordem alfabetica."""
        return sorted(self._adj)

    def arestas(self) -> list[tuple[str, str]]:
        """Todas as arestas (origem, destino) em ordem lexicografica."""
        return sorted(self._pesos)

    def grau_saida(self, no: str) -> int:
        """Numero de arestas que saem do no."""
        return len(self._adj.get(no, []))

    def grau_entrada(self, no: str) -> int:
        """Numero de arestas que chegam ao no."""
        return sum(1 for (_, destino) in self._pesos if destino == no)
'''

_BUSCA = '''"""Buscas em largura (BFS) e profundidade (DFS) com ordem deterministica."""
from collections import deque


def bfs(grafo, inicio: str) -> list[str]:
    """Ordem de descoberta em BFS; vizinhos visitados em ordem alfabetica."""
    visitados = [inicio]
    vistos = {inicio}
    fila = deque([inicio])
    while fila:
        atual = fila.popleft()
        for viz in grafo.vizinhos(atual):
            if viz not in vistos:
                vistos.add(viz)
                visitados.append(viz)
                fila.append(viz)
    return visitados


def dfs(grafo, inicio: str) -> list[str]:
    """Ordem de visita em DFS recursiva; vizinhos em ordem alfabetica."""
    visitados: list[str] = []
    vistos: set[str] = set()

    def _visita(no: str) -> None:
        vistos.add(no)
        visitados.append(no)
        for viz in grafo.vizinhos(no):
            if viz not in vistos:
                _visita(viz)

    _visita(inicio)
    return visitados


def alcancaveis(grafo, inicio: str) -> list[str]:
    """Nos alcancaveis a partir de inicio, em ordem alfabetica."""
    return sorted(bfs(grafo, inicio))
'''

_CAMINHO = '''"""Caminho minimo: BFS (arestas unitarias) e Dijkstra (pesos inteiros)."""
import heapq
from collections import deque


def caminho_bfs(grafo, origem: str, destino: str):
    """Caminho com menor numero de arestas, ou None se inalcancavel."""
    if origem == destino:
        return [origem]
    anterior = {origem: None}
    fila = deque([origem])
    while fila:
        atual = fila.popleft()
        for viz in grafo.vizinhos(atual):
            if viz not in anterior:
                anterior[viz] = atual
                if viz == destino:
                    return _reconstroi(anterior, destino)
                fila.append(viz)
    return None


def _reconstroi(anterior: dict, destino: str) -> list[str]:
    """Reconstroi o caminho seguindo os antecessores ate a origem."""
    caminho = [destino]
    no = anterior[destino]
    while no is not None:
        caminho.append(no)
        no = anterior[no]
    caminho.reverse()
    return caminho


def distancia_dijkstra(grafo, origem: str, destino: str):
    """Custo minimo (soma dos pesos) de origem a destino, ou None."""
    melhores = {origem: 0}
    heap = [(0, origem)]
    while heap:
        custo, atual = heapq.heappop(heap)
        if custo > melhores.get(atual, custo):
            continue
        if atual == destino:
            return custo
        for viz in grafo.vizinhos(atual):
            novo = custo + grafo.peso(atual, viz)
            if viz not in melhores or novo < melhores[viz]:
                melhores[viz] = novo
                heapq.heappush(heap, (novo, viz))
    return None
'''

_CICLOS = '''"""Deteccao de ciclos e ordenacao topologica (algoritmo de Kahn)."""
import bisect


def _kahn(grafo) -> list[str]:
    """Ordem parcial de Kahn; processa sempre o menor no disponivel."""
    graus = {no: 0 for no in grafo.nos()}
    for origem, destino in grafo.arestas():
        graus[destino] += 1
    prontos = sorted(no for no, grau in graus.items() if grau == 0)
    ordem = []
    while prontos:
        no = prontos.pop(0)
        ordem.append(no)
        for viz in grafo.vizinhos(no):
            graus[viz] -= 1
            if graus[viz] == 0:
                bisect.insort(prontos, viz)
    return ordem


def ordena_topologica(grafo):
    """Ordem topologica deterministica (menor no primeiro); None se ha ciclo."""
    ordem = _kahn(grafo)
    if len(ordem) != len(grafo.nos()):
        return None
    return ordem


def tem_ciclo(grafo) -> bool:
    """True se o grafo dirigido contem pelo menos um ciclo."""
    return ordena_topologica(grafo) is None


def nos_fora_da_ordem(grafo) -> list[str]:
    """Nos nao processados pelo Kahn (participam de ciclo ou dependem dele)."""
    processados = set(_kahn(grafo))
    return [no for no in grafo.nos() if no not in processados]
'''

_API = '''"""API de conveniencia: montar grafo a partir de arestas e consultas prontas."""
from busca import bfs
from caminho import caminho_bfs, distancia_dijkstra
from ciclos import tem_ciclo
from grafo import Grafo


def monta_grafo(arestas) -> Grafo:
    """Cria um Grafo de tuplas (origem, destino) ou (origem, destino, peso)."""
    g = Grafo()
    for aresta in arestas:
        if len(aresta) == 3:
            origem, destino, peso = aresta
        else:
            origem, destino = aresta
            peso = 1
        g.adiciona_aresta(origem, destino, peso)
    return g


def resumo(g: Grafo) -> dict:
    """Resumo estrutural do grafo: contagens e presenca de ciclo."""
    return {
        "nos": len(g.nos()),
        "arestas": len(g.arestas()),
        "ciclico": tem_ciclo(g),
    }


def rota(arestas, origem: str, destino: str) -> str:
    """Caminho BFS formatado como "a -> b -> c", ou "sem caminho"."""
    g = monta_grafo(arestas)
    caminho = caminho_bfs(g, origem, destino)
    if caminho is None:
        return "sem caminho"
    return " -> ".join(caminho)


def custo_minimo(arestas, origem: str, destino: str):
    """Custo Dijkstra entre origem e destino sobre as arestas dadas."""
    g = monta_grafo(arestas)
    return distancia_dijkstra(g, origem, destino)
'''

_TESTS = '''"""Suite de testes da biblioteca de grafos dirigidos (test_app.py)."""
from api import monta_grafo, rota
from busca import bfs, dfs
from caminho import caminho_bfs, distancia_dijkstra
from ciclos import ordena_topologica, tem_ciclo
from grafo import Grafo

ARESTAS = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e")]
PONDERADAS = [("a", "b", 4), ("a", "c", 1), ("c", "b", 1), ("b", "d", 1)]


def test_vizinhos_em_ordem_alfabetica():
    g = Grafo()
    g.adiciona_aresta("a", "c")
    g.adiciona_aresta("a", "b")
    assert g.vizinhos("a") == ["b", "c"]


def test_grau_saida():
    g = monta_grafo(ARESTAS)
    assert g.grau_saida("a") == 2
    assert g.grau_saida("e") == 0


def test_bfs_ordem_de_descoberta():
    assert bfs(monta_grafo(ARESTAS), "a") == ["a", "b", "c", "d", "e"]


def test_dfs_ordem_de_visita():
    assert dfs(monta_grafo(ARESTAS), "a") == ["a", "b", "d", "e", "c"]


def test_caminho_bfs_mais_curto():
    assert caminho_bfs(monta_grafo(ARESTAS), "a", "e") == ["a", "b", "d", "e"]


def test_caminho_bfs_inexistente():
    assert caminho_bfs(monta_grafo(ARESTAS), "e", "a") is None


def test_dijkstra_respeita_pesos():
    assert distancia_dijkstra(monta_grafo(PONDERADAS), "a", "d") == 3


def test_dijkstra_sem_caminho():
    assert distancia_dijkstra(monta_grafo(PONDERADAS), "d", "a") is None


def test_grafo_aciclico():
    assert tem_ciclo(monta_grafo(ARESTAS)) is False


def test_grafo_com_ciclo():
    g = monta_grafo([("a", "b"), ("b", "c"), ("c", "a")])
    assert tem_ciclo(g) is True


def test_ordenacao_topologica():
    assert ordena_topologica(monta_grafo(ARESTAS)) == ["a", "b", "c", "d", "e"]


def test_rota_formatada():
    assert rota(ARESTAS, "a", "e") == "a -> b -> d -> e"
'''

_BASE = {
    "grafo.py": _GRAFO,
    "busca.py": _BUSCA,
    "caminho.py": _CAMINHO,
    "ciclos.py": _CICLOS,
    "api.py": _API,
}

_PROMPT = (
    "Este repositorio implementa uma biblioteca de grafos dirigidos: estrutura "
    "com adjacencia ordenada (grafo.py), BFS/DFS deterministicos (busca.py), "
    "caminho minimo por BFS e Dijkstra com pesos inteiros (caminho.py), deteccao "
    "de ciclos e ordenacao topologica (ciclos.py) e API de conveniencia (api.py).\n"
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
        "task_id": f"swe_graphlib_v{n}",
        "family": "graphlib",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TESTS,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    # v1: adjacencia deixa de ser ordenada (sort omitido ao inserir aresta)
    _task(1, "grafo.py", _com_bug(
        _GRAFO,
        "            self._adj[origem].append(destino)\n"
        "            self._adj[origem].sort()\n",
        "            self._adj[origem].append(destino)\n",
    )),
    # v2: DFS itera os vizinhos em ordem INVERTIDA (ordem de visita errada)
    _task(2, "busca.py", _com_bug(
        _BUSCA,
        "        for viz in grafo.vizinhos(no):",
        "        for viz in reversed(grafo.vizinhos(no)):",
    )),
    # v3: Dijkstra ignora o peso da aresta (soma 1 por salto — agregacao errada)
    _task(3, "caminho.py", _com_bug(
        _CAMINHO,
        "            novo = custo + grafo.peso(atual, viz)",
        "            novo = custo + 1",
    )),
    # v4: Kahn incrementa grau da ORIGEM em vez do destino (chave errada)
    _task(4, "ciclos.py", _com_bug(
        _CICLOS,
        "        graus[destino] += 1",
        "        graus[origem] += 1",
    )),
]

__all__ = ["TASKS"]
