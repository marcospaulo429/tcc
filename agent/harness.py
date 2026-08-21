"""Harness V1: políticas determinísticas por regra — cada decisão é explícita e substituível."""

KEEP_LAST = 4  # mensagens preservadas no summarize (além de system + task)
TASK_CHARS = 240  # summarize trunca a task a este tamanho (0 = preserva íntegra)


def estimate_tokens(messages: list[dict]) -> int:
    return sum(len(m.get("content") or "") for m in messages) // 4


def summarize_messages(messages: list[dict], keep_last: int = KEEP_LAST,
                       task_chars: int = TASK_CHARS) -> list[dict]:
    """Resumo determinístico por regra (sem LLM): preserva system, trunca a task a
    task_chars e mantém as últimas keep_last mensagens. Perda de informação REAL —
    detalhes de spec fora dos primeiros task_chars são descartados do contexto."""
    head = [dict(messages[0])]
    task = dict(messages[1])
    if task_chars > 0 and len(task.get("content") or "") > task_chars:
        task["content"] = task["content"][:task_chars] + "\n[...enunciado resumido pelo harness]"
    body = list(messages[2:])
    tail = body[-keep_last:] if len(body) > keep_last else body
    omitted = body[:-keep_last] if len(body) > keep_last else []
    out = head + [task]
    if omitted:
        n_tests = sum(1 for m in omitted if "Resultado dos testes" in (m.get("content") or ""))
        out.append({"role": "user", "content": (
            f"[contexto resumido pelo harness: {len(omitted)} mensagens omitidas, "
            f"das quais {n_tests} eram resultados de testes. O arquivo solution.py "
            f"reflete todas as edições feitas até aqui.]")})
    return out + tail


def summarize_is_vacuous(messages: list[dict], keep_last: int = KEEP_LAST,
                         task_chars: int = TASK_CHARS) -> bool:
    """Vacuo sse aplicar o summarize não altera as mensagens."""
    return summarize_messages(messages, keep_last, task_chars) == list(messages)


class Harness:
    def __init__(self, summarize_threshold_tokens=1200, max_turns=6, keep_last=KEEP_LAST,
                 task_chars=TASK_CHARS):
        self.summarize_threshold_tokens = summarize_threshold_tokens
        self.max_turns = max_turns
        self.keep_last = keep_last
        self.task_chars = task_chars

    def config(self) -> dict:
        return {"summarize_threshold_tokens": self.summarize_threshold_tokens,
                "max_turns": self.max_turns, "keep_last": self.keep_last,
                "task_chars": self.task_chars}

    def decide_context_policy(self, messages: list[dict]) -> str:
        if estimate_tokens(messages) > self.summarize_threshold_tokens:
            return "summarize_context"
        return "keep_context"

    def decide_retry(self, n_retries_this_turn: int) -> str:
        return "retry_once" if n_retries_this_turn == 0 else "give_up"

    def decide_termination(self, turn: int, last_action: str | None, tests_passed: bool) -> str:
        if last_action == "finish" or tests_passed or turn + 1 >= self.max_turns:
            return "terminate"
        return "continue"
