"""Testes do credit/critic.py com dados 100% sintéticos (nunca lê runs/ reais)."""
import json

import numpy as np
import pytest

from credit.critic import evaluate, evaluate_baselines, prepare, run_report

SEED = 20260821
N_TASKS = 8
ROWS_PER_TASK = 25  # 8 * 25 = 200 linhas


def _row(task_id, quantity, turn, ctx, value, *, saturated=False,
         excluded_timeout=False, action="write_file", none_feat=False):
    feats = {
        "turn": turn,
        "context_tokens_before": ctx,
        "n_messages_before": 2 + turn,
        "decision_point": "context_policy" if quantity == "I" else "tool_call",
        "action_type": action,
        "tests_passed_so_far": min(turn, 3),
        "tests_total_so_far": 8,
        "n_writes_so_far": turn,
        "frac_turns_elapsed": turn / 12,
    }
    if none_feat:
        feats["context_tokens_before"] = None
    return {
        "quantity": quantity,
        "config_tag": "g600",
        "threshold": 600,
        "task_id": task_id,
        "stratum": "V1",
        "value": value,
        "saturated": saturated,
        "excluded_timeout": excluded_timeout,
        "noise_floor": 0.0,
        "features_pre": feats,
        "features_post": {},
    }


def _synthetic_rows(quantity="C_H", seed=SEED):
    """y = 0 se turn > 2, senão 0.5 * context_tokens / 1000 + ruído."""
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(N_TASKS):
        task = f"task_{t}"
        for _ in range(ROWS_PER_TASK):
            turn = int(rng.integers(0, 6))
            ctx = float(rng.uniform(200, 2000))
            value = 0.0 if turn > 2 else 0.5 * ctx / 1000 + rng.normal(0, 0.02)
            rows.append(_row(task, quantity, turn, ctx, value))
    return rows


@pytest.fixture(scope="module")
def xy():
    return prepare(_synthetic_rows(), "C_H")


def test_prepare_filters_and_shapes():
    rows = _synthetic_rows()
    rows.append(_row("task_0", "C_H", 1, 500, 0.3, excluded_timeout=True))
    rows.append(_row("task_0", "C_H", 1, 500, 0.3, none_feat=True))
    rows.append(_row("task_0", "C_M", 1, 500, 0.3))  # outra quantity
    xy = prepare(rows, "C_H")
    assert len(xy.y) == N_TASKS * ROWS_PER_TASK
    assert xy.X.shape[0] == len(xy.y) == len(xy.groups) == len(xy.meta)
    assert "threshold" in xy.feature_names  # config sempre covariável
    assert any(n.startswith("decision_point=") for n in xy.feature_names)
    assert any(n.startswith("action_type=") for n in xy.feature_names)


def test_prepare_drops_saturated_only_for_I():
    rows = [_row(f"task_{i}", "I", i % 3, 500 + i, 0.1, saturated=(i % 2 == 0))
            for i in range(10)]
    assert len(prepare(rows, "I").y) == 5
    rows_c = [_row(f"task_{i}", "C_H", i % 3, 500 + i, 0.1,
                   saturated=(i % 2 == 0)) for i in range(10)]
    assert len(prepare(rows_c, "C_H").y) == 10


def test_group_split_no_task_leakage(xy):
    res = evaluate(xy, "linear", seed=SEED, n_boot=10)
    assert res["folds"]
    for fold in res["folds"]:
        assert not set(fold["train_tasks"]) & set(fold["test_tasks"])


def test_zero_inflation_two_stages(xy):
    res = evaluate(xy, "linear", seed=SEED, n_boot=10)
    m = res["metrics"]
    assert m["auroc"] is not None  # estágio classificador
    assert m["mae_nonzero"] is not None  # estágio regressor condicional
    assert 0 <= m["precision_at_10"] <= 1


def test_linear_beats_random(xy):
    res = evaluate(xy, "linear", seed=SEED, n_boot=10)
    base = evaluate_baselines(xy, seed=SEED, n_boot=10)
    rand = base["random"]["metrics"]
    assert res["metrics"]["auroc"] > rand["auroc"]
    assert res["metrics"]["precision_at_10"] > rand["precision_at_10"]


def test_baselines_present(xy):
    base = evaluate_baselines(xy, seed=SEED, n_boot=10)
    assert set(base) == {"position", "context_size", "random"}
    for b in base.values():
        assert "metrics" in b and "ci95" in b


def test_bootstrap_ci_ordering(xy):
    res = evaluate(xy, "linear", seed=SEED, n_boot=50)
    for name, ci in res["ci95"].items():
        if ci["med"] is None:
            continue
        assert ci["lo"] <= ci["med"] <= ci["hi"], name


def test_deterministic_given_seed(xy):
    a = evaluate(xy, "linear", seed=SEED, n_boot=20)
    b = evaluate(xy, "linear", seed=SEED, n_boot=20)
    assert a == b


def test_gbm_runs(xy):
    res = evaluate(xy, "gbm", seed=SEED, n_boot=5)
    assert res["metrics"]["auroc"] > 0.5


def test_skipped_few_points():
    rows = [_row(f"task_{i % 4}", "C_H", 1, 500 + i, 0.1) for i in range(10)]
    xy = prepare(rows, "C_H")
    res = evaluate(xy, "linear", seed=SEED)
    assert "skipped" in res
    assert evaluate_baselines(xy, seed=SEED)["skipped"]


def test_skipped_few_tasks():
    rows = [_row("task_0" if i % 2 else "task_1", "C_H", 1, 500 + i, 0.1)
            for i in range(30)]
    res = evaluate(prepare(rows, "C_H"), "linear", seed=SEED)
    assert "skipped" in res


def test_run_report(tmp_path):
    rows = _synthetic_rows("C_H")
    # C_M com só 10 pontos → skipped; I ausente → skipped
    rows += [_row(f"task_{i % 4}", "C_M", 1, 500 + i, 0.1) for i in range(10)]
    ds = tmp_path / "dataset.jsonl"
    with ds.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    out = tmp_path / "report.json"
    report = run_report(ds, out, seed=SEED)
    assert out.exists()
    q = report["quantities"]
    assert "skipped" in q["C_M"]
    assert "skipped" in q["I"]
    assert q["C_H"]["linear"]["metrics"]["auroc"] > 0.5
    assert q["C_H"]["gbm"]["n"] == N_TASKS * ROWS_PER_TASK
    assert "random" in q["C_H"]["baselines"]
    # gravado em disco == retornado
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(
        json.dumps(report))
