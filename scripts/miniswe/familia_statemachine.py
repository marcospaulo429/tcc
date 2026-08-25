"""Família statemachine do pool mini-SWE (pré-registro 28).

Máquina de estados do ciclo de vida de um pedido: definições de
estados, tabela de transições, executor, histórico e API.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 transicoes.py — destino errado na tabela (enviar pula p/ entregue)
  v2 maquina.py    — evento inválido não levanta erro (retorno silencioso)
  v3 historico.py  — listar() devolve os registros em ordem invertida
  v4 estados.py    — conjunto de estados finais errado
"""

_ESTADOS = '''\
"""Definições dos estados do ciclo de vida de um pedido.

Fluxo normal: novo -> pago -> separado -> enviado -> entregue.
Cancelamento é permitido apenas antes do envio.
"""

NOVO = "novo"
PAGO = "pago"
SEPARADO = "separado"
ENVIADO = "enviado"
ENTREGUE = "entregue"
CANCELADO = "cancelado"

ESTADOS = (NOVO, PAGO, SEPARADO, ENVIADO, ENTREGUE, CANCELADO)
ESTADO_INICIAL = NOVO
ESTADOS_FINAIS = (ENTREGUE, CANCELADO)

DESCRICOES = {
    NOVO: "pedido criado, aguardando pagamento",
    PAGO: "pagamento confirmado",
    SEPARADO: "itens separados no estoque",
    ENVIADO: "pedido despachado para entrega",
    ENTREGUE: "pedido recebido pelo cliente",
    CANCELADO: "pedido cancelado",
}


def e_estado_valido(estado):
    """True se o nome pertence ao conjunto de estados conhecidos."""
    return estado in ESTADOS


def e_final(estado):
    """True se o estado encerra o ciclo de vida do pedido."""
    return estado in ESTADOS_FINAIS


def descricao(estado):
    """Descrição humana do estado; KeyError se desconhecido."""
    return DESCRICOES[estado]
'''

_ESTADOS_BUG = _ESTADOS.replace(
    "ESTADOS_FINAIS = (ENTREGUE, CANCELADO)\n",
    "ESTADOS_FINAIS = (ENTREGUE, ENVIADO)\n")

_TRANSICOES = '''\
"""Tabela de transições da máquina de estados do pedido.

Cada entrada mapeia (estado_origem, evento) -> estado_destino.
Transições ausentes da tabela são inválidas.
"""
from estados import CANCELADO, ENTREGUE, ENVIADO, NOVO, PAGO, SEPARADO

TRANSICOES = {
    (NOVO, "pagar"): PAGO,
    (PAGO, "separar"): SEPARADO,
    (SEPARADO, "enviar"): ENVIADO,
    (ENVIADO, "entregar"): ENTREGUE,
    (NOVO, "cancelar"): CANCELADO,
    (PAGO, "cancelar"): CANCELADO,
    (SEPARADO, "cancelar"): CANCELADO,
}


def destino(estado, evento):
    """Estado de destino da transição, ou None se não permitida."""
    return TRANSICOES.get((estado, evento))


def transicao_valida(estado, evento):
    """True se o par (estado, evento) está na tabela."""
    return (estado, evento) in TRANSICOES


def eventos_possiveis(estado):
    """Eventos aceitos a partir de um estado, na ordem da tabela."""
    return [evento for (origem, evento) in TRANSICOES if origem == estado]
'''

_TRANSICOES_BUG = _TRANSICOES.replace(
    '    (SEPARADO, "enviar"): ENVIADO,\n',
    '    (SEPARADO, "enviar"): ENTREGUE,\n')

_MAQUINA = '''\
"""Executor da máquina de estados de um pedido."""
from estados import ESTADO_INICIAL, e_estado_valido, e_final
from historico import Historico
from transicoes import destino


class Maquina:
    """Mantém o estado atual e registra cada transição no histórico."""

    def __init__(self, estado=ESTADO_INICIAL):
        if not e_estado_valido(estado):
            raise ValueError(f"estado desconhecido: {estado!r}")
        self.estado = estado
        self.historico = Historico()

    def aplicar(self, evento):
        """Aplica um evento; ValueError se a transição não é permitida."""
        novo = destino(self.estado, evento)
        if novo is None:
            raise ValueError(
                f"transicao invalida: {self.estado} nao aceita {evento!r}")
        origem = self.estado
        self.estado = novo
        self.historico.registrar(origem, evento, novo)
        return novo

    def aplicar_todos(self, eventos):
        """Aplica uma sequência de eventos, na ordem dada."""
        for evento in eventos:
            self.aplicar(evento)
        return self.estado

    def finalizado(self):
        """True se o pedido chegou a um estado final."""
        return e_final(self.estado)
'''

_MAQUINA_BUG = _MAQUINA.replace(
    '''        if novo is None:
            raise ValueError(
                f"transicao invalida: {self.estado} nao aceita {evento!r}")
''',
    '''        if novo is None:
            return self.estado
''')

_HISTORICO = '''\
"""Registro em memória das transições executadas."""


class Historico:
    """Guarda os registros na ordem em que as transições ocorreram."""

    def __init__(self):
        self._registros = []

    def registrar(self, origem, evento, destino):
        """Acrescenta um registro ao final do histórico."""
        self._registros.append(
            {"origem": origem, "evento": evento, "destino": destino})

    def listar(self):
        """Cópia dos registros na ordem em que ocorreram."""
        return list(self._registros)

    def contar(self):
        """Quantidade de transições registradas."""
        return len(self._registros)

    def ultimo(self):
        """Último registro, ou None se o histórico está vazio."""
        if not self._registros:
            return None
        return self._registros[-1]

    def formata(self):
        """Linhas 'origem -evento-> destino', uma por transição."""
        return [f"{r['origem']} -{r['evento']}-> {r['destino']}"
                for r in self.listar()]
'''

_HISTORICO_BUG = _HISTORICO.replace(
    "        return list(self._registros)\n",
    "        return list(reversed(self._registros))\n")

_API = '''\
"""API de alto nível: processa sequências de eventos de um pedido."""
from estados import e_final
from maquina import Maquina


def processar_pedido(eventos):
    """Aplica os eventos em ordem; retorna (estado_final, historico).

    historico é a lista de registros {origem, evento, destino}.
    Levanta ValueError na primeira transição inválida.
    """
    maquina = Maquina()
    maquina.aplicar_todos(eventos)
    return maquina.estado, maquina.historico.listar()


def pedido_finalizado(eventos):
    """True se, após os eventos, o pedido está em estado final."""
    estado, _ = processar_pedido(eventos)
    return e_final(estado)


def resumo_pedido(eventos):
    """Resumo textual do processamento, uma linha por transição."""
    maquina = Maquina()
    maquina.aplicar_todos(eventos)
    return maquina.historico.formata()
'''

_TEST = '''\
import pytest
from api import pedido_finalizado, processar_pedido
from estados import ESTADO_INICIAL, e_estado_valido, e_final
from historico import Historico
from maquina import Maquina
from transicoes import destino, eventos_possiveis


def test_estado_inicial():
    assert ESTADO_INICIAL == "novo"
    assert Maquina().estado == "novo"


def test_destino_enviar():
    assert destino("separado", "enviar") == "enviado"


def test_caminho_feliz_completo():
    estado, hist = processar_pedido(["pagar", "separar", "enviar", "entregar"])
    assert estado == "entregue"
    destinos = [r["destino"] for r in hist]
    assert destinos == ["pago", "separado", "enviado", "entregue"]


def test_evento_invalido_levanta():
    maq = Maquina()
    with pytest.raises(ValueError):
        maq.aplicar("entregar")


def test_evento_invalido_nao_muda_estado():
    maq = Maquina()
    try:
        maq.aplicar("entregar")
    except ValueError:
        pass
    assert maq.estado == "novo"
    assert maq.historico.contar() == 0


def test_cancelar_de_pago():
    estado, _ = processar_pedido(["pagar", "cancelar"])
    assert estado == "cancelado"


def test_cancelar_de_enviado_proibido():
    with pytest.raises(ValueError):
        processar_pedido(["pagar", "separar", "enviar", "cancelar"])


def test_historico_ordem():
    hist = Historico()
    hist.registrar("novo", "pagar", "pago")
    hist.registrar("pago", "separar", "separado")
    assert [r["evento"] for r in hist.listar()] == ["pagar", "separar"]
    assert hist.contar() == 2
    assert hist.ultimo()["destino"] == "separado"


def test_estados_finais():
    assert e_final("entregue")
    assert e_final("cancelado")
    assert not e_final("enviado")


def test_pedido_finalizado_api():
    assert pedido_finalizado(["pagar", "cancelar"]) is True
    assert pedido_finalizado(["pagar", "separar"]) is False
'''

_PROMPT = (
    "Este repositório implementa a máquina de estados do ciclo de vida de um\n"
    "pedido: estados.py define os estados, transicoes.py a tabela de\n"
    "transições, maquina.py o executor, historico.py o log de transições e\n"
    "api.py as operações de alto nível. Há testes falhando por causa de um\n"
    "bug em um dos arquivos. Use list_files e read_file para explorar o\n"
    "código, run_tests para ver quais testes falham (a suite está em\n"
    "test_app.py), localize o bug e corrija reescrevendo o arquivo INTEIRO\n"
    "com write_file."
)

_BASE = {
    "estados.py": _ESTADOS,
    "transicoes.py": _TRANSICOES,
    "maquina.py": _MAQUINA,
    "historico.py": _HISTORICO,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_statemachine_v{n}",
        "family": "statemachine",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "transicoes.py", _TRANSICOES_BUG),
    _monta(2, "maquina.py", _MAQUINA_BUG),
    _monta(3, "historico.py", _HISTORICO_BUG),
    _monta(4, "estados.py", _ESTADOS_BUG),
]
