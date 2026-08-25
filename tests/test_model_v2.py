"""sample_alternative_v2: a′ no protocolo V2 plain-text, com fase 2 do WRITE — sem GPU/rede."""
from agent.loop_v2 import PEDIDO_CONTEUDO
from interventions.model_v2 import sample_alternative_v2


class FakeLLM:
    """Respostas em sequência; grava cada chamada (messages + kwargs) p/ auditoria."""

    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    def chat(self, messages, **kw):
        self.calls.append({"messages": [dict(m) for m in messages], **kw})
        text = self._replies.pop(0) if len(self._replies) > 1 else self._replies[0]
        return {"text": text, "finish_reason": "stop"}


MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "t"}]


def test_acha_alternativa_simples():
    llm = FakeLLM(["TEST"])
    r = sample_alternative_v2(llm, MSGS, {"action": "list_files"})
    assert r["found"] and r["action"] == {"action": "run_tests"}
    assert r["seed"] == 2001 and r["n_tried"] == 1
    assert r["attempts"][0] == {"seed": 2001, "finish_reason": "stop",
                                "valid": True, "differs": True, "phase2": False}
    # kwargs propagados (temperature/seed/max_tokens)
    assert llm.calls[0]["temperature"] == 0.8 and llm.calls[0]["seed"] == 2001
    assert llm.calls[0]["max_tokens"] == 2048


def test_write_parcial_dispara_fase_2():
    llm = FakeLLM(["WRITE x.py", "```python\nx = 1\n```"])
    r = sample_alternative_v2(llm, MSGS, {"action": "run_tests"})
    assert r["found"] and r["seed"] == 2001
    assert r["action"] == {"action": "write_file", "path": "x.py", "content": "x = 1\n"}
    assert r["attempts"][0]["phase2"] is True
    # a fase 2 usa lista TEMPORÁRIA: assistant "WRITE x.py" + pedido do conteúdo
    tmp = llm.calls[1]["messages"]
    assert tmp[:len(MSGS)] == MSGS
    assert tmp[-2] == {"role": "assistant", "content": "WRITE x.py"}
    assert tmp[-1] == {"role": "user",
                       "content": PEDIDO_CONTEUDO.format(path="x.py")}
    assert llm.calls[1]["seed"] == 2001  # mesma seed da fase 1


def test_fase_2_sem_bloco_e_invalida_tenta_proxima_seed():
    llm = FakeLLM(["WRITE x.py", "sem bloco aqui", "TEST"])
    r = sample_alternative_v2(llm, MSGS, {"action": "list_files"})
    assert r["found"] and r["seed"] == 2002 and r["n_tried"] == 2
    assert r["action"] == {"action": "run_tests"}
    assert r["attempts"][0] == {"seed": 2001, "finish_reason": "stop",
                                "valid": False, "differs": False, "phase2": True}


def test_not_found_quando_tudo_igual_a_original():
    llm = FakeLLM(["LIST"])
    r = sample_alternative_v2(llm, MSGS, {"action": "list_files", "forced": True})
    assert not r["found"] and r["action"] is None and r["seed"] is None
    assert r["n_tried"] == 8 and len(r["attempts"]) == 8
    assert all(a["valid"] and not a["differs"] for a in r["attempts"])
    assert [a["seed"] for a in r["attempts"]] == list(range(2001, 2009))
