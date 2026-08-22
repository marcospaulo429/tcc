"""Amostrador de a′ (interventions.model) e elegibilidade dos Testes 2/3 — sem vLLM."""
import json

from experiments.teste2 import eligible_points
from experiments.teste3 import eligible_pairs
from interventions.model import sample_alternative
from trajectories.schema import Decision, Trajectory


class SeqLLM:
    """Devolve respostas roteirizadas em ordem, registrando os kwargs de cada chamada."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def chat(self, messages, *, temperature=None, seed=None, max_tokens=None):
        self.calls.append({"temperature": temperature, "seed": seed,
                           "max_tokens": max_tokens})
        out = self.outputs.pop(0)
        return {"text": out["text"], "finish_reason": out.get("finish_reason", "stop"),
                "prompt_tokens": 1, "completion_tokens": 1, "wall_time_s": 0.0}


ORIG = {"action": "run_tests"}


def test_sample_accepts_first_different_action():
    llm = SeqLLM([{"text": '{"action": "finish"}'}])
    r = sample_alternative(llm, [], ORIG)
    assert r["found"] is True
    assert r["action"] == {"action": "finish"}
    assert r["seed"] == 2001 and r["n_tried"] == 1
    assert llm.calls[0] == {"temperature": 0.8, "seed": 2001, "max_tokens": 1200}


def test_sample_rejects_same_canonical_and_invalid():
    # 1ª: mesmo canônico com texto diferente; 2ª: inválida (truncada); 3ª: diferente
    llm = SeqLLM([
        {"text": ' { "action" : "run_tests" } '},
        {"text": '{"action": "write_file", "path": "x.py"', "finish_reason": "length"},
        {"text": '{"action": "finish"}'},
    ])
    r = sample_alternative(llm, [], ORIG)
    assert r["found"] is True and r["seed"] == 2003 and r["n_tried"] == 3
    a0, a1, a2 = r["attempts"]
    assert a0 == {"seed": 2001, "finish_reason": "stop", "valid": True, "differs": False}
    assert a1 == {"seed": 2002, "finish_reason": "length", "valid": False, "differs": False}
    assert a2 == {"seed": 2003, "finish_reason": "stop", "valid": True, "differs": True}


def test_sample_not_found_after_exhausting_seeds():
    llm = SeqLLM([{"text": json.dumps(ORIG)}] * 8)
    r = sample_alternative(llm, [], ORIG)
    assert r["found"] is False and r["action"] is None and r["seed"] is None
    assert r["n_tried"] == 8 and len(r["attempts"]) == 8
    assert [a["seed"] for a in r["attempts"]] == list(range(2001, 2009))


def _dec(i, point, turn, chosen, messages=None):
    dtype = "model" if point == "tool_call" else "harness"
    return Decision(trajectory_id="t", index=i, decision_type=dtype,
                    decision_point=point,
                    state_before={"turn": turn, "messages": messages or [],
                                  "context_tokens": 0},
                    chosen_action=chosen)


def make_traj_with_retry():
    """Turno 0 tem retry (tool_call excluído); turno 1 é limpo."""
    decs = [
        _dec(0, "context_policy", 0, {"action": "keep_context"}),
        _dec(1, "retry", 0, {"action": "retry_once"}),
        _dec(2, "tool_call", 0, {"action": "run_tests", "forced": False}),
        _dec(3, "termination", 0, {"action": "continue"}),
        _dec(4, "context_policy", 1, {"action": "keep_context"}),
        _dec(5, "tool_call", 1, {"action": "run_tests", "forced": False}),
        _dec(6, "termination", 1, {"action": "terminate"}),
    ]
    return Trajectory(task_id="x", config={"harness": {}}, decisions=decs,
                      trajectory_id="t")


def test_teste2_eligibility_excludes_retry_turns():
    traj = make_traj_with_retry()
    points = eligible_points(traj, max_per_traj=10)
    assert [d.index for d in points] == [5]


def test_teste3_eligibility_excludes_retry_turns():
    # mensagens longas o bastante p/ o summarize NÃO ser vácuo nos dois turnos
    msgs = [{"role": "system", "content": "s"},
            {"role": "user", "content": "x" * 500}] + \
           [{"role": "user", "content": f"m{i}" * 50} for i in range(8)]
    traj = make_traj_with_retry()
    for d in traj.decisions:
        d.state_before["messages"] = msgs
    pairs = eligible_pairs(traj, max_per_traj=10)
    assert [(cp.index, tc.index) for cp, tc in pairs] == [(4, 5)]
