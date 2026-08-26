"""Avalia o oráculo condicional (keep se n_writes==0, senão summarize) no pool 35.

Piloto exploratório pré-registro do pré-reg 35: mede a margem do alvo condicional
sobre as políticas fixas calibradas em runs/v2_land35d/calibrate_report.json.
θ=[40,0,0,0,120] com CENTER_V2 ⇒ logit −20 (keep) com n_writes=0 e +20 (summarize)
com n_writes≥1 — determinístico sob greedy.
"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rl.policy_v2 import CENTER_V2  # noqa: E402
from rl.train_v2 import evaluate  # noqa: E402

THETA_ORACULO = [40.0, 0.0, 0.0, 0.0, 120.0]
HARNESS_KW = {"summarize_threshold_tokens": 4500, "max_turns": 25, "keep_last": 6}

def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/v2_land35d")
    pool = json.loads((out / "all24.json").read_text())
    by_id = {t["task_id"]: t
             for t in importlib.import_module("environment.tasks_swe35").TASKS}
    tasks = [by_id[tid] for tid in pool["train"]]
    from agent.llm import LLMClient
    llm = LLMClient()
    rep = evaluate(tasks, llm, THETA_ORACULO, seed=7, out_dir=out / "oraculo",
                   lambda_cost=1.0, center=CENTER_V2, harness_kw=HARNESS_KW)
    (out / "oraculo_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("mean_R", "mean_R_eff")}, indent=2))

if __name__ == "__main__":
    main()
