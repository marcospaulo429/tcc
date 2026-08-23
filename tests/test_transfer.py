"""Testes do credit/transfer.py (A→B) com dados 100% sintéticos."""
import json

import numpy as np
import pytest

from credit.transfer import run_transfer

SEED = 20260821
N_TASKS = 5
ROWS_PER_TASK = 30  # >= 25 pontos por quantity, >= 3 tasks


def _row(task_id, quantity, turn, ctx, value):
    return {
        "quantity": quantity,
        "config_tag": "g600",
        "threshold": 600,
        "task_id": task_id,
        "stratum": "V1",
        "value": value,
        "saturated": False,
        "excluded_timeout": False,
        "noise_floor": 0.0,
        "features_pre": {
            "turn": turn,
            "context_tokens_before": ctx,
            "n_messages_before": 2 + turn,
            "decision_point": "context_policy" if quantity == "I" else "tool_call",
            "action_type": "write_file",
            "tests_passed_so_far": min(turn, 3),
            "tests_total_so_far": 8,
            "n_writes_so_far": turn,
            "frac_turns_elapsed": turn / 12,
        },
        "features_post": {},
    }


def _synthetic_rows(prefix, seed, n_tasks=N_TASKS, rows_per_task=ROWS_PER_TASK):
    """Mesmo processo gerador nos dois ambientes: y monotônico em
    context_tokens_before quando turn <= 2, zero caso contrário."""
    rng = np.random.default_rng(seed)
    rows = []
    for quantity in ("C_M", "I"):
        for t in range(n_tasks):
            task = f"{prefix}_task_{t}"
            for _ in range(rows_per_task):
                turn = int(rng.integers(0, 6))
                ctx = float(rng.uniform(200, 2000))
                value = 0.0 if turn > 2 else 0.5 * ctx / 1000 + rng.normal(0, 0.02)
                rows.append(_row(task, quantity, turn, ctx, value))
    return rows


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("transfer")
    train, test, out = tmp / "a.jsonl", tmp / "b.jsonl", tmp / "report.json"
    _write_jsonl(train, _synthetic_rows("a", seed=1))
    _write_jsonl(test, _synthetic_rows("b", seed=2))
    return run_transfer(train, test, out, seed=SEED, n_boot=20, n_perms=30), out


def test_end_to_end_report_keys(report):
    rep, out = report
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == rep
    assert rep["seed"] == SEED
    # C_H ausente dos dois datasets → insufficient_data
    assert "insufficient_data" in rep["quantities"]["C_H"]
    for q in ("C_M", "I"):
        res = rep["quantities"][q]
        assert res["n_train"] == N_TASKS * ROWS_PER_TASK
        assert res["n_test"] == N_TASKS * ROWS_PER_TASK
        assert res["n_tasks_test"] == N_TASKS
        assert set(res["models"]) == {"linear", "gbm"}
        for m in res["models"].values():
            assert {"pearson", "spearman_pooled", "spearman_clustered", "auroc",
                    "precision_at_10", "mae"} <= set(m["metrics"])
            assert set(m["metrics"]) <= set(m["ci95"])
            assert m["permutation_null"]["n_perms"] == 30
        assert "prediction" in res["baseline_constant"]
        assert "mae" in res["baseline_constant"]


def test_planted_signal_transfers(report):
    rep, _ = report
    for q in ("C_M", "I"):
        m = rep["quantities"][q]["models"]["gbm"]
        assert m["metrics"]["spearman_pooled"] > 0.5
        assert m["metrics"]["spearman_clustered"] > 0.5
        assert m["metrics"]["auroc"] > 0.7
        assert m["permutation_null"]["p_value"] < 0.05


def test_bootstrap_ci_ordering(report):
    rep, _ = report
    for ci in rep["quantities"]["C_M"]["models"]["linear"]["ci95"].values():
        if ci["med"] is not None:
            assert ci["lo"] <= ci["med"] <= ci["hi"]


def test_insufficient_data_small_b(tmp_path):
    train, test, out = tmp_path / "a.jsonl", tmp_path / "b.jsonl", tmp_path / "r.json"
    _write_jsonl(train, _synthetic_rows("a", seed=1))
    # B: só 2 tasks e 10 pontos por quantity → guarda dispara
    _write_jsonl(test, _synthetic_rows("b", seed=2, n_tasks=2, rows_per_task=5))
    rep = run_transfer(train, test, out, seed=SEED, n_boot=5, n_perms=5)
    for q in ("C_M", "I"):
        assert "insufficient_data" in rep["quantities"][q]
        assert rep["quantities"][q]["insufficient_data"].startswith("test:")


def test_strata_merge_labels_mbpp():
    from credit.dataset import STRATA
    from environment.tasks_all import TASKS as TASKS_A
    from environment.tasks_mbpp import TASKS as TASKS_MBPP

    assert STRATA[TASKS_MBPP[0]["task_id"]] == "MBPP"
    for t in TASKS_A:  # ambiente A preservado
        assert STRATA[t["task_id"]] != "MBPP"
