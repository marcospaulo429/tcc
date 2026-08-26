"""Probe diagnóstico (infra, sem análise de screening): imprime o output cru
do modelo servido para as 3 tasks do smoke e testa dois parsers:
o atual (greedy) e um candidato balanceado (primeiro objeto JSON válido)."""
import importlib
import json

from agent.llm import LLMClient
from agent.loop import Episode, parse_action


def parse_balanced(text: str):
    """Candidato: varre objetos {…} balanceados e devolve o 1º JSON válido de ação."""
    i = 0
    while (start := text.find("{", i)) != -1:
        depth, in_str, esc = 0, False, False
        for j in range(start, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    cand = text[start:j + 1]
                    try:
                        obj = json.loads(cand)
                        if isinstance(obj, dict) and obj.get("action") in {"write_file", "run_tests", "finish"}:
                            if obj["action"] == "write_file" and not (
                                    isinstance(obj.get("path"), str) and isinstance(obj.get("content"), str)):
                                break
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
        i = start + 1
    return None


def main() -> None:
    tasks = importlib.import_module("environment.tasks_all").TASKS[:3]
    llm = LLMClient()
    for task in tasks:
        messages = [{"role": "system", "content": Episode.SYSTEM_PROMPT},
                    {"role": "user", "content": task["prompt"]}]
        if task.get("boot_note"):
            messages.append({"role": "user", "content": task["boot_note"]})
        out = llm.chat(messages)
        text = out["text"]
        print(f"\n===== {task['task_id']} | greedy={'OK' if parse_action(text) else 'FALHA'} "
              f"| balanced={'OK' if parse_balanced(text) else 'FALHA'} =====")
        print(text[:1500])
        print("... [truncado]" if len(text) > 1500 else "[fim]")


if __name__ == "__main__":
    main()
