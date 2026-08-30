"""Pré-registro 40 — quarto braço da grade fatorial: R(h′, a).

Para cada ponto com C_M e C_HM medidos (V1: teste3_*; V2: census_v2), roda
UM replay forçando o flip do harness em i e a AÇÃO ORIGINAL a (canônica) no
ponto do modelo j. Predição do auditor (Boclin): nos pontos screened de folga,
R(h′,a) = R exato e I_fact = C_HM − C_Ha − C_M = 0.

Gate prévio: revalidação nula (2 pontos/config, fila nula, todos exatos).
Execução SEQUENCIAL (1 GPU; paralelismo intra-GPU vetado — _ls600_concorrente).

Uso:
  uv run python -m experiments.quarto_braco --stage gate
  uv run python -m experiments.quarto_braco --stage v1
  uv run python -m experiments.quarto_braco --stage v2
  uv run python -m experiments.quarto_braco --stage relatorio
"""
import argparse
import json
import statistics
from pathlib import Path

import openai

from agent.llm import LLMClient
from experiments.census_v2 import OUT as V2OUT
from experiments.census_v2 import _canon, _fila_dupla, _trajs_base
from experiments.common import append_row, done_keys, load_rows, load_trajectories
from experiments.teste3 import FLIP, _by_index, sanitize
from trajectories.replay import replay_from

OUT = Path("runs/preg40")
V1_CONFIGS = ("g450", "g600", "g900", "mt4", "mt6", "mt8")
V1_FOLGA = ("g450", "g600", "g900")


def _trajs_v1(cfg: str) -> dict:
    base = Path(f"runs/teste0_{cfg}/baseline")
    return {t.trajectory_id: t for t in load_trajectories(base)}


def _cf_rows_v1(cfg: str) -> list[dict]:
    return load_rows(Path(f"runs/teste3_{cfg}/cf_results.jsonl"))


def _census_rows_v2() -> list[dict]:
    rows = load_rows(V2OUT / "census_rows.jsonl") + \
        load_rows(V2OUT / "census_esc_rows.jsonl")
    return [r for r in rows if r.get("C_M") is not None
            and r.get("C_HM") is not None]


def _screening_v2() -> dict:
    return {(r["cfg"], r["task_id"], r["index"]): r
            for r in load_rows(V2OUT / "screening_rows.jsonl") if not r["error"]}


# -- stage gate ---------------------------------------------------------------
def stage_gate(llm_v1, llm_v2):
    """Revalidação nula: 2 pontos por config, fila 100% original, ΔR deve ser 0."""
    rows_path = OUT / "gate_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("fase", "cfg", "task_id", "index"))
    for cfg in V1_CONFIGS:
        trajs = _trajs_v1(cfg)
        alvo = sorted(_cf_rows_v1(cfg),
                      key=lambda r: (r["task_id"], r["cp_index"]))[:2]
        for r in alvo:
            chave = ("v1", cfg, r["task_id"], r["cp_index"])
            if chave in feitos:
                continue
            traj = trajs[r["trajectory_id"]]
            cp, tc = _by_index(traj, r["cp_index"]), _by_index(traj, r["index"])
            res = replay_from(traj, cp.index, llm_v1, OUT / "replays",
                              override_actions=[
                                  {"point": "context_policy",
                                   "action": sanitize(cp.chosen_action)},
                                  {"point": "tool_call",
                                   "action": sanitize(tc.chosen_action)}])
            dr = res["reward"] - traj.final_reward
            append_row(rows_path, {"fase": "v1", "cfg": cfg,
                                   "task_id": r["task_id"],
                                   "index": r["cp_index"], "dR": dr,
                                   "exact": dr == 0.0})
            print(f"[gate v1 {cfg}] {r['task_id']} cp{r['cp_index']} "
                  f"dR={dr:+.2f}", flush=True)
    trajs2, scr = _trajs_base(), _screening_v2()
    v2 = [r for r in _census_rows_v2() if not r.get("hm_analitico")]
    por_cfg = {}
    for r in sorted(v2, key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        por_cfg.setdefault(r["cfg"], []).append(r)
    for cfg, rs in por_cfg.items():
        for r in rs[:2]:
            chave = ("v2", cfg, r["task_id"], r["index"])
            if chave in feitos:
                continue
            traj = trajs2[(cfg, r["task_id"])]
            i, j = r["index"], r["j"]
            di, dj = traj.decisions[i], traj.decisions[j]
            entry, fila = _fila_dupla(traj, i, _canon(di.chosen_action),
                                      j, _canon(dj.chosen_action))
            res = replay_from(traj, entry, llm_v2, OUT / "replays",
                              override_actions=fila)
            r_orig = scr[(cfg, r["task_id"], r["index"])]["reward_original"]
            dr = res["reward"] - r_orig
            append_row(rows_path, {"fase": "v2", "cfg": cfg,
                                   "task_id": r["task_id"], "index": i,
                                   "dR": dr, "exact": dr == 0.0})
            print(f"[gate v2 {cfg}] {r['task_id']} idx{i} dR={dr:+.2f}",
                  flush=True)
    rows = load_rows(rows_path)
    ok = bool(rows) and all(r["exact"] for r in rows)
    print(json.dumps({"gate_ok": ok, "n": len(rows),
                      "n_inexact": sum(not r["exact"] for r in rows)}),
          flush=True)
    if not ok:
        raise SystemExit("GATE NULO FALHOU — abortando (pré-reg 40)")


# -- stage v1 -----------------------------------------------------------------
def stage_v1(llm):
    rows_path = OUT / "v1_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "trajectory_id", "cp_index"))
    for cfg in V1_CONFIGS:
        trajs = _trajs_v1(cfg)
        for r in sorted(_cf_rows_v1(cfg),
                        key=lambda r: (r["task_id"], r["cp_index"])):
            if (cfg, r["trajectory_id"], r["cp_index"]) in feitos:
                continue
            traj = trajs[r["trajectory_id"]]
            cp, tc = _by_index(traj, r["cp_index"]), _by_index(traj, r["index"])
            flip = FLIP[sanitize(cp.chosen_action)["action"]]
            res = replay_from(traj, cp.index, llm, OUT / "replays",
                              override_actions=[
                                  {"point": "context_policy",
                                   "action": {"action": flip}},
                                  {"point": "tool_call",
                                   "action": sanitize(tc.chosen_action)}])
            r_ha = res["reward"]
            c_ha = r["r_orig"] - r_ha
            i_fact = round(r["C_HM"] - c_ha - r["C_M"], 4)
            append_row(rows_path, {
                "cfg": cfg, "task_id": r["task_id"],
                "trajectory_id": r["trajectory_id"],
                "cp_index": r["cp_index"], "index": r["index"],
                "direction": r["direction"], "r_orig": r["r_orig"],
                "r_ha": r_ha, "C_Ha": round(c_ha, 4),
                "C_H": r["C_H"], "C_M": r["C_M"], "C_HM": r["C_HM"],
                "I": r["I"], "I_fact": i_fact,
                "exact_ha": r_ha == r["r_orig"],
                "screened": r["C_HM"] == r["C_M"],
                "saturated": r["saturated"],
                "final_timed_out": res["final_timed_out"],
                "replay_traj": res["trajectory_path"]})
            print(f"[v1 {cfg}] {r['task_id']} cp{r['cp_index']} "
                  f"R(h',a)={r_ha:.2f} R={r['r_orig']:.2f} "
                  f"I_fact={i_fact:+.2f}", flush=True)


# -- stage v2 -----------------------------------------------------------------
def stage_v2(llm):
    rows_path = OUT / "v2_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    trajs, scr = _trajs_base(), _screening_v2()
    for r in sorted(_census_rows_v2(),
                    key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        chave = (r["cfg"], r["task_id"], r["index"])
        if chave in feitos:
            continue
        s = scr[chave]
        traj = trajs[(r["cfg"], r["task_id"])]
        i, j = r["index"], r["j"]
        r_orig = s["reward_original"]
        error = None
        if r.get("hm_analitico"):
            # flip terminate em i encerra o episódio antes de j: R(h',a) ≡ R_H
            r_ha, analitico = s["reward_replay"], True
        else:
            analitico = False
            r_ha = None
            dj = traj.decisions[j]
            try:
                entry, fila = _fila_dupla(traj, i, {"action": s["flip"]},
                                          j, _canon(dj.chosen_action))
                r_ha = replay_from(traj, entry, llm, OUT / "replays",
                                   override_actions=fila)["reward"]
            except ValueError as exc:
                error = str(exc)
            except openai.BadRequestError as exc:
                error = f"context_overflow: {exc}"[:200]
        base = {"cfg": r["cfg"], "task_id": r["task_id"], "index": i, "j": j,
                "tipo": r["tipo"], "flip": s["flip"], "r_orig": r_orig,
                "r_ha": r_ha, "C_Ha": None, "C_H": r["C_H"], "C_M": r["C_M"],
                "C_HM": r["C_HM"], "I": r["I"], "I_fact": None,
                "exact_ha": None, "screened": r.get("screened_exato"),
                "hm_analitico": analitico, "error": error}
        if r_ha is not None:
            base["C_Ha"] = round(r_orig - r_ha, 4)
            base["I_fact"] = round(r["C_HM"] - base["C_Ha"] - r["C_M"], 4)
            base["exact_ha"] = r_ha == r_orig
        append_row(rows_path, base)
        print(f"[v2 {r['cfg']}] {r['task_id']} idx{i} ({r['tipo']}) "
              f"R(h',a)={r_ha} R={r_orig} I_fact={base['I_fact']} "
              f"err={error}", flush=True)


# -- stage relatorio ----------------------------------------------------------
def _resumo(vs: list[dict]) -> dict:
    ifs = [r["I_fact"] for r in vs if r["I_fact"] is not None]
    return {"n": len(vs),
            "n_exact_ha": sum(bool(r["exact_ha"]) for r in vs),
            "n_I_fact_zero": sum(x == 0.0 for x in ifs),
            "I_fact_mean": round(statistics.mean(ifs), 4) if ifs else None,
            "I_fact_max_abs": max((abs(x) for x in ifs), default=None)}


def stage_relatorio():
    v1 = load_rows(OUT / "v1_rows.jsonl")
    v2 = load_rows(OUT / "v2_rows.jsonl")
    gate = load_rows(OUT / "gate_rows.jsonl")
    # endpoint primário: pontos screened de folga (C_HM=C_M exato, g450/g600/g900)
    prim = [r for r in v1 if r["cfg"] in V1_FOLGA and r["screened"]]
    n_exact = sum(r["exact_ha"] for r in prim)
    frac = n_exact / len(prim) if prim else None
    desfecho = None
    if frac is not None:
        desfecho = "s1_boclin_confirmado" if frac >= 0.90 else \
            ("s2_misto" if frac >= 0.50 else "s3_boclin_refutado")
    quebras = [r for r in v1 if r["cfg"] not in V1_FOLGA and not r["screened"]]
    report = {
        "gate_ok": bool(gate) and all(r["exact"] for r in gate),
        "n_gate": len(gate),
        "primario": {"n_screened_folga": len(prim), "n_exact_ha": n_exact,
                     "frac_exact_ha": round(frac, 4) if frac is not None else None,
                     "desfecho": desfecho},
        "v1_por_cfg": {c: _resumo([r for r in v1 if r["cfg"] == c])
                       for c in V1_CONFIGS},
        "v1_quebras_pressao": [
            {k: r[k] for k in ("cfg", "task_id", "cp_index", "C_Ha", "C_H",
                               "C_M", "C_HM", "I", "I_fact", "exact_ha")}
            for r in quebras],
        "v2_por_tipo": {t: _resumo([r for r in v2 if r["tipo"] == t
                                    and not r["error"]])
                        for t in sorted({r["tipo"] for r in v2})},
        "v2_n_erros": sum(bool(r["error"]) for r in v2),
        # divergência efeito total (C_H, braço vivo) vs direto (C_Ha)
        "v1_n_CH_diff_CHa": sum(r["C_H"] != r["C_Ha"] for r in v1),
        "v2_n_CH_diff_CHa": sum(r["C_H"] != r["C_Ha"] for r in v2
                                if r["C_Ha"] is not None),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2,
                                                ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["gate", "v1", "v2", "relatorio"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "relatorio":
        stage_relatorio()
    elif args.stage == "gate":
        # paridade de cliente com os censos originais: V1 max_tokens=1200,
        # V2 default (2048)
        stage_gate(LLMClient(max_tokens=1200), LLMClient())
    elif args.stage == "v1":
        stage_v1(LLMClient(max_tokens=1200))
    else:
        stage_v2(LLMClient())
