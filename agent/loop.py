"""Loop do agente: toda decisão (model|harness) é registrada e pode ser forçada (replay/counterfactual).

Invariante central p/ replay: o estado evolui só em função da AÇÃO canônica (JSON parseado),
nunca do texto bruto do modelo — uma ação forçada produz exatamente a mesma evolução de estado.
"""
import json
import re
import time

from environment.sandbox import Sandbox
from trajectories.recorder import Recorder

from .harness import Harness, estimate_tokens

SYSTEM_PROMPT = """Você é um agente de programação. Responda SEMPRE com um único objeto JSON, sem texto fora dele.
Ações disponíveis:
{"action": "write_file", "path": "solution.py", "content": "<código python completo>"}
{"action": "run_tests"}
{"action": "finish"}
Escreva a solução completa em solution.py (sobrescreve o arquivo inteiro), rode os testes para verificar, e use finish quando os testes passarem."""

MODEL_ACTIONS = [{"action": "write_file"}, {"action": "run_tests"}, {"action": "finish"}]
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_action(text: str) -> dict | None:
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or obj.get("action") not in {"write_file", "run_tests", "finish"}:
        return None
    if obj["action"] == "write_file" and not (isinstance(obj.get("path"), str) and isinstance(obj.get("content"), str)):
        return None
    return obj


class Episode:
    PHASES = ("context_policy", "tool_call", "termination")

    def __init__(self, task: dict, llm, harness: Harness, recorder: Recorder,
                 sandbox: Sandbox | None = None):
        self.task, self.llm, self.harness, self.recorder = task, llm, harness, recorder
        self.sandbox = sandbox or Sandbox()
        # fila de ações forçadas (cada item = ação canônica + "_point"); semântica peek-match:
        # o head só é consumido quando o decision_point atual casa com o dele.
        self._forced_queue: list[dict] = []
        self.n_retries = 0
        self.n_give_ups = 0

    # -- helpers -----------------------------------------------------------
    def _state_before(self, messages: list[dict], turn: int) -> dict:
        return {"messages": [dict(m) for m in messages],
                "workspace": self.sandbox.snapshot(),
                "turn": turn, "context_tokens": estimate_tokens(messages)}

    def _record(self, dtype, point, state, available, chosen, observation, costs=None):
        did = self.recorder.record(dtype, point, state, available, chosen)
        self.recorder.observe(did, observation, costs)
        return did

    def _consume_forced(self, point: str) -> dict | None:
        """Peek-match ESTRITO: consome o head da fila sse o ponto casa; senão a decisão
        roda ao vivo e o head fica esperando o ponto certo."""
        if self._forced_queue and self._forced_queue[0]["_point"] == point:
            forced = dict(self._forced_queue.pop(0))
            forced.pop("_point")
            forced.pop("forced", None)  # chave não-canônica de records antigos não pode vazar p/ contexto
            return forced
        return None

    def _apply_model_action(self, action: dict, messages: list[dict]) -> dict:
        """Aplica ação canônica; retorna observation. Muta messages/sandbox deterministicamente."""
        messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
        if action["action"] == "write_file":
            self.sandbox.write_file(action["path"], action["content"])
            messages.append({"role": "user", "content": f"Arquivo {action['path']} gravado."})
            return {"ok": True}
        if action["action"] == "run_tests":
            res = self.sandbox.run_tests(self.task["test_code"])
            messages.append({"role": "user", "content": (
                f"Resultado dos testes: {res['passed']}/{res['total']} passaram."
                + ("" if res["success"] else f"\nSaída:\n{res['output'][-1200:]}"))})
            return {k: res[k] for k in ("passed", "failed", "errors", "total", "reward", "success", "timed_out")}
        return {"finished": True}

    # -- decisões ----------------------------------------------------------
    def _step_context_policy(self, messages: list[dict], turn: int) -> list[dict]:
        state = self._state_before(messages, turn)
        forced = self._consume_forced("context_policy")
        action = forced["action"] if forced else self.harness.decide_context_policy(messages)
        new_messages = self.harness.summarize(messages, self.llm) \
            if action == "summarize_context" else list(messages)
        self._record("harness", "context_policy", state,
                     [{"action": "keep_context"}, {"action": "summarize_context"}],
                     {"action": action, "forced": bool(forced)},
                     {"messages_before": len(messages), "messages_after": len(new_messages),
                      "tokens_before": state["context_tokens"], "tokens_after": estimate_tokens(new_messages)})
        return new_messages

    def _step_model(self, messages: list[dict], turn: int) -> tuple[dict, dict | None]:
        """Retorna (ação canônica, resultado de testes se houver)."""
        state = self._state_before(messages, turn)
        forced = self._consume_forced("tool_call")
        if forced:
            action, costs = forced, {}
        else:
            action, costs = self._call_and_parse(messages, turn)
        obs = self._apply_model_action(action, messages)
        self._record("model", "tool_call", state, MODEL_ACTIONS,
                     {**action, "forced": bool(forced)}, obs, costs)
        tests = obs if action["action"] == "run_tests" else None
        return action, tests

    def _call_and_parse(self, messages: list[dict], turn: int) -> tuple[dict, dict]:
        retries = 0
        while True:
            out = self.llm.chat(messages)
            costs = {k: out[k] for k in ("prompt_tokens", "completion_tokens", "wall_time_s")}
            action = parse_action(out["text"])
            if action is not None:
                return action, costs
            state = self._state_before(messages, turn)
            r_action = self.harness.decide_retry(retries)
            self._record("harness", "retry", state,
                         [{"action": "retry_once"}, {"action": "give_up"}],
                         {"action": r_action}, {"raw_text_len": len(out["text"])}, costs)
            if r_action == "give_up":
                self.n_give_ups += 1
                return {"action": "finish"}, {}
            self.n_retries += 1
            retries += 1
            messages.append({"role": "user", "content":
                             "Resposta inválida. Responda apenas com um objeto JSON de ação válido."})

    def _step_termination(self, messages: list[dict], turn: int,
                          last_action: str | None, tests_passed: bool) -> str:
        state = self._state_before(messages, turn)
        # C2: replay a partir daqui precisa reconstruir os insumos da decisão
        state["last_action"] = last_action
        state["tests_passed"] = tests_passed
        forced = self._consume_forced("termination")
        action = forced["action"] if forced else \
            self.harness.decide_termination(turn, last_action, tests_passed)
        self._record("harness", "termination", state,
                     [{"action": "continue"}, {"action": "terminate"}],
                     {"action": action, "forced": bool(forced)},
                     {"turn": turn, "tests_passed": tests_passed})
        return action

    # -- execução ----------------------------------------------------------
    def run(self, resume: dict | None = None) -> dict:
        """resume = {"messages", "turn", "entry_point", "forced_action"|None,
        "forced_actions"|None} (de um Decision.state_before).
        forced_actions = [{"point": str, "action": dict}] consumidas em ordem (peek-match);
        forced_action (singular) é açúcar retro-compatível = fila de 1 no entry_point."""
        config = {"llm": self.llm.config(), "harness": self.harness.config(),
                  "resumed": bool(resume)}
        self.recorder.start(self.task["task_id"], config)
        t0 = time.monotonic()

        if resume:
            messages = [dict(m) for m in resume["messages"]]
            turn = resume["turn"]
            entry = resume["entry_point"]
            if entry not in self.PHASES:
                raise NotImplementedError(f"replay a partir de '{entry}' não suportado")
            if resume.get("forced_actions"):
                self._forced_queue = [{**fa["action"], "_point": fa["point"]}
                                      for fa in resume["forced_actions"]]
            elif resume.get("forced_action"):
                self._forced_queue = [{**resume["forced_action"], "_point": entry}]
        else:
            self.sandbox.write_file("solution.py", self.task["starter_code"])
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": self.task["prompt"]}]
            turn, entry = 0, "context_policy"

        # C2: entrada em termination restaura os insumos gravados no state_before
        last_action = resume.get("last_action") if resume else None
        tests_passed = bool(resume.get("tests_passed")) if resume else False

        while True:
            if entry == "context_policy":
                messages = self._step_context_policy(messages, turn)
                entry = "tool_call"
            if entry == "tool_call":
                action, tests = self._step_model(messages, turn)
                last_action = action["action"]
                tests_passed = bool(tests and tests.get("success"))
                entry = "termination"
            if entry == "termination":
                decision = self._step_termination(messages, turn, last_action, tests_passed)
                entry = "context_policy"
                if decision == "terminate":
                    break
                turn += 1

        # invariante anti-bug-silencioso: toda forced action DEVE ter sido consumida
        if self._forced_queue:
            raise RuntimeError(f"forced actions não consumidas: {self._forced_queue}")

        final = self.sandbox.run_tests(self.task["test_code"])
        n_decisions = len(self.recorder.trajectory.decisions)
        path = self.recorder.finish(final["reward"], final["success"])
        return {"reward": final["reward"], "success": final["success"],
                "trajectory_path": str(path), "wall_time_s": time.monotonic() - t0,
                "n_retries": self.n_retries, "n_give_ups": self.n_give_ups,
                "final_timed_out": final["timed_out"], "n_decisions": n_decisions}
