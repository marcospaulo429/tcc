"""Amostrador de ações alternativas do modelo (a′) para counterfactuais C(model).

Do-operator sobre a camada do modelo: a′ vem do MESMO estado (messages) da decisão
original, amostrada com temperature alta e seeds fixas (reprodutível). A primeira
ação válida cujo JSON canônico difere da original é aceita; attempts audita cada
tentativa (inclusive truncamento: finish_reason == "length").
"""
import json

from agent.loop import parse_action


def _canonical(action: dict) -> str:
    return json.dumps(action, sort_keys=True, ensure_ascii=False)


def sample_alternative(llm, messages, original_action, *, temperature=0.8,
                       seeds=tuple(range(2001, 2009)), max_tokens=1200) -> dict:
    """Tenta seeds EM SEQUÊNCIA; retorna na primeira a′ válida ≠ original (canônico).

    Retorno: {"found", "action", "seed", "n_tried",
              "attempts": [{"seed", "finish_reason", "valid", "differs"}]}.
    """
    orig = _canonical(original_action)
    attempts = []
    for seed in seeds:
        out = llm.chat(messages, temperature=temperature, seed=seed,
                       max_tokens=max_tokens)
        action = parse_action(out["text"])
        valid = action is not None
        differs = bool(valid and _canonical(action) != orig)
        attempts.append({"seed": seed, "finish_reason": out.get("finish_reason"),
                         "valid": valid, "differs": differs})
        if differs:
            return {"found": True, "action": action, "seed": seed,
                    "n_tried": len(attempts), "attempts": attempts}
    return {"found": False, "action": None, "seed": None,
            "n_tried": len(attempts), "attempts": attempts}
