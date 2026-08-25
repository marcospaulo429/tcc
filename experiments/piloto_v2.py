"""Piloto V2 mini-SWE (pré-reg 28) — estágios 2 (episódios), 3 (determinismo), 4 (pivotalidade).

Uso (SEMPRE sequencial, nunca em paralelo com outro job de GPU):
  uv run python -m experiments.piloto_v2 --stage 2
  uv run python -m experiments.piloto_v2 --stage 3
  uv run python -m experiments.piloto_v2 --stage 4
  uv run python -m experiments.piloto_v2 --stage relatorio
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

import openai

from agent.harness import summarize_is_vacuous
from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from agent.loop_v2 import EpisodeV2
from environment.tasks_swe import TASKS
from experiments.common import append_row, done_keys, load_rows
from trajectories.recorder import Recorder
from trajectories.replay import build_flip_queue, replay_from
from trajectories.schema import load_trajectory

OUT = Path("runs/piloto_v2")

# janelas go/no-go do pré-reg 28
GO_SUCESSO = (0.30, 0.70)
GO_MALFORMADO = 0.15
GO_MEDIANA_S = 180.0
GO_TIPOS_PIVOTAIS = 3


def _canon(action: dict) -> dict:
    return {k: v for k, v in action.items() if k != "forced"}


def _episodio(task: dict) -> dict:
    ep = EpisodeV2(task, LLMClient(), HarnessV2(),
                   Recorder(OUT / "stage2_trajs"))
    try:
        return ep.run()
    finally:
        ep.sandbox.cleanup()


def _transcript_hash(traj) -> str:
    seq = [(d.decision_point, _canon(d.chosen_action)) for d in traj.decisions]
    ultimo = traj.decisions[-1].state_before["messages"]
    blob = json.dumps([seq, ultimo, traj.final_reward], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _trajs_stage2() -> list:
    rows = load_rows(OUT / "stage2_rows.jsonl")
    trajs = []
    for r in rows:
        if r.get("trajectory_path"):
            trajs.append(load_trajectory(r["trajectory_path"]))
    return trajs


def _max_ctx(traj) -> int:
    return max(d.state_before.get("context_tokens", 0) for d in traj.decisions)


def stage2():
    rows_path = OUT / "stage2_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("task_id",))
    for task in TASKS:
        if (task["task_id"],) in feitos:
            continue
        print(f"[stage2] {task['task_id']}", flush=True)
        try:
            r = _episodio(task)
            append_row(rows_path, {"task_id": task["task_id"], **r, "error": None})
        except Exception as exc:  # ex.: 400 por estouro de contexto — reportar, não esconder
            append_row(rows_path, {"task_id": task["task_id"], "reward": 0.0,
                                   "success": False, "trajectory_path": None,
                                   "error": f"{type(exc).__name__}: {exc}"})

    rows = load_rows(rows_path)
    trajs = _trajs_stage2()
    n_tool = sum(1 for t in trajs for d in t.decisions
                 if d.decision_point == "tool_call" and not d.chosen_action.get("forced"))
    n_retry = sum(1 for t in trajs for d in t.decisions if d.decision_point == "retry")
    sucesso = sum(1 for r in rows if r.get("reward") == 1.0) / len(rows)
    malformado = n_retry / (n_tool + n_retry) if (n_tool + n_retry) else 1.0
    mediana_s = statistics.median(r.get("wall_time_s", 0.0) for r in rows if not r["error"]) \
        if any(not r["error"] for r in rows) else float("inf")
    report = {
        "n_tasks": len(rows), "n_erros": sum(1 for r in rows if r["error"]),
        "erros": {r["task_id"]: r["error"] for r in rows if r["error"]},
        "taxa_sucesso": round(sucesso, 3),
        "reward_medio": round(sum(r.get("reward", 0.0) for r in rows) / len(rows), 3),
        "taxa_malformado": round(malformado, 4),
        "mediana_wall_s": round(mediana_s, 1),
        "max_context_tokens": max((_max_ctx(t) for t in trajs), default=0),
        "decisoes_por_tipo": _conta_tipos(trajs),
        "go": {
            "sucesso_na_janela": GO_SUCESSO[0] <= sucesso <= GO_SUCESSO[1],
            "malformado_ok": malformado < GO_MALFORMADO,
            "mediana_ok": mediana_s <= GO_MEDIANA_S,
        },
    }
    report["veredito"] = "GO" if all(report["go"].values()) else \
        ("NO-GO" if sucesso == 0.0 else "RECALIBRA")
    (OUT / "stage2_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


def _conta_tipos(trajs) -> dict:
    contagem = {}
    for t in trajs:
        for d in t.decisions:
            contagem[d.decision_point] = contagem.get(d.decision_point, 0) + 1
    return contagem


def stage3():
    trajs = _trajs_stage2()
    llm = LLMClient()

    # (a) re-execução idêntica dos 5 episódios de maior contexto
    reruns_path = OUT / "stage3_reruns.jsonl"
    feitos = done_keys(load_rows(reruns_path), ("task_id",))
    alvo_a = sorted(trajs, key=_max_ctx, reverse=True)[:5]
    por_id = {t["task_id"]: t for t in TASKS}
    for traj in alvo_a:
        if (traj.task_id,) in feitos:
            continue
        print(f"[stage3a] rerun {traj.task_id}", flush=True)
        ep = EpisodeV2(por_id[traj.task_id], llm, HarnessV2(), Recorder(OUT / "stage3_trajs"))
        try:
            r = ep.run()
        finally:
            ep.sandbox.cleanup()
        nova = load_trajectory(r["trajectory_path"])
        append_row(reruns_path, {
            "task_id": traj.task_id,
            "hash_original": _transcript_hash(traj), "hash_rerun": _transcript_hash(nova),
            "reward_original": traj.final_reward, "reward_rerun": nova.final_reward,
            "identico": _transcript_hash(traj) == _transcript_hash(nova)})

    # (b) replay nulo com fila forçada = decisões originais (sem retries; zero calls de LLM)
    nulos_path = OUT / "stage3_nulos.jsonl"
    feitos = done_keys(load_rows(nulos_path), ("task_id",))
    alvo_b = sorted(trajs, key=lambda t: len(t.decisions), reverse=True)[:5]
    for traj in alvo_b:
        if (traj.task_id,) in feitos:
            continue
        print(f"[stage3b] nulo {traj.task_id}", flush=True)
        queue = [{"point": d.decision_point, "action": _canon(d.chosen_action)}
                 for d in traj.decisions if d.decision_point != "retry"]
        rep = replay_from(traj, 0, llm, OUT / "stage3_trajs", override_actions=queue)
        append_row(nulos_path, {"task_id": traj.task_id,
                                "reward_original": traj.final_reward,
                                "reward_replay": rep["reward"],
                                "exato": rep["reward"] == traj.final_reward})

    reruns = load_rows(reruns_path)
    nulos = load_rows(nulos_path)
    report = {
        "reruns": {r["task_id"]: r["identico"] for r in reruns},
        "nulos": {r["task_id"]: r["exato"] for r in nulos},
        "go": {"reruns_identicos": all(r["identico"] for r in reruns) and len(reruns) == 5,
               "nulos_exatos": all(r["exato"] for r in nulos) and len(nulos) == 5},
    }
    report["veredito"] = "GO" if all(report["go"].values()) else "NO-GO(1 fix permitido)"
    (OUT / "stage3_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


FLIPS = {
    "context_policy": {"keep_context": "summarize_context", "summarize_context": "keep_context"},
    "observation_policy": {"full_output": "compact_output", "compact_output": "full_output"},
    "test_schedule": {"auto_test": "defer_test", "defer_test": "auto_test"},
    "retry": {"retry_once": "give_up"},
    "termination": {"continue": "terminate"},
}


def _candidatos(trajs) -> dict[str, list]:
    """Heurística declarada no pré-reg: pontos onde o braço alternativo muda o insumo."""
    cand = {tipo: [] for tipo in FLIPS}
    for traj in trajs:
        for i, d in enumerate(traj.decisions):
            p = d.decision_point
            if p not in FLIPS:
                continue
            acao = d.chosen_action["action"]
            if acao not in FLIPS[p]:
                continue
            score = d.state_before.get("context_tokens", 0)
            if p == "context_policy":
                # adendo 28b: prioriza keep→summarize (direção do Teste 1 V1);
                # summarize vácuo não muda o contexto → candidato inútil, filtrado
                if acao == "keep_context":
                    if summarize_is_vacuous(d.state_before["messages"], keep_last=6,
                                            task_chars=0):
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
            cand[p].append((score, traj, i, {"action": FLIPS[p][acao]}))
    for p in cand:  # até 5 por tipo, no máx. 2 por task (diversidade)
        cand[p].sort(key=lambda c: (-c[0], c[1].task_id, c[2]))
        sel, por_task = [], {}
        for c in cand[p]:
            tid = c[1].task_id
            if por_task.get(tid, 0) >= 2:
                continue
            sel.append(c)
            por_task[tid] = por_task.get(tid, 0) + 1
            if len(sel) == 5:
                break
        cand[p] = sel
    return cand


def stage4():
    trajs = _trajs_stage2()
    llm = LLMClient()
    rows_path = OUT / "stage4_rows.jsonl"
    feitos = done_keys(load_rows(rows_path), ("tipo", "task_id", "index"))
    for tipo, lista in _candidatos(trajs).items():
        for _, traj, i, flip in lista:
            if (tipo, traj.task_id, i) in feitos:
                continue
            print(f"[stage4] {tipo} {traj.task_id} idx{i} -> {flip['action']}", flush=True)
            try:
                entry, queue = build_flip_queue(traj, i, flip)
                rep = replay_from(traj, entry, llm, OUT / "stage4_trajs",
                                  override_actions=queue)
                append_row(rows_path, {
                    "tipo": tipo, "task_id": traj.task_id, "index": i,
                    "flip": flip["action"], "reward_original": traj.final_reward,
                    "reward_replay": rep["reward"],
                    "flipou": rep["reward"] != traj.final_reward, "error": None})
            except ValueError as exc:  # span com retry — pulado e reportado
                append_row(rows_path, {"tipo": tipo, "task_id": traj.task_id, "index": i,
                                       "flip": flip["action"], "flipou": None,
                                       "error": str(exc)})
            except openai.BadRequestError as exc:
                # overflow de contexto sob o flip (ex.: keep forçado onde o original
                # sumarizou) — consequência causal do flip, mas sem R mensurável no
                # serving de 8k: reportado à parte, não conta como flip.
                append_row(rows_path, {"tipo": tipo, "task_id": traj.task_id, "index": i,
                                       "flip": flip["action"], "flipou": None,
                                       "error": f"context_overflow: {exc}"[:200]})

    rows = load_rows(rows_path)
    por_tipo = {}
    for r in rows:
        t = por_tipo.setdefault(r["tipo"], {"pontos": 0, "flips": 0, "pulados": 0, "dRs": []})
        if r["error"]:
            t["pulados"] += 1
            continue
        t["pontos"] += 1
        t["flips"] += bool(r["flipou"])
        t["dRs"].append(round(r["reward_replay"] - r["reward_original"], 4))
    tipos_com_flip = sum(1 for t in por_tipo.values() if t["flips"] > 0)
    report = {"por_tipo": por_tipo, "tipos_com_flip": tipos_com_flip,
              "go": {"tipos_pivotais": tipos_com_flip >= GO_TIPOS_PIVOTAIS},
              "nota": "flip de terminate precoce é mecanicamente esperado (pré-reg 28)"}
    report["veredito"] = "GO" if tipos_com_flip >= GO_TIPOS_PIVOTAIS else "RECALIBRA/NO-GO"
    (OUT / "stage4_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


def relatorio():
    partes = {}
    for nome in ("stage2_report", "stage3_report", "stage4_report"):
        p = OUT / f"{nome}.json"
        partes[nome] = json.loads(p.read_text()) if p.exists() else None
    vereditos = [v.get("veredito") for v in partes.values() if v]
    final = "GO" if all(v == "GO" for v in vereditos) and len(vereditos) == 3 else \
        ("NO-GO" if any(v and v.startswith("NO-GO") for v in vereditos) else "RECALIBRA")
    rel = {"pre_registro": 28, "estagio1_pool": {"aprovadas": len(TASKS), "reprovadas": 0},
           **partes, "veredito_final": final}
    (OUT / "relatorio.json").write_text(json.dumps(rel, indent=2, ensure_ascii=False))
    print(json.dumps({"veredito_final": final,
                      "vereditos": {k: (v or {}).get("veredito") for k, v in partes.items()}},
                     indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["2", "3", "4", "relatorio"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"2": stage2, "3": stage3, "4": stage4, "relatorio": relatorio}[args.stage]()
