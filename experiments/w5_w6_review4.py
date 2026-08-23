"""Análises W5/W6 do review 4 (CPU, dados existentes).

W5: contraste folga vs pressão condicionado a não-saturação, com inferência
    clusterizada por task (permutação sign-flip pareada + permutação de labels).
W6: dose de episódios por braço no C1b + visitação de estados (context tokens
    em decisões context_policy) por braço — evidência direta da starvação.

Uso: uv run python experiments/w5_w6_review4.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "experiments" / "results" / "2026-08-23_w5_w6_review4.json"

SLACK = ["teste3_g450", "teste3_g600", "teste3_g900"]
PRESSURE = ["teste3_mt4", "teste3_mt6", "teste3_mt8"]
EPS = 1e-9


def load_points(tag: str) -> list[dict]:
    rows = []
    for line in (RUNS / tag / "cf_results.jsonl").open():
        d = json.loads(line)
        if d.get("final_timed_out"):
            continue
        d["break_"] = abs(d["C_HM"] - d["C_M"]) > EPS
        rows.append(d)
    return rows


def w5() -> dict:
    per_task: dict[str, dict[str, list[bool]]] = defaultdict(lambda: {"slack": [], "pressure": []})
    for tag in SLACK + PRESSURE:
        regime = "slack" if tag in SLACK else "pressure"
        for d in load_points(tag):
            if d.get("saturated"):
                continue
            per_task[d["task_id"]][regime].append(d["break_"])

    # pareado: tasks com pontos não-saturados nos dois regimes
    paired = {
        t: (sum(v["pressure"]) / len(v["pressure"]) - sum(v["slack"]) / len(v["slack"]))
        for t, v in per_task.items()
        if v["slack"] and v["pressure"]
    }
    obs = sum(paired.values()) / len(paired)
    rng = random.Random(20260823)
    n_perm = 100_000
    count = 0
    diffs = list(paired.values())
    for _ in range(n_perm):
        s = sum(d * rng.choice((1, -1)) for d in diffs) / len(diffs)
        if s >= obs - EPS:
            count += 1
    p_signflip = count / n_perm

    # não-pareado: permutar rótulo de regime entre clusters task×regime
    clusters = []
    for t, v in per_task.items():
        for reg in ("slack", "pressure"):
            if v[reg]:
                clusters.append((reg, sum(v[reg]) / len(v[reg])))
    n_press = sum(1 for r, _ in clusters if r == "pressure")
    rates = [r for _, r in clusters]
    obs_np = (
        sum(r for reg, r in clusters if reg == "pressure") / n_press
        - sum(r for reg, r in clusters if reg == "slack") / (len(clusters) - n_press)
    )
    count = 0
    for _ in range(n_perm):
        rng.shuffle(rates)
        d = sum(rates[:n_press]) / n_press - sum(rates[n_press:]) / (len(rates) - n_press)
        if d >= obs_np - EPS:
            count += 1
    p_label = count / n_perm

    return {
        "n_tasks_pareadas": len(paired),
        "diffs_pareados": {t: round(v, 3) for t, v in sorted(paired.items())},
        "estat_obs_pareada": round(obs, 4),
        "p_signflip_pareado": p_signflip,
        "estat_obs_nao_pareada": round(obs_np, 4),
        "n_clusters": len(clusters),
        "p_permutacao_labels": p_label,
    }


def w6() -> dict:
    arms = ["outcome", "ch", "chm_cm", "zero"]
    out: dict[str, dict] = {}
    for arm in arms:
        eps_total = 0
        visits = []
        for seed in (1, 2, 3):
            d = RUNS / f"c1b_{arm}_s{seed}"
            eps_total += sum(1 for _ in (d / "train_log.jsonl").open())
            for f in (d / "episodes").glob("*.jsonl"):
                for line in f.open():
                    r = json.loads(line)
                    if r.get("kind") == "decision" and r.get("decision_type") == "harness" \
                            and r.get("decision_point") == "context_policy":
                        ctx = (r.get("state_before") or {}).get("context_tokens")
                        if ctx is None:
                            ctx = r.get("context_tokens_before")
                        if ctx is not None:
                            visits.append(ctx)
        visits.sort()
        n = len(visits)
        frac_informative = sum(1 for v in visits if v >= 2500) / n if n else None
        out[arm] = {
            "episodios_total_3seeds": eps_total,
            "decisoes_context_policy": n,
            "ctx_tokens_p50": visits[n // 2] if n else None,
            "ctx_tokens_p90": visits[int(n * 0.9)] if n else None,
            "ctx_tokens_max": visits[-1] if n else None,
            "frac_estados_>=2500_tokens": round(frac_informative, 4) if n else None,
        }
    return out


if __name__ == "__main__":
    res = {"data": "2026-08-23", "analise": "W5/W6 do review 4", "W5": w5(), "W6": w6()}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))
