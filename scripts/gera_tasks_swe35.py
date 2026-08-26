"""Gera e congela o pool adversarial de landscape (futuro pré-reg 35) — iteração 3.

24 tasks determinísticas (seed fixa): 12 da família P ("poison") e 12 da F ("free").
Formato idêntico a environment/tasks_swe.py MAIS os campos `boot_note` e `char_budget`.

Família P — summarize destrói informação necessária e irrecuperável:
  checksum.py é PEQUENO (~2k chars; o echo do write não estoura o keep), mas a
  fórmula de fold correta está definida SOMENTE em docs/spec_mixing.md (~9k chars,
  coeficientes de rotação R1/R2 não adivinháveis do código) e as constantes de
  mixing PARAM_A/PARAM_B chegam SOMENTE pela boot_note. As mensagens de falha
  apontam explicitamente para docs/spec_mixing.md. O caminho mínimo pré-write
  (prompt + boot + TEST + read spec [+ read checksum]) cruza o gatilho REAL do
  summarize (estimate_tokens = chars//4 > 4500 ⇒ >18.000 chars) ANTES do primeiro
  write → default(4500) mata a boot_note → no máximo 3/5 (os 3 testes genéricos).
  keep-always fecha 5/5 com <24.000 chars totais (<8192 tokens reais ≈ chars/3.3).
  5 testes: 3 genéricos (fórmula certa, sem constantes) + 2 pontos de mixing.

Família F — summarize estritamente melhor; keep leva a overflow REAL:
  boot_note inócua (mesmo comprimento da P pareada); pipeline de 2 estágios
  (normaliza → agrega), 1 bug por estágio; a suite (5 testes) revela o estágio 2
  só depois do estágio 1 consertado. O conserto do agrega exige ler o contrato
  em formato.py (fator de escala não adivinhável: o diff da falha OCULTA o
  esperado). Caminho keep canônico (TEST; READ+WRITE normaliza; READ agrega;
  READ formato; WRITE agrega) cruza 8192·3.3≈27.033 chars no turno 6 → R=0;
  sob summarize (keep_last=6) toda chamada fica <20.000 chars e o episódio
  completa. Travessia do threshold DEPOIS do 1º write. Frações: 0→0/5, 1→2/5,
  2→5/5. Mensagens de falha verbosas (blocos de 3000–3500 chars no pytest bruto).

Validações (task reprovada aborta a geração):
  1. Execução real em sandbox: canônica 5/5; P bug inicial 0/5 e fórmula certa
     sem constantes EXATAMENTE 3/5; F progressão 0/5 → 2/5 → 5/5.
  2. Não-vazamento no blob VISÍVEL (repo_files/test_code — NUNCA inspecionando
     os canônicos): PARAM_A/PARAM_B ausentes de tudo; R1/R2 e a fórmula de fold
     ausentes de tudo FORA de docs/spec_mixing.md (na spec é o ponto).
  3. Orçamentos medidos por SIMULAÇÃO REAL (EpisodeV2 + HarnessV2 + sandbox, LLM
     roteirizado): P pré-write >18.000 (gatilho real) e keep total <24.000, boot
     morta no write sob default no caminho canônico mínimo (TEST + READ checksum
     + READ spec); F pré-1º-write
     <14.850, pós-1º-write ≥14.850, turno 5 ≤27.033, turno 6 >27.033 (overflow),
     máximo por chamada sob default <20.000.
  4. Orçamentos gravados por task no campo `char_budget`; boot F pareada com a P.

Uso: uv run python scripts/gera_tasks_swe35.py [--out environment/tasks_swe35.py]
"""
import argparse
import os
import pprint
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.harness_v2 import HarnessV2  # noqa: E402
from agent.loop_v2 import EpisodeV2  # noqa: E402
from environment.sandbox import Sandbox  # noqa: E402
from trajectories.recorder import Recorder  # noqa: E402

M = 10007  # primo do anel de mixing
SEED_BASE = 3500
N_POR_FAMILIA = 12

CHARS_POR_TOKEN = 3.3
MAX_MODEL_CHARS = int(8192 * CHARS_POR_TOKEN)      # overflow real: 27033 chars
THRESHOLD_REF_CHARS = int(4500 * CHARS_POR_TOKEN)  # referência do pré-reg: 14850
THRESHOLD_EST_CHARS = 4500 * 4                     # gatilho REAL (estimate_tokens=chars//4)

SPEC_PATH = "docs/spec_mixing.md"

# -- gerador determinístico de texto de enchimento ---------------------------
_S1 = ("O pipeline de ingestão", "A rotina de conciliação", "O worker de replicação",
       "O serviço de fila secundária", "O coletor de métricas", "O agendador noturno",
       "A camada de persistência", "O verificador de integridade", "O roteador de eventos",
       "O compactador de segmentos", "O daemon de sincronização", "O monitor de quorum")
_S2 = ("processa", "valida", "reconcilia", "propaga", "reindexa", "compacta",
       "reprocessa", "arquiva", "particiona", "normaliza", "replica", "audita")
_S3 = ("os lotes da fila secundária", "os manifestos de sincronização",
       "os segmentos do diário de operações", "as janelas de agregação por origem",
       "os identificadores de pacote pendentes", "os registros do catálogo de rotas",
       "as entradas do índice invertido", "os deltas do snapshot incremental",
       "os cursores de leitura por consumidor", "os carimbos do relógio lógico")
_S4 = ("a cada janela de dez minutos", "sem intervenção manual",
       "sob supervisão do agendador", "antes do corte diário",
       "respeitando o contrato de idempotência", "com retentativa exponencial",
       "em ordem estável de chegada", "após o handshake de quorum",
       "dentro do orçamento de latência", "com trilha de auditoria completa")


def _frase(rng: random.Random) -> str:
    return f"{rng.choice(_S1)} {rng.choice(_S2)} {rng.choice(_S3)} {rng.choice(_S4)}."


def _texto(rng: random.Random, alvo_chars: int, por_linha: int = 1) -> str:
    """Frases determinísticas até atingir ~alvo_chars (>= alvo)."""
    linhas, total = [], 0
    while total < alvo_chars:
        frase = " ".join(_frase(rng) for _ in range(por_linha))
        linhas.append(frase)
        total += len(frase) + 1
    return "\n".join(linhas)


def _modulo_padding(rng: random.Random, titulo: str, alvo_chars: int) -> str:
    corpo = _texto(rng, alvo_chars - len(titulo) - 20)
    return f'"""{titulo}\n\n{corpo}\n"""\n'


# -- simulação real (EpisodeV2 roteirizado) -----------------------------------
class _ScriptLLM:
    """LLM roteirizado: devolve o script na ordem e grava cada prompt enviado."""

    def __init__(self, script: list[str]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def config(self) -> dict:
        return {"model": "script", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kw):
        self.calls.append([dict(m) for m in messages])
        if not self.script:
            raise AssertionError("script do episódio simulado esgotou")
        return {"text": self.script.pop(0), "prompt_tokens": 0,
                "completion_tokens": 0, "wall_time_s": 0.0}


def _blk(content: str) -> str:
    return "```python\n" + content + "```"  # content já termina em \n


def _chars(messages: list[dict]) -> int:
    return sum(len(m.get("content") or "") for m in messages)


def _boot_em(messages: list[dict], boot: str) -> bool:
    return any((m.get("content") or "") == boot for m in messages)


def _roda_ep(task: dict, script: list[str], harness: HarnessV2):
    llm = _ScriptLLM(script)
    with tempfile.TemporaryDirectory(prefix="swe35_ep_") as d:
        ep = EpisodeV2(task, llm, harness, Recorder(Path(d) / "traj"))
        try:
            res = ep.run()
        finally:
            ep.sandbox.cleanup()
    return res, llm.calls


def _harness_keep() -> HarnessV2:
    return HarnessV2(summarize_threshold_tokens=10**9, max_turns=25, keep_last=6)


def _harness_default() -> HarnessV2:
    return HarnessV2(summarize_threshold_tokens=4500, max_turns=25, keep_last=6)


# -- família P ("poison") ----------------------------------------------------
P_PROMPT_CHARS = 6300
P_BOOT_HEAD_CHARS = 700
P_BOOT_TAIL_CHARS = 850
P_SPEC_CHARS = 9500
P_CHECKSUM_DOC_CHARS = 700

MIXING_PY = '''"""Mixing modular do serviço de checksum.

O mixing linear (x*a + b) %% M dispersa identificadores no anel Z_M.
Os parâmetros (a, b) variam por instalação e chegam pela nota de deploy;
nenhum valor de instalação é versionado neste repositório.
"""

M = 10007  # primo do anel; NÃO alterar


def mix(x, a, b):
    """Mistura linear modular usada na assinatura de pacotes."""
    return (x * a + b) %% M
'''.replace("%%", "%")

CHECKSUM_TPL = '''"""Assinatura e checksum de pacotes do serviço de sincronização.

{doc}
"""
from mixing import M, mix

# Parâmetros de mixing DESTA instalação (ver nota de deploy; os valores
# versionados abaixo são apenas placeholders de desenvolvimento).
PARAM_A = {a}
PARAM_B = {b}


def checksum(valores):
    """Fold do checksum; a fórmula normativa está em docs/spec_mixing.md."""
    h = 0
    for v in valores:
        h = {fold} % M
    return h


def assina(x):
    """Assinatura do identificador x com os parâmetros da instalação."""
    return mix(x, PARAM_A, PARAM_B)


def verifica(valores, esperado):
    """True sse o checksum dos valores bate com o esperado."""
    return checksum(valores) == esperado
'''

TESTS_P_TPL = '''"""Suite do serviço de checksum (5 testes)."""
from checksum import assina, checksum

_SPEC = ("a formula normativa do fold NAO e a versionada em checksum.py: esta "
         "definida em docs/spec_mixing.md — leia docs/spec_mixing.md ANTES de "
         "reescrever checksum.py INTEIRO com write_file")
_NOTA = ("os parametros PARAM_A/PARAM_B desta instalacao chegam pela nota de "
         "deploy (nao sao versionados) e a especificacao normativa do fold "
         "esta em docs/spec_mixing.md")


def test_checksum_fold_unitario():
    assert checksum([@v1@]) == @E1@, "checksum([@v1@]) divergiu do normativo: " + _SPEC


def test_checksum_fold_dupla():
    assert checksum([@v1@, @v2@]) == @E2@, "checksum de dois valores divergiu: " + _SPEC


def test_checksum_sensivel_a_ordem():
    assert checksum([@v1@, @v2@]) != checksum([@v2@, @v1@]), \\
        "o fold normativo e sensivel a ordem dos valores: " + _SPEC


def test_assina_ponto_a():
    assert assina(@x1@) == @e1@, "assina(@x1@) divergiu da instalacao: " + _NOTA


def test_assina_ponto_b():
    assert assina(@x2@) == @e2@, "assina(@x2@) divergiu da instalacao: " + _NOTA
'''

PROMPT_P_BASE = (
    "Este repositório implementa o serviço de assinatura e checksum de pacotes: "
    "mixing.py traz o mixing modular, checksum.py o fold de checksum e a assinatura "
    "da instalação, auditoria.py documenta o procedimento de verificação e "
    "docs/spec_mixing.md é a ESPECIFICAÇÃO NORMATIVA do algoritmo de fold. Há "
    "testes falhando (a suite está em test_app.py). A fórmula de fold correta "
    "desta instalação está definida SOMENTE em docs/spec_mixing.md — leia "
    "docs/spec_mixing.md e o arquivo suspeito com read_file antes de editar, e "
    "corrija reescrevendo o arquivo INTEIRO com write_file.\n\n"
    "Contexto operacional:\n")

_PRIMOS_2DIG = (11, 13, 17, 19, 23, 29, 37, 41, 43, 47,
                53, 59, 61, 67, 71, 73, 79, 83, 89, 97)


def _spec_md(rng: random.Random, r1: int, r2: int, alvo_chars: int) -> str:
    partes = [
        "# Especificação normativa do mixing e do fold de checksum\n",
        "\n## Escopo e vigência\n\n" + _texto(rng, 2100) + "\n",
        ("\n## Fold de checksum (normativo)\n\n"
         "O fold de checksum desta instalação NÃO é o fold aditivo ingênuo. A "
         "recorrência normativa, aplicada da esquerda para a direita sobre a "
         "sequência de valores v_1..v_n, é:\n\n"
         "    h_0 = 0\n"
         f"    h_k = (h_(k-1) * {r1} + v_k * {r2}) % 10007\n\n"
         f"Os coeficientes de rotação R1 = {r1} e R2 = {r2} são fixados por esta "
         "especificação e não podem ser alterados. A ordem das operações importa: "
         "o acumulador é multiplicado por R1 ANTES da soma, e cada valor corrente "
         "entra multiplicado por R2.\n"),
        ("\n## Assinatura e parâmetros de instalação\n\n"
         "PARAM_A e PARAM_B não são versionados nem constam desta especificação: "
         "chegam exclusivamente pela nota de deploy de cada instalação e devem ser "
         "aplicados junto com o fold normativo em qualquer correção de checksum.py.\n"),
        "\n## Notas operacionais\n\n",
    ]
    corpo = "".join(partes)
    return corpo + _texto(rng, alvo_chars - len(corpo)) + "\n"


def _gera_p(i: int) -> dict:
    rng = random.Random(SEED_BASE + i)
    while True:
        a_const = rng.randrange(1009, 9973)
        b_const = rng.randrange(1009, 9973)
        x1, x2 = rng.randrange(101, 9006), rng.randrange(101, 9006)
        v1, v2 = rng.randrange(2, 98), rng.randrange(2, 98)
        r1, r2 = rng.sample(_PRIMOS_2DIG, 2)
        if x1 == x2 or v1 == v2:
            continue
        e1, e2 = (x1 * a_const + b_const) % M, (x2 * a_const + b_const) % M
        E1 = (v1 * r2) % M
        E2 = (E1 * r1 + v2 * r2) % M
        E_swap = (((v2 * r2) % M) * r1 + v1 * r2) % M
        # placeholders (1, 0) falham AMBOS os pontos de mixing…
        if e1 == x1 % M or e2 == x2 % M:
            continue
        # …e o fold aditivo bugado falha os genéricos (o bug é simétrico p/ ordem)
        if E1 == v1 % M or E2 == (v1 + v2) % M or E2 == E_swap:
            continue
        doc = _texto(random.Random(SEED_BASE + 100 + i), P_CHECKSUM_DOC_CHARS)
        bug = CHECKSUM_TPL.format(doc=doc, a=1, b=0, fold="(h + v)")
        canon = CHECKSUM_TPL.format(doc=doc, a=a_const, b=b_const,
                                    fold=f"(h * {r1} + v * {r2})")
        spec = _spec_md(random.Random(SEED_BASE + 200 + i), r1, r2, P_SPEC_CHARS)
        test_code = TESTS_P_TPL
        for tok, val in {"@v1@": v1, "@v2@": v2, "@x1@": x1, "@x2@": x2,
                         "@E1@": E1, "@E2@": E2, "@e1@": e1, "@e2@": e2}.items():
            test_code = test_code.replace(tok, str(val))
        repo = {
            "mixing.py": MIXING_PY,
            "checksum.py": bug,
            SPEC_PATH: spec,
            "auditoria.py": _modulo_padding(random.Random(SEED_BASE + 300 + i),
                                            "Procedimento de auditoria da assinatura.", 1600),
            "test_app.py": test_code,
        }
        visivel = "".join(repo.values())  # canônica NUNCA entra na checagem de ausência
        if str(a_const) in visivel or str(b_const) in visivel:
            continue
        fora_spec = "".join(v for k, v in repo.items() if k != SPEC_PATH)
        # fórmula/coeficientes normativos só podem existir na spec
        if str(r1) in fora_spec or str(r2) in fora_spec:
            continue
        break

    prompt = PROMPT_P_BASE + _texto(random.Random(SEED_BASE + 400 + i),
                                    P_PROMPT_CHARS - len(PROMPT_P_BASE))
    boot_rng = random.Random(SEED_BASE + 500 + i)
    boot_note = (
        "Nota do deploy (leia antes de mexer no serviço de checksum):\n"
        + _texto(boot_rng, P_BOOT_HEAD_CHARS) + "\n"
        + f"IMPORTANTE: nesta instalação o serviço de checksum usa PARAM_A={a_const} "
          f"e PARAM_B={b_const}; os placeholders de desenvolvimento versionados no "
          "repositório NÃO valem aqui e precisam ser trocados junto com qualquer correção.\n"
        + _texto(boot_rng, P_BOOT_TAIL_CHARS))
    if str(a_const) not in boot_note or str(b_const) not in boot_note:
        raise AssertionError("boot_note P sem as constantes")

    task = {
        "task_id": f"p_swe35_{i:02d}",
        "family": "p_checksum",
        "prompt": prompt,
        "boot_note": boot_note,
        "repo_files": repo,
        "canonical_files": {"checksum.py": canon},
        "bug_file": "checksum.py",
        "test_code": test_code,
    }
    task["char_budget"] = _budget_p(task)
    return task


def _budget_p(task: dict) -> dict:
    """Orçamentos por simulação REAL do caminho canônico mínimo.
    keep: TEST → READ checksum → READ spec → WRITE checksum (auto_test 5/5).
    default: mesmo caminho + caminho fraco SEM ler checksum.py (blind write):
    nos dois a boot_note tem de estar MORTA na chamada do WRITE."""
    canon = task["canonical_files"]["checksum.py"]
    script = ["TEST", "READ checksum.py", f"READ {SPEC_PATH}",
              "WRITE checksum.py", _blk(canon)]
    res_k, calls_k = _roda_ep(task, script, _harness_keep())
    pre_write = _chars(calls_k[3])
    echo = len(f"WRITE checksum.py\n```python\n{canon}\n```")
    keep_total = pre_write + echo + len("Arquivo checksum.py gravado.") + 40

    res_d, calls_d = _roda_ep(task, script, _harness_default())
    script_fraco = ["TEST", f"READ {SPEC_PATH}", "WRITE checksum.py", _blk(canon)]
    res_f, calls_f = _roda_ep(task, script_fraco, _harness_default())
    boot = task["boot_note"]
    src = {k: v for k, v in task["repo_files"].items() if k != "test_app.py"}
    return {
        "prompt": len(task["prompt"]),
        "boot_note": len(boot),
        "spec_chars": len(task["repo_files"][SPEC_PATH]),
        "repo_src": sum(len(v) for v in src.values()),
        "pre_write": pre_write,
        "pre_write_sem_checksum": _chars(calls_f[2]),
        "keep_total_est": keep_total,
        "sim_keep_ok": bool(res_k["success"] and len(calls_k) == 5
                            and _boot_em(calls_k[3], boot)),
        "sim_default_ok": bool(res_d["success"] and res_f["success"]),
        "boot_morta_default": not _boot_em(calls_d[3], boot),
        # no caminho fraco (TEST + READ spec, blind write) a boot fica DENTRO da
        # janela keep_last=6 — estruturalmente impossível morrer com <3 ações
        # prévias; o que se garante é a travessia do gatilho (chars > 18000).
        "boot_viva_blind_write": _boot_em(calls_f[2], boot),
    }


# -- família F ("free") ------------------------------------------------------
# Pipeline de 2 estágios; bug por estágio; o conserto do agrega exige formato.py.
F_ORDEM = ("normaliza.py", "agrega.py")
LARGURA_MSG_FALHA = 3050  # chars da mensagem de _falha (pytest renderiza ~+390)
F_PROMPT_CHARS = 1250
F_NORM_DOC_CHARS = 6050
F_AGREGA_DOC_CHARS = 1400
F_FORMATO_DOC_CHARS = 3600  # ×2 blocos + contrato ≈ 8.0k

NORMALIZA_TPL = '''"""Normalização de registros de consumo (estágio 1 do pipeline).

{doc}
"""


def normaliza(registros):
    """Nome sem espaços nas pontas e em minúsculas; descarta valor não positivo."""
    saida = []
    for nome, valor in registros:
{corpo}
    return saida
'''

CORPO_NORM_BUG = "        saida.append((nome.strip().lower(), valor))"
CORPO_NORM_OK = ("        if valor > 0:\n"
                 "            saida.append((nome.strip().lower(), valor))")

AGREGA_TPL = '''"""Agregação de totais publicados por nome (estágio 2 do pipeline).

{doc}
"""
{imp}

def agrega(registros):
    """Total publicado por nome, conforme o contrato de agregação (formato.py)."""
    totais = {{}}
    for nome, valor in registros:
        totais[nome] = {expr}
    return {ret}
'''

AGREGA_BUG = {"imp": "", "expr": "valor", "ret": "totais"}
AGREGA_OK = {"imp": "from formato import FATOR_CONTRATO\n",
             "expr": "totais.get(nome, 0) + valor",
             "ret": "{nome: total * FATOR_CONTRATO for nome, total in totais.items()}"}

FORMATO_TPL = '''"""Contrato de agregação e formato de publicação dos totais.

{doc1}

CONTRATO DE AGREGACAO (normativo): o total publicado por nome e a SOMA dos
valores normalizados daquele nome MULTIPLICADA pelo fator de escala do contrato
(FATOR_CONTRATO abaixo). Publicar a soma crua, sem o fator, viola o contrato.

{doc2}
"""

FATOR_CONTRATO = {fator}
'''

# Substituição por tokens @X@ (o corpo tem chaves demais para str.format).
TESTS_F_TPL = '''"""Suite do pipeline de consumo (5 testes, 2 estágios encadeados)."""
from agrega import agrega
from normaliza import normaliza

DADOS = @DADOS@
NORM_ESP = @NORM_ESP@
TOT_ESP = @TOT_ESP@
T4_IN = @T4_IN@
T4_ESP = @T4_ESP@
T5_IN = @T5_IN@
T5_ESP = @T5_ESP@

OCULTO = "<definido pelo contrato de agregacao em formato.py>"
LARGURA_MSG = @LARGURA@
_ENCH = ("contexto do runner: lote unico, ordem estavel de chegada, sem retentativa "
         "pendente e trilha de auditoria completa para esta janela de processamento")
_DICA = {
    "normaliza.py": ("o proximo conserto e em normaliza.py; reescreva normaliza.py "
                     "INTEIRO com write_file e rode os testes de novo"),
    "agrega.py": ("o proximo conserto e em agrega.py; o contrato de agregacao esta "
                  "em formato.py — leia formato.py ANTES de reescrever agrega.py "
                  "INTEIRO com write_file"),
}


def _falha(arquivo, estagio, esperado, obtido):
    linhas = [
        f"FALHA no estagio {estagio} do pipeline (arquivo {arquivo}).",
        "Tabela de linhas processadas nesta execucao (entrada bruta da ingestao):",
    ]
    for k, (nome, valor) in enumerate(DADOS):
        linhas.append(f"  linha {k:02d} | nome={nome!r} | valor={valor} "
                      f"| origem=ingestao | lote=unico | rota=padrao")
    linhas += [
        "Diff esperado-vs-obtido no ponto da falha:",
        f"  esperado: {esperado!r}",
        f"  obtido..: {obtido!r}",
        "Traceback sintetico do runner (mais recente por ultimo):",
        '  File "runner/executa_lote.py", line 88, in executa_lote',
        f'  File "{arquivo}", line 12, in {estagio}',
        f"  EstagioInvalidoError: saida do estagio {estagio} diverge do contrato",
        "Contexto adicional (janelas anteriores, para conferencia):",
    ]
    corpo = "\\n".join(linhas)
    rodape = "\\nDIAGNOSTICO: " + _DICA[arquivo] + "."
    k = 0
    while len(corpo) + len(rodape) < LARGURA_MSG:
        corpo += f"\\n  janela {k:03d} | {_ENCH}"
        k += 1
    return corpo[:LARGURA_MSG - len(rodape)] + rodape


def _gate_normaliza():
    """Gate encadeado: falhas do agrega so aparecem com o normaliza consertado."""
    obtido = normaliza(DADOS)
    ok = obtido == NORM_ESP
    assert ok, _falha("normaliza.py", "normaliza", NORM_ESP, obtido)
    return obtido


def test_normaliza_minusculas_espacos_e_filtro():
    entrada = [("  @N1@  ", @w1@), ("@n3@", 0)]
    esperado = [("@n1@", @w1@)]
    obtido = normaliza(entrada)
    ok = obtido == esperado
    assert ok, _falha("normaliza.py", "normaliza", esperado, obtido)


def test_normaliza_descarta_nao_positivo():
    entrada = [("@n3@", -@d@), ("@N2@", @w2@)]
    esperado = [("@n2@", @w2@)]
    obtido = normaliza(entrada)
    ok = obtido == esperado
    assert ok, _falha("normaliza.py", "normaliza", esperado, obtido)


def test_agrega_contrato_com_duplicatas():
    regs = _gate_normaliza()
    obtido = agrega(regs)
    ok = obtido == TOT_ESP
    assert ok, _falha("agrega.py", "agrega", OCULTO, obtido)


def test_agrega_contrato_sem_duplicatas():
    _gate_normaliza()
    obtido = agrega(T4_IN)
    ok = obtido == T4_ESP
    assert ok, _falha("agrega.py", "agrega", OCULTO, obtido)


def test_agrega_contrato_tres_ocorrencias():
    _gate_normaliza()
    obtido = agrega(T5_IN)
    ok = obtido == T5_ESP
    assert ok, _falha("agrega.py", "agrega", OCULTO, obtido)
'''

_NOMES = ("ana", "bruno", "carla", "davi", "elisa", "fabio", "gina", "hugo")

PROMPT_F_BASE = (
    "Este repositório implementa o pipeline de consumo em dois estágios: "
    "normaliza.py (estágio 1, limpeza dos registros) e agrega.py (estágio 2, "
    "totais publicados por nome conforme o contrato de agregação definido em "
    "formato.py); leitura.py e catalogo.py documentam a ingestão e o catálogo de "
    "origens. Há um bug em cada estágio e a suite (test_app.py) revela um estágio "
    "de cada vez, na ordem do fluxo. Use run_tests para ver a falha atual, corrija "
    "UM arquivo por vez reescrevendo-o INTEIRO com write_file e rode os testes de "
    "novo: a mensagem de falha aponta o próximo arquivo e o que ler antes.\n\n"
    "Contexto operacional:\n")


def _gera_f(i: int, boot_len: int) -> dict:
    rng = random.Random(SEED_BASE + 1000 + i)
    n1, n2, n3, n4 = rng.sample(_NOMES, 4)
    w = [rng.randrange(2, 61) for _ in range(5)]
    d = rng.randrange(1, 9)
    u = [rng.randrange(2, 41) for _ in range(3)]
    fator = rng.choice((3, 4, 6, 7, 8, 9))  # ≠1: soma crua nunca satisfaz o contrato
    dados = [(f"  {n1.upper()}  ", w[0]), (n2.title(), w[1]), (f" {n1} ", w[2]),
             (n3, -d), (n2, w[3]), (n4.upper(), w[4])]
    norm_esp = [(n.strip().lower(), v) for n, v in dados if v > 0]
    soma: dict = {}
    for n, v in norm_esp:
        soma[n] = soma.get(n, 0) + v
    tot_esp = {n: s * fator for n, s in soma.items()}
    t4_in, t4_esp = [(n4, w[4])], {n4: w[4] * fator}
    t5_in = [(n3, u[0]), (n3, u[1]), (n3, u[2])]
    t5_esp = {n3: sum(u) * fator}

    subs = {"@DADOS@": repr(dados), "@NORM_ESP@": repr(norm_esp),
            "@TOT_ESP@": repr(tot_esp), "@T4_IN@": repr(t4_in),
            "@T4_ESP@": repr(t4_esp), "@T5_IN@": repr(t5_in),
            "@T5_ESP@": repr(t5_esp), "@LARGURA@": str(LARGURA_MSG_FALHA),
            "@n1@": n1, "@N1@": n1.upper(), "@n2@": n2, "@N2@": n2.upper(),
            "@n3@": n3, "@w1@": str(w[0]), "@w2@": str(w[1]), "@d@": str(d)}
    test_code = TESTS_F_TPL
    for tok, val in subs.items():
        test_code = test_code.replace(tok, val)

    doc1 = _texto(random.Random(SEED_BASE + 1100 + i), F_NORM_DOC_CHARS)
    doc2 = _texto(random.Random(SEED_BASE + 1200 + i), F_AGREGA_DOC_CHARS)
    doc3a = _texto(random.Random(SEED_BASE + 1250 + i), F_FORMATO_DOC_CHARS)
    doc3b = _texto(random.Random(SEED_BASE + 1270 + i), F_FORMATO_DOC_CHARS)
    repo = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_BUG),
        "agrega.py": AGREGA_TPL.format(doc=doc2, **AGREGA_BUG),
        "formato.py": FORMATO_TPL.format(doc1=doc3a, doc2=doc3b, fator=fator),
        "leitura.py": _modulo_padding(random.Random(SEED_BASE + 1300 + i),
                                      "Ingestão de registros de consumo.", 1800),
        "catalogo.py": _modulo_padding(random.Random(SEED_BASE + 1400 + i),
                                       "Catálogo de origens do pipeline.", 1500),
        "test_app.py": test_code,
    }
    canonical = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_OK),
        "agrega.py": AGREGA_TPL.format(doc=doc2, **AGREGA_OK),
    }
    prompt = PROMPT_F_BASE + _texto(random.Random(SEED_BASE + 1600 + i),
                                    F_PROMPT_CHARS - len(PROMPT_F_BASE))
    boot_rng = random.Random(SEED_BASE + 1700 + i)
    boot_note = ("Nota do deploy (status da janela de manutenção, sem ação necessária):\n"
                 + _texto(boot_rng, boot_len))[:boot_len]  # pareada com a P de mesmo i

    task = {
        "task_id": f"f_swe35_{i:02d}",
        "family": "f_pipeline",
        "prompt": prompt,
        "boot_note": boot_note,
        "repo_files": repo,
        "canonical_files": canonical,
        "bug_file": "normaliza.py",
        "test_code": test_code,
    }
    task["char_budget"] = _budget_f(task)
    return task


def _budget_f(task: dict) -> dict:
    """Orçamentos por simulação REAL do caminho canônico mínimo (6 turnos):
    TEST → READ normaliza → WRITE normaliza (auto_test) → READ agrega →
    READ formato → WRITE agrega (auto_test 5/5). Chamadas LLM (com fase 2 do
    WRITE): [t1, t2, t3, t3b, t4, t5, t6, t6b]."""
    canon_n = task["canonical_files"]["normaliza.py"]
    canon_a = task["canonical_files"]["agrega.py"]
    script = ["TEST", "READ normaliza.py", "WRITE normaliza.py", _blk(canon_n),
              "READ agrega.py", "READ formato.py", "WRITE agrega.py", _blk(canon_a)]
    res_k, calls_k = _roda_ep(task, script, _harness_keep())
    res_d, calls_d = _roda_ep(task, script, _harness_default())
    boot = task["boot_note"]
    src = {k: v for k, v in task["repo_files"].items() if k != "test_app.py"}
    return {
        "prompt": len(task["prompt"]),
        "boot_note": len(boot),
        "repo_src": sum(len(v) for v in src.values()),
        "msg_falha_chars": LARGURA_MSG_FALHA,
        "pre_primeiro_write": _chars(calls_k[2]),
        "pos_primeiro_write": _chars(calls_k[4]),
        "keep_turno5": _chars(calls_k[5]),
        "keep_turno6": _chars(calls_k[6]),
        "keep_write1_total": _chars(calls_k[3]) + len(canon_n),
        "summ_max_call": max(_chars(c) for c in calls_d),
        "sim_keep_ok": bool(res_k["success"] and len(calls_k) == 8),
        "sim_default_ok": bool(res_d["success"] and len(calls_d) == 8
                               and not _boot_em(calls_d[6], boot)),
    }


# -- validação ----------------------------------------------------------------
REQUIRED_KEYS = {"task_id", "family", "prompt", "boot_note", "repo_files",
                 "canonical_files", "test_code", "bug_file", "char_budget"}
_PARAM_RE = re.compile(r"PARAM_A=(\d+) e PARAM_B=(\d+)")
_FOLD_RE = re.compile(r"h = \(h \* (\d+) \+ v \* (\d+)\) % M")


def _run(files: dict[str, str], test_code: str) -> tuple[dict, float]:
    sb = Sandbox()
    try:
        for rel, content in files.items():
            sb.write_file(rel, content)
        t0 = time.monotonic()
        return sb.run_tests(test_code), time.monotonic() - t0
    finally:
        sb.cleanup()


def _pytest_bruto(files: dict[str, str], test_code: str) -> str:
    """Saída COMPLETA do pytest (sem a truncagem do Sandbox), mesmos flags/env."""
    with tempfile.TemporaryDirectory(prefix="swe35_full_") as d:
        for rel, content in files.items():
            Path(d, rel).parent.mkdir(parents=True, exist_ok=True)
            Path(d, rel).write_text(content, encoding="utf-8")
        Path(d, "test_solution.py").write_text(test_code, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "test_solution.py",
             "-q", "--tb=line", "-p", "no:cacheprovider"],
            cwd=d, env={"PATH": os.environ.get("PATH", ""),
                        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            capture_output=True, text=True, timeout=60)
        return (proc.stdout or "") + (proc.stderr or "")


def _blocos_falha(saida: str) -> list[str]:
    """Blocos 'E   AssertionError: …' + continuações indentadas do --tb=line."""
    blocos, atual = [], None
    for ln in saida.splitlines():
        if ln.startswith("E   AssertionError:"):
            if atual:
                blocos.append("\n".join(atual))
            atual = [ln]
        elif atual is not None and ln.startswith("    "):
            atual.append(ln)
        elif atual is not None:
            blocos.append("\n".join(atual))
            atual = None
    if atual:
        blocos.append("\n".join(atual))
    return blocos


def _valida_p(task: dict) -> list[str]:
    erros = []
    repo, cb = task["repo_files"], task["char_budget"]
    m = _PARAM_RE.search(task["boot_note"])
    if not m:
        return ["boot_note P sem constantes extraíveis"]
    a_const, b_const = m.group(1), m.group(2)
    canon = task["canonical_files"]["checksum.py"]
    mf = _FOLD_RE.search(canon)
    if not mf:
        return ["canônica P sem fold normativo extraível"]
    r1, r2 = mf.group(1), mf.group(2)
    spec = repo.get(SPEC_PATH, "")

    # não-vazamento (NUNCA inspeciona canônicos em checagem de ausência)
    visivel = "".join(repo.values())
    if a_const in visivel or b_const in visivel:
        erros.append("constantes PARAM aparecem no blob visível")
    fora_spec = "".join(v for k, v in repo.items() if k != SPEC_PATH)
    if r1 in fora_spec or r2 in fora_spec or "(h * " in fora_spec:
        erros.append("fórmula/coeficientes normativos vazam fora da spec")
    if f"R1 = {r1}" not in spec or f"R2 = {r2}" not in spec:
        erros.append("spec não define R1/R2 do fold canônico")
    if not 8000 <= len(spec) <= 9800:
        erros.append(f"spec com {len(spec)} chars fora de [8000, 9800]")
    if "docs/spec_mixing.md" not in task["test_code"]:
        erros.append("mensagens de falha não apontam para docs/spec_mixing.md")
    if a_const not in canon or b_const not in canon:
        erros.append("canônica não usa as constantes da boot_note")

    # execução real: bug 0/5; canônica 5/5; fórmula certa sem constantes 3/5
    res_0, _ = _run(repo, task["test_code"])
    if not (res_0["total"] == 5 and res_0["passed"] == 0):
        erros.append(f"estado inicial != 0/5 ({res_0['passed']}/{res_0['total']})")
    res_c, dur_c = _run({**repo, "checksum.py": canon}, task["test_code"])
    if not (res_c["success"] and res_c["total"] == 5):
        erros.append(f"canônica != 5/5 ({res_c['passed']}/{res_c['total']})")
    if dur_c >= 10.0:
        erros.append(f"suite lenta ({dur_c:.1f}s)")
    errado = re.sub(r"PARAM_A = \d+", "PARAM_A = 1",
                    re.sub(r"PARAM_B = \d+", "PARAM_B = 0", canon))
    res_e, _ = _run({**repo, "checksum.py": errado}, task["test_code"])
    if not (res_e["passed"] == 3 and res_e["total"] == 5):
        erros.append(f"fórmula certa sem constantes != 3/5 "
                     f"({res_e['passed']}/{res_e['total']})")

    # orçamentos (simulação real): poison morde ANTES do write; keep fecha folgado
    if not (cb["sim_keep_ok"] and cb["sim_default_ok"]):
        erros.append("simulação P falhou (keep 5/5 c/ boot viva OU default não completa)")
    if not cb["boot_morta_default"]:
        erros.append("default NÃO summariza antes do write (boot viva)")
    if cb["pre_write"] < THRESHOLD_EST_CHARS + 200:
        erros.append(f"P: pré-write {cb['pre_write']} < {THRESHOLD_EST_CHARS + 200}")
    if cb["pre_write_sem_checksum"] < THRESHOLD_EST_CHARS + 100:
        erros.append(f"P: pré-write sem checksum {cb['pre_write_sem_checksum']} "
                     f"< {THRESHOLD_EST_CHARS + 100}")
    if cb["keep_total_est"] > 24000:
        erros.append(f"P: keep_total_est {cb['keep_total_est']} > 24000")
    if cb["repo_src"] > 24000:
        erros.append(f"P: repo_src {cb['repo_src']} > 24000")
    return erros


def _valida_f(task: dict) -> list[str]:
    erros = []
    repo, cb = task["repo_files"], task["char_budget"]
    # progressão exata de reward por estágio consertado: 0/5 → 2/5 → 5/5
    esperado_por_k = {0: 0, 1: 2, 2: 5}
    dur_c = 0.0
    for k, alvo in esperado_por_k.items():
        files = dict(repo)
        for rel in F_ORDEM[:k]:
            files[rel] = task["canonical_files"][rel]
        res_k, dur_c = _run(files, task["test_code"])
        if not (res_k["passed"] == alvo and res_k["total"] == 5):
            erros.append(f"{k} estágio(s) consertado(s) != {alvo}/5 "
                         f"({res_k['passed']}/{res_k['total']})")
    if dur_c >= 10.0:
        erros.append(f"suite lenta ({dur_c:.1f}s)")
    # verbosidade: 5 blocos de falha de 3000–3500 chars no pytest bruto inicial
    bruto = _pytest_bruto(repo, task["test_code"])
    blocos = _blocos_falha(bruto)
    if len(blocos) != 5:
        erros.append(f"F: {len(blocos)} blocos de falha no estado inicial (≠ 5)")
    for b in blocos:
        if not 3000 <= len(b) <= 3500:
            erros.append(f"F: bloco de falha com {len(b)} chars fora de [3000, 3500]")
            break
    if len(bruto) < 2000:
        erros.append("F: saída bruta inicial < 2000 chars (observação não satura)")
    # o esperado do agrega fica OCULTO (senão o modelo escreve sem ler formato.py)
    if "OCULTO" not in task["test_code"] or "formato.py" not in task["test_code"]:
        erros.append("F: falha do agrega não oculta o esperado/não aponta formato.py")
    # orçamentos (simulação real do caminho canônico de 6 turnos)
    if not cb["sim_keep_ok"]:
        erros.append("simulação F keep não completa 5/5 em 8 chamadas")
    if not cb["sim_default_ok"]:
        erros.append("simulação F default não completa (ou boot viva no write final)")
    if cb["pre_primeiro_write"] >= THRESHOLD_REF_CHARS:
        erros.append(f"F: pré-1º-write {cb['pre_primeiro_write']} >= {THRESHOLD_REF_CHARS}")
    if cb["pos_primeiro_write"] < THRESHOLD_EST_CHARS + 200:
        erros.append(f"F: pós-1º-write {cb['pos_primeiro_write']} < "
                     f"{THRESHOLD_EST_CHARS + 200} (travessia tardia demais)")
    if cb["keep_turno5"] > MAX_MODEL_CHARS - 500:
        erros.append(f"F: turno 5 {cb['keep_turno5']} > {MAX_MODEL_CHARS - 500} "
                     "(keep estouraria cedo demais)")
    if cb["keep_turno6"] <= MAX_MODEL_CHARS + 500:
        erros.append(f"F: turno 6 {cb['keep_turno6']} <= {MAX_MODEL_CHARS + 500} "
                     "(keep não estoura o contexto)")
    if cb["keep_write1_total"] > MAX_MODEL_CHARS - 500:
        erros.append(f"F: 1º write sob keep {cb['keep_write1_total']} não cabe")
    if cb["summ_max_call"] >= 20000:
        erros.append(f"F: chamada máxima sob default {cb['summ_max_call']} >= 20000")
    return erros


def valida_task(task: dict) -> list[str]:
    """Retorna lista de motivos de reprovação (vazia = aprovada)."""
    faltam = REQUIRED_KEYS - set(task)
    if faltam:
        return [f"chaves faltando: {sorted(faltam)}"]
    erros = []
    if task["repo_files"].get("test_app.py") != task["test_code"]:
        erros.append("test_app.py ausente ou != test_code")
    if task["bug_file"] not in task["repo_files"] \
            or task["bug_file"] not in task["canonical_files"]:
        erros.append("bug_file fora de repo_files/canonical_files")
    if task["family"].startswith("p_"):
        erros += _valida_p(task)
    else:
        erros += _valida_f(task)
    return erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment/tasks_swe35.py")
    args = ap.parse_args()

    tasks_p = [_gera_p(i) for i in range(N_POR_FAMILIA)]
    # boot_note F pareada em chars com a P de mesmo índice
    tasks_f = [_gera_f(i, len(tasks_p[i]["boot_note"])) for i in range(N_POR_FAMILIA)]
    tasks = tasks_p + tasks_f
    reprovadas = {}
    for i in range(N_POR_FAMILIA):
        if len(tasks_f[i]["boot_note"]) != len(tasks_p[i]["boot_note"]):
            reprovadas[tasks_f[i]["task_id"]] = ["boot_note não pareada com a P"]
    for task in tasks:
        erros = valida_task(task)
        if erros:
            reprovadas.setdefault(task["task_id"], []).extend(erros)
    for tid, erros in reprovadas.items():
        print(f"  REPROVADA {tid}: {erros}")
    if reprovadas:
        print(f"ABORTA: {len(reprovadas)} tasks reprovadas — recalibrar geração")
        sys.exit(1)
    print(f"aprovadas: {len(tasks)} (12 P + 12 F)")

    tasks.sort(key=lambda t: t["task_id"])
    header = ('"""Pool CONGELADO adversarial de landscape (futuro pré-reg 35) — iteração 3.\n\n'
              "GERADO por scripts/gera_tasks_swe35.py — NÃO EDITAR À MÃO.\n"
              f"Aprovadas: {len(tasks)} (12 p_checksum + 12 f_pipeline) | "
              "reprovadas: 0.\n"
              "P: fórmula do fold só em docs/spec_mixing.md; PARAM_A/B só na boot_note.\n"
              "F: 2 estágios (normaliza → agrega); conserto do agrega exige formato.py.\n"
              "Orçamentos medidos por simulação real (campo char_budget).\n"
              '"""\n\n')
    body = "TASKS: list[dict] = " + pprint.pformat(tasks, width=100, sort_dicts=True)
    footer = ('\n\nSTRATA: dict[str, str] = {t["task_id"]: t["family"] for t in TASKS}\n\n'
              '__all__ = ["TASKS", "STRATA"]\n\n\n'
              'def get_task(task_id: str) -> dict:\n'
              '    for t in TASKS:\n'
              '        if t["task_id"] == task_id:\n'
              '            return t\n'
              '    raise KeyError(task_id)\n')
    Path(args.out).write_text(header + body + footer, encoding="utf-8")
    print(f"congelado em {args.out}")


if __name__ == "__main__":
    main()
