"""Testes do summarizer por LLM (harness variante 'llm')."""
from agent.harness import (Harness, SUMMARY_PROMPT, llm_summarize_messages,
                           summarize_is_vacuous)


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat(self, messages, **kw):
        self.calls.append((messages, kw))
        return {"text": "RESUMO: task de somar; solution.py escrito; testes 2/3.",
                "prompt_tokens": 100, "completion_tokens": 20,
                "wall_time_s": 0.01, "finish_reason": "stop"}


def _msgs(n_body=6):
    return ([{"role": "system", "content": "sys"},
             {"role": "user", "content": "task " * 200}]
            + [{"role": "user", "content": f"m{i}"} for i in range(n_body)])


def test_llm_summarize_preserva_system_e_tail():
    llm = FakeLLM()
    out = llm_summarize_messages(_msgs(), llm, keep_last=4)
    assert out[0] == {"role": "system", "content": "sys"}
    assert "RESUMO" in out[1]["content"]
    assert [m["content"] for m in out[-4:]] == ["m2", "m3", "m4", "m5"]
    assert len(out) == 6  # system + resumo + 4 tail
    # a chamada é greedy e usa o prompt fixo
    (msgs, kw), = llm.calls
    assert msgs[0]["content"] == SUMMARY_PROMPT
    assert kw["temperature"] == 0.0
    # task + corpo omitido entram no transcript
    assert "task" in msgs[1]["content"] and "m0" in msgs[1]["content"]
    assert "m5" not in msgs[1]["content"]


def test_llm_summarize_nunca_vacuo_e_config_roundtrip():
    assert summarize_is_vacuous([{"role": "system", "content": "s"},
                                 {"role": "user", "content": "t"}],
                                summarizer="llm") is False
    h = Harness(summarize_threshold_tokens=600, max_turns=12, summarizer="llm")
    assert h.config()["summarizer"] == "llm"
    assert Harness(**h.config()).summarizer == "llm"


def test_harness_summarize_dispatch():
    llm = FakeLLM()
    msgs = _msgs()
    rule = Harness(summarizer="rule").summarize(msgs)
    assert llm.calls == []
    assert rule[0]["role"] == "system"
    out = Harness(summarizer="llm").summarize(msgs, llm)
    assert len(llm.calls) == 1
    assert "RESUMO" in out[1]["content"]
