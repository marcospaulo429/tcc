#!/usr/bin/env bash
# Pós-grid: espera o grid_faseA terminar, roda GATE-1b (pressão de orçamento,
# max_turns 6), consolida o dataset e roda o critic. Sequencial (premissa do piso).
# Uso: nohup bash experiments/pos_grid.sh > runs/pos_grid.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."

while pgrep -f grid_faseA.sh >/dev/null; do sleep 120; done
echo "=== grid terminou ($(date -Is)); iniciando GATE-1b ==="

# GATE-1b: hipótese pré-registrada no DIARIO — sinergia sob pressão de orçamento.
# Config: threshold 600, max_turns 6 (vs 12 do grid). Mesmas 30 tasks.
TAG="mt6"
uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
  --tasks-module environment.tasks_all --threshold 600 --max-turns 6 \
  --points 3 --reps 3 || echo "FALHA teste0 ${TAG}"
uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
  --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
  --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
  --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
  --samples-from "runs/teste2_${TAG}/samples.jsonl" \
  --max-per-traj 3 || echo "FALHA teste3 ${TAG}"

echo "=== GATE-1b concluído; consolidando dataset ==="
uv run python -m credit.dataset --tags g600 g450 g900 --thresholds 600 450 900 \
  --out runs/credit_dataset.jsonl || echo "FALHA dataset"
uv run python -m credit.critic --dataset runs/credit_dataset.jsonl \
  --out runs/critic_report.json --seed 20260821 || echo "FALHA critic"
echo "=== POS-GRID COMPLETO ($(date -Is)) ==="
