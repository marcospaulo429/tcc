"""Census multi-decisão V2 (pré-reg 29) — baselines, nulos, screening seletivo, census.

Uso (SEMPRE sequencial, nunca em paralelo com outro job de GPU):
  uv run python -m experiments.census_v2 --stage base
  uv run python -m experiments.census_v2 --stage nulos
  uv run python -m experiments.census_v2 --stage screening
  uv run python -m experiments.census_v2 --stage census
  uv run python -m experiments.census_v2 --stage relatorio
"""
import argparse
import json
import statistics
from pathlib import Path

import openai

from agent.harness import summarize_is_vacuous
from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from agent.loop import Episode
from agent.loop_v2 import EpisodeV2
from environment.tasks_swe import TASKS
from experiments.common import append_row, done_keys, load_rows
from interventions.model_v2 import sample_alternative_v2
from trajectories.recorder import Recorder
from trajectories.replay import build_flip_queue, replay_from
from trajectories.schema import load_trajectory

OUT = Path("runs/census_v2")

# kwargs de HarnessV2 por config (pré-reg 29)
CONFIGS = {
    "v2_folga": {},
    "v2_pressao": {"summarize_threshold_tokens": 2500, "max_turns": 12, "keep_last": 4},
}

FLIPS = {
    "context_policy": {"keep_context": "summarize_context", "summarize_context": "keep_context"},
    "observation_policy": {"full_output": "compact_output", "compact_output": "full_output"},
    "test_schedule": {"auto_test": "defer_test", "defer_test": "auto_test"},
    "retry": {"retry_once": "give_up"},
    "termination": {"continue": "terminate"},
}
# ordem do round-robin de seleção (pré-reg 29)
ORDEM_TIPOS = ("context_policy", "observation_policy", "test_schedule",
               "termination", "retry")
MAX_POR_TIPO = 2   # por trajetória
MAX_POR_TRAJ = 6

GATE_F4F5_FRAC = 0.20


def _canon(action: dict) -> dict:
    return {k: v for k, v in action.items() if k != "forced"}


def _trajs_base() -> dict:
    """(cfg, task_id) -> Trajectory, para as rows do base com trajetória gravada."""
    out = {}
    for r in load_rows(OUT / "base_rows.jsonl"):
        if r.get("trajectory_path"):
            out[(r["cfg"], r["task_id"])] = load_trajectory(r["trajectory_path"])
    return out


# -- stage base --------------------------------------------------------------
def _episodio(task: dict, harness_kwargs: dict) -> dict:
    ep = EpisodeV2(task, LLMClient(), HarnessV2(**harness_kwargs),
                   Recorder(OUT / "base_trajs"))
    try:
        return ep.run()
    finally:
        ep.sandbox.cleanup()


def _conta_tipos(trajs) -> dict:
    contagem = {}
    for t in trajs:
        for d in t.decisions:
            contagem[d.decision_point] = contagem.get(d.decision_point, 0) + 1
    return contagem


def stage_base():
    rows_path = OUT / "base_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id"))
    for cfg, kwargs in CONFIGS.items():
        for task in TASKS:
            if (cfg, task["task_id"]) in feitos:
                continue
            print(f"[base] {cfg} {task['task_id']}", flush=True)
            try:
                r = _episodio(task, kwargs)
                append_row(rows_path, {"cfg": cfg, "task_id": task["task_id"],
                                       **r, "error": None})
            except Exception as exc:  # ex.: 400 por estouro de contexto — reportar
                append_row(rows_path, {"cfg": cfg, "task_id": task["task_id"],
                                       "reward": 0.0, "success": False,
                                       "trajectory_path": None,
                                       "error": f"{type(exc).__name__}: {exc}"})

    rows = load_rows(rows_path)
    trajs = _trajs_base()
    report = {}
    for cfg in CONFIGS:
        rc = [r for r in rows if r["cfg"] == cfg]
        tc = [t for (c, _), t in trajs.items() if c == cfg]
        ok = [r for r in rc if not r["error"]]
        report[cfg] = {
            "n": len(rc), "n_erros": len(rc) - len(ok),
            "erros": {r["task_id"]: r["error"] for r in rc if r["error"]},
            "taxa_sucesso": round(sum(1 for r in rc if r.get("reward") == 1.0)
                                  / len(rc), 3) if rc else None,
            "reward_medio": round(sum(r.get("reward", 0.0) for r in rc)
                                  / len(rc), 3) if rc else None,
            "mediana_wall_s": round(statistics.median(
                r.get("wall_time_s", 0.0) for r in ok), 1) if ok else None,
            "decisoes_por_tipo": _conta_tipos(tc),
        }
    (OUT / "base_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


# -- stage nulos (Teste 0 V2) -------------------------------------------------
def stage_nulos():
    trajs = _trajs_base()
    llm = LLMClient()  # nunca chamado: fila forçada total (custo LLM ~zero)
    rows_path = OUT / "nulos_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id"))
    for (cfg, task_id), traj in sorted(trajs.items()):
        if (cfg, task_id) in feitos:
            continue
        print(f"[nulos] {cfg} {task_id}", flush=True)
        com_retry = any(d.decision_point == "retry" for d in traj.decisions)
        queue = [{"point": d.decision_point, "action": _canon(d.chosen_action)}
                 for d in traj.decisions if d.decision_point != "retry"]
        rep = replay_from(traj, 0, llm, OUT / "nulos_trajs", override_actions=queue)
        append_row(rows_path, {"cfg": cfg, "task_id": task_id,
                               "reward_original": traj.final_reward,
                               "reward_replay": rep["reward"],
                               "exato": rep["reward"] == traj.final_reward,
                               "com_retry": com_retry})

    rows = load_rows(rows_path)
    sem = [r for r in rows if not r["com_retry"]]
    com = [r for r in rows if r["com_retry"]]
    report = {
        "n": len(rows),
        "sem_retry": {"n": len(sem), "exatos": sum(r["exato"] for r in sem),
                      "desvios": [r for r in sem if not r["exato"]]},
        "com_retry": {"n": len(com), "exatos": sum(r["exato"] for r in com),
                      "desvios": [r for r in com if not r["exato"]]},
        "piso_ok": all(r["exato"] for r in sem),
    }
    (OUT / "nulos_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


# -- stage screening ----------------------------------------------------------
def _candidatos_traj(traj) -> list[tuple[str, int, dict]]:
    """Candidatos POR TRAJETÓRIA (regras do 28b), teto ≤2/tipo e ≤6/traj,
    round-robin por tipo na ordem ORDEM_TIPOS pegando o melhor por score,
    depois o segundo — determinístico (desempate por task_id e índice)."""
    hcfg = traj.config["harness"]
    por_tipo = {t: [] for t in ORDEM_TIPOS}
    for i, d in enumerate(traj.decisions):
        p = d.decision_point
        if p not in FLIPS:
            continue
        acao = d.chosen_action["action"]
        if acao not in FLIPS[p]:
            continue
        score = d.state_before.get("context_tokens", 0)
        if p == "context_policy":
            # adendo 28b: prioriza keep→summarize; summarize vácuo é filtrado —
            # vacuidade avaliada com keep_last/task_chars da config DA trajetória
            if acao == "keep_context":
                if summarize_is_vacuous(d.state_before["messages"],
                                        keep_last=hcfg["keep_last"],
                                        task_chars=hcfg["task_chars"],
                                        summarizer=hcfg.get("summarizer", "rule")):
                    continue
                score += 10**6
        if p == "observation_policy":
            if not (d.observation or {}).get("chars_full"):
                continue  # sem output de falha, compact==full (vácuo)
            score = d.observation["chars_full"]
        if p == "termination":
            if d.state_before.get("tests_passed") or d.state_before.get("turn", 0) < 2:
                continue
            score = -d.state_before.get("turn", 0)  # mais cedo = mais informativo
        por_tipo[p].append((score, i, {"action": FLIPS[p][acao]}))
    for p in por_tipo:
        por_tipo[p].sort(key=lambda c: (-c[0], traj.task_id, c[1]))
        por_tipo[p] = por_tipo[p][:MAX_POR_TIPO]
    sel = []
    for rank in range(MAX_POR_TIPO):
        for p in ORDEM_TIPOS:
            if len(sel) >= MAX_POR_TRAJ:
                break
            if rank < len(por_tipo[p]):
                _, i, flip = por_tipo[p][rank]
                sel.append((p, i, flip))
    return sel


def stage_screening():
    trajs = _trajs_base()
    llm = LLMClient()
    rows_path = OUT / "screening_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    for (cfg, task_id), traj in sorted(trajs.items()):
        for tipo, i, flip in _candidatos_traj(traj):
            if (cfg, task_id, i) in feitos:
                continue
            print(f"[screening] {cfg} {task_id} idx{i} {tipo} -> {flip['action']}",
                  flush=True)
            base = {"cfg": cfg, "task_id": task_id, "index": i, "tipo": tipo,
                    "flip": flip["action"], "reward_original": traj.final_reward}
            try:
                entry, queue = build_flip_queue(traj, i, flip)
                rep = replay_from(traj, entry, llm, OUT / "screening_trajs",
                                  override_actions=queue)
                dR = round(rep["reward"] - traj.final_reward, 4)
                append_row(rows_path, {**base, "reward_replay": rep["reward"],
                                       "dR": dR, "pivotal": dR != 0, "error": None})
            except ValueError as exc:  # span com retry — pulado e reportado
                append_row(rows_path, {**base, "reward_replay": None, "dR": None,
                                       "pivotal": None, "error": str(exc)})
            except openai.BadRequestError as exc:
                # overflow de contexto sob o flip — consequência causal sem R
                # mensurável no serving de 8k: categoria própria (28b)
                append_row(rows_path, {**base, "reward_replay": None, "dR": None,
                                       "pivotal": None,
                                       "error": f"context_overflow: {exc}"[:200]})

    rows = load_rows(rows_path)
    por = {}
    for r in rows:
        t = por.setdefault(f'{r["tipo"]}|{r["cfg"]}',
                           {"n_pontos": 0, "n_pivotais": 0, "n_overflow": 0,
                            "n_pulados": 0, "dRs": []})
        if r["error"]:
            if str(r["error"]).startswith("context_overflow"):
                t["n_overflow"] += 1
            else:
                t["n_pulados"] += 1
            continue
        t["n_pontos"] += 1
        t["n_pivotais"] += bool(r["pivotal"])
        t["dRs"].append(r["dR"])
    report = {"por_tipo_cfg": por,
              "n_rows": len(rows),
              "n_pivotais": sum(1 for r in rows if not r["error"] and r["pivotal"])}
    (OUT / "screening_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


# -- stage census -------------------------------------------------------------
def _fila_dupla(traj, i: int, flip: dict, j: int, a_prime: dict) -> tuple[int, list[dict]]:
    """Fila de span duplo: entra no último ponto canônico ≤ i e força as decisões
    originais de entry..j, com flip em i e a′ em j. Mesma recusa do build_flip_queue:
    tool_call FORÇADO do span (inclusive j) precedido por retry no original."""
    d = traj.decisions
    entry = max(k for k in range(i + 1) if d[k].decision_point in Episode.PHASES)
    fila = []
    for k in range(entry, j + 1):
        if d[k].decision_point == "tool_call" and k > 0 \
                and d[k - 1].decision_point == "retry":
            raise ValueError(
                f"tool_call idx {k} precedido por retry — prefixo não reconstruível sob ação forçada")
        if k == i:
            action = flip
        elif k == j:
            action = a_prime
        else:
            action = _canon(d[k].chosen_action)
        fila.append({"point": d[k].decision_point, "action": action})
    return entry, fila


def stage_census():
    trajs = _trajs_base()
    llm = LLMClient()
    scr = [r for r in load_rows(OUT / "screening_rows.jsonl")
           if not r["error"] and r["dR"] != 0]
    rows_path = OUT / "census_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("cfg", "task_id", "index"))
    for r in sorted(scr, key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        if (r["cfg"], r["task_id"], r["index"]) in feitos:
            continue
        traj = trajs[(r["cfg"], r["task_id"])]
        i = r["index"]
        base = {"cfg": r["cfg"], "task_id": r["task_id"], "index": i,
                "tipo": r["tipo"], "j": None, "a_prime_seed": None, "C_H": None,
                "C_M": None, "C_HM": None, "I": None, "screened_exato": None}
        j = next((k for k in range(i + 1, len(traj.decisions))
                  if traj.decisions[k].decision_point == "tool_call"), None)
        if j is None:  # sem tool_call após o flip — excluído e reportado
            append_row(rows_path, {**base, "error": "sem_par"})
            continue
        print(f"[census] {r['cfg']} {r['task_id']} idx{i} ({r['tipo']}) j={j}",
              flush=True)
        base["j"] = j
        dj = traj.decisions[j]
        amostra = sample_alternative_v2(llm, dj.state_before["messages"],
                                        _canon(dj.chosen_action))
        if not amostra["found"]:
            append_row(rows_path, {**base, "error": "sem_a_prime"})
            continue
        a_prime = amostra["action"]
        base["a_prime_seed"] = amostra["seed"]
        R_orig = r["reward_original"]
        base["C_H"] = round(R_orig - r["reward_replay"], 4)  # já medido no screening
        R_M = R_HM = None
        error = None
        try:
            entry_m, queue_m = build_flip_queue(traj, j, a_prime)
            R_M = replay_from(traj, entry_m, llm, OUT / "census_trajs",
                              override_actions=queue_m)["reward"]
            entry_hm, fila = _fila_dupla(traj, i, {"action": r["flip"]}, j, a_prime)
            R_HM = replay_from(traj, entry_hm, llm, OUT / "census_trajs",
                               override_actions=fila)["reward"]
        except ValueError as exc:  # span com retry — pulado e reportado
            error = str(exc)
        except openai.BadRequestError as exc:
            error = f"context_overflow: {exc}"[:200]
        if R_M is not None:
            base["C_M"] = round(R_orig - R_M, 4)
        if R_HM is not None:
            base["C_HM"] = round(R_orig - R_HM, 4)
        if base["C_M"] is not None and base["C_HM"] is not None:
            base["I"] = round(base["C_HM"] - base["C_H"] - base["C_M"], 4)
            base["screened_exato"] = R_HM == R_M
        append_row(rows_path, {**base, "error": error})

    rows = load_rows(rows_path)
    report = _report_census(rows)
    (OUT / "census_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


def avalia_desfecho(por_tipo: dict) -> dict:
    """Desfechos do pré-reg 29 sobre {tipo: {"n": int, "taxa": float}} (função pura).

    s1: ≥1 tipo com screening <0.75 E ≥1 tipo ≥0.90, ambos com ≥5 pontos;
    s2: todos os tipos com ≥5 pontos têm taxa ≥0.90 (e existe ≥1 tal tipo);
    s3: ≥2 tipos com taxa <0.75. Campo "desfecho" = primeiro na ordem s1,s3,s2."""
    com5 = {t: v for t, v in por_tipo.items() if v["n"] >= 5}
    s1 = any(v["taxa"] < 0.75 for v in com5.values()) and \
        any(v["taxa"] >= 0.90 for v in com5.values())
    s2 = bool(com5) and all(v["taxa"] >= 0.90 for v in com5.values())
    s3 = sum(1 for v in por_tipo.values() if v["taxa"] < 0.75) >= 2
    desfecho = next((nome for nome, hit in
                     (("s1", s1), ("s3", s3), ("s2", s2)) if hit), "indeterminado")
    return {"s1": s1, "s2": s2, "s3": s3, "desfecho": desfecho}


def gate_f4f5(frac_nao_screened: float) -> bool:
    """GATE F4–F5 (pré-reg 29): treino V2 só se ≥20% dos pontos não-screened."""
    return frac_nao_screened >= GATE_F4F5_FRAC


def _agrega(rows_validos, key_fn) -> dict:
    por = {}
    for r in rows_validos:
        t = por.setdefault(key_fn(r), {"n_census": 0, "n_exatos": 0,
                                       "n_I_nao_zero": 0, "C_H": [], "C_M": [], "I": []})
        t["n_census"] += 1
        t["n_exatos"] += bool(r["screened_exato"])
        t["n_I_nao_zero"] += r["I"] != 0
        for k in ("C_H", "C_M", "I"):
            t[k].append(r[k])
    for t in por.values():
        t["taxa_screening_exato"] = round(t["n_exatos"] / t["n_census"], 4)
    return por


def _report_census(rows: list[dict]) -> dict:
    validos = [r for r in rows if not r["error"] and r["screened_exato"] is not None]
    excluidos = {"sem_par": sum(1 for r in rows if r["error"] == "sem_par"),
                 "sem_a_prime": sum(1 for r in rows if r["error"] == "sem_a_prime"),
                 "context_overflow": sum(1 for r in rows if r["error"]
                                         and str(r["error"]).startswith("context_overflow")),
                 "outros_erros": [r["error"] for r in rows if r["error"] and
                                  r["error"] not in ("sem_par", "sem_a_prime") and
                                  not str(r["error"]).startswith("context_overflow")]}
    por_tipo = _agrega(validos, lambda r: r["tipo"])
    por_tipo_cfg = _agrega(validos, lambda r: f'{r["tipo"]}|{r["cfg"]}')
    frac = round(sum(1 for r in validos if not r["screened_exato"])
                 / len(validos), 4) if validos else None
    taxas = {t: {"n": v["n_census"], "taxa": v["taxa_screening_exato"]}
             for t, v in por_tipo.items()}
    return {"n_rows": len(rows), "n_validos": len(validos), "excluidos": excluidos,
            "por_tipo": por_tipo, "por_tipo_cfg": por_tipo_cfg,
            "global": {"frac_nao_screened": frac,
                       "gate_f4f5": gate_f4f5(frac) if frac is not None else None,
                       **avalia_desfecho(taxas)}}


# -- relatório ----------------------------------------------------------------
def relatorio():
    partes = {}
    for nome in ("base_report", "nulos_report", "screening_report", "census_report"):
        p = OUT / f"{nome}.json"
        partes[nome] = json.loads(p.read_text()) if p.exists() else None
    rel = {"pre_registro": 29, **partes}
    (OUT / "relatorio.json").write_text(json.dumps(rel, indent=2, ensure_ascii=False))
    print(json.dumps({"partes": {k: v is not None for k, v in partes.items()},
                      "desfecho": ((partes.get("census_report") or {})
                                   .get("global", {}).get("desfecho"))},
                     indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["base", "nulos", "screening", "census", "relatorio"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"base": stage_base, "nulos": stage_nulos, "screening": stage_screening,
     "census": stage_census, "relatorio": relatorio}[args.stage]()
