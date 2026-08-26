"""Gera e congela o pool adversarial de landscape (futuro pré-reg 35).

24 tasks determinísticas (seed fixa): 12 da família P ("poison") e 12 da F ("free").
Formato idêntico a environment/tasks_swe.py MAIS os campos `boot_note` e `char_budget`.

Família P — summarize destrói informação necessária e irrecuperável:
  a correção completa exige 2 constantes opacas (mixing (x*A+B) % 10007) que
  aparecem SOMENTE na boot_note; 5 testes: 3 genéricos + 2 comparam o mixing com
  valores pré-computados. Canonical → 5/5; canonical com constantes erradas → 3/5.

Família F — summarize estritamente melhor; keep leva a overflow REAL:
  boot_note inócua (mesmo comprimento da P pareada); pipeline de 4 estágios
  (normaliza → agrega → valida → exporta), 1 bug por estágio; a suite (5 testes)
  só revela o erro do estágio k+1 depois que o estágio k está consertado.
  Reward fracionário: 0 estágios→0/5, 1→2/5, 2→3/5, 3→4/5, 4→5/5.
  Mensagens de falha verbosas (~3000–3500 chars no output bruto do pytest);
  no caminho keep canônico (TEST; READ+WRITE por estágio) o prompt cumulativo
  cruza 8192·3.3 chars até o turno 6 → BadRequestError → R=0 (regra 32a).
  Sob summarize (keep-last-6) o episódio completa. Tudo persiste em arquivos.

Validações (task reprovada aborta a geração):
  1. P: constantes ausentes do blob VISÍVEL (repo_files/test_code — nunca dos
     canônicos); canonical→5/5; constantes erradas→3/5.
  2. F: canonical→5/5; progressão por estágio exata (0/5, 2/5, 3/5, 4/5);
     5 blocos de falha verbosos de 3000–3500 chars no pytest bruto;
     simulação do caminho keep: pré-1º-write < 4500·3.3 chars, pós-1º-write
     ≥ 4500·3.3, prompt do turno 6 > 8192·3.3; boot_note pareada com a P.
  3. Todas: canonical roda 5/5 num sandbox limpo (mesmo mecanismo do gera_tasks_swe).
  4. Orçamentos de chars por família verificados numericamente e gravados por
     task no campo `char_budget`.

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

from agent.loop_v2 import SYSTEM_PROMPT_V2  # noqa: E402
from environment.sandbox import Sandbox  # noqa: E402

M = 10007  # primo do anel de mixing
SEED_BASE = 3500
N_POR_FAMILIA = 12

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


# -- família P ("poison") ----------------------------------------------------
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
    """Fold polinomial: h = (h*31 + v) % M, iniciando em 0."""
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


def test_checksum_unitario():
    assert checksum([{v1}]) == {v1}


def test_checksum_fold_polinomial():
    assert checksum([{v1}, {v2}]) == ({v1} * 31 + {v2}) % 10007


def test_checksum_sensivel_a_ordem():
    assert checksum([{v1}, {v2}]) != checksum([{v2}, {v1}])


def test_assina_ponto_a():
    assert assina({x1}) == {e1}


def test_assina_ponto_b():
    assert assina({x2}) == {e2}
'''

PROMPT_P_BASE = (
    "Este repositório implementa o serviço de assinatura e checksum de pacotes: "
    "mixing.py traz o mixing modular, checksum.py o fold polinomial e a assinatura "
    "da instalação, protocolo.py documenta o contrato de pacotes e auditoria.py o "
    "procedimento de verificação. Há testes falhando (a suite está em test_app.py). "
    "Antes de editar qualquer coisa, leia protocolo.py e auditoria.py para entender "
    "o contrato completo do serviço; depois use read_file no arquivo suspeito e "
    "corrija reescrevendo o arquivo INTEIRO com write_file.\n\n"
    "Contexto operacional:\n")


def _gera_p(i: int) -> dict:
    rng = random.Random(SEED_BASE + i)
    while True:
        a_const = rng.randrange(1009, 9973)
        b_const = rng.randrange(1009, 9973)
        x1, x2 = rng.randrange(101, 9006), rng.randrange(101, 9006)
        v1, v2 = rng.randrange(2, 98), rng.randrange(2, 98)
        if x1 == x2 or v1 == v2:
            continue
        e1, e2 = (x1 * a_const + b_const) % M, (x2 * a_const + b_const) % M
        # placeholders (1, 0) devem falhar AMBOS os testes de mixing
        if e1 == x1 % M or e2 == x2 % M:
            continue
        doc = _texto(random.Random(SEED_BASE + 100 + i), 1100)
        bug = CHECKSUM_TPL.format(doc=doc, a=1, b=0, fold="(h + v)")
        canon = CHECKSUM_TPL.format(doc=doc, a=a_const, b=b_const, fold="(h * 31 + v)")
        test_code = TESTS_P_TPL.format(v1=v1, v2=v2, x1=x1, x2=x2, e1=e1, e2=e2)
        repo = {
            "mixing.py": MIXING_PY,
            "checksum.py": bug,
            "protocolo.py": _modulo_padding(random.Random(SEED_BASE + 200 + i),
                                            "Contrato de pacotes do serviço de checksum.", 11400),
            "auditoria.py": _modulo_padding(random.Random(SEED_BASE + 300 + i),
                                            "Procedimento de auditoria da assinatura.", 4500),
            "test_app.py": test_code,
        }
        blob = "".join(repo.values())  # só o que é visível ao agente (canônica fica fora)
        # as constantes NÃO podem aparecer em nenhum arquivo nem no test_code…
        if str(a_const) in blob or str(b_const) in blob:
            continue
        break

    prompt = PROMPT_P_BASE + _texto(random.Random(SEED_BASE + 400 + i),
                                    2950 - len(PROMPT_P_BASE))
    boot_rng = random.Random(SEED_BASE + 500 + i)
    boot_note = (
        "Nota do deploy (leia antes de mexer no serviço de checksum):\n"
        + _texto(boot_rng, 550) + "\n"
        + f"IMPORTANTE: nesta instalação o serviço de checksum usa PARAM_A={a_const} "
          f"e PARAM_B={b_const}; os placeholders de desenvolvimento versionados no "
          "repositório NÃO valem aqui e precisam ser trocados junto com qualquer correção.\n"
        + _texto(boot_rng, 620))
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
    task["char_budget"] = _char_budget_p(task)
    return task


def _lista_chars(repo: dict) -> int:
    return len("Arquivos do repositório: " + ", ".join(sorted(repo)))


def _char_budget_p(task: dict) -> dict:
    src = {k: v for k, v in task["repo_files"].items() if k != "test_app.py"}
    base = len(SYSTEM_PROMPT_V2) + len(task["prompt"]) + len(task["boot_note"])
    maior = max(len(v) for k, v in src.items() if k != task["bug_file"])
    return {
        "prompt": len(task["prompt"]),
        "boot_note": len(task["boot_note"]),
        "repo_src": sum(len(v) for v in src.values()),
        # leitura natural: list + read do bug + 1 arquivo grande → cruza o threshold
        "leitura_ate_decisao": base + _lista_chars(task["repo_files"])
                               + len(src[task["bug_file"]]) + maior,
        # keep até o fim (todas as leituras + 1 write + observações) fica < 8192 tok
        "keep_total_est": base + _lista_chars(task["repo_files"])
                          + sum(len(v) for v in src.values())
                          + len(task["canonical_files"][task["bug_file"]]) + 800,
    }


# -- família F ("free") ------------------------------------------------------
# Pipeline de 4 estágios; 1 bug por estágio; suite revela um estágio por vez.
CHARS_POR_TOKEN = 3.3
MAX_MODEL_CHARS = int(8192 * CHARS_POR_TOKEN)      # overflow keep: 27033 chars
THRESHOLD_CHARS = int(4500 * CHARS_POR_TOKEN)      # summarize_threshold: 14850 chars
OBS_TEST_CHARS = len("Resultado dos testes: 0/5 passaram.\nSaída:\n") + 1200
LARGURA_MSG_FALHA = 3050  # chars da mensagem de _falha (pytest renderiza ~+390)

F_ORDEM = ("normaliza.py", "agrega.py", "valida.py", "exporta.py")

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

AGREGA_TPL = '''"""Agregação de totais por nome (estágio 2 do pipeline).

{doc}
"""


def agrega(registros):
    """Total por nome, acumulando valores de nomes repetidos."""
    totais = {{}}
    for nome, valor in registros:
        totais[nome] = {expr}
    return totais
'''

VALIDA_TPL = '''"""Validação de totais contra o limite operacional (estágio 3 do pipeline).

{doc}
"""

LIMITE_PADRAO = {lim}


def valida(totais, limite=LIMITE_PADRAO):
    """(nome, total, status) ordenado por nome; status "acima" sse total > limite."""
    saida = []
    for nome in sorted(totais):
        total = totais[nome]
        status = "acima" if total {op} limite else "ok"
        saida.append((nome, total, status))
    return saida
'''

EXPORTA_TPL = '''"""Exportação do relatório final (estágio 4 do pipeline).

{doc}
"""


def exporta(itens):
    """Uma linha por item no formato nome|total|status, unidas por quebra de linha."""
    linhas = []
    for nome, total, status in itens:
        linhas.append({linha})
    return "\\n".join(linhas)
'''

LINHA_EXPORTA_BUG = 'f"{nome}|{total}"'
LINHA_EXPORTA_OK = 'f"{nome}|{total}|{status}"'

# Substituição por tokens @X@ (o corpo tem chaves demais para str.format).
TESTS_F_TPL = '''"""Suite do pipeline de consumo (5 testes, 4 estágios encadeados)."""
from agrega import agrega
from exporta import exporta
from normaliza import normaliza
from valida import valida

DADOS = @DADOS@
NORM_ESP = @NORM_ESP@
TOT_ESP = @TOT_ESP@
VAL_ESP = @VAL_ESP@
EXP_ESP = @EXP_ESP@

LARGURA_MSG = @LARGURA@
_ENCH = ("contexto do runner: lote unico, ordem estavel de chegada, sem retentativa "
         "pendente e trilha de auditoria completa para esta janela de processamento")


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
    rodape = (f"\\nDIAGNOSTICO: o proximo conserto e em {arquivo}; reescreva "
              f"{arquivo} INTEIRO com write_file e rode os testes de novo.")
    k = 0
    while len(corpo) + len(rodape) < LARGURA_MSG:
        corpo += f"\\n  janela {k:03d} | {_ENCH}"
        k += 1
    return corpo[:LARGURA_MSG - len(rodape)] + rodape


def _ate(estagio):
    """Gate encadeado: o erro do estágio k+1 só aparece com o estágio k consertado."""
    regs = normaliza(DADOS)
    assert regs == NORM_ESP, _falha("normaliza.py", "normaliza", NORM_ESP, regs)
    if estagio == "agrega":
        return regs
    tot = agrega(regs)
    assert tot == TOT_ESP, _falha("agrega.py", "agrega", TOT_ESP, tot)
    if estagio == "valida":
        return tot
    val = valida(tot)
    assert val == VAL_ESP, _falha("valida.py", "valida", VAL_ESP, val)
    return val


def test_normaliza_minusculas_espacos_e_filtro():
    entrada = [("  @N1@  ", @w1@), ("@n3@", 0)]
    esperado = [("@n1@", @w1@)]
    obtido = normaliza(entrada)
    assert obtido == esperado, _falha("normaliza.py", "normaliza", esperado, obtido)


def test_normaliza_descarta_nao_positivo():
    entrada = [("@n3@", -@d@), ("@N2@", @w2@)]
    esperado = [("@n2@", @w2@)]
    obtido = normaliza(entrada)
    assert obtido == esperado, _falha("normaliza.py", "normaliza", esperado, obtido)


def test_agrega_acumula_duplicatas():
    regs = _ate("agrega")
    obtido = agrega(regs)
    assert obtido == TOT_ESP, _falha("agrega.py", "agrega", TOT_ESP, obtido)


def test_valida_status_no_limite():
    tot = _ate("valida")
    obtido = valida(tot)
    assert obtido == VAL_ESP, _falha("valida.py", "valida", VAL_ESP, obtido)


def test_exporta_relatorio_final():
    val = _ate("exporta")
    obtido = exporta(val)
    assert obtido == EXP_ESP, _falha("exporta.py", "exporta", EXP_ESP, obtido)
'''

_NOMES = ("ana", "bruno", "carla", "davi", "elisa", "fabio", "gina", "hugo")

PROMPT_F_BASE = (
    "Este repositório implementa o pipeline de consumo em quatro estágios: "
    "normaliza.py (estágio 1, limpeza dos registros), agrega.py (estágio 2, totais "
    "por nome), valida.py (estágio 3, status contra o limite operacional) e "
    "exporta.py (estágio 4, relatório final); leitura.py, formato.py e catalogo.py "
    "documentam a ingestão e o catálogo de origens. Há um bug em cada estágio e a "
    "suite (test_app.py) revela um estágio de cada vez, na ordem do fluxo. Use "
    "run_tests para ver a falha atual, corrija UM arquivo por vez reescrevendo-o "
    "INTEIRO com write_file e rode os testes de novo: a mensagem de falha aponta o "
    "próximo arquivo.\n\n"
    "Contexto operacional:\n")


def _gera_f(i: int, boot_len: int) -> dict:
    rng = random.Random(SEED_BASE + 1000 + i)
    n1, n2, n3, n4 = rng.sample(_NOMES, 4)
    while True:
        w = [rng.randrange(2, 61) for _ in range(5)]
        if w[0] + w[2] > w[1] + w[3]:  # garante um "acima" estrito no valida
            break
    d = rng.randrange(1, 9)
    dados = [(f"  {n1.upper()}  ", w[0]), (n2.title(), w[1]), (f" {n1} ", w[2]),
             (n3, -d), (n2, w[3]), (n4.upper(), w[4])]
    norm_esp = [(n.strip().lower(), v) for n, v in dados if v > 0]
    totais_esp: dict = {}
    for n, v in norm_esp:
        totais_esp[n] = totais_esp.get(n, 0) + v
    lim = totais_esp[n2]  # total EXATAMENTE no limite: >= (bug) difere de > (ok)
    val_esp = [(n, t, "acima" if t > lim else "ok")
               for n, t in sorted(totais_esp.items())]
    exp_esp = "\n".join(f"{n}|{t}|{s}" for n, t, s in val_esp)

    subs = {"@DADOS@": repr(dados), "@NORM_ESP@": repr(norm_esp),
            "@TOT_ESP@": repr(totais_esp), "@VAL_ESP@": repr(val_esp),
            "@EXP_ESP@": repr(exp_esp), "@LARGURA@": str(LARGURA_MSG_FALHA),
            "@n1@": n1, "@N1@": n1.upper(), "@n2@": n2, "@N2@": n2.upper(),
            "@n3@": n3, "@w1@": str(w[0]), "@w2@": str(w[1]), "@d@": str(d)}
    test_code = TESTS_F_TPL
    for tok, val in subs.items():
        test_code = test_code.replace(tok, val)

    doc1 = _texto(random.Random(SEED_BASE + 1100 + i), 5450)
    doc2 = _texto(random.Random(SEED_BASE + 1200 + i), 5450)
    doc3 = _texto(random.Random(SEED_BASE + 1250 + i), 2750)
    doc4 = _texto(random.Random(SEED_BASE + 1270 + i), 2800)
    repo = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_BUG),
        "agrega.py": AGREGA_TPL.format(doc=doc2, expr="valor"),
        "valida.py": VALIDA_TPL.format(doc=doc3, lim=lim, op=">="),
        "exporta.py": EXPORTA_TPL.format(doc=doc4, linha=LINHA_EXPORTA_BUG),
        "leitura.py": _modulo_padding(random.Random(SEED_BASE + 1300 + i),
                                      "Ingestão de registros de consumo.", 3800),
        "formato.py": _modulo_padding(random.Random(SEED_BASE + 1400 + i),
                                      "Formato de saída dos totais agregados.", 3800),
        "catalogo.py": _modulo_padding(random.Random(SEED_BASE + 1500 + i),
                                       "Catálogo de origens do pipeline.", 3000),
        "test_app.py": test_code,
    }
    canonical = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_OK),
        "agrega.py": AGREGA_TPL.format(doc=doc2, expr="totais.get(nome, 0) + valor"),
        "valida.py": VALIDA_TPL.format(doc=doc3, lim=lim, op=">"),
        "exporta.py": EXPORTA_TPL.format(doc=doc4, linha=LINHA_EXPORTA_OK),
    }
    prompt = PROMPT_F_BASE + _texto(random.Random(SEED_BASE + 1600 + i),
                                    1250 - len(PROMPT_F_BASE))
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
    task["char_budget"] = _char_budget_f(task)
    return task


def _simula_keep_f(task: dict) -> dict:
    """Chars do prompt cumulativo no caminho keep canônico: TEST; depois, por
    estágio, READ do arquivo bugado e WRITE do canônico (auto_test após write).
    Observações de teste usam a truncagem REAL do loop_v2 (últimos 1200 chars)."""
    base = len(SYSTEM_PROMPT_V2) + len(task["prompt"]) + len(task["boot_note"])
    cum, por_turno = base, []
    cum += len("TEST") + OBS_TEST_CHARS                                  # turno 1
    por_turno.append(cum)
    for rel in F_ORDEM:
        cum += len(f"READ {rel}") + len(f"Conteúdo de {rel}:\n") \
               + len(task["repo_files"][rel])                            # READ
        por_turno.append(cum)
        canon = task["canonical_files"][rel]
        cum += len(f"WRITE {rel}\n```python\n{canon}\n```") \
               + len(f"Arquivo {rel} gravado.") + OBS_TEST_CHARS         # WRITE
        por_turno.append(cum)
    # prompt enviado no turno t = acumulado até o fim do turno t-1
    return {"pre_primeiro_write": por_turno[1],   # prompt do turno 3 (1º WRITE)
            "pos_primeiro_write": por_turno[2],   # prompt do turno 4
            "keep_turno6_est": por_turno[4],      # prompt do turno 6
            "keep_total_est": por_turno[-1]}


def _char_budget_f(task: dict) -> dict:
    src = {k: v for k, v in task["repo_files"].items() if k != "test_app.py"}
    sim = _simula_keep_f(task)
    return {
        "prompt": len(task["prompt"]),
        "boot_note": len(task["boot_note"]),
        "repo_src": sum(len(v) for v in src.values()),
        "msg_falha_chars": LARGURA_MSG_FALHA,
        **sim,
    }


# -- validação ----------------------------------------------------------------
REQUIRED_KEYS = {"task_id", "family", "prompt", "boot_note", "repo_files",
                 "canonical_files", "test_code", "bug_file", "char_budget"}
_PARAM_RE = re.compile(r"PARAM_A=(\d+) e PARAM_B=(\d+)")


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


def valida_task(task: dict) -> list[str]:
    """Retorna lista de motivos de reprovação (vazia = aprovada)."""
    erros = []
    faltam = REQUIRED_KEYS - set(task)
    if faltam:
        return [f"chaves faltando: {sorted(faltam)}"]
    repo = task["repo_files"]
    if repo.get("test_app.py") != task["test_code"]:
        erros.append("test_app.py ausente ou != test_code")
    if task["bug_file"] not in repo or task["bug_file"] not in task["canonical_files"]:
        erros.append("bug_file fora de repo_files/canonical_files")

    canon = {**repo, **task["canonical_files"]}
    res_c, dur_c = _run(canon, task["test_code"])
    if not (res_c["success"] and res_c["total"] == 5):
        erros.append(f"canônica != 5/5 ({res_c['passed']}/{res_c['total']})")
    if dur_c >= 10.0:
        erros.append(f"suite lenta ({dur_c:.1f}s)")
    cb = task["char_budget"]

    if task["family"].startswith("p_"):
        m = _PARAM_RE.search(task["boot_note"])
        if not m:
            return erros + ["boot_note P sem constantes extraíveis"]
        a_const, b_const = m.group(1), m.group(2)
        blob = "".join(repo.values()) + "".join(task["canonical_files"].values())
        # constantes só podem existir na canônica (que fica fora do contexto do agente)
        blob_visivel = "".join(repo.values()) + task["test_code"]
        if a_const in blob_visivel or b_const in blob_visivel:
            erros.append("constantes P aparecem em repo_files/test_code")
        assert a_const in blob  # sanidade: canônica usa as constantes
        errado = re.sub(r"PARAM_A = \d+", "PARAM_A = 1",
                        re.sub(r"PARAM_B = \d+", "PARAM_B = 0",
                               task["canonical_files"][task["bug_file"]]))
        res_e, _ = _run({**repo, task["bug_file"]: errado}, task["test_code"])
        if not (res_e["passed"] == 3 and res_e["total"] == 5):
            erros.append(f"canônica c/ constantes erradas != 3/5 "
                         f"({res_e['passed']}/{res_e['total']})")
        if cb["leitura_ate_decisao"] < 18000:
            erros.append(f"P: leitura natural {cb['leitura_ate_decisao']} < 18000 chars")
        if cb["repo_src"] > 24000:
            erros.append(f"P: repo_src {cb['repo_src']} > 24000 chars")
        if cb["keep_total_est"] > 30000:
            erros.append(f"P: keep_total_est {cb['keep_total_est']} > 30000 chars")
    else:
        # (b) progressão exata de reward por estágio consertado: 0/5→2/5→3/5→4/5(→5/5)
        esperado_por_k = {0: 0, 1: 2, 2: 3, 3: 4}
        for k, alvo in esperado_por_k.items():
            files = dict(repo)
            for rel in F_ORDEM[:k]:
                files[rel] = task["canonical_files"][rel]
            res_k, _ = _run(files, task["test_code"])
            if not (res_k["passed"] == alvo and res_k["total"] == 5):
                erros.append(f"{k} estágio(s) consertado(s) != {alvo}/5 "
                             f"({res_k['passed']}/{res_k['total']})")
        # (verbosidade) 5 blocos de falha de 3000–3500 chars no pytest bruto inicial
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
        # (c) simulação do caminho keep com a truncagem real do loop_v2
        if cb["pre_primeiro_write"] >= THRESHOLD_CHARS:
            erros.append(f"F: pré-1º-write {cb['pre_primeiro_write']} >= "
                         f"{THRESHOLD_CHARS} chars (threshold cruzaria cedo demais)")
        if cb["pos_primeiro_write"] < THRESHOLD_CHARS:
            erros.append(f"F: pós-1º-write {cb['pos_primeiro_write']} < "
                         f"{THRESHOLD_CHARS} chars (threshold não cruza após o write)")
        if cb["keep_turno6_est"] <= MAX_MODEL_CHARS:
            erros.append(f"F: prompt do turno 6 {cb['keep_turno6_est']} <= "
                         f"{MAX_MODEL_CHARS} chars (keep não estoura o contexto)")
    return erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment/tasks_swe35.py")
    args = ap.parse_args()

    tasks_p = [_gera_p(i) for i in range(N_POR_FAMILIA)]
    # (d) boot_note F pareada em chars com a P de mesmo índice
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
    header = ('"""Pool CONGELADO adversarial de landscape (futuro pré-reg 35).\n\n'
              "GERADO por scripts/gera_tasks_swe35.py — NÃO EDITAR À MÃO.\n"
              f"Aprovadas: {len(tasks)} (12 p_checksum + 12 f_pipeline) | "
              "reprovadas: 0.\n"
              "Orçamentos de chars verificados por task (campo char_budget).\n"
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
