"""Controles de estimando do census V2 (pré-reg 30) — re-amostragem de a′ + a′_s.

PRÉ-REGISTRO (DIARIO-EXPERIMENTAL.md, 2026-08-27, commitado ANTES de rodar):
- Parte A: re-amostragem de a′ nos 48 pontos válidos do census, 2 schedules
  disjuntos (A1=4001–4008, A2=5001–5008), temp igual à do ponto. Draw
  informativo := encontrado E ≠ a′ do census (canônico). Estabilidade =
  frac de draws informativos com screened_exato_re == census. Headline por
  schedule: substituir a′→draw e recomputar desfecho (avalia_desfecho) e a
  célula primária do gate (medidos sem duais, 0.20).
- Parte B: a′_s do estado sumarizado (summarize_messages com a config da
  trajetória e WORKSPACE_NOTE do V2), só context_policy keep→summarize,
  seeds 6001–6008. screened_s := R_HMs == R_Ms; informativo := algum de
  (C_H, C_Ms, C_HMs) ≠ 0.
- Desfechos: A → r1/r2/r3; B → b1 ≥0.90 / b2 [0.75,0.90) / b3 <0.75.

Uso (sequencial, servidor 8321 com APC off):
  uv run python -m experiments.v2_controles --parte a
  uv run python -m experiments.v2_controles --parte b
  uv run python -m experiments.v2_controles --parte relatorio
"""
import argparse
import json
from pathlib import Path

import openai

from agent.harness import summarize_messages
from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from experiments.census_v2 import (_canon, _fila_dupla, _rows_census_mescladas,
                                   _trajs_base, avalia_desfecho, gate_f4f5)
from experiments.common import append_row, done_keys, load_rows
from interventions.model_v2 import _canonical, sample_alternative_v2
from trajectories.replay import build_flip_queue, replay_from

OUT = Path("runs/v2_controles")
CENSUS = Path("runs/census_v2")
SCHEDULES = {"A1": tuple(range(4001, 4009)), "A2": tuple(range(5001, 5009))}
SEEDS_B = tuple(range(6001, 6009))


def _validos() -> list[dict]:
    return [r for r in _rows_census_mescladas()
            if not r["error"] and r["screened_exato"] is not None]


def _screening() -> dict:
    return {(r["cfg"], r["task_id"], r["index"]): r
            for r in load_rows(CENSUS / "screening_rows.jsonl")
            if not r["error"] and r["dR"] != 0}


def _dual(r: dict, scr: dict) -> bool:
    """Adendo 29a: braço HM degenerado (flip terminal)."""
    s = scr[(r["cfg"], r["task_id"], r["index"])]
    return r["tipo"] == "termination" and s["flip"] == "terminate"


def _a_prime_census(llm, traj, r: dict) -> dict | None:
    """Reconstroi o a′ do census deterministicamente via a seed gravada."""
    dj = traj.decisions[r["j"]]
    amostra = sample_alternative_v2(
        llm, dj.state_before["messages"], _canon(dj.chosen_action),
        temperature=r.get("a_prime_temp", 0.8), seeds=(r["a_prime_seed"],))
    return amostra["action"] if amostra["found"] else None


def _bracos(llm, traj, r: dict, scr_row: dict, a_prime: dict,
            dual: bool, trajs_dir: Path) -> dict:
    """Mede braços M e HM com a′ dado; mesmas exclusões do census."""
    out = {"R_M": None, "R_HM": None, "error": None}
    try:
        entry_m, queue_m = build_flip_queue(traj, r["j"], a_prime)
        out["R_M"] = replay_from(traj, entry_m, llm, trajs_dir,
                                 override_actions=queue_m)["reward"]
        if dual:
            out["R_HM"] = scr_row["reward_replay"]  # ≡ R_H (29a)
        else:
            entry_hm, fila = _fila_dupla(traj, r["index"],
                                         {"action": scr_row["flip"]},
                                         r["j"], a_prime)
            out["R_HM"] = replay_from(traj, entry_hm, llm, trajs_dir,
                                      override_actions=fila)["reward"]
    except ValueError as exc:
        out["error"] = str(exc)
    except openai.BadRequestError as exc:
        out["error"] = f"context_overflow: {exc}"[:200]
    return out


# -- Parte A ------------------------------------------------------------------
def parte_a():
    trajs, scr = _trajs_base(), _screening()
    llm = LLMClient()
    rows_path = OUT / "a_rows.jsonl"
    feitos = done_keys(load_rows(rows_path),
                       ("schedule", "cfg", "task_id", "index"))
    for r in sorted(_validos(), key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        chave = (r["cfg"], r["task_id"], r["index"])
        traj, scr_row = trajs[(r["cfg"], r["task_id"])], scr[chave]
        dual = _dual(r, scr)
        a_orig = None
        for nome, seeds in SCHEDULES.items():
            if (nome, *chave) in feitos:
                continue
            base = {"schedule": nome, "cfg": r["cfg"], "task_id": r["task_id"],
                    "index": r["index"], "tipo": r["tipo"], "j": r["j"],
                    "dual": dual, "temp": r.get("a_prime_temp", 0.8),
                    "screened_census": r["screened_exato"]}
            print(f"[A:{nome}] {r['cfg']} {r['task_id']} idx{r['index']} "
                  f"({r['tipo']})", flush=True)
            if a_orig is None:
                a_orig = _a_prime_census(llm, traj, r)
                if a_orig is None:
                    append_row(rows_path, {**base, "status": "a_prime_orig_irreproduzivel"})
                    continue
            dj = traj.decisions[r["j"]]
            amostra = sample_alternative_v2(
                llm, dj.state_before["messages"], _canon(dj.chosen_action),
                temperature=base["temp"], seeds=seeds)
            if not amostra["found"]:
                append_row(rows_path, {**base, "status": "sem_a_prime_re"})
                continue
            if _canonical(amostra["action"]) == _canonical(a_orig):
                append_row(rows_path, {**base, "status": "identico",
                                       "seed": amostra["seed"]})
                continue
            b = _bracos(llm, traj, r, scr_row, amostra["action"], dual,
                        OUT / "a_trajs")
            if b["error"]:
                append_row(rows_path, {**base, "status": "erro_replay",
                                       "seed": amostra["seed"], "error": b["error"]})
                continue
            screened_re = b["R_HM"] == b["R_M"]
            append_row(rows_path, {
                **base, "status": "informativo", "seed": amostra["seed"],
                "R_M": b["R_M"], "R_HM": b["R_HM"],
                "screened_re": screened_re,
                "estavel": screened_re == r["screened_exato"]})
    relatorio()


# -- Parte B ------------------------------------------------------------------
def parte_b():
    trajs, scr = _trajs_base(), _screening()
    llm = LLMClient()
    rows_path = OUT / "b_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    alvo = [r for r in _validos() if r["tipo"] == "context_policy"
            and scr[(r["cfg"], r["task_id"], r["index"])]["flip"] == "summarize_context"]
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
        print(f"[B] {r['cfg']} {r['task_id']} idx{r['index']}", flush=True)
        amostra = sample_alternative_v2(llm, msgs_s, _canon(dj.chosen_action),
                                        temperature=base["temp"], seeds=SEEDS_B)
        if not amostra["found"]:
            append_row(rows_path, {**base, "status": "sem_a_prime_s"})
            continue
        b = _bracos(llm, traj, r, scr_row, amostra["action"], False,
                    OUT / "b_trajs")
        if b["error"]:
            append_row(rows_path, {**base, "status": "erro_replay",
                                   "seed": amostra["seed"], "error": b["error"]})
            continue
        r_orig = scr_row["reward_original"]
        c_ms, c_hms = round(r_orig - b["R_M"], 4), round(r_orig - b["R_HM"], 4)
        screened_s = b["R_HM"] == b["R_M"]
        append_row(rows_path, {
            **base, "status": "ok", "seed": amostra["seed"],
            "R_Ms": b["R_M"], "R_HMs": b["R_HM"], "C_Ms": c_ms, "C_HMs": c_hms,
            "I_s": round(c_hms - r["C_H"] - c_ms, 4), "screened_s": screened_s,
            "informativo": any(x != 0 for x in (r["C_H"], c_ms, c_hms))})
    relatorio()


# -- Relatório ----------------------------------------------------------------
def _headline_schedule(validos, scr, rows_a, nome) -> dict:
    """Substitui a classificação pelo draw informativo do schedule; recomputa
    desfecho e a célula primária do gate (medidos sem duais)."""
    subs = {(x["cfg"], x["task_id"], x["index"]): x["screened_re"]
            for x in rows_a if x["schedule"] == nome
            and x["status"] == "informativo"}
    por_tipo, nao_scr_sd, n_sd = {}, 0, 0
    for r in validos:
        chave = (r["cfg"], r["task_id"], r["index"])
        s = subs.get(chave, r["screened_exato"])
        t = por_tipo.setdefault(r["tipo"], {"n": 0, "scr": 0})
        t["n"] += 1
        t["scr"] += bool(s)
        if not _dual(r, scr):
            n_sd += 1
            nao_scr_sd += not s
    taxas = {t: {"n": v["n"], "taxa": round(v["scr"] / v["n"], 4)}
             for t, v in por_tipo.items()}
    frac = round(nao_scr_sd / n_sd, 4) if n_sd else None
    return {"n_substituidos": len(subs), "taxas_por_tipo": taxas,
            "desfecho": avalia_desfecho(taxas),
            "gate_medidos_sem_duais": {"frac": frac, "abre": gate_f4f5(frac)}}


def relatorio():
    validos, scr = _validos(), _screening()
    rows_a = load_rows(OUT / "a_rows.jsonl")
    info = [x for x in rows_a if x["status"] == "informativo"]
    rows_b = load_rows(OUT / "b_rows.jsonl")
    ok_b = [x for x in rows_b if x["status"] == "ok"]
    info_b = [x for x in ok_b if x["informativo"]]
    estab = (round(sum(x["estavel"] for x in info) / len(info), 4)
             if info else None)
    heads = {n: _headline_schedule(validos, scr, rows_a, n) for n in SCHEDULES}
    mantidos = all(h["desfecho"]["desfecho"] == "s3"
                   and h["gate_medidos_sem_duais"]["abre"] for h in heads.values())
    desfecho_a = None
    if estab is not None:
        desfecho_a = ("r1" if estab >= 0.90 and mantidos else
                      "r2" if mantidos else "r3")
    taxa_b = (round(sum(x["screened_s"] for x in info_b) / len(info_b), 4)
              if info_b else None)
    desfecho_b = None
    if taxa_b is not None:
        desfecho_b = ("b1" if taxa_b >= 0.90 else
                      "b2" if taxa_b >= 0.75 else "b3")
    summary = {
        "pre_registro": 30,
        "parte_a": {
            "n_draws": len(rows_a),
            "status": {s: sum(1 for x in rows_a if x["status"] == s)
                       for s in sorted({x["status"] for x in rows_a})},
            "n_informativos": len(info),
            "n_estaveis": sum(x["estavel"] for x in info),
            "estabilidade": estab,
            "flips": [{k: x[k] for k in ("schedule", "cfg", "task_id", "index",
                                         "tipo", "screened_census", "screened_re")}
                      for x in info if not x["estavel"]],
            "headline_por_schedule": heads,
            "desfecho": desfecho_a},
        "parte_b": {
            "n_pontos": len(rows_b),
            "status": {s: sum(1 for x in rows_b if x["status"] == s)
                       for s in sorted({x["status"] for x in rows_b})},
            "n_informativos": len(info_b),
            "n_screened_s": sum(x["screened_s"] for x in info_b),
            "taxa_screened_s": taxa_b,
            "descreenados": [{k: x[k] for k in ("cfg", "task_id", "index",
                                                "screened_census", "screened_s", "I_s")}
                             for x in info_b if not x["screened_s"]],
            "desfecho": desfecho_b}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2,
                                                 ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--parte", required=True, choices=["a", "b", "relatorio"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"a": parte_a, "b": parte_b, "relatorio": relatorio}[args.parte]()
