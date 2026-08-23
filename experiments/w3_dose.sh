#!/usr/bin/env bash
# W3 dose-resposta (pré-registro 13): pipeline do GATE-1b com max_turns ∈ {4, 8}.
# Compõe curva com mt6 e g600 (mt12) já medidos. thr600, 30 tasks, sequencial.
set -uo pipefail
cd "$(dirname "$0")/.."
for MT in 4 8; do
  TAG="mt${MT}"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== W3 ${TAG} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module environment.tasks_all --threshold 600 --max-turns "$MT" \
    --points 3 --reps 3 || echo "FALHA teste0 ${TAG}"
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 ${TAG}"
done
echo "=== W3 DOSE-RESPOSTA COMPLETO ($(date -Is)) ==="
