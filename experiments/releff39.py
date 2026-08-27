"""Análise descritiva pós-desfecho 39 (não-decisional, declarada no diário):
pivotalidade do censo 39 recomputada em R_eff(λ*=0.1) sobre os 92 flips pagos.

Contabilidade (espelho do pré-reg 31): R_eff(ramo) = R − λ·prompt_tokens/1e5;
prompt_tokens do ramo flipado = Σ prompt_tokens das decisões ORIGINAIS [0:entry]
+ total_prompt_tokens do replay (entry = último ponto canônico ≤ index).
Zero rollouts novos. Saída: runs/preg39/releff_report.json.
"""
import json
import statistics
from pathlib import Path

from agent.loop import Episode
from trajectories.schema import load_trajectory

OUT = Path("runs/preg39/census")
LAMBDA = 0.1
MARGEM_GATE1 = 0.166


def _rows(name: str) -> list[dict]:
    return [json.loads(l) for l in open(OUT / f"{name}_rows.jsonl")]


def _replays_ordenados(dirname: str) -> list[dict]:
    """Trajetórias de replay em ordem de execução (started_at)."""
    metas = []
    for p in sorted((OUT / dirname).glob("*.jsonl")):
        head = json.loads(open(p).readline())
        metas.append({"path": p, "task_id": head["task_id"],
                      "reward": head["final_reward"],
                      "started": head["meta"]["started_at"],
                      "prompt_tokens": head["meta"]["total_prompt_tokens"]})
    return sorted(metas, key=lambda m: m["started"])


def _base_por_task() -> dict[str, dict]:
    out = {}
    for r in _rows("base"):
        if not r.get("trajectory_path"):
            continue
        traj = load_trajectory(r["trajectory_path"])
        pref = []
        acc = 0
        for d in traj.decisions:
            pref.append(acc)
            acc += d.costs.get("prompt_tokens", 0)
        out[r["task_id"]] = {"traj": traj, "prefixo": pref, "total": acc,
                             "reward": traj.final_reward}
    return out


def _entry(traj, index: int) -> int:
    return max(i for i in range(index + 1)
               if traj.decisions[i].decision_point in Episode.PHASES)


def _pareia(rows: list[dict], replays: list[dict]) -> list[tuple[dict, dict]]:
    """Rows executadas (sem erro) casam 1:1 com replays em ordem de execução."""
    exec_rows = [r for r in rows if r.get("error") is None]
    assert len(exec_rows) == len(replays), (len(exec_rows), len(replays))
    pares = []
    for r, m in zip(exec_rows, replays):
        assert r["task_id"] == m["task_id"], (r, m)
        assert abs(r["reward_replay"] - m["reward"]) < 1e-9, (r, m)
        pares.append((r, m))
    return pares


def main() -> None:
    base = _base_por_task()
    resultado = {}
    for estagio, dirname in (("piso", "piso_trajs"), ("screening", "screening_trajs")):
        pares = _pareia(_rows(estagio), _replays_ordenados(dirname))
        linhas = []
        for r, m in pares:
            b = base[r["task_id"]]
            entry = _entry(b["traj"], r["index"]) if "index" in r else r.get("index", 0)
            tokens_flip = b["prefixo"][entry] + m["prompt_tokens"]
            reff_flip = m["reward"] - LAMBDA * tokens_flip / 1e5
            reff_orig = b["reward"] - LAMBDA * b["total"] / 1e5
            linhas.append({**{k: r.get(k) for k in ("task_id", "index", "tipo", "flip")},
                           "dR": r.get("dR"),
                           "dR_eff": round(reff_flip - reff_orig, 6),
                           "tokens_orig": b["total"], "tokens_flip": tokens_flip})
        resultado[estagio] = linhas

    rep = {"lambda": LAMBDA, "margem_gate1": MARGEM_GATE1, "estagios": {}}
    for estagio, linhas in resultado.items():
        por_tipo = {}
        for l in linhas:
            t = l.get("tipo") or "nulo"
            por_tipo.setdefault(t, []).append(l)
        rep["estagios"][estagio] = {
            tipo: {
                "n": len(ls),
                "n_dR_nao_zero": sum(1 for l in ls if l["dR"] not in (0, 0.0, None)),
                "n_dReff_nao_zero": sum(1 for l in ls if l["dR_eff"] != 0),
                "mediana_abs_dReff": round(statistics.median(abs(l["dR_eff"]) for l in ls), 4),
                "max_abs_dReff": round(max(abs(l["dR_eff"]) for l in ls), 4),
                "n_abs_dReff_ge_margem": sum(1 for l in ls if abs(l["dR_eff"]) >= MARGEM_GATE1),
            } for tipo, ls in sorted(por_tipo.items())}
    out_path = Path("runs/preg39/releff_report.json")
    out_path.write_text(json.dumps(rep, indent=1))
    (Path("runs/preg39/releff_rows.jsonl")).write_text(
        "\n".join(json.dumps(l) for e in resultado.values() for l in e) + "\n")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
