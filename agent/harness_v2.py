"""Harness V2 (piloto mini-SWE, pré-reg 28): 5 tipos de decisão, todos por regra.

Herda context_policy/retry/termination do V1 e adiciona:
- observation_policy: full_output | compact_output (formatação do resultado de testes);
- test_schedule: auto_test | defer_test (rodar testes automaticamente após write_file).
"""
from .harness import Harness


class HarnessV2(Harness):
    def __init__(self, summarize_threshold_tokens=4000, max_turns=25, keep_last=6,
                 task_chars=0, summarizer="rule", observation_policy="full_output",
                 test_schedule="auto_test"):
        assert observation_policy in ("full_output", "compact_output")
        assert test_schedule in ("auto_test", "defer_test")
        super().__init__(summarize_threshold_tokens, max_turns, keep_last,
                         task_chars, summarizer)
        self.observation_policy = observation_policy
        self.test_schedule = test_schedule

    def config(self) -> dict:
        return {**super().config(), "kind": "v2",
                "observation_policy": self.observation_policy,
                "test_schedule": self.test_schedule}

    def decide_observation_policy(self) -> str:
        return self.observation_policy

    def decide_test_schedule(self) -> str:
        return self.test_schedule
