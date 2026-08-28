"""Análise descritiva 2.2: censo recomputado em R_eff nas células V2-4B e
Mistral-7B (generalização de experiments/releff39.py; zero rollouts novos).

λ = 0.2 (λ* registrado do pré-reg 33; Mistral herda — mesmo stack), limiar de
escala 0.10. Saída: runs/preg39/releff_cells_report.json.
"""
import json
import statistics
from pathlib import Path

from agent.loop import Episode
from trajectories.schema import load_trajectory

LAMBDA = 0.2
LIMIAR = 0.10
CELLS = {"v2_4b": Path("runs/census_v2"), "mistral": Path("runs/v2_xfam_mistral")}


def _rows(base: Path, name: str) -> list[dict]:
    p = base / f"{name}_rows.jsonl"
    return [json.loads(l) for l in open(p)] if p.exists() else []


def _replays_ordenados(base: Path, dirname: str) -> list[dict]:
    metas = []
    for p in sorted((base / dirname).glob("*.jsonl")):
        head = json.loads(open(p).readline())
        metas.append({"task_id": head["task_id"], "reward": head["final_reward"],
                      "started": head["meta"]["started_at"],
                      "prompt_tokens": head["meta"]["total_prompt_tokens"]})
    return sorted(metas, key=lambda m: m["started"])


def _base_idx(base: Path) -> dict[tuple, dict]:
    out = {}
    for r in _rows(base, "base"):
        if not r.get("trajectory_path"):
            continue
        traj = load_trajectory(r["trajectory_path"])
        pref, acc = [], 0
        for d in traj.decisions:
            pref.append(acc)
            acc += d.costs.get("prompt_tokens", 0)
        out[(r["cfg"], r["task_id"])] = {"traj": traj, "prefixo": pref,
                                         "total": acc, "reward": traj.final_reward}
    return out


def _entry(traj, index: int) -> int:
    return max(i for i in range(index + 1)
               if traj.decisions[i].decision_point in Episode.PHASES)


def _analisa(base: Path) -> dict:
    idx = _base_idx(base)
    rep = {}
    por_estagio = {}
    for estagio, dirname in (("nulos", "nulos_trajs"), ("piso", "piso_trajs"),
                             ("screening", "screening_trajs")):
        if not (base / dirname).is_dir():
            continue
        rows = [r for r in _rows(base, estagio) if r.get("reward_replay") is not None]
        replays = _replays_ordenados(base, dirname)
        assert len(rows) == len(replays), (estagio, len(rows), len(replays))
        linhas = []
        for r, m in zip(rows, replays):
            assert r["task_id"] == m["task_id"], (r, m)
            assert abs(r["reward_replay"] - m["reward"]) < 1e-9, (r, m)
            b = idx[(r["cfg"], r["task_id"])]
            if "index" in r:  # intervenção em um ponto: prefixo original + replay
                entry = _entry(b["traj"], r["index"])
                tokens_flip = b["prefixo"][entry] + m["prompt_tokens"]
            else:  # replay nulo: reexecução desde o início
                tokens_flip = m["prompt_tokens"]
            dr_eff = (m["reward"] - LAMBDA * tokens_flip / 1e5) \
                - (b["reward"] - LAMBDA * b["total"] / 1e5)
            linhas.append({"dR": r.get("dR", 0.0) or 0.0, "dR_eff": dr_eff})
        piv_r = sum(1 for l in linhas if l["dR"] != 0)
        piv_eff = sum(1 for l in linhas if abs(l["dR_eff"]) >= LIMIAR)
        identicos = all((l["dR"] != 0) == (abs(l["dR_eff"]) >= LIMIAR) for l in linhas)
        so_tokens = [abs(l["dR_eff"]) for l in linhas if l["dR"] == 0]
        por_estagio[estagio] = linhas
        rep[estagio] = {
            "n": len(linhas), "pivotais_R": piv_r, "ge_limiar_Reff": piv_eff,
            "conjuntos_identicos": identicos,
            "mediana_so_tokens": round(statistics.median(so_tokens), 4) if so_tokens else None,
            "max_so_tokens": round(max(so_tokens), 4) if so_tokens else None}
    # Análise 2.2b: cruzamentos só-tokens vs distribuição nula de |dR_eff|
    if "nulos" in por_estagio and "screening" in por_estagio:
        nulos = sorted(abs(l["dR_eff"]) for l in por_estagio["nulos"])
        n = len(nulos)
        cruz = sorted(abs(l["dR_eff"]) for l in por_estagio["screening"]
                      if l["dR"] == 0 and abs(l["dR_eff"]) >= LIMIAR)
        detal = [{"dR_eff": round(v, 4),
                  "quantil_nulo": round(sum(1 for x in nulos if x <= v) / n, 3),
                  "p_perm": round(sum(1 for x in nulos if x >= v) / n, 3)}
                 for v in cruz]
        reverso = sum(1 for l in por_estagio["screening"]
                      if l["dR"] != 0 and abs(l["dR_eff"]) < LIMIAR)
        rep["cruzamentos_2_2b"] = {
            "n_cruzamentos": len(cruz), "n_nulos": n,
            "max_nulo": round(nulos[-1], 4),
            "todos_no_suporte_nulo": all(v <= nulos[-1] for v in cruz),
            "p_perm_min": min((d["p_perm"] for d in detal), default=None),
            "reverso_pivotal_R_abaixo_limiar_Reff": reverso,
            "detalhe": detal}
    return rep


def main() -> None:
    rep = {"lambda": LAMBDA, "limiar": LIMIAR,
           "cells": {nome: _analisa(base) for nome, base in CELLS.items()}}
    Path("runs/preg39/releff_cells_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
