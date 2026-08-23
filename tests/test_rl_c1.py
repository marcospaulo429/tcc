"""Testes do C1 (rl/policy.py + rl/train_c1.py) — SEM servidor: LLM fake determinístico."""
import json
import math

import pytest

from environment.tasks_v2 import TASKS as TASKS_V2
from rl.policy import LogisticContextPolicy
from rl.train_c1 import collect_episode, credit_for_point, train
from trajectories.schema import load_trajectory

GOOD_SOLUTION = "def foo():\n    return 42\n"
WRITE_GOOD = json.dumps({"action": "write_file", "path": "solution.py",
                         "content": GOOD_SOLUTION})
RUN_TESTS = '{"action": "run_tests"}'
FINISH = '{"action": "finish"}'

# prompt >240 chars para o summarize truncar e deixar marca detectável no contexto
SYNTH_TASK = {
    "task_id": "synth_marker",
    "prompt": ("Implemente em solution.py a funcao foo() que retorna 42. "
               + "Este paragrafo existe apenas para deixar o enunciado longo o "
                 "suficiente para o summarize do harness truncar o texto. " * 3),
    "starter_code": "def foo():\n    return 0\n",
    "test_code": "from solution import foo\n\n\ndef test_foo():\n    assert foo() == 42\n",
}

MARKER = "resumido pelo harness"


class ScriptedFakeLLM:
    """Devolve textos em sequência (cíclico); custos fixos e determinísticos."""

    def __init__(self, script):
        self.script = list(script)
        self.call_count = 0

    def config(self):
        return {"model": "fake", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kw):
        text = self.script[self.call_count % len(self.script)]
        self.call_count += 1
        return {"text": text, "prompt_tokens": 100, "completion_tokens": 5,
                "wall_time_s": 0.0, "finish_reason": "stop"}


class BranchingFakeLLM:
    """Roteiro condicional ao contexto: um script quando há marca de summarize,
    outro quando não há. Iteradores por episódio (reset quando não há assistant)."""

    def __init__(self, script_summarized, script_keep):
        self.script_sum = list(script_summarized)
        self.script_keep = list(script_keep)
        self.call_count = 0
        self._i_sum = 0
        self._i_keep = 0

    def config(self):
        return {"model": "fake-branching", "temperature": 0.0, "seed": 0, "max_tokens": 0}

    def chat(self, messages, **kw):
        self.call_count += 1
        if not any(m.get("role") == "assistant" for m in messages):
            self._i_sum = self._i_keep = 0  # início de episódio/replay
        summarized = any(MARKER in (m.get("content") or "") for m in messages)
        if summarized:
            text = self.script_sum[min(self._i_sum, len(self.script_sum) - 1)]
            self._i_sum += 1
        else:
            text = self.script_keep[min(self._i_keep, len(self.script_keep) - 1)]
            self._i_keep += 1
        return {"text": text, "prompt_tokens": 100, "completion_tokens": 5,
                "wall_time_s": 0.0, "finish_reason": "stop"}


def _msgs(n_chars_task=300):
    return [{"role": "system", "content": "s" * 200},
            {"role": "user", "content": "t" * n_chars_task}]


# -- logística ------------------------------------------------------------------

def test_theta_zero_gives_p_half_and_greedy_keep():
    pol = LogisticContextPolicy(theta=[0.0] * 5, greedy=True)
    phi = pol.features(_msgs())
    assert pol.p_summarize(phi) == 0.5
    assert pol.decide_context_policy(_msgs()) == "keep_context"  # p>0.5 é estrito


def test_grad_logp_matches_finite_difference():
    theta = [0.3, -0.2, 0.1, 0.5, -0.4]
    phi = [1.0, 0.8, 0.5, 0.7, 1 / 3]

    def logp(th, action):
        p = 1.0 / (1.0 + math.exp(-sum(t * f for t, f in zip(th, phi))))
        return math.log(p if action == "summarize_context" else 1.0 - p)

    pol = LogisticContextPolicy(theta=theta)
    h = 1e-6
    for action in ("summarize_context", "keep_context"):
        grad = pol.grad_logp(phi, action)
        for i in range(5):
            up = list(theta)
            dn = list(theta)
            up[i] += h
            dn[i] -= h
            num = (logp(up, action) - logp(dn, action)) / (2 * h)
            assert grad[i] == pytest.approx(num, abs=1e-5)


def test_sampling_reproducible_and_greedy_differs():
    theta = [1.0, 0.0, 0.0, 0.0, 0.0]  # p = sigmoid(1) ≈ 0.73
    a = LogisticContextPolicy(theta=theta, rng_seed=7)
    b = LogisticContextPolicy(theta=theta, rng_seed=7)
    seq_a = [a.decide_context_policy(_msgs()) for _ in range(30)]
    seq_b = [b.decide_context_policy(_msgs()) for _ in range(30)]
    assert seq_a == seq_b  # mesmo seed → mesma sequência
    assert {"keep_context", "summarize_context"} == set(seq_a)  # amostrado mistura
    g = LogisticContextPolicy(theta=theta, greedy=True)
    seq_g = [g.decide_context_policy(_msgs()) for _ in range(30)]
    assert seq_g == ["summarize_context"] * 30  # greedy determinístico
    other = LogisticContextPolicy(theta=theta, rng_seed=8)
    assert [other.decide_context_policy(_msgs()) for _ in range(30)] != seq_a


def test_decision_log_filled():
    pol = LogisticContextPolicy(theta=[0.0] * 5, rng_seed=3)
    for _ in range(4):
        pol.decide_context_policy(_msgs())
    assert len(pol.decision_log) == 4
    for entry in pol.decision_log:
        assert set(entry) == {"phi", "action", "p"}
        assert len(entry["phi"]) == 5 and entry["p"] == 0.5


def test_features_use_turn_state_hook():
    pol = LogisticContextPolicy(max_turns=6)
    pol.set_turn_state(turn=3, tests_passed_frac=0.5, n_writes=2)
    phi = pol.features(_msgs())
    assert phi[0] == 1.0
    assert phi[2] == pytest.approx(3 / 6)
    assert phi[3] == pytest.approx(0.5)
    assert phi[4] == pytest.approx(2 / 3)


# -- collect_episode --------------------------------------------------------------

def test_collect_episode_r_eff_and_cp_points(tmp_path):
    llm = ScriptedFakeLLM([WRITE_GOOD, RUN_TESTS])
    pol = LogisticContextPolicy(theta=[0.0] * 5, greedy=True)  # keep sempre
    ep = collect_episode(SYNTH_TASK, llm, pol, tmp_path / "ep", episode_seed=11,
                         lambda_cost=1.0)
    # turno 0: write; turno 1: run_tests passa → terminate. 2 chamadas × 100 tokens.
    assert ep["R"] == 1.0
    assert ep["llm_calls"] == 2 == llm.call_count
    assert ep["prompt_tokens_total"] == 200
    assert ep["R_eff"] == pytest.approx(1.0 - 1.0 * 200 / 100000)
    traj = load_trajectory(ep["trajectory"])
    assert len(ep["cp_points"]) == 2
    for pt in ep["cp_points"]:
        d = traj.decisions[pt["index"]]
        assert d.decision_point == "context_policy"
        assert d.chosen_action["action"] == pt["action"] == "keep_context"
        assert pt["p"] == 0.5 and len(pt["phi"]) == 5


# -- crédito C(H) via replay de verdade -------------------------------------------

def test_credit_ch_uses_real_replay(tmp_path):
    task = TASKS_V2[0]  # registrada no registry (necessário p/ replay) e prompt >240
    assert len(task["prompt"]) > 240
    # sem marca → finish direto (R=0, 1 chamada); com marca → run_tests, finish (2 chamadas)
    llm = BranchingFakeLLM(script_summarized=[RUN_TESTS, FINISH], script_keep=[FINISH])
    pol = LogisticContextPolicy(theta=[0.0] * 5, greedy=True)  # keep no baseline
    ep = collect_episode(task, llm, pol, tmp_path / "base", episode_seed=1,
                         lambda_cost=1.0)
    assert ep["R"] == 0.0 and ep["llm_calls"] == 1
    assert ep["R_eff"] == pytest.approx(-100 / 100000)

    traj = load_trajectory(ep["trajectory"])
    cp = traj.decisions[ep["cp_points"][0]["index"]]
    greedy = LogisticContextPolicy(theta=[0.0] * 5, greedy=True)
    calls_before = llm.call_count
    res = credit_for_point(traj, cp, llm, greedy, "ch", tmp_path / "replays",
                           lambda_cost=1.0)
    # replay flip (summarize) gasta 2 chamadas → 200 tokens; prefixo original = 0
    # C_H_eff = R_eff_orig − R_eff_flip = −0.001 − (−0.002) = 0.001
    assert res["llm_calls"] == 2 == llm.call_count - calls_before
    assert res["credit"] == pytest.approx((-100 / 100000) - (-200 / 100000))


# -- treino outcome: sanidade de aprendizado --------------------------------------

def _branching_training_llm():
    # summarize → escreve solução boa e passa (R=1); keep → finish imediato (R=0)
    return BranchingFakeLLM(script_summarized=[WRITE_GOOD, RUN_TESTS],
                            script_keep=[FINISH])


def test_train_outcome_moves_p_summarize_up(tmp_path):
    llm = _branching_training_llm()
    summary = train([SYNTH_TASK], llm, arm="outcome", budget_calls=60, seed=1,
                    out_dir=tmp_path / "train", lambda_cost=1.0)
    assert summary["episodes"] >= 30  # ≤2 chamadas/episódio
    pol = LogisticContextPolicy(theta=summary["theta"], greedy=True)
    p0 = pol.p_summarize(pol.features(_msgs()))
    assert p0 > 0.6, f"p(summarize) não subiu: {p0} (theta={summary['theta']})"


def test_train_budget_accounting_and_stop(tmp_path):
    llm = _branching_training_llm()
    budget = 10
    summary = train([SYNTH_TASK], llm, arm="outcome", budget_calls=budget, seed=2,
                    out_dir=tmp_path / "train", lambda_cost=1.0)
    assert summary["llm_calls_total"] == llm.call_count  # contagem bate com o fake
    assert summary["llm_calls_total"] >= budget  # parou ao esgotar
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    assert len(rows) == summary["episodes"]
    assert rows[-1]["calls_cum"] == llm.call_count
    # o penúltimo episódio ainda estava dentro do orçamento (senão teria parado antes)
    if len(rows) > 1:
        assert rows[-2]["calls_cum"] < budget
    for r in rows:
        assert r["arm"] == "outcome" and len(r["theta"]) == 5


def test_train_arm_zero_freezes_theta_and_pays_no_replays(tmp_path):
    llm = _branching_training_llm()
    summary = train([SYNTH_TASK], llm, arm="zero", budget_calls=20, seed=3,
                    out_dir=tmp_path / "train", lambda_cost=1.0)
    assert summary["theta"] == [0.0] * 5  # controle: crédito 0 → θ nunca muda
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    for r in rows:
        assert r["credits"] == [] and r["grad_norm"] == 0.0
    # 0 replays: todas as chamadas vêm de episódios (mesma dose que outcome)
    llm2 = _branching_training_llm()
    ref = train([SYNTH_TASK], llm2, arm="outcome", budget_calls=20, seed=3,
                out_dir=tmp_path / "ref", lambda_cost=1.0)
    assert summary["episodes"] == ref["episodes"]


def test_center_shifts_features_not_bias():
    pol = LogisticContextPolicy(center=[0.0, 0.6, 0.5, 0.5, 0.5])
    raw = LogisticContextPolicy()
    m = _msgs()
    f_raw, f_c = raw.features(m), pol.features(m)
    assert f_c[0] == 1.0  # bias intocado
    assert abs(f_c[1] - (f_raw[1] - 0.6)) < 1e-12
    assert all(abs(f_c[i] - (f_raw[i] - 0.5)) < 1e-12 for i in (2, 3, 4))
    assert "center" in pol.config() and pol.config()["center"][1] == 0.6


def test_train_clip_norm_limits_update(tmp_path):
    llm = _branching_training_llm()
    summary = train([SYNTH_TASK], llm, arm="outcome", budget_calls=10, seed=4,
                    out_dir=tmp_path / "train", lambda_cost=1.0,
                    lr=0.1, clip_norm=1.0)
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    prev = [0.0] * 5
    for r in rows:
        step = math.sqrt(sum((a - b) ** 2 for a, b in zip(r["theta"], prev)))
        assert step <= 0.1 + 1e-9, f"update excedeu lr*clip: {step}"
        prev = r["theta"]
        assert r["grad_norm"] >= 0.0  # grad_norm logado é PRÉ-clip
