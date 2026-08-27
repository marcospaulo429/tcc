"""Pipeline do pré-reg 39 — ramo positivo do gate (Qwen3-8B, pool it.4 congelado).

Estágios (sequenciais, idempotentes por report):
- gate1:  analítico, 0 GPU — margem por atrator no nível do sinal de treino
          (mean R_eff(λ)) sobre artefatos congelados de runs/v2_land35_8b;
          escolhe λ*, escreve gate1_report.json e pool39.json (split registrado).
- base/nulos/piso/screening/census/census_esc: census de screening da célula
          (8B, HarnessV2 default 4500/25/6, 24 tasks swe35) — reuso do
          census_v2 (pré-reg 29) com OUT redirecionado, base própria (swe35)
          e piso do 38 (gate de instrumento >=0.95 exatos).
- gate2:  decisão do census — contabilidade PRIMÁRIA registrada
          (medidos_sem_duais >= 0.20) + piso ok + N válido >= 12 tasks.
- dual:   contabilidade episode-matched (protocolo do pré-reg 31): braço
          outcome re-avaliado no held-out com θ fatiado nos nº de episódios
          dos braços ch/chm_cm por seed; fidelity gate = re-eval exata do
          θ final.
- final:  agrega tudo → final_report.json com desfecho d1/d2/d3 declarado.

Uso: uv run python -m experiments.preg39 --stage <s>
"""
import argparse
import importlib
import json
import os
import statistics
from pathlib import Path

OUT = Path("runs/preg39")
CENSUS_OUT = "runs/preg39/census"
os.environ.setdefault("TCC_XFAM_OUT", CENSUS_OUT)

import experiments.census_v2 as cv            # noqa: E402
import experiments.census_v2_xfam as xf       # noqa: E402
from experiments.common import append_row, done_keys, load_rows  # noqa: E402

FROZEN = Path("runs/v2_land35_8b")
POOL_ALL = Path("runs/v2_land35d/all24.json")
LAMBDA_GRID = (0.1, 0.2, 0.5, 1.0, 2.0)
MARGEM_MIN = 0.10
SENSIBILIDADE = (0.15, 0.08)
N_VALIDO_MIN = 12          # risco (i) do pré-reg: census com N < 12 → x0
MECH = ("f_swe35_02", "f_swe35_05", "f_swe35_07", "f_swe35_11")
EASY = ("f_swe35_00",)
SEEDS = (1, 2, 3)
ARMS = ("outcome", "ch", "chm_cm", "zero")


def _reff(t: dict, lam: float) -> float:
    return t["R"] - lam * t["prompt_tokens_total"] / 100000.0


def _mean_reff(per_task: list[dict], lam: float, ids: set | None = None) -> float:
    sel = [t for t in per_task if ids is None or t["task_id"] in ids]
    return sum(_reff(t, lam) for t in sel) / len(sel)


def _frozen_per_task() -> dict:
    cal = json.loads((FROZEN / "calibrate_report.json").read_text())
    ora = json.loads((FROZEN / "oraculo_report.json").read_text())
    pt = {name: p["per_task"] for name, p in cal["policies"].items()}
    pt["oraculo"] = ora["per_task"]
    return pt


def _split() -> tuple[list[str], list[str]]:
    """Regra registrada: estratos, ordenar por task_id, pares→treino."""
    todos = sorted(json.loads(POOL_ALL.read_text())["train"])
    f_hard = [t for t in todos if t.startswith("f_") and t not in MECH + EASY]
    p_tasks = [t for t in todos if t.startswith("p_")]
    train, heldout = [], []
    for estrato in (sorted(MECH), list(EASY), f_hard, p_tasks):
        for i, tid in enumerate(estrato):
            (train if i % 2 == 0 else heldout).append(tid)
    return train, heldout


def stage_gate1():
    pt = _frozen_per_task()
    atratores = ("keep_always", "summarize_always", "default")
    por_lambda = {}
    for lam in LAMBDA_GRID:
        m_ora = _mean_reff(pt["oraculo"], lam)
        margens = {a: round(m_ora - _mean_reff(pt[a], lam), 4) for a in atratores}
        por_lambda[str(lam)] = {"mean_reff_oraculo": round(m_ora, 4),
                                "margens": margens,
                                "min_margem": round(min(margens.values()), 4)}
    lam_star = max(LAMBDA_GRID,
                   key=lambda l: (por_lambda[str(l)]["min_margem"], -l))
    min_m = por_lambda[str(lam_star)]["min_margem"]
    abre = min_m >= MARGEM_MIN
    train, heldout = _split()
    report = {"pre_registro": 39, "grade_lambda": list(LAMBDA_GRID),
              "por_lambda": por_lambda, "lambda_star": lam_star,
              "min_margem_em_lambda_star": min_m,
              "criterio": MARGEM_MIN, "gate1_abre": abre,
              "desfecho": None if abre else "g0",
              "sensibilidade": {str(s): min_m >= s for s in SENSIBILIDADE},
              "split": {"train": train, "heldout": heldout,
                        "n_train": len(train), "n_heldout": len(heldout)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gate1_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    if abre:
        (OUT / "pool39.json").write_text(
            json.dumps({"train": train, "heldout": heldout,
                        "lambda_star": lam_star}))
    print(json.dumps({k: report[k] for k in
                      ("lambda_star", "min_margem_em_lambda_star", "gate1_abre",
                       "sensibilidade")}, indent=2, ensure_ascii=False))


def stage_base():
    """Base do census: 24 tasks swe35, HarnessV2 default (4500/25/6), cfg única."""
    from environment.tasks_swe35 import TASKS
    rows_path = xf.OUT / "base_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id"))
    for task in TASKS:
        if ("v2_default", task["task_id"]) in feitos:
            continue
        print(f"[base] v2_default {task['task_id']}", flush=True)
        try:
            r = cv._episodio(task, {})
            append_row(rows_path, {"cfg": "v2_default", "task_id": task["task_id"],
                                   **r, "error": None})
        except Exception as exc:  # overflow etc. — excluído do census, reportado
            append_row(rows_path, {"cfg": "v2_default", "task_id": task["task_id"],
                                   "reward": 0.0, "success": False,
                                   "trajectory_path": None,
                                   "error": f"{type(exc).__name__}: {exc}"})
    rows = load_rows(rows_path)
    ok = [r for r in rows if not r["error"]]
    report = {"n": len(rows), "n_validas": len(ok),
              "erros": {r["task_id"]: r["error"] for r in rows if r["error"]},
              "taxa_sucesso": round(sum(1 for r in rows if r.get("reward") == 1.0)
                                    / len(rows), 3) if rows else None,
              "mediana_wall_s": round(statistics.median(
                  r.get("wall_time_s", 0.0) for r in ok), 1) if ok else None}
    (xf.OUT / "base_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


def stage_gate2():
    census_rep = cv._report_census(cv._rows_census_mescladas())
    piso = json.loads((xf.OUT / "piso_report.json").read_text())
    base = json.loads((xf.OUT / "base_report.json").read_text())
    n_validas = base["n_validas"]
    prim = census_rep["gate_por_contabilidade"]["medidos_sem_duais"]
    instrumento_ok = bool(piso["gate_ok"]) and n_validas >= N_VALIDO_MIN
    abre = instrumento_ok and bool(prim["gate_abre"])
    desfecho = None
    if not instrumento_ok:
        desfecho = "x0"
    elif not abre:
        desfecho = "c0"
    report = {"pre_registro": 39, "n_tasks_validas": n_validas,
              "piso_taxa_exatos": piso["taxa_exatos"], "piso_ok": piso["gate_ok"],
              "contabilidade_primaria": prim,
              "outras_contabilidades": {k: v for k, v in
                                        census_rep["gate_por_contabilidade"].items()
                                        if k != "medidos_sem_duais"},
              "por_tipo": {t: {"n": v["n_census"], "taxa": v["taxa_screening_exato"]}
                           for t, v in census_rep["por_tipo"].items()},
              "gate2_abre": abre, "desfecho": desfecho,
              "prossegue_treino": abre}
    (OUT / "gate2_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


# -- contabilidade dual (protocolo do pré-reg 31) ------------------------------
def _theta_no_corte(log_path: Path, n_episodios: int) -> tuple[list[float], int]:
    thetas = [json.loads(l) for l in log_path.read_text().splitlines()]
    n = min(n_episodios, len(thetas))
    return thetas[n - 1]["theta"], n


def stage_dual():
    from agent.llm import LLMClient
    from rl.policy_v2 import CENTER_V2
    from rl.train_c1 import CountingLLM
    from rl.train_v2 import evaluate
    pool = json.loads((OUT / "pool39.json").read_text())
    lam = pool["lambda_star"]
    by_id = {t["task_id"]: t for t in
             importlib.import_module("environment.tasks_swe35").TASKS}
    heldout = [by_id[tid] for tid in pool["heldout"]]
    hkw = {"summarize_threshold_tokens": 4500, "max_turns": 25, "keep_last": 6}
    llm = CountingLLM(LLMClient())
    rows_path = OUT / "dual_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("seed", "slice"))
    for seed in SEEDS:
        summ_out = json.loads((OUT / f"train/outcome_s{seed}/summary.json").read_text())
        log = OUT / f"train/outcome_s{seed}/train_log.jsonl"
        # fidelity gate: re-eval exata do θ final (greedy determinístico)
        alvos = {"fidelity_final": (summ_out["theta"], summ_out["episodes"])}
        for arm in ("ch", "chm_cm"):
            n_ep = json.loads(
                (OUT / f"train/{arm}_s{seed}/summary.json").read_text())["episodes"]
            theta, n_real = _theta_no_corte(log, n_ep)
            alvos[f"corte_{arm}"] = (theta, n_real)
        for nome, (theta, n_ep) in alvos.items():
            if (seed, nome) in feitos:
                continue
            print(f"[dual] seed {seed} {nome} (n_ep={n_ep})", flush=True)
            ev = evaluate(heldout, llm, theta, seed, OUT / "dual",
                          lambda_cost=lam, center=CENTER_V2, harness_kw=hkw)
            row = {"seed": seed, "slice": nome, "n_episodios": n_ep,
                   "theta": theta, "mean_R": ev["mean_R"],
                   "mean_R_eff": ev["mean_R_eff"]}
            if nome == "fidelity_final":
                row["fidelity_ok"] = (
                    abs(ev["mean_R_eff"] - summ_out["heldout"]["mean_R_eff"]) < 1e-9)
            append_row(rows_path, row)
    rows = load_rows(rows_path)
    report = {"rows": rows,
              "fidelity_ok": all(r.get("fidelity_ok", True) for r in rows
                                 if r["slice"] == "fidelity_final")}
    (OUT / "dual_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report["rows"], indent=2))


def stage_final():
    gate1 = json.loads((OUT / "gate1_report.json").read_text())
    gate2 = json.loads((OUT / "gate2_report.json").read_text())
    pool = json.loads((OUT / "pool39.json").read_text())
    lam = pool["lambda_star"]
    held_ids = set(pool["heldout"])
    # referências held-out: subset analítico dos artefatos congelados em λ*
    pt = _frozen_per_task()
    refs = {name: round(_mean_reff(per, lam, held_ids), 4)
            for name, per in pt.items()}
    max_atrator = max(v for k, v in refs.items() if k != "oraculo")
    celulas = {}
    for arm in ARMS:
        for seed in SEEDS:
            s = json.loads((OUT / f"train/{arm}_s{seed}/summary.json").read_text())
            celulas[f"{arm}_s{seed}"] = {
                "episodes": s["episodes"], "llm_calls_total": s["llm_calls_total"],
                "stopped_by": s["stopped_by"], "theta": s["theta"],
                "heldout_mean_R": s["heldout"]["mean_R"],
                "heldout_mean_R_eff": s["heldout"]["mean_R_eff"]}
    dual = {(r["seed"], r["slice"]): r
            for r in load_rows(OUT / "dual_rows.jsonl")}
    # comparações por seed (primário: held-out mean R_eff)
    por_seed = {}
    for seed in SEEDS:
        o = celulas[f"outcome_s{seed}"]["heldout_mean_R_eff"]
        cred = {a: celulas[f"{a}_s{seed}"]["heldout_mean_R_eff"]
                for a in ("ch", "chm_cm")}
        por_seed[seed] = {
            "outcome": o, **cred,
            "zero": celulas[f"zero_s{seed}"]["heldout_mean_R_eff"],
            "chm_cm_gt_outcome_dose": cred["chm_cm"] > o,
            "chm_cm_gt_outcome_epis": cred["chm_cm"] >
                dual[(seed, "corte_chm_cm")]["mean_R_eff"],
            "chm_cm_gt_max_atrator": cred["chm_cm"] > max_atrator,
            "ch_gt_outcome_dose": cred["ch"] > o,
            "ch_gt_outcome_epis": cred["ch"] > dual[(seed, "corte_ch")]["mean_R_eff"],
            "ch_gt_max_atrator": cred["ch"] > max_atrator,
            "outcome_gt_max_atrator": o > max_atrator,
            "chm_cm_ge_ch": cred["chm_cm"] >= cred["ch"]}
    n = len(SEEDS)
    win_dose = sum(por_seed[s]["chm_cm_gt_outcome_dose"] for s in SEEDS)
    win_epis = sum(por_seed[s]["chm_cm_gt_outcome_epis"] for s in SEEDS)
    escapa_chm = sum(por_seed[s]["chm_cm_gt_max_atrator"] for s in SEEDS)
    escapa_algum = sum(
        any(por_seed[s][f"{a}_gt_max_atrator"] for a in ("outcome", "ch", "chm_cm"))
        for s in SEEDS)
    if win_dose >= 2 and win_epis >= 2 and escapa_chm >= 2:
        desfecho = "d1"
    elif escapa_algum >= 2 and (n - win_dose >= 2 or n - win_epis >= 2):
        desfecho = "d2"
    elif escapa_algum < 2:
        desfecho = "d3"
    else:
        desfecho = "indeterminado_reportar_como_d2_parcial"
    report = {"pre_registro": 39, "lambda_star": lam,
              "gate1": {k: gate1[k] for k in ("gate1_abre",
                                              "min_margem_em_lambda_star")},
              "gate2": {k: gate2[k] for k in ("gate2_abre", "piso_taxa_exatos",
                                              "contabilidade_primaria")},
              "referencias_heldout": {**refs, "max_atrator_fixo": max_atrator},
              "celulas": celulas, "por_seed": por_seed,
              "dual": [r for r in load_rows(OUT / "dual_rows.jsonl")],
              "contagens": {"chm_cm_gt_outcome_dose": win_dose,
                            "chm_cm_gt_outcome_epis": win_epis,
                            "chm_cm_escapa": escapa_chm,
                            "algum_braco_escapa": escapa_algum},
              "desfecho": desfecho}
    (OUT / "final_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"desfecho": desfecho, "por_seed": por_seed,
                      "referencias_heldout": report["referencias_heldout"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["gate1", "base", "nulos", "piso", "screening",
                             "census", "census_esc", "gate2", "dual", "final"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    Path(CENSUS_OUT).mkdir(parents=True, exist_ok=True)
    {"gate1": stage_gate1, "base": stage_base, "nulos": cv.stage_nulos,
     "piso": xf.stage_piso, "screening": cv.stage_screening,
     "census": cv.stage_census, "census_esc": cv.stage_census_esc,
     "gate2": stage_gate2, "dual": stage_dual, "final": stage_final}[args.stage]()
