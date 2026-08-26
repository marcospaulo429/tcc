#!/usr/bin/env bash
# Pré-registro 37: censo exaustivo in-window no MBPP+ (4B, g600 + mt6).
# Baselines congelados de teste0_mbpp_*; filtro por symlink; max-per-traj 99.
set -uo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python - <<'EOF'
import json, os
from pathlib import Path
INW = {"g600": {"mbpp_111","mbpp_276","mbpp_410","mbpp_420","mbpp_606",
                "mbpp_620","mbpp_7","mbpp_769","mbpp_792","mbpp_809"},
       "mt6": {"mbpp_111","mbpp_276","mbpp_410","mbpp_420","mbpp_563","mbpp_606",
               "mbpp_620","mbpp_7","mbpp_769","mbpp_792","mbpp_809"}}
for cfg, tasks in INW.items():
    src = Path(f"runs/teste0_mbpp_{cfg}/baseline")
    dst = Path(f"runs/preg37_{cfg}/baseline")
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob("*.jsonl")):
        first = json.loads(f.open().readline())
        if first.get("task", first).get("task_id") in tasks or first.get("task_id") in tasks:
            link = dst / f.name
            if not link.exists():
                link.symlink_to(f.resolve())
            n += 1
    print(f"preg37 {cfg}: {n} trajetórias in-window linkadas")
EOF

for CFG in g600 mt6; do
  echo "=== preg37 ${CFG} ($(date -Is)) ==="
  uv run python -m experiments.teste2 --baseline "runs/preg37_${CFG}/baseline" \
    --out "runs/preg37_teste2_${CFG}" --floor-from "runs/teste0_mbpp_${CFG}/summary.json" \
    --max-per-traj 99 || echo "FALHA teste2 ${CFG}"
  uv run python -m experiments.teste3 --baseline "runs/preg37_${CFG}/baseline" \
    --out "runs/preg37_teste3_${CFG}" --floor-from "runs/teste0_mbpp_${CFG}/summary.json" \
    --samples-from "runs/preg37_teste2_${CFG}/samples.jsonl" \
    --max-per-traj 99 || echo "FALHA teste3 ${CFG}"
done
echo "=== PREG37 COMPLETO ($(date -Is)) ==="
