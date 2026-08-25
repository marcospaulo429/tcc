"""Loop V2 (piloto mini-SWE, pré-reg 28): tools multi-arquivo + 5 tipos de decisão de harness.

Mesmo invariante do V1: o estado evolui só em função da AÇÃO canônica. Diferenças:
- ações do modelo: list_files, read_file, write_file, run_tests, finish;
- decisões novas do harness (test_schedule, observation_policy) são gravadas em ORDEM
  DE EXECUÇÃO (o tool_call é gravado ANTES de aplicar a ação), para que uma fila
  forçada construída da trajetória reproduza o prefixo exatamente.
"""
import json

from .harness_v2 import HarnessV2  # noqa: F401 (par canônico do EpisodeV2 no replay)
from .loop import _JSON_RE, Episode

SYSTEM_PROMPT_V2 = """Você é um agente de programação num repositório Python com testes falhando.
Responda SEMPRE com um único objeto JSON, sem texto fora dele. Ações disponíveis:
{"action": "list_files"}
{"action": "read_file", "path": "<arquivo>"}
{"action": "write_file", "path": "<arquivo>", "content": "<conteúdo COMPLETO do arquivo>"}
{"action": "run_tests"}
{"action": "finish"}
Explore o repositório, localize o bug, corrija reescrevendo o arquivo inteiro com
write_file e confirme com run_tests. Use finish quando os testes passarem."""

_V2_ACTIONS = ("list_files", "read_file", "write_file", "run_tests", "finish")
MODEL_ACTIONS_V2 = [{"action": a} for a in _V2_ACTIONS]


def _safe_path(path: str) -> bool:
    return bool(path) and not path.startswith(("/", "~")) and ".." not in path.split("/")


def parse_action_v2(text: str) -> dict | None:
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or obj.get("action") not in _V2_ACTIONS:
        return None
    a = obj["action"]
    if a == "read_file":
        if not isinstance(obj.get("path"), str):
            return None
        return {"action": a, "path": obj["path"]}  # canônico: só chaves relevantes
    if a == "write_file":
        if not (isinstance(obj.get("path"), str) and isinstance(obj.get("content"), str)):
            return None
        return {"action": a, "path": obj["path"], "content": obj["content"]}
    return {"action": a}


class EpisodeV2(Episode):
    MODEL_ACTIONS = MODEL_ACTIONS_V2
    SYSTEM_PROMPT = SYSTEM_PROMPT_V2
    _parse = staticmethod(parse_action_v2)

    def _seed_workspace(self) -> None:
        for rel, content in self.task["repo_files"].items():
            self.sandbox.write_file(rel, content)

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
        messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
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
