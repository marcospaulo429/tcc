#!/usr/bin/env bash
# Grid da Fase A (PLANO-EXECUCAO.md): por config, cadeia teste0 -> teste1 -> teste2 -> teste3.
# Sequencial DE PROPÓSITO (premissa de identificação do piso; pré-registro g).
# Uso: nohup bash experiments/grid_faseA.sh > runs/grid_faseA.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."

CONFIGS="${CONFIGS:-600 450 900}"   # thr600 primeiro: regime conhecido, decide GATE 1
TASKS_MODULE="environment.tasks_all"

for THR in $CONFIGS; do
  TAG="g${THR}"
  echo "=== CONFIG threshold=${THR} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module "$TASKS_MODULE" --threshold "$THR" --max-turns 12 \
    --points 3 --reps 3 || { echo "FALHA teste0 ${TAG}"; exit 1; }
  uv run python -m experiments.teste1 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste1_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || { echo "FALHA teste1 ${TAG}"; exit 1; }
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || { echo "FALHA teste2 ${TAG}"; exit 1; }
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || { echo "FALHA teste3 ${TAG}"; exit 1; }
  echo "=== CONFIG ${THR} concluída ($(date -Is)) ==="
done
echo "GRID COMPLETO ($(date -Is))"
