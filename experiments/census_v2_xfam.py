"""Pipeline do pré-reg 38 — census V2 cross-family sob harness congelado.

Reusa os estágios do census_v2 (pré-reg 29) com OUT redirecionado por env
TCC_XFAM_OUT; o modelo vem de TCC_MODEL (cliente). Estágios novos:
- base: só a config v2_folga (60 tasks);
- piso: piso greedy da célula nova (replay com flip NULO no 1º candidato de
  screening por trajetória, sufixo greedy) — gate de validade do instrumento
  (exatos >=0.95) antes de qualquer leitura de screening;
- aprime_s: braço a′_s (pré-reg 30B) sobre os pontos context keep→summarize
  do census novo, seeds 6001–6008;
- relatorio: desfechos declarados X1/X2/X4 + E1/E2 vs. comparador Qwen/v2_folga.

Uso (sequencial): uv run python -m experiments.census_v2_xfam --stage <s>
"""
import argparse
import json
import os
import statistics
from pathlib import Path

import openai

import experiments.census_v2 as cv
from agent.harness import summarize_messages
from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from experiments.common import append_row, done_keys, load_rows
from experiments.v2_controles import _bracos
from interventions.model_v2 import _canonical, sample_alternative_v2
from trajectories.replay import build_flip_queue, replay_from

OUT = Path(os.environ.get("TCC_XFAM_OUT", "runs/v2_xfam_mistral"))
cv.OUT = OUT  # redireciona todos os estágios reutilizados do census_v2

SEEDS_S = tuple(range(6001, 6009))  # 30B
PISO_GATE = 0.95

# Comparador declarado no pré-reg 38 (célula Qwen/v2_folga, pré-regs 29+30B)
COMPARADOR_QWEN = {
    "por_tipo": {"context_policy": {"n": 18, "taxa": 0.5},
                 "observation_policy": {"n": 10, "taxa": 0.6},
                 "test_schedule": {"n": 3, "taxa": 0.3333},
                 "termination": {"n": 7, "taxa": 0.0}},
    "desfecho": "s3", "gate_medidos_sem_duais": 0.50,
    "taxa_screened_s": 0.381, "bucket_s": "b3",
}


# -- base (só v2_folga) --------------------------------------------------------
def stage_base():
    from environment.tasks_swe import TASKS
    rows_path = OUT / "base_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id"))
    for task in TASKS:
        if ("v2_folga", task["task_id"]) in feitos:
            continue
        print(f"[base] v2_folga {task['task_id']}", flush=True)
        try:
            r = cv._episodio(task, {})
            append_row(rows_path, {"cfg": "v2_folga", "task_id": task["task_id"],
                                   **r, "error": None})
        except Exception as exc:  # ex.: 400 por estouro de contexto — reportar
            append_row(rows_path, {"cfg": "v2_folga", "task_id": task["task_id"],
                                   "reward": 0.0, "success": False,
                                   "trajectory_path": None,
                                   "error": f"{type(exc).__name__}: {exc}"})
    rows = load_rows(rows_path)
    ok = [r for r in rows if not r["error"]]
    report = {"n": len(rows), "n_erros": len(rows) - len(ok),
              "erros": {r["task_id"]: r["error"] for r in rows if r["error"]},
              "taxa_sucesso": round(sum(1 for r in rows if r.get("reward") == 1.0)
                                    / len(rows), 3) if rows else None,
              "reward_medio": round(sum(r.get("reward", 0.0) for r in rows)
                                    / len(rows), 3) if rows else None,
              "mediana_wall_s": round(statistics.median(
                  r.get("wall_time_s", 0.0) for r in ok), 1) if ok else None}
    (OUT / "base_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


# -- piso greedy (gate de validade do instrumento) -----------------------------
def stage_piso():
    trajs = cv._trajs_base()
    llm = LLMClient()
    rows_path = OUT / "piso_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id"))
    for (cfg, task_id), traj in sorted(trajs.items()):
        if (cfg, task_id) in feitos:
            continue
        cands = cv._candidatos_traj(traj)
        base = {"cfg": cfg, "task_id": task_id}
        if not cands:
            append_row(rows_path, {**base, "status": "sem_candidato"})
            continue
        tipo, i, _flip = cands[0]
        print(f"[piso] {cfg} {task_id} idx{i} ({tipo}) flip nulo", flush=True)
        null_action = cv._canon(traj.decisions[i].chosen_action)
        try:
            entry, queue = build_flip_queue(traj, i, null_action)
            rep = replay_from(traj, entry, llm, OUT / "piso_trajs",
                              override_actions=queue)
            append_row(rows_path, {**base, "status": "medido", "index": i,
                                   "tipo": tipo,
                                   "reward_original": traj.final_reward,
                                   "reward_replay": rep["reward"],
                                   "exato": rep["reward"] == traj.final_reward})
        except ValueError as exc:  # span com retry — pulado e reportado
            append_row(rows_path, {**base, "status": "pulado", "error": str(exc)})
        except openai.BadRequestError as exc:
            append_row(rows_path, {**base, "status": "erro",
                                   "error": f"context_overflow: {exc}"[:200]})
    rows = load_rows(rows_path)
    med = [r for r in rows if r["status"] == "medido"]
    taxa = round(sum(r["exato"] for r in med) / len(med), 4) if med else None
    report = {"n_rows": len(rows), "n_medidos": len(med),
              "n_exatos": sum(r["exato"] for r in med), "taxa_exatos": taxa,
              "gate_ok": (taxa is not None and taxa >= PISO_GATE),
              "desvios": [r for r in med if not r["exato"]],
              "nao_medidos": {s: sum(1 for r in rows if r["status"] == s)
                              for s in ("sem_candidato", "pulado", "erro")}}
    (OUT / "piso_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


# -- braço a′_s (30B) -----------------------------------------------------------
def stage_aprime_s():
    trajs = cv._trajs_base()
    llm = LLMClient()
    scr = {(r["cfg"], r["task_id"], r["index"]): r
           for r in load_rows(OUT / "screening_rows.jsonl")
           if not r["error"] and r["dR"] != 0}
    validos = [r for r in cv._rows_census_mescladas()
               if not r["error"] and r["screened_exato"] is not None]
    alvo = [r for r in validos if r["tipo"] == "context_policy"
            and scr[(r["cfg"], r["task_id"], r["index"])]["flip"] == "summarize_context"]
    rows_path = OUT / "aprime_s_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    for r in sorted(alvo, key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        chave = (r["cfg"], r["task_id"], r["index"])
        if chave in feitos:
            continue
        traj, scr_row = trajs[(r["cfg"], r["task_id"])], scr[chave]
        h = traj.config["harness"]
        di, dj = traj.decisions[r["index"]], traj.decisions[r["j"]]
        msgs_s = summarize_messages(di.state_before["messages"],
                                    h["keep_last"], h["task_chars"],
                                    HarnessV2.WORKSPACE_NOTE)
        base = {"cfg": r["cfg"], "task_id": r["task_id"], "index": r["index"],
                "j": r["j"], "temp": r.get("a_prime_temp", 0.8),
                "C_H": r["C_H"], "screened_census": r["screened_exato"]}
        print(f"[a's] {r['cfg']} {r['task_id']} idx{r['index']}", flush=True)
        amostra = sample_alternative_v2(llm, msgs_s, cv._canon(dj.chosen_action),
                                        temperature=base["temp"], seeds=SEEDS_S)
        if not amostra["found"]:
            append_row(rows_path, {**base, "status": "sem_a_prime_s"})
            continue
        b = _bracos(llm, traj, r, scr_row, amostra["action"], False,
                    OUT / "aprime_s_trajs")
        if b["error"]:
            append_row(rows_path, {**base, "status": "erro_replay",
                                   "seed": amostra["seed"], "error": b["error"]})
            continue
        r_orig = scr_row["reward_original"]
        c_ms, c_hms = round(r_orig - b["R_M"], 4), round(r_orig - b["R_HM"], 4)
        append_row(rows_path, {
            **base, "status": "ok", "seed": amostra["seed"],
            "R_Ms": b["R_M"], "R_HMs": b["R_HM"], "C_Ms": c_ms, "C_HMs": c_hms,
            "I_s": round(c_hms - r["C_H"] - c_ms, 4),
            "screened_s": b["R_HM"] == b["R_M"],
            "informativo": any(x != 0 for x in (r["C_H"], c_ms, c_hms))})


# -- relatório (desfechos declarados do pré-reg 38) -----------------------------
def _bucket_s(taxa: float | None) -> str | None:
    if taxa is None:
        return None
    return "b1" if taxa >= 0.90 else ("b2" if taxa >= 0.75 else "b3")


def relatorio():
    census_rep = cv._report_census(cv._rows_census_mescladas())
    partes = {}
    for nome in ("base_report", "nulos_report", "piso_report", "screening_report"):
        p = OUT / f"{nome}.json"
        partes[nome] = json.loads(p.read_text()) if p.exists() else None
    s_rows = load_rows(OUT / "aprime_s_rows.jsonl")
    s_ok = [r for r in s_rows if r.get("status") == "ok"]
    taxa_s = round(sum(r["screened_s"] for r in s_ok) / len(s_ok), 4) if s_ok else None
    piso_ok = bool((partes["piso_report"] or {}).get("gate_ok"))
    desfecho = None
    if not piso_ok:
        desfecho = "X4_piso_falhou"
    elif census_rep["global"]["desfecho"] == "s3" and \
            census_rep["gate_por_contabilidade"]["medidos_sem_duais"]["gate_abre"]:
        desfecho = "X1_estrutura_transporta"
    else:
        desfecho = "X2_dependencia_de_familia"
    estimando = None if taxa_s is None else (
        "E1_acoplamento_transporta" if _bucket_s(taxa_s) == "b3"
        else "E2_acoplamento_dependente")
    rel = {"pre_registro": 38, "modelo": os.environ.get("TCC_MODEL"),
           "out": str(OUT), **partes, "census_report": census_rep,
           "aprime_s": {"n_pontos": len(s_rows), "n_ok": len(s_ok),
                        "taxa_screened_s": taxa_s, "bucket": _bucket_s(taxa_s),
                        "status": {s: sum(1 for r in s_rows if r.get("status") == s)
                                   for s in ("ok", "sem_a_prime_s", "erro_replay")},
                        "descreenados": [r for r in s_ok if not r["screened_s"]]},
           "comparador_qwen": COMPARADOR_QWEN,
           "desfecho_38": {"fenomeno": desfecho, "estimando": estimando}}
    (OUT / "relatorio38.json").write_text(json.dumps(rel, indent=2, ensure_ascii=False))
    print(json.dumps({"desfecho_38": rel["desfecho_38"],
                      "por_tipo": {t: {"n": v["n_census"],
                                       "taxa": v["taxa_screening_exato"]}
                                   for t, v in census_rep["por_tipo"].items()},
                      "gate": census_rep["gate_por_contabilidade"],
                      "piso": (partes["piso_report"] or {}).get("taxa_exatos"),
                      "taxa_screened_s": taxa_s},
                     indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["base", "nulos", "piso", "screening", "census",
                             "census_esc", "aprime_s", "relatorio"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"base": stage_base, "nulos": cv.stage_nulos, "piso": stage_piso,
     "screening": cv.stage_screening, "census": cv.stage_census,
     "census_esc": cv.stage_census_esc, "aprime_s": stage_aprime_s,
     "relatorio": relatorio}[args.stage]()
