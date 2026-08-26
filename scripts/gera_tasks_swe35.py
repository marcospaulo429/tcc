"""Gera e congela o pool adversarial de landscape (futuro pré-reg 35).

24 tasks determinísticas (seed fixa): 12 da família P ("poison") e 12 da F ("free").
Formato idêntico a environment/tasks_swe.py MAIS os campos `boot_note` e `char_budget`.

Família P — summarize destrói informação necessária e irrecuperável:
  a correção completa exige 2 constantes opacas (mixing (x*A+B) % 10007) que
  aparecem SOMENTE na boot_note; 5 testes: 3 genéricos + 2 comparam o mixing com
  valores pré-computados. Canonical → 5/5; canonical com constantes erradas → 3/5.

Família F — summarize estritamente melhor; keep leva a overflow:
  boot_note inócua; bug em 2 estágios (arquivo 1, depois a falha aponta o arquivo 2);
  repo grande/redundante tal que keep até o fim estoura ~8000 tokens. Canonical → 5/5;
  só estágio 1 → 3/5. Toda informação necessária persiste em arquivos.

Validações (task reprovada aborta a geração):
  1. P: constantes ausentes de repo_files/test_code; canonical→5/5; constantes erradas→3/5.
  2. F: canonical→5/5; estágio 1 apenas→2–3/5.
  3. Todas: canonical roda 5/5 num sandbox limpo (mesmo mecanismo do gera_tasks_swe).
  4. Orçamentos de chars por família (P rasa, F profunda) verificados numericamente
     e gravados por task no campo `char_budget`.

Uso: uv run python scripts/gera_tasks_swe35.py [--out environment/tasks_swe35.py]
"""
import argparse
import pprint
import random
import re
import sys
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

TESTS_F_TPL = '''"""Suite do pipeline de consumo (5 testes)."""
from agrega import agrega
from normaliza import normaliza

DADOS = {dados}


def test_normaliza_minusculas_e_espacos():
    assert normaliza([("  {N1}  ", {w1})]) == [("{n1}", {w1})]


def test_normaliza_descarta_nao_positivo():
    assert normaliza([("{n2}", 0), ("{n1}", {w2})]) == [("{n1}", {w2})]


def test_normaliza_preserva_ordem():
    assert normaliza([("{N2}", {w1}), ("{n1}", {w2})]) == [("{n2}", {w1}), ("{n1}", {w2})]


def test_fluxo_total_por_nome():
    regs = normaliza(DADOS)
    assert regs == {norm_esp}, "normaliza.py ainda incorreto"
    assert agrega(regs) == {totais_esp}, "bug em agrega.py: revise agrega.py"


def test_fluxo_acumula_duplicatas():
    regs = normaliza(DADOS)
    assert regs == {norm_esp}, "normaliza.py ainda incorreto"
    assert agrega(regs)["{nome_dup}"] == {soma_dup}, "bug em agrega.py: revise agrega.py"
'''

PROMPT_F_BASE = (
    "Este repositório implementa o pipeline de consumo em dois estágios: leitura.py "
    "descreve a ingestão, normaliza.py o estágio 1 (limpeza dos registros), "
    "agrega.py o estágio 2 (totais por nome), formato.py o formato de saída e "
    "catalogo.py o catálogo de origens. Há testes falhando em mais de um ponto do "
    "fluxo (a suite está em test_app.py). Use run_tests para ver as falhas, corrija "
    "um arquivo por vez reescrevendo-o INTEIRO com write_file e rode os testes de "
    "novo: a mensagem de falha indica onde está o próximo problema.\n\n"
    "Contexto operacional:\n")

_NOMES = ("ana", "bruno", "carla", "davi", "elisa", "fabio", "gina", "hugo")


def _gera_f(i: int) -> dict:
    rng = random.Random(SEED_BASE + 1000 + i)
    n1, n2, n3, n4 = rng.sample(_NOMES, 4)
    w = [rng.randrange(2, 61) for _ in range(5)]
    dados = [(f"  {n1.upper()}  ", w[0]), (n2.title(), w[1]), (f" {n1} ", w[2]),
             (n3, -rng.randrange(1, 9)), (n2, w[3]), (n4.upper(), w[4])]
    norm_esp = [(n.strip().lower(), v) for n, v in dados if v > 0]
    totais_esp: dict = {}
    for n, v in norm_esp:
        totais_esp[n] = totais_esp.get(n, 0) + v

    doc1 = _texto(random.Random(SEED_BASE + 1100 + i), 1300)
    doc2 = _texto(random.Random(SEED_BASE + 1200 + i), 1500)
    test_code = TESTS_F_TPL.format(
        dados=repr(dados), n1=n1, n2=n2, N1=n1.upper(), N2=n2.upper(),
        w1=w[0], w2=w[1], norm_esp=repr(norm_esp), totais_esp=repr(totais_esp),
        nome_dup=n1, soma_dup=w[0] + w[2])
    repo = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_BUG),
        "agrega.py": AGREGA_TPL.format(doc=doc2, expr="valor"),
        "leitura.py": _modulo_padding(random.Random(SEED_BASE + 1300 + i),
                                      "Ingestão de registros de consumo.", 9200),
        "formato.py": _modulo_padding(random.Random(SEED_BASE + 1400 + i),
                                      "Formato de saída dos totais agregados.", 9200),
        "catalogo.py": _modulo_padding(random.Random(SEED_BASE + 1500 + i),
                                       "Catálogo de origens do pipeline.", 6600),
        "test_app.py": test_code,
    }
    canonical = {
        "normaliza.py": NORMALIZA_TPL.format(doc=doc1, corpo=CORPO_NORM_OK),
        "agrega.py": AGREGA_TPL.format(doc=doc2, expr="totais.get(nome, 0) + valor"),
    }
    prompt = PROMPT_F_BASE + _texto(random.Random(SEED_BASE + 1600 + i),
                                    1250 - len(PROMPT_F_BASE))
    boot_rng = random.Random(SEED_BASE + 1700 + i)
    boot_note = ("Nota do deploy (status da janela de manutenção, sem ação necessária):\n"
                 + _texto(boot_rng, 1400))

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


def _char_budget_f(task: dict) -> dict:
    src = {k: v for k, v in task["repo_files"].items() if k != "test_app.py"}
    base = len(SYSTEM_PROMPT_V2) + len(task["prompt"]) + len(task["boot_note"])
    return {
        "prompt": len(task["prompt"]),
        "boot_note": len(task["boot_note"]),
        "repo_src": sum(len(v) for v in src.values()),
        # antes do 1º write: list + read do estágio 1 → NÃO cruza o threshold
        "pre_primeiro_write": base + _lista_chars(task["repo_files"])
                              + len(src[task["bug_file"]]),
        # keep até o fim (todas as leituras + 2 writes + observações) → > 8192 tok
        "keep_total_est": base + _lista_chars(task["repo_files"])
                          + sum(len(v) for v in src.values())
                          + sum(len(v) for v in task["canonical_files"].values()) + 1600,
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
        estagio1 = {**repo, task["bug_file"]: task["canonical_files"][task["bug_file"]]}
        res_1, _ = _run(estagio1, task["test_code"])
        if not (2 <= res_1["passed"] <= 3 and res_1["total"] == 5):
            erros.append(f"estágio 1 fora de 2-3/5 ({res_1['passed']}/{res_1['total']})")
        if cb["pre_primeiro_write"] >= 18000:
            erros.append(f"F: pre_primeiro_write {cb['pre_primeiro_write']} >= 18000 chars")
        if cb["keep_total_est"] < 32500:
            erros.append(f"F: keep_total_est {cb['keep_total_est']} < 32500 chars")
    return erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment/tasks_swe35.py")
    args = ap.parse_args()

    tasks = [_gera_p(i) for i in range(N_POR_FAMILIA)] + \
            [_gera_f(i) for i in range(N_POR_FAMILIA)]
    reprovadas = {}
    for task in tasks:
        erros = valida_task(task)
        if erros:
            reprovadas[task["task_id"]] = erros
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
