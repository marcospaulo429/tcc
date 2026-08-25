"""Loop V2 (piloto mini-SWE, pré-reg 28): tools multi-arquivo + 5 tipos de decisão de harness.

Mesmo invariante do V1: o estado evolui só em função da AÇÃO canônica. Diferenças:
- ações do modelo: list_files, read_file, write_file, run_tests, finish;
- decisões novas do harness (test_schedule, observation_policy) são gravadas em ORDEM
  DE EXECUÇÃO (o tool_call é gravado ANTES de aplicar a ação), para que uma fila
  forçada construída da trajetória reproduza o prefixo exatamente.

Recalibração rodada 1 (pré-reg 28): protocolo de ação em TEXTO PLANO (LIST/READ/
WRITE/TEST/FINISH) com WRITE em duas fases — diagnóstico da rodada 1 mostrou que
o Qwen3-4B greedy sem thinking nunca emite write_file com conteúdo dentro de JSON
(0 write_file em 437 tool_calls), mas escreve normalmente em bloco ```python```
quando o conteúdo é pedido em mensagem separada. A ação CANÔNICA gravada na
trajetória permanece o dict de sempre; só a serialização modelo↔contexto mudou.
A troca da fase 2 usa lista TEMPORÁRIA: o contexto persistente evolui apenas pela
serialização canônica (serialize_action_v2), preservando o invariante de replay.
"""
import re

from .harness_v2 import HarnessV2  # noqa: F401 (par canônico do EpisodeV2 no replay)
from .loop import Episode

SYSTEM_PROMPT_V2 = """Você é um agente de programação num repositório Python com testes falhando.
Responda com UMA ação por resposta, exatamente neste formato, sem nenhum outro texto:
LIST — lista os arquivos do repositório
READ <arquivo> — mostra o conteúdo de um arquivo
WRITE <arquivo> — reescreve um arquivo (o conteúdo completo será pedido em seguida)
TEST — roda os testes
FINISH — encerra quando os testes passarem
Procedimento: TEST para ver as falhas; READ no arquivo suspeito; WRITE para corrigir;
TEST para confirmar; FINISH. Não repita uma ação já executada com os mesmos argumentos."""

PEDIDO_CONTEUDO = ("Envie agora o conteúdo COMPLETO de {path} em um único bloco "
                   "```python```.")
RETRY_MSG_V2 = ("Resposta inválida. Responda apenas com uma ação válida "
                "(LIST, READ <arquivo>, WRITE <arquivo>, TEST ou FINISH).")

_V2_ACTIONS = ("list_files", "read_file", "write_file", "run_tests", "finish")
MODEL_ACTIONS_V2 = [{"action": a} for a in _V2_ACTIONS]
_ACTION_RE = re.compile(r"^\s*(LIST|READ|TEST|FINISH|WRITE)(?:[ \t]+(\S+))?[ \t]*$", re.M)
_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)```", re.S)


def _safe_path(path: str) -> bool:
    return bool(path) and not path.startswith(("/", "~")) and ".." not in path.split("/")


def parse_action_v2(text: str) -> dict | None:
    """Texto plano → ação canônica. WRITE sem bloco inline retorna ação PARCIAL
    (sem 'content'); o conteúdo é obtido na fase 2 por _call_and_parse."""
    m = _ACTION_RE.search(text)
    if not m:
        return None
    kw, arg = m.group(1), m.group(2)
    if kw == "LIST":
        return {"action": "list_files"}
    if kw == "TEST":
        return {"action": "run_tests"}
    if kw == "FINISH":
        return {"action": "finish"}
    if not arg:
        return None
    if kw == "READ":
        return {"action": "read_file", "path": arg}
    b = _BLOCK_RE.search(text)
    if b:
        return {"action": "write_file", "path": arg, "content": b.group(1)}
    return {"action": "write_file", "path": arg}


def serialize_action_v2(action: dict) -> str:
    """Serialização CANÔNICA da ação para o contexto (função pura do dict)."""
    a = action["action"]
    if a == "list_files":
        return "LIST"
    if a == "run_tests":
        return "TEST"
    if a == "finish":
        return "FINISH"
    if a == "read_file":
        return f"READ {action['path']}"
    return f"WRITE {action['path']}\n```python\n{action['content']}\n```"


class EpisodeV2(Episode):
    MODEL_ACTIONS = MODEL_ACTIONS_V2
    SYSTEM_PROMPT = SYSTEM_PROMPT_V2
    _parse = staticmethod(parse_action_v2)

    def _seed_workspace(self) -> None:
        for rel, content in self.task["repo_files"].items():
            self.sandbox.write_file(rel, content)

    def _call_and_parse(self, messages: list[dict], turn: int) -> tuple[dict, dict]:
        """Como no V1, mas com fase 2 do WRITE em lista TEMPORÁRIA (não vaza p/ contexto)."""
        retries = 0
        while True:
            out = self.llm.chat(messages)
            costs = {k: out[k] for k in ("prompt_tokens", "completion_tokens", "wall_time_s")}
            action = self._parse(out["text"])
            if action is not None and action["action"] == "write_file" and "content" not in action:
                tmp = messages + [
                    {"role": "assistant", "content": f"WRITE {action['path']}"},
                    {"role": "user", "content": PEDIDO_CONTEUDO.format(path=action["path"])}]
                out2 = self.llm.chat(tmp)
                for k in ("prompt_tokens", "completion_tokens", "wall_time_s"):
                    costs[k] += out2[k]
                b = _BLOCK_RE.search(out2["text"])
                if b:
                    return {"action": "write_file", "path": action["path"],
                            "content": b.group(1)}, costs
                action = None  # fase 2 sem bloco → fluxo de retry
            if action is not None:
                return action, costs
            state = self._state_before(messages, turn)
            forced_r = self._consume_forced("retry")
            r_action = forced_r["action"] if forced_r else self.harness.decide_retry(retries)
            self._record("harness", "retry", state,
                         [{"action": "retry_once"}, {"action": "give_up"}],
                         {"action": r_action, "forced": bool(forced_r)},
                         {"raw_text_len": len(out["text"])}, costs)
            if r_action == "give_up":
                self.n_give_ups += 1
                return {"action": "finish"}, {}
            self.n_retries += 1
            retries += 1
            messages.append({"role": "user", "content": RETRY_MSG_V2})

    # tool_call gravado ANTES de aplicar: decisões aninhadas ficam em ordem de execução
    def _step_model(self, messages: list[dict], turn: int) -> tuple[dict, dict | None]:
        self._turn = turn
        self._step_tests = None
        state = self._state_before(messages, turn)
        forced = self._consume_forced("tool_call")
        if forced:
            action, costs = forced, {}
        else:
            action, costs = self._call_and_parse(messages, turn)
        did = self.recorder.record("model", "tool_call", state, self.MODEL_ACTIONS,
                                   {**action, "forced": bool(forced)})
        obs = self._apply_model_action(action, messages)
        self.recorder.observe(did, obs, costs)
        return action, self._step_tests

    def _apply_model_action(self, action: dict, messages: list[dict]) -> dict:
        messages.append({"role": "assistant", "content": serialize_action_v2(action)})
        a = action["action"]
        if a == "list_files":
            files = self.sandbox.list_files()
            messages.append({"role": "user",
                             "content": "Arquivos do repositório: " + ", ".join(files)})
            return {"ok": True, "n_files": len(files)}
        if a == "read_file":
            if not _safe_path(action["path"]):
                messages.append({"role": "user", "content": f"Caminho inválido: {action['path']}"})
                return {"ok": False, "invalid_path": True}
            try:
                content = self.sandbox.read_file(action["path"])
            except (FileNotFoundError, IsADirectoryError):
                messages.append({"role": "user", "content": f"Arquivo {action['path']} não existe."})
                return {"ok": False}
            messages.append({"role": "user",
                             "content": f"Conteúdo de {action['path']}:\n{content}"})
            return {"ok": True, "chars": len(content)}
        if a == "write_file":
            if not _safe_path(action["path"]):
                messages.append({"role": "user", "content": f"Caminho inválido: {action['path']}"})
                return {"ok": False, "invalid_path": True}
            self.sandbox.write_file(action["path"], action["content"])
            messages.append({"role": "user", "content": f"Arquivo {action['path']} gravado."})
            obs = {"ok": True}
            if self._step_test_schedule(messages) == "auto_test":
                obs["auto_tests"] = self._run_and_report_tests(messages)
            return obs
        if a == "run_tests":
            return self._run_and_report_tests(messages)
        return {"finished": True}

    # -- decisões novas do harness ------------------------------------------
    def _step_test_schedule(self, messages: list[dict]) -> str:
        state = self._state_before(messages, self._turn)
        forced = self._consume_forced("test_schedule")
        action = forced["action"] if forced else self.harness.decide_test_schedule()
        self._record("harness", "test_schedule", state,
                     [{"action": "auto_test"}, {"action": "defer_test"}],
                     {"action": action, "forced": bool(forced)}, {})
        return action

    def _run_and_report_tests(self, messages: list[dict]) -> dict:
        res = self.sandbox.run_tests(self.task["test_code"])
        state = self._state_before(messages, self._turn)
        forced = self._consume_forced("observation_policy")
        policy = forced["action"] if forced else self.harness.decide_observation_policy()
        full = "" if res["success"] else f"\nSaída:\n{res['output'][-1200:]}"
        if policy == "compact_output" and not res["success"]:
            first = next((ln for ln in res["output"].splitlines()
                          if "assert" in ln or "Error" in ln), "")
            shown = f"\nPrimeira falha:\n{first}" if first else ""
        else:
            shown = full
        messages.append({"role": "user", "content":
                         f"Resultado dos testes: {res['passed']}/{res['total']} passaram." + shown})
        self._record("harness", "observation_policy", state,
                     [{"action": "full_output"}, {"action": "compact_output"}],
                     {"action": policy, "forced": bool(forced)},
                     {"chars_full": len(full), "chars_shown": len(shown),
                      "reward": res["reward"]})
        self._step_tests = {k: res[k] for k in
                            ("passed", "failed", "errors", "total", "reward",
                             "success", "timed_out")}
        return self._step_tests
