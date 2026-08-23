#!/usr/bin/env bash
# D3 (pré-registro 16): segundo ambiente — MBPP+ multi-turn, Qwen3-4B, thr600, 60 tasks.
# Espera o D2d terminar (marcador em runs/q8_chain.log) e o 4B voltar à porta 8321.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "=== D3 aguardando D2D COMPLETO ($(date -Is)) ==="
while ! grep -q "D2D COMPLETO" runs/q8_chain.log 2>/dev/null; do sleep 60; done
for i in $(seq 1 60); do
  curl -s localhost:8321/v1/models | grep -q "Qwen3-4B" && break
  sleep 10
done
curl -s localhost:8321/v1/models | grep -q "Qwen3-4B" || { echo "4B não voltou"; exit 1; }

export TCC_MODEL="Qwen/Qwen3-4B"
for CFG in "mbpp_g600:12" "mbpp_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D3 ${TAG} max_turns=${MT} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module environment.tasks_mbpp --threshold 600 --max-turns "$MT" \
    --points 3 --reps 3 || echo "FALHA teste0 ${TAG}"
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 ${TAG}"
done
echo "=== D3 COMPLETO ($(date -Is)) ==="
