"""Estágio A do pré-reg 32 — seleção analítica de λ* e pool de treino V2.

Regra pré-registrada (DIARIO 2026-08-26, pré-reg 32, commitada ANTES de rodar):
- Insumo: calibrate_report.json (3 políticas fixas × 60 tasks, R e prompt_tokens
  por task → R_eff(λ) recomputável para qualquer λ sem GPU).
- Grade λ ∈ {1, 2, 5, 10, 25}. Task ELEGÍVEL sob λ: default (thr4500) domina
  ESTRITAMENTE keep_always E summarize_always em R_eff(λ).
- λ* = λ que maximiza elegíveis (empate → menor λ). Pool = elegíveis por margem
  mínima de dominância desc, cap 16, mínimo 10 (senão ABORTA — reportável).
- Ranks pares = treino, ímpares = held-out.

Saída: pool.json {lambda_grid, lambda_star, viable, n, ranked, train, heldout}.
"""
import argparse
import json
from pathlib import Path

LAMBDA_GRID = (1.0, 2.0, 5.0, 10.0, 25.0)
CAP = 16
MIN_POOL = 10


def r_eff(R: float, tokens: int, lam: float) -> float:
    return R - lam * (tokens / 100000.0)


def select(report: dict) -> dict:
    by_policy = {name: {t["task_id"]: t for t in p["per_task"]}
                 for name, p in report["policies"].items()}
    task_ids = sorted(by_policy["default"])
    eligible_by_lambda: dict[float, list[tuple[str, float]]] = {}
    for lam in LAMBDA_GRID:
        rows = []
        for tid in task_ids:
            reffs = {name: r_eff(by_policy[name][tid]["R"],
                                 by_policy[name][tid]["prompt_tokens_total"], lam)
                     for name in ("default", "keep_always", "summarize_always")}
            margin = min(reffs["default"] - reffs["keep_always"],
                         reffs["default"] - reffs["summarize_always"])
            if margin > 0:
                rows.append((tid, margin))
        eligible_by_lambda[lam] = rows
    lambda_star = max(LAMBDA_GRID,
                      key=lambda lam: (len(eligible_by_lambda[lam]), -lam))
    ranked = sorted(eligible_by_lambda[lambda_star],
                    key=lambda r: (-r[1], r[0]))[:CAP]
    result = {"lambda_grid": list(LAMBDA_GRID), "lambda_star": lambda_star,
              "viable": {str(lam): len(v) for lam, v in eligible_by_lambda.items()},
              "n": len(ranked),
              "ranked": [{"task_id": t, "min_margin": round(m, 6)} for t, m in ranked],
              "train": [t for i, (t, _) in enumerate(ranked) if i % 2 == 0],
              "heldout": [t for i, (t, _) in enumerate(ranked) if i % 2 == 1]}
    if len(ranked) < MIN_POOL:
        result["aborted"] = True
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="pré-reg 32 estágio A: λ* + pool")
    ap.add_argument("--report", default="runs/v2_train/calibrate/calibrate_report.json")
    ap.add_argument("--out", default="runs/v2_train/pool.json")
    args = ap.parse_args()
    report = json.loads(Path(args.report).read_text())
    result = select(report)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("lambda_star", "viable", "n")} |
                     {"aborted": result.get("aborted", False)}, indent=2))
    if result.get("aborted"):
        raise SystemExit("ABORTA (pré-reg 32): elegíveis < 10 sob todos os λ — "
                         "landscape sem sala p/ política treinável; reportável.")


if __name__ == "__main__":
    main()
