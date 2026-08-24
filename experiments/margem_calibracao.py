"""Regenera a margem thr600−keep da calibração (λ=25) e FALHA em caso de drift.

O artefato runs/c1_calibrate/calibrate_report.json guarda R e prompt_tokens_total
brutos por task (λ=1); a margem publicada usa R_eff(λ=25) = R − 25·tokens·1e−5.
Bootstrap pareado por task (10k, seed 20260821), CI 95% por percentis.

Valores publicados (paper, §treino): média +0.024, CI95 [−0.029, +0.079],
P(diff≤0) = 0.19 — não significativa; o teto keep-always era semi-previsível.
"""
import json
import random
import sys
from pathlib import Path

REPORT = (Path(__file__).resolve().parent.parent
          / "runs" / "c1_calibrate" / "calibrate_report.json")
LAMBDA = 25.0
SEED = 20260821
N_BOOT = 10000
PAPER = {"mean": 0.024, "ci_lo": -0.029, "ci_hi": 0.079, "p_le0": 0.19}


def main() -> int:
    d = json.loads(REPORT.read_text())

    def eff(policy):
        return {t["task_id"]: t["R"] - LAMBDA * t["prompt_tokens_total"] / 100000
                for t in d["policies"][policy]["per_task"]}

    keep, thr = eff("keep_always"), eff("thr600")
    assert keep.keys() == thr.keys()
    diffs = [thr[t] - keep[t] for t in sorted(keep)]
    mean = sum(diffs) / len(diffs)
    rng = random.Random(SEED)
    boots = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs)
                   for _ in range(N_BOOT))
    ci = [boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT)]]
    p_le0 = sum(b <= 0 for b in boots) / N_BOOT
    got = {"mean": round(mean, 3), "ci_lo": round(ci[0], 3),
           "ci_hi": round(ci[1], 3), "p_le0": round(p_le0, 2)}
    print(f"n_tasks={len(diffs)} media={mean:+.4f} "
          f"CI95=[{ci[0]:+.4f}, {ci[1]:+.4f}] P(<=0)={p_le0:.3f}")
    print("RECONCILIADO" if got == PAPER else f"DRIFT: paper={PAPER} got={got}")
    return 0 if got == PAPER else 1


if __name__ == "__main__":
    sys.exit(main())
