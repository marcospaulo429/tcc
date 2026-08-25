"""Família cache do pool mini-SWE (pré-registro 29).

Cache LRU com TTL lógico: o tempo avança apenas por um relógio de
contador (nunca time.time), garantindo determinismo absoluto.
4 variantes, cada uma com um bug em arquivo/natureza distinta:
  v1 cache.py   — chamada omitida (get não refresca a recência LRU)
  v2 lru.py     — extremo errado (expulsa o MAIS recente, não o menos)
  v3 entrada.py — off-by-one (entrada vale um tick a mais que o TTL)
  v4 relogio.py — passo errado (tick avança passos+1)
"""

_RELOGIO = '''\
"""Relógio lógico por contador — o tempo NUNCA vem de time.time.

O instante atual é um inteiro que começa em 0 e só avança quando
alguém chama tick(). Todo o TTL do cache é medido nesses ticks.
"""


class Relogio:
    """Contador monotônico de instantes lógicos."""

    def __init__(self):
        self._agora = 0

    def agora(self):
        """Instante lógico atual (inteiro >= 0)."""
        return self._agora

    def tick(self, passos=1):
        """Avança o relógio em `passos` (>= 1) e retorna o novo instante."""
        if passos < 1:
            raise ValueError(f"passos deve ser >= 1: {passos}")
        self._agora += passos
        return self._agora
'''

_RELOGIO_BUG = _RELOGIO.replace(
    "        self._agora += passos\n",
    "        self._agora += passos + 1\n")

_ENTRADA = '''\
"""Entrada do cache: valor armazenado + instante de expiração lógico."""


class Entrada:
    """Par (valor, expiração) medido em ticks do relógio lógico."""

    def __init__(self, valor, criada_em, ttl):
        if ttl < 1:
            raise ValueError(f"ttl deve ser >= 1: {ttl}")
        self.valor = valor
        self.criada_em = criada_em
        self.expira_em = criada_em + ttl

    def expirada(self, agora):
        """True se a entrada já expirou no instante `agora`.

        Uma entrada criada em t com ttl=k vale nos instantes t..t+k-1
        e expira exatamente quando o relógio alcança t+k.
        """
        return agora >= self.expira_em

    def restante(self, agora):
        """Ticks de vida restantes (0 se já expirada)."""
        if self.expirada(agora):
            return 0
        return self.expira_em - agora
'''

_ENTRADA_BUG = _ENTRADA.replace(
    "        return agora >= self.expira_em\n",
    "        return agora > self.expira_em\n")

_LRU = '''\
"""Ordem de uso das chaves para a política LRU.

A lista interna vai da chave menos recentemente usada (início) para a
mais recentemente usada (fim). Toda leitura/escrita no cache deve
chamar toca() para levar a chave ao fim.
"""


class OrdemLRU:
    """Mantém a ordem de uso; a vítima de expulsão é o início da lista."""

    def __init__(self):
        self._ordem = []

    def toca(self, chave):
        """Marca a chave como usada agora (move para o fim)."""
        if chave in self._ordem:
            self._ordem.remove(chave)
        self._ordem.append(chave)

    def remove(self, chave):
        """Esquece a chave, se presente."""
        if chave in self._ordem:
            self._ordem.remove(chave)

    def menos_recente(self):
        """Chave menos recentemente usada; KeyError se não há chaves."""
        if not self._ordem:
            raise KeyError("ordem vazia")
        return self._ordem[0]

    def chaves(self):
        """Cópia da ordem atual, da menos para a mais recente."""
        return list(self._ordem)
'''

_LRU_BUG = _LRU.replace(
    "        return self._ordem[0]\n",
    "        return self._ordem[-1]\n")

_CACHE = '''\
"""Cache LRU com TTL lógico, combinando relógio, entradas e ordem de uso."""
from entrada import Entrada
from lru import OrdemLRU


class CacheLRU:
    """Cache de capacidade fixa com expulsão LRU e expiração por TTL.

    O TTL é medido em ticks do relógio lógico injetado; nada aqui
    consulta o relógio de parede.
    """

    def __init__(self, capacidade, ttl, relogio):
        if capacidade < 1:
            raise ValueError(f"capacidade deve ser >= 1: {capacidade}")
        self.capacidade = capacidade
        self.ttl = ttl
        self._relogio = relogio
        self._dados = {}
        self._ordem = OrdemLRU()

    def _expurga(self):
        """Remove todas as entradas expiradas no instante atual."""
        agora = self._relogio.agora()
        for chave in list(self._dados):
            if self._dados[chave].expirada(agora):
                del self._dados[chave]
                self._ordem.remove(chave)

    def put(self, chave, valor):
        """Insere/atualiza a chave, expulsando a LRU se necessário."""
        self._expurga()
        if chave not in self._dados and len(self._dados) >= self.capacidade:
            vitima = self._ordem.menos_recente()
            del self._dados[vitima]
            self._ordem.remove(vitima)
        agora = self._relogio.agora()
        self._dados[chave] = Entrada(valor, agora, self.ttl)
        self._ordem.toca(chave)

    def get(self, chave, padrao=None):
        """Valor da chave (refresca a recência) ou `padrao` se ausente."""
        self._expurga()
        if chave not in self._dados:
            return padrao
        self._ordem.toca(chave)
        return self._dados[chave].valor

    def contem(self, chave):
        """True se a chave está presente e não expirada."""
        self._expurga()
        return chave in self._dados

    def __len__(self):
        """Quantidade de entradas vivas (não expiradas)."""
        self._expurga()
        return len(self._dados)
'''

_CACHE_BUG = _CACHE.replace(
    '''        self._ordem.toca(chave)
        return self._dados[chave].valor
''',
    '''        return self._dados[chave].valor
''')

_API = '''\
"""Helpers de montagem e uso do cache LRU com TTL lógico."""
from cache import CacheLRU
from relogio import Relogio


def cria_cache(capacidade, ttl):
    """Cria (cache, relogio) já conectados; o chamador controla os ticks."""
    relogio = Relogio()
    return CacheLRU(capacidade, ttl, relogio), relogio


def aquece(cache, pares):
    """Insere os pares (chave, valor) na ordem dada; retorna quantos."""
    for chave, valor in pares:
        cache.put(chave, valor)
    return len(pares)
'''

_TEST = '''\
import pytest
from api import aquece, cria_cache
from cache import CacheLRU
from entrada import Entrada
from lru import OrdemLRU
from relogio import Relogio


def test_relogio_tick_unitario():
    r = Relogio()
    assert r.agora() == 0
    r.tick()
    assert r.agora() == 1


def test_relogio_tick_passos():
    r = Relogio()
    assert r.tick(3) == 3


def test_put_get_basico():
    cache, _ = cria_cache(2, 10)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("x", "padrao") == "padrao"


def test_expira_exatamente_no_ttl():
    cache, relogio = cria_cache(2, 2)
    cache.put("a", 1)
    relogio.tick(2)
    assert cache.get("a") is None


def test_vale_antes_do_ttl():
    cache, relogio = cria_cache(2, 3)
    cache.put("a", 1)
    relogio.tick(1)
    assert cache.get("a") == 1


def test_ordem_menos_recente():
    ordem = OrdemLRU()
    ordem.toca("a")
    ordem.toca("b")
    ordem.toca("a")
    assert ordem.menos_recente() == "b"


def test_evicao_lru_basica():
    cache, _ = cria_cache(2, 10)
    aquece(cache, [("a", 1), ("b", 2), ("c", 3)])
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_get_refresca_recencia():
    cache, _ = cria_cache(2, 10)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_len_conta_apenas_vivas():
    cache, relogio = cria_cache(3, 1)
    cache.put("a", 1)
    cache.put("b", 2)
    relogio.tick(1)
    assert len(cache) == 0


def test_entrada_restante():
    entrada = Entrada("v", 5, 3)
    assert entrada.restante(5) == 3
    assert entrada.restante(8) == 0


def test_capacidade_invalida():
    with pytest.raises(ValueError):
        CacheLRU(0, 5, Relogio())
'''

_PROMPT = (
    "Este repositório implementa um cache LRU com TTL lógico (o tempo é um\n"
    "contador, nunca time.time): relogio.py é o relógio por contador,\n"
    "entrada.py guarda valor e expiração, lru.py mantém a ordem de uso,\n"
    "cache.py combina tudo no CacheLRU e api.py oferece helpers de\n"
    "montagem. Há testes falhando por causa de um bug em um dos arquivos.\n"
    "Use list_files e read_file para explorar o código, run_tests para ver\n"
    "quais testes falham (a suite está em test_app.py), localize o bug e\n"
    "corrija reescrevendo o arquivo INTEIRO com write_file."
)

_BASE = {
    "relogio.py": _RELOGIO,
    "entrada.py": _ENTRADA,
    "lru.py": _LRU,
    "cache.py": _CACHE,
    "api.py": _API,
}


def _monta(n: int, bug_file: str, bug_src: str) -> dict:
    repo = dict(_BASE)
    repo[bug_file] = bug_src
    repo["test_app.py"] = _TEST
    return {
        "task_id": f"swe_cache_v{n}",
        "family": "cache",
        "prompt": _PROMPT,
        "repo_files": repo,
        "canonical_files": {bug_file: _BASE[bug_file]},
        "test_code": _TEST,
        "bug_file": bug_file,
    }


TASKS: list[dict] = [
    _monta(1, "cache.py", _CACHE_BUG),
    _monta(2, "lru.py", _LRU_BUG),
    _monta(3, "entrada.py", _ENTRADA_BUG),
    _monta(4, "relogio.py", _RELOGIO_BUG),
]
