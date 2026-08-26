"""Pool adversarial swe35 (futuro pré-reg 35): estrutura, execução real e boot_note."""
import itertools
import re

from agent.harness import summarize_messages
from agent.harness_v2 import HarnessV2
from agent.loop_v2 import EpisodeV2
from environment.sandbox import Sandbox
from environment.tasks_swe import TASKS as TASKS_SWE
from environment.tasks_swe35 import STRATA, TASKS, get_task
from trajectories.recorder import Recorder
from trajectories.schema import load_trajectory

REQUIRED = {"task_id", "family", "prompt", "boot_note", "repo_files",
            "canonical_files", "test_code", "bug_file", "char_budget"}
_PARAM_RE = re.compile(r"PARAM_A=(\d+) e PARAM_B=(\d+)")

P_TASKS = [t for t in TASKS if t["task_id"].startswith("p_")]
F_TASKS = [t for t in TASKS if t["task_id"].startswith("f_")]


def _run(files: dict[str, str], test_code: str) -> dict:
    sb = Sandbox()
    try:
        for rel, content in files.items():
            sb.write_file(rel, content)
        return sb.run_tests(test_code)
    finally:
        sb.cleanup()


# -- estruturais ---------------------------------------------------------------
def test_pool_24_tasks_12_por_familia():
    assert len(TASKS) == 24
    assert len(P_TASKS) == 12 and len(F_TASKS) == 12
    assert all(t["family"].startswith("p_") for t in P_TASKS)
    assert all(t["family"].startswith("f_") for t in F_TASKS)


def test_campos_obrigatorios_e_ids_unicos():
    ids = [t["task_id"] for t in TASKS]
    assert len(set(ids)) == 24
    for t in TASKS:
        assert REQUIRED <= set(t), t["task_id"]
        assert t["repo_files"]["test_app.py"] == t["test_code"]
        assert t["bug_file"] in t["repo_files"]
        assert t["bug_file"] in t["canonical_files"]
        assert t["boot_note"]
    assert STRATA == {t["task_id"]: t["family"] for t in TASKS}
    assert get_task(ids[0])["task_id"] == ids[0]


def _constantes(task: dict) -> tuple[str, str]:
    m = _PARAM_RE.search(task["boot_note"])
    assert m, f"{task['task_id']}: boot_note sem constantes"
    return m.group(1), m.group(2)


def test_p_constantes_so_na_boot_note():
    for t in P_TASKS:
        a_const, b_const = _constantes(t)
        visivel = "".join(t["repo_files"].values())  # inclui test_app.py == test_code
        assert a_const not in visivel and b_const not in visivel, t["task_id"]
        canon = "".join(t["canonical_files"].values())
        assert a_const in canon and b_const in canon, t["task_id"]


_FOLD_RE = re.compile(r"h = \(h \* (\d+) \+ v \* (\d+)\) % M")


def test_p_spec_mixing_define_formula_e_nao_vaza():
    for t in P_TASKS:
        spec = t["repo_files"]["docs/spec_mixing.md"]
        assert 8000 <= len(spec) <= 9800, t["task_id"]
        # falhas apontam explicitamente para a spec
        assert "docs/spec_mixing.md" in t["test_code"], t["task_id"]
        m = _FOLD_RE.search(t["canonical_files"]["checksum.py"])
        assert m, f"{t['task_id']}: can\u00f4nica sem fold normativo"
        r1, r2 = m.group(1), m.group(2)
        assert f"R1 = {r1}" in spec and f"R2 = {r2}" in spec, t["task_id"]
        fora_spec = "".join(v for k, v in t["repo_files"].items()
                            if k != "docs/spec_mixing.md")
        # f\u00f3rmula/coeficientes s\u00f3 existem na spec (fora dela, nada vaza)
        assert r1 not in fora_spec and r2 not in fora_spec, t["task_id"]
        assert "(h * " not in fora_spec, t["task_id"]


def test_orcamentos_de_chars_por_familia():
    for t in P_TASKS:
        cb = t["char_budget"]
        # gatilho REAL do summarize \u00e9 estimate_tokens = chars//4 > 4500 \u21d2 18000 chars
        assert cb["pre_write"] >= 18000, t["task_id"]
        assert cb["pre_write_sem_checksum"] >= 18000, t["task_id"]
        assert cb["boot_morta_default"], t["task_id"]
        assert cb["repo_src"] <= 24000, t["task_id"]
        assert cb["keep_total_est"] <= 24000, t["task_id"]
    for t in F_TASKS:
        cb = t["char_budget"]
        # threshold (refer\u00eancia 4500 tok \u2248 14850 chars) cruza s\u00f3 DEPOIS do 1\u00ba write\u2026
        assert cb["pre_primeiro_write"] < 14850, t["task_id"]
        assert cb["pos_primeiro_write"] >= 14850, t["task_id"]
        # \u2026keep estoura o max-model-len (8192 tok \u2248 27033 chars) no turno 6, n\u00e3o antes\u2026
        assert cb["keep_turno5"] <= 27033, t["task_id"]
        assert cb["keep_turno6"] > 27033, t["task_id"]
        # \u2026e sob summarize (keep_last=6) toda chamada fecha com folga
        assert cb["summ_max_call"] < 20000, t["task_id"]
        assert cb["sim_keep_ok"] and cb["sim_default_ok"], t["task_id"]
        assert cb["msg_falha_chars"] >= 3000, t["task_id"]


def test_f_boot_note_pareada_com_p():
    for p, f in zip(P_TASKS, F_TASKS):
        assert len(f["boot_note"]) == len(p["boot_note"]), f["task_id"]


# -- execução real em sandbox ----------------------------------------------------
def test_p_canonica_5de5_e_sem_constantes_3de5():
    for t in P_TASKS[:2]:
        res = _run({**t["repo_files"], **t["canonical_files"]}, t["test_code"])
        assert res["total"] == 5 and res["passed"] == 5, t["task_id"]
        errado = re.sub(r"PARAM_A = \d+", "PARAM_A = 1",
                        re.sub(r"PARAM_B = \d+", "PARAM_B = 0",
                               t["canonical_files"][t["bug_file"]]))
        res_e = _run({**t["repo_files"], t["bug_file"]: errado}, t["test_code"])
        assert res_e["total"] == 5 and res_e["passed"] == 3, t["task_id"]


F_ORDEM = ("normaliza.py", "agrega.py")


def test_f_canonica_5de5_e_progressao_por_estagio():
    # 0 estágios→0/5, 1→2/5, 2→5/5 (reward fracionário estrito)
    esperado = {0: 0, 1: 2, 2: 5}
    for t in F_TASKS[:2]:
        assert set(t["canonical_files"]) == set(F_ORDEM), t["task_id"]
        for k, alvo in esperado.items():
            files = dict(t["repo_files"])
            for rel in F_ORDEM[:k]:
                files[rel] = t["canonical_files"][rel]
            res = _run(files, t["test_code"])
            assert res["total"] == 5 and res["passed"] == alvo, \
                f"{t['task_id']}: {k} estágio(s) → {res['passed']}/5 (esperado {alvo}/5)"
        assert res["success"]  # k=2 é a canônica completa


def test_f_conserto_do_agrega_exige_formato():
    for t in F_TASKS:
        # o diff da falha do agrega OCULTA o esperado e aponta o contrato
        assert "OCULTO" in t["test_code"], t["task_id"]
        assert "formato.py" in t["test_code"], t["task_id"]
        assert "FATOR_CONTRATO" in t["repo_files"]["formato.py"], t["task_id"]


# -- boot_note no EpisodeV2 -------------------------------------------------------
class FakeLLM:
    def __init__(self, script):
        self._iter = itertools.cycle(script)

    def config(self):
        return {"model": "fake", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kw):
        return {"text": next(self._iter), "prompt_tokens": 1, "completion_tokens": 1,
                "wall_time_s": 0.0}


def _mensagens_iniciais(task, tmp_path, sub):
    ep = EpisodeV2(task, FakeLLM(["FINISH"]), HarnessV2(max_turns=3),
                   Recorder(tmp_path / sub))
    result = ep.run()
    ep.sandbox.cleanup()
    traj = load_trajectory(result["trajectory_path"])
    return traj.decisions[0].state_before["messages"]

def test_boot_note_inserida_na_posicao_2_no_fresh(tmp_path):
    task = P_TASKS[0]
    msgs = _mensagens_iniciais(task, tmp_path, "boot")
    assert [m["role"] for m in msgs] == ["system", "user", "user"]
    assert msgs[1]["content"] == task["prompt"]
    assert msgs[2]["content"] == task["boot_note"]


def test_task_sem_boot_note_mensagens_identicas(tmp_path):
    task = TASKS_SWE[0]
    assert "boot_note" not in task
    msgs = _mensagens_iniciais(task, tmp_path, "sem_boot")
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[1]["content"] == task["prompt"]


def test_summarize_nao_protege_boot_note():
    task = P_TASKS[0]
    messages = [{"role": "system", "content": "sys"},
                {"role": "user", "content": task["prompt"]},
                {"role": "user", "content": task["boot_note"]}]
    for i in range(8):  # boot fica fora da janela keep_last
        messages.append({"role": "assistant" if i % 2 == 0 else "user",
                         "content": f"mensagem posterior {i}"})
    out = summarize_messages(messages, keep_last=6, task_chars=len(task["prompt"]))
    assert out[1]["content"] == task["prompt"]  # task protegida na íntegra
    a_const, b_const = _constantes(task)
    blob = "".join(m["content"] or "" for m in out)
    assert task["boot_note"] not in blob
    assert a_const not in blob and b_const not in blob  # informação irrecuperável
