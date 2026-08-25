"""census_v2: fila dupla, seleção de candidatos com tetos, desfechos — sem GPU/rede."""
import pytest

from experiments.census_v2 import (_candidatos_traj, _fila_dupla, avalia_desfecho,
                                   gate_f4f5)
from trajectories.schema import Decision, Trajectory


def _dec(idx, point, action, state=None, obs=None):
    return Decision(trajectory_id="t", index=idx, decision_type="x",
                    decision_point=point, state_before=state or {},
                    chosen_action=action, observation=obs)


# -- _fila_dupla ---------------------------------------------------------------
def _traj_fila():
    return Trajectory(task_id="t1", decisions=[
        _dec(0, "context_policy", {"action": "keep_context"}),
        _dec(1, "tool_call", {"action": "run_tests"}),
        _dec(2, "observation_policy", {"action": "full_output"}),
        _dec(3, "termination", {"action": "continue", "forced": False}),
        _dec(4, "context_policy", {"action": "keep_context"}),
        _dec(5, "tool_call", {"action": "run_tests", "forced": True}),
    ])


def test_fila_dupla_flip_em_i_a_prime_em_j_originais_no_meio():
    traj = _traj_fila()
    flip, a_prime = {"action": "compact_output"}, {"action": "finish"}
    entry, fila = _fila_dupla(traj, 2, flip, 5, a_prime)
    assert entry == 1  # último ponto canônico <= i (tool_call)
    assert fila == [
        {"point": "tool_call", "action": {"action": "run_tests"}},
        {"point": "observation_policy", "action": flip},
        {"point": "termination", "action": {"action": "continue"}},  # "forced" fora
        {"point": "context_policy", "action": {"action": "keep_context"}},
        {"point": "tool_call", "action": a_prime},
    ]


def test_fila_dupla_recusa_retry_antes_de_tool_call_forcado():
    traj = Trajectory(task_id="t1", decisions=[
        _dec(0, "context_policy", {"action": "keep_context"}),
        _dec(1, "retry", {"action": "retry_once"}),
        _dec(2, "tool_call", {"action": "run_tests"}),
    ])
    with pytest.raises(ValueError):
        _fila_dupla(traj, 0, {"action": "summarize_context"}, 2, {"action": "finish"})


# -- _candidatos_traj ------------------------------------------------------------
def _msgs(n_body):
    return [{"role": "system", "content": "s"}, {"role": "user", "content": "t"}] + \
        [{"role": "user", "content": f"m{i}"} for i in range(n_body)]


def _traj_cand():
    nonvac = _msgs(8)   # body 8 > keep_last 6 → summarize não-vácuo
    vac = _msgs(2)      # body 2 <= keep_last → vácuo
    decs = [
        _dec(0, "context_policy", {"action": "keep_context"},
             {"context_tokens": 100, "messages": nonvac}),
        _dec(1, "context_policy", {"action": "keep_context"},
             {"context_tokens": 300, "messages": nonvac}),
        _dec(2, "context_policy", {"action": "keep_context"},
             {"context_tokens": 200, "messages": nonvac}),
        _dec(3, "observation_policy", {"action": "full_output"},
             {"context_tokens": 1}, {"chars_full": 10}),
        _dec(4, "observation_policy", {"action": "full_output"},
             {"context_tokens": 1}, {"chars_full": 30}),
        _dec(5, "observation_policy", {"action": "full_output"},
             {"context_tokens": 1}, {"chars_full": 20}),
        _dec(6, "test_schedule", {"action": "auto_test"}, {"context_tokens": 5}),
        _dec(7, "test_schedule", {"action": "auto_test"}, {"context_tokens": 15}),
        _dec(8, "test_schedule", {"action": "auto_test"}, {"context_tokens": 10}),
        _dec(9, "termination", {"action": "continue"},
             {"context_tokens": 1, "tests_passed": False, "turn": 2}),
        _dec(10, "termination", {"action": "continue"},
             {"context_tokens": 1, "tests_passed": False, "turn": 3}),
        _dec(11, "retry", {"action": "retry_once"}, {"context_tokens": 1}),
        # filtrados: keep vácuo, observation sem chars_full, termination saturada/cedo
        _dec(12, "context_policy", {"action": "keep_context"},
             {"context_tokens": 999, "messages": vac}),
        _dec(13, "observation_policy", {"action": "full_output"},
             {"context_tokens": 1}, {"chars_full": 0}),
        _dec(14, "termination", {"action": "continue"},
             {"context_tokens": 1, "tests_passed": True, "turn": 5}),
        _dec(15, "termination", {"action": "continue"},
             {"context_tokens": 1, "tests_passed": False, "turn": 1}),
    ]
    return Trajectory(task_id="t1", decisions=decs,
                      config={"harness": {"keep_last": 6, "task_chars": 0,
                                          "summarizer": "rule"}})


def test_candidatos_respeitam_tetos_e_round_robin():
    sel = _candidatos_traj(_traj_cand())
    assert sel == [
        ("context_policy", 1, {"action": "summarize_context"}),   # melhor por tipo
        ("observation_policy", 4, {"action": "compact_output"}),
        ("test_schedule", 7, {"action": "defer_test"}),
        ("termination", 9, {"action": "terminate"}),
        ("retry", 11, {"action": "give_up"}),
        ("context_policy", 2, {"action": "summarize_context"}),   # 2º melhor → teto 6
    ]
    assert len(sel) == 6
    por_tipo = {}
    for tipo, _, _ in sel:
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
    assert all(n <= 2 for n in por_tipo.values())
    indices = [i for _, i, _ in sel]
    assert not {12, 13, 14, 15} & set(indices)  # filtrados nunca entram


def test_candidatos_deterministicos():
    assert _candidatos_traj(_traj_cand()) == _candidatos_traj(_traj_cand())


def test_candidatos_teto_por_tipo_sem_outros_tipos():
    decs = [_dec(i, "observation_policy", {"action": "full_output"},
                 {"context_tokens": 1}, {"chars_full": 10 + i}) for i in range(5)]
    traj = Trajectory(task_id="t1", decisions=decs,
                      config={"harness": {"keep_last": 6, "task_chars": 0}})
    sel = _candidatos_traj(traj)
    assert [(t, i) for t, i, _ in sel] == [("observation_policy", 4),
                                           ("observation_policy", 3)]


# -- desfechos (pré-reg 29) ------------------------------------------------------
def test_desfecho_s1_heterogeneidade():
    r = avalia_desfecho({"a": {"n": 6, "taxa": 0.5}, "b": {"n": 7, "taxa": 1.0}})
    assert r["s1"] and r["desfecho"] == "s1"


def test_desfecho_s1_prevalece_sobre_s3():
    r = avalia_desfecho({"a": {"n": 5, "taxa": 0.5}, "b": {"n": 5, "taxa": 0.6},
                         "c": {"n": 5, "taxa": 0.95}})
    assert r["s1"] and r["s3"] and r["desfecho"] == "s1"


def test_desfecho_s2_extensao():
    r = avalia_desfecho({"a": {"n": 5, "taxa": 0.95}, "b": {"n": 8, "taxa": 1.0},
                         "c": {"n": 2, "taxa": 0.0}})  # <5 pontos não conta p/ s2
    assert r["s2"] and not r["s1"] and r["desfecho"] == "s2"


def test_desfecho_s3_quebra_geral():
    r = avalia_desfecho({"a": {"n": 6, "taxa": 0.5}, "b": {"n": 6, "taxa": 0.6}})
    assert r["s3"] and not r["s1"] and r["desfecho"] == "s3"


def test_desfecho_indeterminado():
    r = avalia_desfecho({"a": {"n": 3, "taxa": 0.5}})
    assert r == {"s1": False, "s2": False, "s3": False, "desfecho": "indeterminado"}


def test_gate_f4f5():
    assert gate_f4f5(0.25) and gate_f4f5(0.20)
    assert not gate_f4f5(0.19)
