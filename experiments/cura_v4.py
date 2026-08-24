"""Curação do pool v4 (pré-registro 17): mantém tasks com reward baseline do
8B em (0.05, 0.95); exige ≥12 sobreviventes. Constrói runs/teste0_v4cur_<tag>/
com os baselines filtrados + summary.json do run completo (piso conservador:
nulos do pool inteiro).

Uso: uv run python -m experiments.cura_v4 --from-tag v4_g600 --apply-tags v4_g600 v4_mt6
"""
import argparse
import json
import shutil
from pathlib import Path

from trajectories.schema import load_trajectory

LO, HI = 0.05, 0.95
MIN_TASKS = 12


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-tag", required=True, help="tag cujo baseline define a curação")
    ap.add_argument("--apply-tags", nargs="+", required=True)
    args = ap.parse_args()

    rewards: dict[str, float] = {}
    for p in sorted(Path(f"runs/teste0_{args.from_tag}/baseline").glob("*.jsonl")):
        t = load_trajectory(p)
        rewards[t.task_id] = t.final_reward
    survivors = sorted(tid for tid, r in rewards.items() if LO < r < HI)
    result = {"criterion": f"({LO}, {HI})", "from_tag": args.from_tag,
              "rewards": rewards, "survivors": survivors,
              "n_survivors": len(survivors), "curation_ok": len(survivors) >= MIN_TASKS}
    Path("runs/v4_curation.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("survivors", "n_survivors", "curation_ok")}, indent=1))
    if not result["curation_ok"]:
        raise SystemExit(f"CURADORIA FALHOU: {len(survivors)} < {MIN_TASKS} (pré-registro 17)")

    for tag in args.apply_tags:
        src = Path(f"runs/teste0_{tag}")
        dst = Path(f"runs/teste0_v4cur_{tag.removeprefix('v4_')}")
        (dst / "baseline").mkdir(parents=True, exist_ok=True)
        n = 0
        for p in sorted((src / "baseline").glob("*.jsonl")):
            if load_trajectory(p).task_id in survivors:
                shutil.copy2(p, dst / "baseline" / p.name)
                n += 1
        shutil.copy2(src / "summary.json", dst / "summary.json")
        print(f"{dst}: {n} baselines")


if __name__ == "__main__":
    main()
