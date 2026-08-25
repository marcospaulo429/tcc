"""Amostrador de a′ para o protocolo V2 plain-text (census multi-decisão, pré-reg 29).

Análogo a interventions/model.py, mas o parse é o do loop V2 (LIST/READ/WRITE/TEST/
FINISH) e um write_file PARCIAL (sem "content") dispara a fase 2 do protocolo:
pedido do conteúdo em lista TEMPORÁRIA (não vaza p/ contexto), bloco ```python```
extraído com o MESMO regex do loop_v2 — a′ de write_file inclui o conteúdo da
fase 2. Fase 2 sem bloco → tentativa inválida (próxima seed).
"""
import json

from agent.loop_v2 import _BLOCK_RE, PEDIDO_CONTEUDO, parse_action_v2


def _canonical(action: dict) -> str:
    return json.dumps({k: v for k, v in action.items() if k != "forced"},
                      sort_keys=True, ensure_ascii=False)


def sample_alternative_v2(llm, messages, original_action, *, temperature=0.8,
                          seeds=tuple(range(2001, 2009)), max_tokens=2048) -> dict:
    """Tenta seeds EM SEQUÊNCIA; retorna na primeira a′ válida ≠ original (canônico).

    Retorno: {"found", "action", "seed", "n_tried",
              "attempts": [{"seed", "finish_reason", "valid", "differs", "phase2"}]}.
    """
    orig = _canonical(original_action)
    attempts = []
    for seed in seeds:
        out = llm.chat(messages, temperature=temperature, seed=seed,
                       max_tokens=max_tokens)
        action = parse_action_v2(out["text"])
        phase2 = False
        if action is not None and action["action"] == "write_file" \
                and "content" not in action:
            phase2 = True
            path = action["path"]
            tmp = messages + [
                {"role": "assistant", "content": f"WRITE {path}"},
                {"role": "user", "content": PEDIDO_CONTEUDO.format(path=path)}]
            out2 = llm.chat(tmp, temperature=temperature, seed=seed,
                            max_tokens=max_tokens)
            b = _BLOCK_RE.search(out2["text"])
            action = {"action": "write_file", "path": path,
                      "content": b.group(1)} if b else None
        valid = action is not None
        differs = bool(valid and _canonical(action) != orig)
        attempts.append({"seed": seed, "finish_reason": out.get("finish_reason"),
                         "valid": valid, "differs": differs, "phase2": phase2})
        if differs:
            return {"found": True, "action": action, "seed": seed,
                    "n_tried": len(attempts), "attempts": attempts}
    return {"found": False, "action": None, "seed": None,
            "n_tried": len(attempts), "attempts": attempts}
