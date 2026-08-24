"""Curação D4b (pré-registro 18): união v4 ∪ v5, janela (0.05, 0.95) sobre os
baselines 8B thr600 mt12 (v4 reutilizado, v5 fresco); exige ≥12 sobreviventes.
Constrói runs/teste0_v5cur_<cfg>/ com baselines curados das duas fontes e
summary.json com noise_floor = max dos pisos das fontes (conservador).

Uso: uv run python -m experiments.cura_v5
"""
import json
import shutil
from pathlib import Path

from trajectories.schema import load_trajectory

LO, HI = 0.05, 0.95
MIN_TASKS = 12
CONFIGS = {"g600": ["v4_g600", "v5_g600"], "mt6": ["v4_mt6", "v5_mt6"]}


def task_rewards(tag: str) -> dict[str, float]:
    return {t.task_id: t.final_reward
            for t in (load_trajectory(p)
                      for p in sorted(Path(f"runs/teste0_{tag}/baseline").glob("*.jsonl")))}


def main():
    rewards = task_rewards("v4_g600") | task_rewards("v5_g600")
    survivors = sorted(tid for tid, r in rewards.items() if LO < r < HI)
    result = {"criterion": f"({LO}, {HI})", "sources": CONFIGS["g600"],
              "rewards": rewards, "survivors": survivors,
              "n_survivors": len(survivors), "curation_ok": len(survivors) >= MIN_TASKS}
    Path("runs/v5_curation.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("survivors", "n_survivors", "curation_ok")}, indent=1))
    if not result["curation_ok"]:
        raise SystemExit(f"CURADORIA D4b FALHOU: {len(survivors)} < {MIN_TASKS} (pré-registro 18)")

    for cfg, tags in CONFIGS.items():
        dst = Path(f"runs/teste0_v5cur_{cfg}")
        (dst / "baseline").mkdir(parents=True, exist_ok=True)
        n, floors = 0, []
        for tag in tags:
            src = Path(f"runs/teste0_{tag}")
            floors.append(json.loads((src / "summary.json").read_text())["noise_floor"])
            for p in sorted((src / "baseline").glob("*.jsonl")):
                if load_trajectory(p).task_id in survivors:
                    shutil.copy2(p, dst / "baseline" / p.name)
                    n += 1
        (dst / "summary.json").write_text(json.dumps(
            {"noise_floor": max(floors), "source_floors": dict(zip(tags, floors)),
             "note": "união curada D4b; piso = max das fontes"}, indent=1))
        print(f"{dst}: {n} baselines, piso={max(floors)}")


if __name__ == "__main__":
    main()
