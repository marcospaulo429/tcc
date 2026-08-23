#!/usr/bin/env bash
# C1b (pré-registro 12): 4 braços × 3 seeds, SOMENTE otimização muda vs C1:
# centering fixo a priori + lr 0.1 + clip 1.0 (--c1b). λ=25, budget 2000, split idêntico.
set -u
cd "$(dirname "$0")/.."
for SEED in 1 2 3; do
  for ARM in outcome ch chm_cm zero; do
    OUT="runs/c1b_${ARM}_s${SEED}"
    if [ -f "$OUT/summary.json" ]; then echo "=== pula $ARM s$SEED (existe) ==="; continue; fi
    echo "=== C1b arm=$ARM seed=$SEED λ=25 budget=2000 ($(date -Is)) ==="
    uv run python -m rl.train_c1 --arm "$ARM" --seed "$SEED" --out "$OUT" \
      --lambda-cost 25 --budget-calls 2000 --c1b
    echo "=== fim $ARM s$SEED rc=$? ($(date -Is)) ==="
  done
done
echo "=== C1B CHAIN COMPLETA ($(date -Is)) ==="
