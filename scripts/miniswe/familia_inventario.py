"""Família inventario do pool mini-SWE (pré-registro 29).

Controle de estoque com entradas/saídas físicas, reservas e alerta de
saldo mínimo: catálogo, movimentos, reservas, visão consolidada e API.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 movimentos.py — saída soma no saldo em vez de subtrair (operador)
  v2 reservas.py   — total_reservado conta as canceladas (condição invertida)
  v3 estoque.py    — abaixo_do_minimo dispara na borda (off-by-one)
  v4 api.py        — registrar_saida não checa o disponível (checagem omitida)
"""

_PRODUTOS = '''\
"""Catálogo de produtos do estoque, com saldo mínimo de reposição.

O saldo mínimo indica a quantidade disponível abaixo da qual o
produto deve entrar na lista de reposição.
"""

CATALOGO = {
    "parafuso": {"nome": "Parafuso M4", "minimo": 10},
    "porca": {"nome": "Porca M4", "minimo": 5},
    "arruela": {"nome": "Arruela lisa", "minimo": 20},
}


def existe(codigo):
    """True se o código pertence ao catálogo."""
    return codigo in CATALOGO


def valida(codigo):
    """ValueError se o código não pertence ao catálogo."""
    if not existe(codigo):
        raise ValueError(f"produto desconhecido: {codigo!r}")


def minimo(codigo):
    """Saldo mínimo de reposição do produto."""
    valida(codigo)
    return CATALOGO[codigo]["minimo"]


def nome(codigo):
    """Nome humano do produto."""
    valida(codigo)
    return CATALOGO[codigo]["nome"]


def codigos():
    """Códigos do catálogo em ordem alfabética."""
    return sorted(CATALOGO)
'''

_MOVIMENTOS = '''\
"""Registro de entradas e saídas físicas do estoque."""


class Movimentos:
    """Guarda os movimentos na ordem em que foram registrados."""

    def __init__(self):
        self._registros = []

    def entrada(self, codigo, quantidade):
        """Registra chegada de mercadoria; quantidade deve ser positiva."""
        self._registrar(codigo, "entrada", quantidade)

    def saida(self, codigo, quantidade):
        """Registra saída de mercadoria; quantidade deve ser positiva."""
        self._registrar(codigo, "saida", quantidade)

    def _registrar(self, codigo, tipo, quantidade):
        if quantidade <= 0:
            raise ValueError(f"quantidade deve ser positiva: {quantidade}")
        self._registros.append(
            {"codigo": codigo, "tipo": tipo, "quantidade": quantidade})

    def saldo(self, codigo):
        """Saldo físico: soma das entradas menos a soma das saídas."""
        total = 0
        for r in self._registros:
            if r["codigo"] != codigo:
                continue
            if r["tipo"] == "entrada":
                total += r["quantidade"]
            else:
                total -= r["quantidade"]
        return total

    def listar(self, codigo):
        """Movimentos de um produto, na ordem de registro."""
        return [r for r in self._registros if r["codigo"] == codigo]

    def contar(self):
        """Quantidade total de movimentos registrados."""
        return len(self._registros)
'''

_MOVIMENTOS_BUG = _MOVIMENTOS.replace(
    "                total -= r[\"quantidade\"]\n",
    "                total += r[\"quantidade\"]\n")

_RESERVAS = '''\
"""Reservas de mercadoria: separam quantidade do saldo disponível."""


class Reservas:
    """Mantém as reservas com identificador sequencial determinístico."""

    def __init__(self):
        self._reservas = []
        self._proximo_id = 0

    def reservar(self, codigo, quantidade):
        """Cria uma reserva ativa e devolve o identificador dela."""
        if quantidade <= 0:
            raise ValueError(f"quantidade deve ser positiva: {quantidade}")
        self._proximo_id += 1
        self._reservas.append({
            "id": self._proximo_id,
            "codigo": codigo,
            "quantidade": quantidade,
            "ativa": True,
        })
        return self._proximo_id

    def cancelar(self, id_reserva):
        """Desativa a reserva; ValueError se não existe ou já cancelada."""
        for r in self._reservas:
            if r["id"] == id_reserva and r["ativa"]:
                r["ativa"] = False
                return
        raise ValueError(f"reserva inexistente ou cancelada: {id_reserva}")

    def total_reservado(self, codigo):
        """Quantidade somada das reservas ativas de um produto."""
        total = 0
        for r in self._reservas:
            if r["codigo"] == codigo and r["ativa"]:
                total += r["quantidade"]
        return total

    def ativas(self, codigo):
        """Identificadores das reservas ativas do produto, em ordem."""
        return [r["id"] for r in self._reservas
                if r["codigo"] == codigo and r["ativa"]]
'''

_RESERVAS_BUG = _RESERVAS.replace(
    "            if r[\"codigo\"] == codigo and r[\"ativa\"]:\n",
    "            if r[\"codigo\"] == codigo and not r[\"ativa\"]:\n")

_ESTOQUE = '''\
"""Visão consolidada do estoque: saldo físico, reservas e reposição."""
import produtos
from movimentos import Movimentos
from reservas import Reservas


class Estoque:
    """Combina movimentos físicos e reservas de um mesmo depósito."""

    def __init__(self):
        self.movimentos = Movimentos()
        self.reservas = Reservas()

    def disponivel(self, codigo):
        """Saldo físico menos o total reservado do produto."""
        fisico = self.movimentos.saldo(codigo)
        return fisico - self.reservas.total_reservado(codigo)

    def abaixo_do_minimo(self, codigo):
        """True se o disponível caiu abaixo do saldo mínimo do catálogo."""
        return self.disponivel(codigo) < produtos.minimo(codigo)

    def sugestao_reposicao(self, codigo):
        """Quanto comprar para voltar ao saldo mínimo (0 se não precisa)."""
        falta = produtos.minimo(codigo) - self.disponivel(codigo)
        return max(falta, 0)

    def resumo(self, codigo):
        """Dicionário com saldo físico, reservado e disponível."""
        return {
            "fisico": self.movimentos.saldo(codigo),
            "reservado": self.reservas.total_reservado(codigo),
            "disponivel": self.disponivel(codigo),
        }
'''

_ESTOQUE_BUG = _ESTOQUE.replace(
    "        return self.disponivel(codigo) < produtos.minimo(codigo)\n",
    "        return self.disponivel(codigo) <= produtos.minimo(codigo)\n")

_API = '''\
"""Operações de alto nível do inventário, com validações de negócio."""
import produtos
from estoque import Estoque


def novo_inventario():
    """Cria um estoque vazio."""
    return Estoque()


def registrar_entrada(estoque, codigo, quantidade):
    """Valida o produto e registra a chegada de mercadoria."""
    produtos.valida(codigo)
    estoque.movimentos.entrada(codigo, quantidade)


def registrar_saida(estoque, codigo, quantidade):
    """Registra saída; ValueError se não há disponível suficiente."""
    produtos.valida(codigo)
    if quantidade > estoque.disponivel(codigo):
        raise ValueError(f"disponivel insuficiente para {codigo!r}")
    estoque.movimentos.saida(codigo, quantidade)


def reservar(estoque, codigo, quantidade):
    """Reserva mercadoria disponível; devolve o id da reserva."""
    produtos.valida(codigo)
    if quantidade > estoque.disponivel(codigo):
        raise ValueError(f"disponivel insuficiente para {codigo!r}")
    return estoque.reservas.reservar(codigo, quantidade)


def alerta_reposicao(estoque):
    """Códigos abaixo do mínimo, em ordem alfabética."""
    return [c for c in produtos.codigos() if estoque.abaixo_do_minimo(c)]
'''

_API_BUG = _API.replace(
    '''    if quantidade > estoque.disponivel(codigo):
        raise ValueError(f"disponivel insuficiente para {codigo!r}")
    estoque.movimentos.saida(codigo, quantidade)
''',
    '''    estoque.movimentos.saida(codigo, quantidade)
''')

_TEST = '''\
import pytest
from api import (alerta_reposicao, novo_inventario, registrar_entrada,
                 registrar_saida, reservar)
from estoque import Estoque
from movimentos import Movimentos


def test_saldo_entradas_e_saidas():
    mov = Movimentos()
    mov.entrada("parafuso", 10)
    mov.saida("parafuso", 3)
    mov.entrada("parafuso", 2)
    assert mov.saldo("parafuso") == 9


def test_saldo_por_produto_isolado():
    mov = Movimentos()
    mov.entrada("parafuso", 10)
    mov.entrada("porca", 4)
    mov.saida("porca", 1)
    assert mov.saldo("parafuso") == 10
    assert mov.saldo("porca") == 3


def test_quantidade_invalida():
    mov = Movimentos()
    with pytest.raises(ValueError):
        mov.entrada("parafuso", 0)
    with pytest.raises(ValueError):
        mov.saida("parafuso", -2)


def test_reserva_reduz_disponivel():
    est = Estoque()
    est.movimentos.entrada("porca", 10)
    est.reservas.reservar("porca", 4)
    assert est.disponivel("porca") == 6


def test_cancelar_reserva_devolve_disponivel():
    est = Estoque()
    est.movimentos.entrada("porca", 10)
    rid = est.reservas.reservar("porca", 4)
    est.reservas.cancelar(rid)
    assert est.disponivel("porca") == 10
    with pytest.raises(ValueError):
        est.reservas.cancelar(rid)


def test_abaixo_do_minimo_na_borda():
    est = Estoque()
    est.movimentos.entrada("parafuso", 10)
    assert est.abaixo_do_minimo("parafuso") is False
    est.movimentos.saida("parafuso", 1)
    assert est.abaixo_do_minimo("parafuso") is True


def test_sugestao_reposicao():
    est = Estoque()
    est.movimentos.entrada("arruela", 12)
    assert est.sugestao_reposicao("arruela") == 8
    est.movimentos.entrada("arruela", 20)
    assert est.sugestao_reposicao("arruela") == 0


def test_saida_sem_disponivel_levanta():
    inv = novo_inventario()
    registrar_entrada(inv, "parafuso", 5)
    with pytest.raises(ValueError):
        registrar_saida(inv, "parafuso", 8)
    assert inv.disponivel("parafuso") == 5


def test_reserva_conta_para_saida():
    inv = novo_inventario()
    registrar_entrada(inv, "porca", 10)
    reservar(inv, "porca", 7)
    with pytest.raises(ValueError):
        registrar_saida(inv, "porca", 5)
    registrar_saida(inv, "porca", 3)
    assert inv.disponivel("porca") == 0


def test_produto_desconhecido_e_alerta():
    inv = novo_inventario()
    with pytest.raises(ValueError):
        registrar_entrada(inv, "prego", 1)
    registrar_entrada(inv, "parafuso", 3)
    registrar_entrada(inv, "porca", 9)
    registrar_entrada(inv, "arruela", 30)
    assert alerta_reposicao(inv) == ["parafuso"]
'''

_PROMPT = (
    "Este repositório implementa o controle de estoque de um depósito:\n"
    "produtos.py define o catálogo com saldos mínimos, movimentos.py o\n"
    "registro de entradas/saídas, reservas.py as reservas de mercadoria,\n"
    "estoque.py a visão consolidada (disponível, reposição) e api.py as\n"
    "operações de alto nível. Há testes falhando por causa de um bug em\n"
    "um dos arquivos. Use list_files e read_file para explorar o código,\n"
    "run_tests para ver quais testes falham (a suite está em test_app.py),\n"
    "localize o bug e corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "produtos.py": _PRODUTOS,
    "movimentos.py": _MOVIMENTOS,
    "reservas.py": _RESERVAS,
    "estoque.py": _ESTOQUE,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_inventario_v{n}",
        "family": "inventario",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "movimentos.py", _MOVIMENTOS_BUG),
    _monta(2, "reservas.py", _RESERVAS_BUG),
    _monta(3, "estoque.py", _ESTOQUE_BUG),
    _monta(4, "api.py", _API_BUG),
]
