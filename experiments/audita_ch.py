"""Auditoria do CRÍTICO 1 (revisor, 2026-08-22): o colapso do braço ch é genuíno?

O C_H logado no treino compara r_eff da trajetória ORIGINAL (continuação estocástica
da política de coleta) com r_eff do replay do flip (continuação greedy). Sob λ=25
esse mismatch pode gerar crédito positivo espúrio para summarize.

Correção testada aqui: C_H_corrigido = r_eff(replay greedy com a ação ORIGINAL
forçada) − r_eff(replay greedy com o flip forçado) — mesmo estimador nos dois lados.
Se a fração de créditos positivos despencar vs a logada (264/403), o colapso é
artefato; se persistir, o claim sobrevive fortalecido.

Amostra: até N pontos estratificados por sinal do crédito logado (pos/neg/zero).
θ usado nos replays = θ PRÉ-update do episódio (linha anterior do train_log).

Uso: uv run python -m experiments.audita_ch --run-dir runs/c1_ch_s1 --n 60
     [--dry-run]  (só valida o mapeamento episódio→trajetória, sem LLM)
"""
import argparse
import json
import random
from pathlib import Path

from rl.policy import N_FEATURES, LogisticContextPolicy
from rl.train_c1 import CountingLLM, _prompt_tokens, _replay_with_policy, r_eff
from trajectories.schema import load_trajectory

LAMBDA = 25.0
SEED = 20260821


def map_episodes(run_dir: Path) -> list[dict]:
    """Join train_log ↔ arquivos de trajetória por (ordem mtime, task_id, R)."""
    rows = [json.loads(l) for l in open(run_dir / "train_log.jsonl", encoding="utf-8")]
    files = sorted((run_dir / "episodes").glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    assert len(files) == len(rows), f"{len(files)} arquivos vs {len(rows)} episódios"
    out = []
    for i, (row, f) in enumerate(zip(rows, files)):
        traj = load_trajectory(str(f))
        assert traj.task_id == row["task_id"], f"ep{i}: {traj.task_id} != {row['task_id']}"
        assert abs(traj.final_reward - row["R"]) < 1e-9, f"ep{i}: reward não bate"
        theta_pre = rows[i - 1]["theta"] if i > 0 else [0.0] * N_FEATURES
        out.append({"row": row, "path": str(f), "theta_pre": theta_pre})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="runs/c1_ch_s1")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--out", default="runs/audita_ch.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    eps = map_episodes(run_dir)

    points = []  # (ep, credit_dict)
    for ep in eps:
        for c in ep["row"]["credits"]:
            points.append((ep, c))
    pos = [p for p in points if p[1]["credit"] > 0]
    neg = [p for p in points if p[1]["credit"] < 0]
    zer = [p for p in points if p[1]["credit"] == 0]
    rng = random.Random(SEED)
    n_pos, n_neg, n_zer = (min(len(pos), args.n // 2), min(len(neg), args.n // 3),
                           min(len(zer), args.n - args.n // 2 - args.n // 3))
    sample = (rng.sample(pos, n_pos) + rng.sample(neg, n_neg) + rng.sample(zer, n_zer))
    print(f"mapeados {len(eps)} episódios, {len(points)} créditos "
          f"({len(pos)} pos / {len(neg)} neg / {len(zer)} zero); amostra {len(sample)}")
    if args.dry_run:
        return

    from agent.llm import LLMClient
    llm = CountingLLM(LLMClient())
    results = []
    for k, (ep, c) in enumerate(sample):
        traj = load_trajectory(ep["path"])
        d = traj.decisions[c["index"]]
        orig = d.chosen_action["action"]
        flip = "keep_context" if orig == "summarize_context" else "summarize_context"
        policy = LogisticContextPolicy(theta=ep["theta_pre"], greedy=True)
        prefix = _prompt_tokens(traj.decisions[:c["index"]])

        def _reff(action: str) -> float:
            res, rtok = _replay_with_policy(
                traj, c["index"], llm, policy, run_dir / "audit_replays",
                [{"point": "context_policy", "action": {"action": action}}])
            return r_eff(res["reward"], prefix + rtok, LAMBDA)

        c_corr = _reff(orig) - _reff(flip)
        results.append({"task_id": traj.task_id, "index": c["index"],
                        "action_orig": orig, "credit_logged": c["credit"],
                        "credit_corrigido": c_corr})
        print(f"[{k+1}/{len(sample)}] {traj.task_id} idx={c['index']} {orig}: "
              f"logado {c['credit']:+.3f} → corrigido {c_corr:+.3f}")

    def frac_pos(key):
        return sum(1 for r in results if r[key] > 0) / len(results)
    summary = {"n": len(results), "llm_calls": llm.call_count,
               "frac_pos_logged": frac_pos("credit_logged"),
               "frac_pos_corrigido": frac_pos("credit_corrigido"),
               "frac_pos_logged_summarize": (
                   lambda s: sum(1 for r in s if r["credit_logged"] > 0) / max(len(s), 1)
               )([r for r in results if r["action_orig"] == "summarize_context"]),
               "frac_pos_corrigido_summarize": (
                   lambda s: sum(1 for r in s if r["credit_corrigido"] > 0) / max(len(s), 1)
               )([r for r in results if r["action_orig"] == "summarize_context"]),
               "results": results}
    Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
