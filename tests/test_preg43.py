"""Testes unitários do preg43 (helpers puros, sem I/O)."""
import statistics

from experiments.preg43 import (desfecho, estratos, holm, perm_task_level)


def _p(task, nde0, h, hw, henv, cha=None):
    return {"task_id": task, "cfg": "g600", "cp_index": 0,
            "C_H": 1.0, "C_Ha": 0.0 if nde0 else (cha if cha is not None else 0.5),
            "nde0": nde0, "H": h, "H_w": hw, "H_env": henv}


def test_estratos_basico():
    pontos = [_p("t1", True, 0, 0, 0),   # implicado
              _p("t2", True, 3, 2, 3),   # informativo, nde0
              _p("t3", False, 4, 1, 4)]  # informativo, nde!=0
    e = estratos(pontos)
    assert e["n"] == 3 and e["n_nde0"] == 2
    assert e["frac_Hw0"] == round(1 / 3, 4)
    assert e["frac_nde0_implicado_Hw0"] == 0.5
    assert e["checagem_implicacao"]["taxa_nde0_em_Hw0"] == 1.0
    assert e["checagem_implicacao"]["violacoes"] == []
    assert e["endpoint_Hw_ge1"] == {"k": 1, "n": 2, "taxa": 0.5}
    assert e["sens_H_ge2"]["n"] == 2
    assert e["dist_H_w"] == {"0": 1, "1": 1, "2": 1}


def test_estratos_violacao():
    pontos = [_p("t1", False, 1, 0, 1, cha=0.3)]  # H_w=0 mas NDE != 0
    e = estratos(pontos)
    v = e["checagem_implicacao"]["violacoes"]
    assert len(v) == 1 and v[0]["task_id"] == "t1" and v[0]["C_Ha"] == 0.3


def test_desfecho():
    assert desfecho(0.8) == "h1"
    assert desfecho(0.75) == "h1"
    assert desfecho(0.6) == "h2"
    assert desfecho(0.4) == "h3"
    assert desfecho(None) is None


def test_holm():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": None})
    assert adj["a"] == 0.03          # 3 * 0.01
    assert adj["c"] == 0.06          # max(0.03, 2*0.03)
    assert adj["b"] == 0.06          # monotônico
    assert adj["d"] is None


def test_perm_task_level_degenerado():
    # todas as tasks com mesmo rótulo -> stat indefinida
    pontos = [_p("t1", True, 1, 1, 1), _p("t2", True, 2, 1, 2)]
    r = perm_task_level(pontos, "H")
    assert r["stat_obs"] is None and r["p_perm"] is None


def test_perm_task_level_sinal():
    # tasks NDE!=0 com H alto: p deve ser pequeno; mediana por task
    pontos = ([_p(f"a{i}", True, 0, 0, 0) for i in range(6)]
              + [_p(f"b{i}", False, 10, 5, 10) for i in range(6)])
    r = perm_task_level(pontos, "H")
    assert r["n_tasks"] == 12 and r["n_tasks_nde_nao0"] == 6
    assert r["stat_obs"] == 10.0
    assert r["p_perm"] < 0.01
    # pontos da mesma task movem juntos (cluster): mediana por task
    pontos2 = [_p("t1", True, 0, 0, 0), _p("t1", True, 8, 4, 8),
               _p("t2", False, 6, 3, 6)]
    r2 = perm_task_level(pontos2, "H")
    assert r2["stat_obs"] == 6.0 - statistics.median([0, 8])
