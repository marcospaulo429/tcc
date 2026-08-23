"""Política treinável de context_policy (C1): logística π_θ(summarize | φ).

Herda do Harness: retry e termination continuam regras fixas. Os insumos de φ que
não estão em `messages` (turn, tests_passed_frac, n_writes) são injetados pelo
runner via set_turn_state() ANTES de cada decisão — a assinatura de
decide_context_policy não muda.
"""
import math
import random

from agent.harness import Harness, estimate_tokens

N_FEATURES = 5

# C1b (pré-registro 12): centering fixo a priori das features não-bias.
# tokens/1000 centrado em 0.6 (context_threshold default da família de harness);
# demais centradas no ponto médio 0.5 dos ranges [0,1]. Bias intocado.
CENTER_C1B = [0.0, 0.6, 0.5, 0.5, 0.5]


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


class LogisticContextPolicy(Harness):
    """Harness com context_policy treinável; retry/termination herdados (regras fixas)."""

    def __init__(self, theta: list[float] | None = None, rng_seed: int = 0,
                 greedy: bool = False, center: list[float] | None = None,
                 **harness_kw):
        super().__init__(**harness_kw)
        self.theta = list(theta) if theta is not None else [0.0] * N_FEATURES
        if len(self.theta) != N_FEATURES:
            raise ValueError(f"theta deve ter {N_FEATURES} componentes")
        self.center = list(center) if center is not None else None
        if self.center is not None and len(self.center) != N_FEATURES:
            raise ValueError(f"center deve ter {N_FEATURES} componentes")
        self.greedy = greedy
        self.rng_seed = rng_seed
        self._rng = random.Random(rng_seed)  # rng próprio, nunca o global
        self._turn = 0
        self._tests_passed_frac = 0.0
        self._n_writes = 0
        self.decision_log: list[dict] = []  # (phi, action, p) por decisão, p/ o gradiente

    def reseed(self, seed: int) -> None:
        self.rng_seed = seed
        self._rng = random.Random(seed)

    def set_turn_state(self, turn: int, tests_passed_frac: float, n_writes: int) -> None:
        """Hook chamado pelo runner antes de cada decisão de context_policy."""
        self._turn = turn
        self._tests_passed_frac = tests_passed_frac
        self._n_writes = n_writes

    def features(self, messages: list[dict]) -> list[float]:
        raw = [1.0,
               estimate_tokens(messages) / 1000.0,
               self._turn / self.max_turns,
               self._tests_passed_frac,
               self._n_writes / 3.0]
        if self.center is None:
            return raw
        return [f - c for f, c in zip(raw, self.center)]

    def p_summarize(self, phi: list[float]) -> float:
        return sigmoid(sum(t * f for t, f in zip(self.theta, phi)))

    def decide_context_policy(self, messages: list[dict]) -> str:
        phi = self.features(messages)
        p = self.p_summarize(phi)
        if self.greedy:
            action = "summarize_context" if p > 0.5 else "keep_context"
        else:
            action = "summarize_context" if self._rng.random() < p else "keep_context"
        self.decision_log.append({"phi": phi, "action": action, "p": p})
        return action

    def grad_logp(self, phi: list[float], action: str) -> list[float]:
        """∇θ log π(a|φ) da logística: (1[a=summarize] − p)·φ."""
        p = self.p_summarize(phi)
        ind = 1.0 if action == "summarize_context" else 0.0
        return [(ind - p) * f for f in phi]

    def config(self) -> dict:
        return {**super().config(), "theta": list(self.theta),
                "greedy": self.greedy, "rng_seed": self.rng_seed,
                "center": list(self.center) if self.center is not None else None}
