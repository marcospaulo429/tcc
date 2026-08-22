#!/usr/bin/env bash
# C1: 4 braços × 3 seeds, sequencial (premissa de identificação), seed-major
# (comparação completa dos 4 braços disponível já após a 1ª seed).
# λ=25 fixado pela calibração analítica (runs/c1_calibrate, 2026-08-22): menor λ
# redondo em que thr600 > keep_always com margem (>17.2) e thr600 > summarize_always.
set -u
cd "$(dirname "$0")/.."
LAMBDA=25
BUDGET=2000
for SEED in 1 2 3; do
  for ARM in outcome ch chm_cm zero; do
    OUT="runs/c1_${ARM}_s${SEED}"
    if [ -f "$OUT/summary.json" ]; then
      echo "=== pulando $ARM s$SEED (summary existe) ==="
      continue
    fi
    echo "=== C1 arm=$ARM seed=$SEED λ=$LAMBDA budget=$BUDGET ($(date -Is)) ==="
    uv run python -m rl.train_c1 --arm "$ARM" --tasks-module environment.tasks_all \
      --budget-calls "$BUDGET" --seed "$SEED" --out "$OUT" --lambda-cost "$LAMBDA"
    echo "=== fim $ARM s$SEED rc=$? ($(date -Is)) ==="
  done
done
echo "=== C1 CHAIN COMPLETA ($(date -Is)) ==="
