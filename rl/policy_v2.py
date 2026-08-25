"""Política treinável de context_policy no harness V2 (mini-SWE): logística π_θ(summarize|φ).

Herança múltipla enxuta: a matemática logística (p_summarize, grad_logp, set_turn_state,
decision_log, reseed) vem de LogisticContextPolicy; as decisões fixas do V2
(observation_policy, test_schedule) e retry/termination vêm de HarnessV2. Só features()
muda: a feature de tokens é normalizada pelo summarize_threshold_tokens da config
(no V1 era /1000), então "1.0" significa "no limiar da regra fixa".
"""
from agent.harness import estimate_tokens
from agent.harness_v2 import HarnessV2

from .policy import N_FEATURES, LogisticContextPolicy  # noqa: F401 (contrato do V1)

# Centering fixo a priori (mesmo racional do CENTER_C1B): tokens/threshold centrado
# em 1.0 (o ponto de decisão da regra fixa); demais no ponto médio 0.5. Bias intocado.
CENTER_V2 = [0.0, 1.0, 0.5, 0.5, 0.5]


class LogisticContextPolicyV2(LogisticContextPolicy, HarnessV2):
    """HarnessV2 com context_policy treinável; demais decisões continuam regras fixas.

    MRO: a logística sobrescreve decide_context_policy exatamente como o V1 faz com
    Harness; __init__(**harness_kw) alcança HarnessV2 (aceita observation_policy e
    test_schedule) e config() carrega kind="v2" + θ.
    """

    def features(self, messages: list[dict]) -> list[float]:
        raw = [1.0,
               estimate_tokens(messages) / self.summarize_threshold_tokens,
               self._turn / self.max_turns,
               self._tests_passed_frac,
               self._n_writes / 3.0]
        if self.center is None:
            return raw
        return [f - c for f, c in zip(raw, self.center)]
