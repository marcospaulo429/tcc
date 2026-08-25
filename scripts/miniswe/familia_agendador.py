"""Família agendador do pool mini-SWE (pré-registro 29).

Fila de prioridade de tarefas com dependências e desempate estável por
relógio lógico de contador (nunca usa tempo real): relógio, tarefas,
ordenação, dependências e o agendador.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 prioridade.py   — desempate invertido: mais nova vence (operador)
  v2 relogio.py      — primeiro carimbo é 0 em vez de 1 (off-by-one)
  v3 dependencias.py — pronta() exige dependências NÃO concluídas (condição invertida)
  v4 agendador.py    — executar_uma não registra a conclusão (chamada omitida)
"""

_RELOGIO = '''\
"""Relógio lógico por contador: nunca consulta o tempo real.

Cada chamada de marca() devolve um carimbo estritamente crescente,
usado para desempate determinístico na fila de prioridade.
"""


class Relogio:
    """Contador monotônico iniciado em zero; primeiro carimbo é 1."""

    def __init__(self):
        self._agora = 0

    def marca(self):
        """Avança o relógio e devolve o novo carimbo."""
        self._agora += 1
        return self._agora

    def agora(self):
        """Último carimbo emitido (0 se nenhum)."""
        return self._agora
'''

_RELOGIO_BUG = _RELOGIO.replace(
    '''        self._agora += 1
        return self._agora
''',
    '''        atual = self._agora
        self._agora += 1
        return atual
''')

_TAREFAS = '''\
"""Definição de tarefa e validação dos campos."""

PRIORIDADE_MINIMA = 1
PRIORIDADE_MAXIMA = 5


class Tarefa:
    """Tarefa nomeada com prioridade (1 = mais urgente) e dependências.

    O campo seq recebe o carimbo do relógio lógico quando a tarefa
    entra na fila; é usado para desempate determinístico.
    """

    def __init__(self, nome, prioridade, dependencias=()):
        valida_prioridade(prioridade)
        if not nome:
            raise ValueError("tarefa precisa de nome")
        self.nome = nome
        self.prioridade = prioridade
        self.dependencias = tuple(dependencias)
        self.seq = None

    def __repr__(self):
        return f"Tarefa({self.nome!r}, p={self.prioridade}, seq={self.seq})"


def valida_prioridade(prioridade):
    """ValueError se a prioridade está fora de [1, 5]."""
    if not PRIORIDADE_MINIMA <= prioridade <= PRIORIDADE_MAXIMA:
        raise ValueError(f"prioridade fora da faixa: {prioridade}")
'''

_PRIORIDADE = '''\
"""Ordenação da fila: menor número de prioridade vence; empate vai
para o carimbo mais antigo do relógio lógico (ordem estável)."""


def chave(tarefa):
    """Chave de ordenação: (prioridade, carimbo de chegada)."""
    return (tarefa.prioridade, tarefa.seq)


def mais_urgente(tarefas):
    """Tarefa de menor chave; ValueError se a lista está vazia."""
    if not tarefas:
        raise ValueError("nenhuma tarefa para escolher")
    escolhida = tarefas[0]
    for tarefa in tarefas[1:]:
        if chave(tarefa) < chave(escolhida):
            escolhida = tarefa
    return escolhida


def ordena(tarefas):
    """Tarefas em ordem de urgência, sem modificar a lista original."""
    return sorted(tarefas, key=chave)


def agrupa_por_prioridade(tarefas):
    """Dicionário prioridade -> nomes, percorrendo em ordem de urgência."""
    grupos = {}
    for tarefa in ordena(tarefas):
        grupos.setdefault(tarefa.prioridade, []).append(tarefa.nome)
    return grupos
'''

_PRIORIDADE_BUG = _PRIORIDADE.replace(
    "    return (tarefa.prioridade, tarefa.seq)\n",
    "    return (tarefa.prioridade, -tarefa.seq)\n")

_DEPENDENCIAS = '''\
"""Verificação de dependências entre tarefas."""


def pronta(tarefa, concluidas):
    """True se toda dependência da tarefa já foi concluída."""
    return all(d in concluidas for d in tarefa.dependencias)


def prontas(tarefas, concluidas):
    """Subconjunto de tarefas prontas, preservando a ordem dada."""
    return [t for t in tarefas if pronta(t, concluidas)]


def nomes_desconhecidos(tarefas):
    """Dependências que não correspondem a nenhuma tarefa da lista."""
    nomes = {t.nome for t in tarefas}
    faltando = []
    for tarefa in tarefas:
        for dep in tarefa.dependencias:
            if dep not in nomes and dep not in faltando:
                faltando.append(dep)
    return faltando
'''

_DEPENDENCIAS_BUG = _DEPENDENCIAS.replace(
    "    return all(d in concluidas for d in tarefa.dependencias)\n",
    "    return all(d not in concluidas for d in tarefa.dependencias)\n")

_AGENDADOR = '''\
"""Fila de prioridade com dependências e relógio lógico."""
from dependencias import pronta
from prioridade import mais_urgente
from relogio import Relogio
from tarefas import Tarefa


class Agendador:
    """Escolhe sempre a tarefa pronta mais urgente; desempate estável."""

    def __init__(self):
        self._fila = []
        self._concluidas = []
        self._relogio = Relogio()

    def adicionar(self, nome, prioridade, dependencias=()):
        """Cria a tarefa, carimba com o relógio lógico e enfileira."""
        tarefa = Tarefa(nome, prioridade, dependencias)
        tarefa.seq = self._relogio.marca()
        self._fila.append(tarefa)
        return tarefa

    def proxima(self):
        """Tarefa pronta mais urgente, ou None se nenhuma está pronta."""
        candidatas = [t for t in self._fila if pronta(t, self._concluidas)]
        if not candidatas:
            return None
        return mais_urgente(candidatas)

    def executar_uma(self):
        """Remove e conclui a próxima tarefa; ValueError se bloqueado."""
        tarefa = self.proxima()
        if tarefa is None:
            raise ValueError("nenhuma tarefa pronta: bloqueio ou fila vazia")
        self._fila.remove(tarefa)
        self._concluidas.append(tarefa.nome)
        return tarefa.nome

    def executar_todas(self):
        """Executa até esvaziar a fila; devolve os nomes na ordem."""
        ordem = []
        while self._fila:
            ordem.append(self.executar_uma())
        return ordem

    def pendentes(self):
        """Nomes ainda na fila, na ordem de chegada."""
        return [t.nome for t in self._fila]

    def concluidas(self):
        """Nomes já concluídos, na ordem de execução."""
        return list(self._concluidas)
'''

_AGENDADOR_BUG = _AGENDADOR.replace(
    '''        self._fila.remove(tarefa)
        self._concluidas.append(tarefa.nome)
        return tarefa.nome
''',
    '''        self._fila.remove(tarefa)
        return tarefa.nome
''')

_TEST = '''\
import pytest
from agendador import Agendador
from dependencias import nomes_desconhecidos, pronta
from prioridade import ordena
from relogio import Relogio
from tarefas import Tarefa, valida_prioridade


def test_relogio_comeca_em_um():
    relogio = Relogio()
    assert relogio.marca() == 1
    assert relogio.marca() == 2
    assert relogio.agora() == 2


def test_prioridade_invalida():
    with pytest.raises(ValueError):
        valida_prioridade(0)
    with pytest.raises(ValueError):
        Tarefa("x", 6)


def test_ordena_por_prioridade():
    a = Tarefa("a", 3)
    a.seq = 1
    b = Tarefa("b", 1)
    b.seq = 2
    c = Tarefa("c", 2)
    c.seq = 3
    assert [t.nome for t in ordena([a, b, c])] == ["b", "c", "a"]


def test_empate_vence_a_mais_antiga():
    ag = Agendador()
    ag.adicionar("primeira", 2)
    ag.adicionar("segunda", 2)
    assert ag.executar_todas() == ["primeira", "segunda"]


def test_pronta_por_dependencias():
    tarefa = Tarefa("b", 1, dependencias=("a",))
    assert pronta(tarefa, []) is False
    assert pronta(tarefa, ["a"]) is True
    assert pronta(Tarefa("solta", 1), []) is True


def test_execucao_ordem_de_prioridade():
    ag = Agendador()
    ag.adicionar("relatorio", 3)
    ag.adicionar("backup", 1)
    ag.adicionar("emails", 2)
    assert ag.executar_todas() == ["backup", "emails", "relatorio"]


def test_dependencia_segura_a_execucao():
    ag = Agendador()
    ag.adicionar("deploy", 1, dependencias=("build",))
    ag.adicionar("build", 2)
    assert ag.executar_todas() == ["build", "deploy"]


def test_bloqueio_levanta():
    ag = Agendador()
    ag.adicionar("a", 1, dependencias=("fantasma",))
    with pytest.raises(ValueError):
        ag.executar_todas()
    assert nomes_desconhecidos([Tarefa("a", 1, ("fantasma",))]) == ["fantasma"]


def test_concluidas_registradas_em_ordem():
    ag = Agendador()
    ag.adicionar("um", 1)
    ag.adicionar("dois", 2)
    ag.executar_uma()
    assert ag.concluidas() == ["um"]
    assert ag.pendentes() == ["dois"]


def test_proxima_nao_remove():
    ag = Agendador()
    ag.adicionar("solo", 1)
    assert ag.proxima().nome == "solo"
    assert ag.pendentes() == ["solo"]
'''

_PROMPT = (
    "Este repositório implementa um agendador de tarefas com fila de\n"
    "prioridade e dependências: relogio.py é o relógio lógico por contador,\n"
    "tarefas.py define a tarefa, prioridade.py a ordenação com desempate\n"
    "estável, dependencias.py a checagem de pré-requisitos e agendador.py\n"
    "a fila em si. Há testes falhando por causa de um bug em um dos\n"
    "arquivos. Use list_files e read_file para explorar o código,\n"
    "run_tests para ver quais testes falham (a suite está em test_app.py),\n"
    "localize o bug e corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "relogio.py": _RELOGIO,
    "tarefas.py": _TAREFAS,
    "prioridade.py": _PRIORIDADE,
    "dependencias.py": _DEPENDENCIAS,
    "agendador.py": _AGENDADOR,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_agendador_v{n}",
        "family": "agendador",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "prioridade.py", _PRIORIDADE_BUG),
    _monta(2, "relogio.py", _RELOGIO_BUG),
    _monta(3, "dependencias.py", _DEPENDENCIAS_BUG),
    _monta(4, "agendador.py", _AGENDADOR_BUG),
]
