"""Testes do treino V2 (rl/policy_v2.py + rl/train_v2.py) — SEM servidor: LLM fake determinístico."""
import math

import httpx2 as httpx  # openai 3.x depende de httpx2 (fork), não de httpx
import openai
import pytest

from environment.tasks_swe import TASKS
from rl.policy_v2 import CENTER_V2, LogisticContextPolicyV2
from rl.train_v2 import (_replay_with_policy, calibrate, collect_episode,
                         credit_for_point, train)
from trajectories.schema import load_trajectory

TASK = TASKS[0]  # registrada no registry (necessário p/ replay)
FIX = TASK["canonical_files"][TASK["bug_file"]]
BUG = TASK["repo_files"][TASK["bug_file"]]
# WRITE com bloco inline → 1 chamada só (sem fase 2), contagem de orçamento simples
WRITE_FIX = f"WRITE {TASK['bug_file']}\n```python\n{FIX}```"
WRITE_BUG = f"WRITE {TASK['bug_file']}\n```python\n{BUG}```"


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


def _msgs(n_chars_task=300):
    return [{"role": "system", "content": "s" * 200},
            {"role": "user", "content": "t" * n_chars_task}]


def _overflow_error():
    req = httpx.Request("POST", "http://fake/v1/chat/completions")
    resp = httpx.Response(400, request=req,
                          json={"error": {"message": "maximum context length exceeded"}})
    return openai.BadRequestError("maximum context length exceeded",
                                  response=resp, body=None)


class OverflowFakeLLM(ScriptedFakeLLM):
    """Levanta BadRequestError (overflow de contexto) na fail_at-ésima chamada (1-based)."""

    def __init__(self, script, fail_at):
        super().__init__(script)
        self.fail_at = fail_at

    def chat(self, messages, **kw):
        if self.call_count + 1 == self.fail_at:
            self.call_count += 1
            raise _overflow_error()
        return super().chat(messages, **kw)


# -- política V2 -----------------------------------------------------------------

def test_features_normalized_by_threshold():
    pol = LogisticContextPolicyV2(summarize_threshold_tokens=1000)
    pol.set_turn_state(turn=5, tests_passed_frac=0.5, n_writes=2)
    phi = pol.features(_msgs())  # 500 chars → 125 tokens estimados
    assert phi[0] == 1.0
    assert phi[1] == pytest.approx(125 / 1000)  # /threshold, não /1000 fixo do V1
    assert phi[2] == pytest.approx(5 / 25)  # max_turns default V2 = 25
    assert phi[3] == pytest.approx(0.5)
    assert phi[4] == pytest.approx(2 / 3)
    default = LogisticContextPolicyV2()  # threshold default V2 = 4500
    assert default.features(_msgs())[1] == pytest.approx(125 / 4500)


def test_center_v2_shifts_features_not_bias():
    pol = LogisticContextPolicyV2(center=CENTER_V2, summarize_threshold_tokens=1000)
    raw = LogisticContextPolicyV2(summarize_threshold_tokens=1000)
    m = _msgs()
    f_raw, f_c = raw.features(m), pol.features(m)
    assert f_c[0] == 1.0  # bias intocado
    assert f_c[1] == pytest.approx(f_raw[1] - 1.0)  # centrado no limiar da regra fixa
    assert all(f_c[i] == pytest.approx(f_raw[i] - 0.5) for i in (2, 3, 4))
    cfg = pol.config()
    assert cfg["kind"] == "v2" and cfg["center"] == CENTER_V2 and "theta" in cfg


def test_greedy_vs_sampled_and_reproducible():
    theta = [1.0, 0.0, 0.0, 0.0, 0.0]  # p = sigmoid(1) ≈ 0.73
    g = LogisticContextPolicyV2(theta=theta, greedy=True)
    assert [g.decide_context_policy(_msgs()) for _ in range(20)] == \
        ["summarize_context"] * 20
    a = LogisticContextPolicyV2(theta=theta, rng_seed=7)
    b = LogisticContextPolicyV2(theta=theta, rng_seed=7)
    seq_a = [a.decide_context_policy(_msgs()) for _ in range(30)]
    assert seq_a == [b.decide_context_policy(_msgs()) for _ in range(30)]
    assert {"keep_context", "summarize_context"} == set(seq_a)
    assert len(a.decision_log) == 30
    assert set(a.decision_log[0]) == {"phi", "action", "p"}


def test_grad_logp_matches_finite_difference():
    theta = [0.3, -0.2, 0.1, 0.5, -0.4]
    phi = [1.0, 0.8, 0.5, 0.7, 1 / 3]

    def logp(th, action):
        p = 1.0 / (1.0 + math.exp(-sum(t * f for t, f in zip(th, phi))))
        return math.log(p if action == "summarize_context" else 1.0 - p)

    pol = LogisticContextPolicyV2(theta=theta)
    h = 1e-6
    for action in ("summarize_context", "keep_context"):
        grad = pol.grad_logp(phi, action)
        for i in range(5):
            up, dn = list(theta), list(theta)
            up[i] += h
            dn[i] -= h
            num = (logp(up, action) - logp(dn, action)) / (2 * h)
            assert grad[i] == pytest.approx(num, abs=1e-5)


# -- collect_episode: contadores das ações V2 --------------------------------------

def test_collect_episode_counts_writes(tmp_path):
    llm = ScriptedFakeLLM([WRITE_FIX, "TEST"])
    pol = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True,  # keep sempre
                                  test_schedule="defer_test")
    ep = collect_episode(TASK, llm, pol, tmp_path / "ep", episode_seed=11)
    # turno 0: write (defer, sem auto-teste); turno 1: TEST passa → terminate
    assert ep["R"] == 1.0 and ep["llm_calls"] == 2 == llm.call_count
    assert ep["prompt_tokens_total"] == 200
    assert len(ep["cp_points"]) == 2
    phi0, phi1 = ep["cp_points"][0]["phi"], ep["cp_points"][1]["phi"]
    assert phi0[4] == 0.0 and phi0[2] == 0.0
    assert phi1[4] == pytest.approx(1 / 3)  # write_file do protocolo V2 contado
    assert phi1[3] == 0.0  # defer_test: nenhum teste rodou antes da 2ª decisão
    assert phi1[2] == pytest.approx(1 / 25)


def test_collect_episode_auto_tests_update_frac(tmp_path):
    llm = ScriptedFakeLLM([WRITE_BUG, "FINISH"])
    pol = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True)  # auto_test default
    ep = collect_episode(TASK, llm, pol, tmp_path / "ep", episode_seed=12)
    traj = load_trajectory(ep["trajectory"])
    w = next(d for d in traj.decisions if d.decision_point == "tool_call"
             and d.chosen_action["action"] == "write_file")
    at = w.observation["auto_tests"]  # caminho test_schedule (não run_tests do modelo)
    assert 0 < at["passed"] < at["total"]
    phi1 = ep["cp_points"][1]["phi"]
    assert phi1[3] == pytest.approx(at["passed"] / at["total"])
    assert phi1[4] == pytest.approx(1 / 3)


# -- train: braços e parada dual ---------------------------------------------------

def test_train_arm_zero_freezes_theta(tmp_path):
    import json
    llm = ScriptedFakeLLM(["FINISH"])
    summary = train([TASK], llm, arm="zero", budget_calls=3, seed=1,
                    out_dir=tmp_path / "train")
    assert summary["theta"] == [0.0] * 5
    assert summary["stopped_by"] == "budget_calls"
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    assert len(rows) == summary["episodes"]
    for r in rows:
        assert r["credits"] == [] and r["grad_norm"] == 0.0


def test_train_outcome_updates_theta_and_budget_stop(tmp_path):
    llm = ScriptedFakeLLM(["FINISH"])
    budget = 3
    summary = train([TASK], llm, arm="outcome", budget_calls=budget, seed=2,
                    out_dir=tmp_path / "train")
    assert summary["theta"] != [0.0] * 5  # adv = R_eff − 0 ≠ 0 move θ
    assert summary["llm_calls_total"] == llm.call_count >= budget
    assert summary["stopped_by"] == "budget_calls"
    assert summary["episodes"] == budget  # 1 chamada por episódio


def test_train_max_episodes_stops_first(tmp_path):
    llm = ScriptedFakeLLM(["FINISH"])
    summary = train([TASK], llm, arm="outcome", budget_calls=10**9, seed=3,
                    out_dir=tmp_path / "train", max_episodes=2)
    assert summary["episodes"] == 2
    assert summary["stopped_by"] == "max_episodes"
    assert summary["max_episodes"] == 2
    assert summary["llm_calls_total"] == 2  # episode-matched: dose registrada


# -- crédito: fallback quando a′ não é encontrado -----------------------------------

def test_credit_chm_cm_fallback_to_ch(tmp_path):
    llm = ScriptedFakeLLM(["FINISH"])
    pol = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True)  # keep no baseline
    ep = collect_episode(TASK, llm, pol, tmp_path / "base", episode_seed=1)
    assert ep["llm_calls"] == 1
    traj = load_trajectory(ep["trajectory"])
    cp = traj.decisions[ep["cp_points"][0]["index"]]
    greedy = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True)
    calls_before = llm.call_count
    res = credit_for_point(traj, cp, llm, greedy, "chm_cm", tmp_path / "replays")
    # amostragem: 8 seeds devolvem "FINISH" == ação original → a′ não encontrado
    assert res["arm"] == "chm_cm" and res["fallback"] is True
    assert res["fallback_reason"] == "a_prime não encontrado"
    assert res["n_tried"] == 8
    # 8 chamadas de amostragem + 1 do replay C_H — tudo contado no orçamento
    assert res["llm_calls"] == 9 == llm.call_count - calls_before
    # flip summarize é vácuo em [system, task] (task_chars=0) → mesmo R, mesmos tokens
    assert res["credit"] == pytest.approx(0.0)


# -- _replay_with_policy: reconstrução do prefixo -----------------------------------

def test_replay_with_policy_reconstructs_counters(tmp_path):
    llm = ScriptedFakeLLM(["TEST", WRITE_FIX, "TEST"])
    pol = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True,
                                  test_schedule="defer_test")
    ep = collect_episode(TASK, llm, pol, tmp_path / "base", episode_seed=5)
    assert ep["R"] == 1.0 and len(ep["cp_points"]) == 3
    traj = load_trajectory(ep["trajectory"])
    first_tests = next(d.observation for d in traj.decisions
                       if d.decision_point == "tool_call"
                       and d.chosen_action["action"] == "run_tests")
    f = first_tests["passed"] / first_tests["total"]
    assert 0 < f < 1

    idx = ep["cp_points"][2]["index"]  # cp do turno 2: prefixo tem 1 teste + 1 write
    greedy = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True,
                                     test_schedule="defer_test")
    llm2 = ScriptedFakeLLM(["LIST", "TEST"])
    res, rtok = _replay_with_policy(
        traj, idx, llm2, greedy, tmp_path / "rep",
        [{"point": "context_policy", "action": {"action": "keep_context"}}])
    assert res["reward"] == 1.0 and rtok == 200
    # cp forçado não loga; a 1ª decisão VIVA (turno 3) vê os contadores do prefixo
    phi = greedy.decision_log[0]["phi"]
    assert phi[2] == pytest.approx(3 / 25)
    assert phi[3] == pytest.approx(f)  # frac do TEST original reconstruída
    assert phi[4] == pytest.approx(1 / 3)  # write do prefixo contado


# -- emenda 32a: overflow de contexto = episódio falho (R=0, tokens pagos) ----------

def test_collect_episode_overflow_is_failed_episode(tmp_path):
    llm = OverflowFakeLLM(["LIST"], fail_at=2)  # 1ª chamada paga, 2ª estoura
    pol = LogisticContextPolicyV2(theta=[0.0] * 5, greedy=True)  # keep sempre
    ep = collect_episode(TASK, llm, pol, tmp_path / "ep", episode_seed=21)
    assert ep["context_overflow"] is True
    assert ep["R"] == 0.0 and ep["trajectory"] is None
    assert ep["prompt_tokens_total"] == 100  # só a chamada que retornou foi paga
    assert ep["R_eff"] == pytest.approx(-100 / 100000)
    assert ep["llm_calls"] == 2 == llm.call_count  # a chamada que estourou conta
    # cp_points vêm do decision_log da política (2 turnos iniciados), sem index
    assert len(ep["cp_points"]) == 2
    assert all(pt["index"] is None for pt in ep["cp_points"])
    assert all("phi" in pt and "action" in pt for pt in ep["cp_points"])


def test_train_outcome_survives_overflow_and_updates_theta(tmp_path):
    import json
    llm = OverflowFakeLLM(["FINISH"], fail_at=2)  # ep 0 normal, ep 1 estoura
    summary = train([TASK], llm, arm="outcome", budget_calls=10**9, seed=4,
                    out_dir=tmp_path / "train", max_episodes=2)
    assert summary["episodes"] == 2
    assert summary["theta"] != [0.0] * 5  # decision_log do overflow alimentou o grad
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    assert rows[0]["context_overflow"] is False
    assert rows[1]["context_overflow"] is True
    assert rows[1]["R"] == 0.0 and rows[1]["grad_norm"] > 0


def test_train_ch_skips_credit_on_overflow_episode(tmp_path):
    import json
    llm = OverflowFakeLLM(["FINISH"], fail_at=1)  # estoura já na 1ª chamada
    summary = train([TASK], llm, arm="ch", budget_calls=10**9, seed=5,
                    out_dir=tmp_path / "train", max_episodes=1)
    assert summary["episodes"] == 1
    assert llm.call_count == 1  # nenhum replay tentado
    rows = [json.loads(line) for line in
            (tmp_path / "train" / "train_log.jsonl").read_text().splitlines()]
    assert rows[0]["context_overflow"] is True
    assert rows[0]["credits"] == [] and rows[0]["grad_norm"] == 0.0
    assert summary["theta"] == [0.0] * 5


def test_calibrate_survives_overflow_and_marks_task(tmp_path):
    llm = OverflowFakeLLM(["FINISH"], fail_at=1)  # keep_always/1ª task estoura
    report = calibrate([TASK], llm, tmp_path / "cal", lambda_cost=1.0)
    ka = report["policies"]["keep_always"]["per_task"][0]
    assert ka["context_overflow"] is True
    assert ka["R"] == 0.0 and ka["prompt_tokens_total"] == 0
    assert ka["R_eff"] == 0.0
    for name in ("summarize_always", "default"):
        pt = report["policies"][name]["per_task"][0]
        assert pt["context_overflow"] is False and pt["prompt_tokens_total"] > 0
