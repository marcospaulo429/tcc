"""Testes do pré-registro 41 (fixtures sintéticas, sem trajetórias reais)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import preg41
from experiments.preg41 import (consistencia, desfecho_m, diagnostico_arm,
                                mann_whitney, tabela_2x2)


def _v1_row(cfg="g450", task="t1", cp=0, idx=1, C_H=0.0, exact_ha=True,
            C_Ha=0.0, **kw):
    base = {"cfg": cfg, "task_id": task, "trajectory_id": f"traj_{task}",
            "cp_index": cp, "index": idx, "C_Ha": C_Ha, "C_H": C_H,
            "C_M": 0.0, "C_HM": 0.0, "I": 0.0, "I_fact": 0.0,
            "exact_ha": exact_ha, "screened": True, "r_orig": 1.0}
    base.update(kw)
    return base


# -- tabela 2x2 -----------------------------------------------------------------
def test_tabela_2x2_m_e_desfecho():
    rows = [
        _v1_row(task="a", C_H=1.0, exact_ha=True),    # piv_nde0
        _v1_row(task="b", C_H=0.5, exact_ha=True),    # piv_nde0
        _v1_row(task="c", C_H=0.5, exact_ha=True),    # piv_nde0
        _v1_row(task="d", C_H=0.2, exact_ha=False, C_Ha=0.2),  # piv_nde_nao0
        _v1_row(task="e", C_H=0.0, exact_ha=True),    # npiv_nde0
        _v1_row(task="f", C_H=0.0, exact_ha=False, C_Ha=0.1),  # npiv_nde_nao0
    ]
    tab = tabela_2x2(rows, lambda r: (r["task_id"], r["cp_index"]))
    assert tab["piv_nde0"] == 3
    assert tab["piv_nde_nao0"] == 1
    assert tab["npiv_nde0"] == 1
    assert tab["npiv_nde_nao0"] == 1
    assert tab["m"] == 0.75
    assert desfecho_m(tab["m"]) == "m2"
    assert tab["abs_TE_piv_nde0"]["n"] == 3
    assert tab["abs_TE_piv_nde0"]["mediana"] == 0.5
    assert tab["abs_TE_piv_nde0"]["max"] == 1.0
    assert tab["pares_unicos"] == 6
    assert tab["tasks_unicas"] == 6


def test_desfecho_m_faixas():
    assert desfecho_m(0.95) == "m1"
    assert desfecho_m(0.90) == "m1"
    assert desfecho_m(0.60) == "m2"
    assert desfecho_m(0.59) == "m3"
    assert desfecho_m(None) is None


def test_tabela_2x2_vazia():
    tab = tabela_2x2([], lambda r: (r["task_id"], r["cp_index"]))
    assert tab["m"] is None
    assert tab["abs_TE_piv_nde0"]["n"] == 0


# -- consistência de mediação ---------------------------------------------------
def _t6_row(config="g450", regime="slack", task="t1", cp=0, r_orig=1.0,
            C_H=1.0, r_cf_hm=0.0, found=True):
    return {"config": config, "regime": regime, "task_id": task,
            "cp_index": cp, "C_H": C_H, "r_orig": r_orig,
            "r_cf_m": 0.0, "r_cf_hm": r_cf_hm, "C_M": C_H, "C_HM": C_H,
            "found": found, "informative": True}


def test_consistencia_k_e_desfecho():
    rows = [
        _t6_row(task="a", C_H=1.0, r_cf_hm=0.0),           # R_H=0 → consistente
        _t6_row(task="b", C_H=0.5, r_cf_hm=0.5),           # R_H=0.5 → consistente
        _t6_row(task="c", C_H=1.0, r_cf_hm=0.3,
                regime="pressure", config="mt6"),          # R_H=0 → discordante
        _t6_row(task="d", found=False),                    # excluída
        _t6_row(task="e", r_cf_hm=None),                   # excluída
    ]
    out = consistencia(rows)
    assert out["total"] == {"n": 3, "n_consistente": 2, "k": round(2 / 3, 4)}
    assert out["desfecho"] == "k2"
    assert out["por_regime"]["slack"]["n"] == 2
    assert out["por_regime"]["pressure"]["k"] == 0.0
    assert len(out["discordancias"]) == 1
    d = out["discordancias"][0]
    assert d["task_id"] == "c" and d["config"] == "mt6"
    assert d["R_H"] == 0.0 and d["delta"] == 0.3


def test_consistencia_desfechos_extremos():
    ok = [_t6_row(task=str(i)) for i in range(4)]
    assert consistencia(ok)["desfecho"] == "k1"
    ruim = [_t6_row(task=str(i), r_cf_hm=0.7) for i in range(4)]
    assert consistencia(ruim)["desfecho"] == "k3"


# -- Mann-Whitney ---------------------------------------------------------------
def test_mann_whitney_trivial():
    out = mann_whitney([10, 11, 12, 13, 14], [1, 2, 3, 4, 5])
    assert out["U"] == 25.0
    assert out["p"] is not None and out["p"] < 0.05


def test_mann_whitney_vazio():
    assert mann_whitney([], [1, 2]) == {"U": None, "p": None}


def test_mann_whitney_aprox_normal_coerente():
    # força o caminho manual comparando com a direção esperada
    x, y = [5, 6, 7, 8, 9, 10], [1, 2, 3, 4, 5, 6]
    out = mann_whitney(x, y)
    assert out["p"] < 0.5  # x tende a ser maior


# -- diagnóstico C1 ---------------------------------------------------------------
def _log_row(idx, credits, grad_norm=0.01, R_eff=0.1):
    return {"episode_idx": idx, "R": 0.0, "R_eff": R_eff, "calls_cum": 10,
            "grad_norm": grad_norm, "credits": credits, "arm": "ch"}


def test_diagnostico_arm_zero_e_nao_zero():
    rows = [
        _log_row(0, [{"credit": 0.0, "index": 1, "llm_calls": 2, "arm": "ch"},
                     {"credit": 0.5, "index": 3, "llm_calls": 4, "arm": "ch"}]),
        _log_row(1, [{"credit": 0.0, "index": 2, "llm_calls": 2, "arm": "ch"}],
                 grad_norm=0.0),
        _log_row(2, []),
    ]
    out = diagnostico_arm(rows)
    assert out["n_episodios"] == 3
    assert out["creditos_por_episodio"] == 1.0
    assert out["frac_creditos_zero"] == round(2 / 3, 4)
    assert out["abs_credit"]["max"] == 0.5
    assert out["llm_calls_por_credito"] == round(8 / 3, 4)
    assert out["frac_episodios_sem_credito_nao_nulo"] == round(2 / 3, 4)
    assert out["grad_norm"]["frac_zero"] == round(1 / 3, 4)


def test_diagnostico_arm_sem_creditos():
    out = diagnostico_arm([_log_row(0, []), _log_row(1, [])])
    assert out["frac_creditos_zero"] is None
    assert out["abs_credit"]["mediana"] is None
    assert out["frac_episodios_sem_credito_nao_nulo"] == 1.0


# -- integração main() com mini runs/ --------------------------------------------
def _fake_traj(traj_id, indices_tool_call):
    decs = [SimpleNamespace(index=i, decision_point="tool_call",
                            chosen_action={"action": "run_tests"})
            for i in indices_tool_call]
    return SimpleNamespace(trajectory_id=traj_id, final_reward=1.0,
                           decisions=decs)


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_main_integracao(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_jsonl(tmp_path / "runs/preg40/v1_rows.jsonl", [
        _v1_row(cfg="g450", task="a", C_H=1.0, exact_ha=True),
        _v1_row(cfg="g600", task="b", C_H=0.0, exact_ha=True),
        _v1_row(cfg="mt6", task="c", C_H=0.5, exact_ha=False, C_Ha=0.5),
    ])
    _write_jsonl(tmp_path / "runs/preg40/v2_rows.jsonl", [
        {"cfg": "v2_folga", "task_id": "sa", "index": 2, "j": 3,
         "tipo": "termination", "C_Ha": 0.0, "C_H": 0.2, "C_M": 0.0,
         "C_HM": 0.2, "I": 0.0, "I_fact": 0.2, "exact_ha": True,
         "hm_analitico": False, "error": None},
        {"cfg": "v2_folga", "task_id": "sb", "index": 1, "j": 2,
         "tipo": "retry", "C_Ha": None, "C_H": 0.1, "C_M": 0.0,
         "C_HM": 0.1, "I": 0.0, "I_fact": None, "exact_ha": None,
         "hm_analitico": False, "error": "context_overflow"},  # excluída
    ])
    _write_jsonl(tmp_path / "runs/teste6_estimando/g450/results.jsonl", [
        _t6_row(task="a", C_H=1.0, r_cf_hm=0.0),
        _t6_row(task="b", C_H=1.0, r_cf_hm=0.5),
    ])
    _write_jsonl(tmp_path / "runs/c1d_ch_s1/train_log.jsonl", [
        _log_row(0, [{"credit": 0.3, "index": 1, "llm_calls": 2, "arm": "ch"}]),
    ])
    _write_jsonl(tmp_path / "runs/teste3_g450/cf_results.jsonl", [
        {"task_id": "a", "cp_index": 0, "index": 1, "C_H": 1.0},
        {"task_id": "a", "cp_index": 0, "index": 1, "C_H": 0.0},
    ])
    trajs_v1 = {f"traj_{t}": _fake_traj(f"traj_{t}", [1, 3, 5])
                for t in ("a", "b", "c")}
    monkeypatch.setattr(preg41, "_trajs_v1", lambda cfg: trajs_v1)
    monkeypatch.setattr(preg41, "_trajs_v2_base",
                        lambda: {("v2_folga", "sa"): _fake_traj("sa", [3, 4, 5])})
    report = preg41.main()

    assert (tmp_path / "runs/preg41/report.json").exists()
    assert report["meta"]["pre_registro"] == 41
    tab = report["tabela_2x2"]
    assert tab["v1_folga"]["piv_nde0"] == 1
    assert tab["v1_folga"]["m"] == 1.0
    assert tab["v1_folga"]["desfecho"] == "m1"
    assert tab["v1_pressao"]["piv_nde_nao0"] == 1
    assert tab["v2_total"]["piv_nde0"] == 1  # linha com error excluída
    assert "termination" in tab["v2_por_tipo"]
    assert report["consistencia_mediacao"]["total"]["n"] == 2
    assert report["consistencia_mediacao"]["desfecho"] == "k2"
    hz = report["horizonte"]
    assert hz["v1_folga"]["n_nde0"] == 2  # tool_calls com index > 1 → H=2
    assert hz["v1_folga"]["H_nde0"]["mediana"] == 2
    assert hz["v2_total"]["n_nde0"] == 1
    assert hz["v2_total"]["H_nde0"]["mediana"] == 2  # índices 4,5 > j=3
    assert hz["anatomia_v1_quebras"][0]["task_id"] == "c"
    fat = report["v2_fatorial_por_tipo"]
    assert fat["total"]["n"] == 1
    assert fat["total"]["frac_nde_zero"] == 1.0
    diag = report["diagnostico_preg31"]
    assert diag["agregado"]["ch"]["n_episodios"] == 1
    assert diag["agregado"]["ch"]["n_cp_points_por_episodio"] is None
    ne = report["n_efetivo"]
    assert ne["g450"] == {"n_pontos": 2, "pares_unicos": 1,
                          "tasks_unicas": 1, "n_pivotais": 1}
