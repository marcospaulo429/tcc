#!/usr/bin/env bash
# D2c (pré-registro 14): replicação com Qwen3-1.7B, thr600, 30 tasks, mt12 + mt6.
# Troca o modelo do vLLM (porta 8321), roda o pipeline e RESTAURA o 4B ao final.
set -uo pipefail
cd "$(dirname "$0")/.."

start_vllm () {  # $1 = modelo
  pkill -f "vllm.entrypoints.openai.api_server" || true
  sleep 10
  HF_HOME=~/hf_cache CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python \
    -m vllm.entrypoints.openai.api_server --model "$1" --max-model-len 8192 \
    --gpu-memory-utilization 0.85 --port 8321 --disable-log-requests \
    --no-enable-prefix-caching > vllm.log 2>&1 &
  for i in $(seq 1 120); do
    curl -s localhost:8321/v1/models | grep -q "$1" && return 0
    sleep 10
  done
  echo "TIMEOUT esperando vLLM com $1"; return 1
}

export TCC_MODEL="Qwen/Qwen3-1.7B"
start_vllm "$TCC_MODEL" || exit 1

for CFG in "q17_g600:12" "q17_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D2c ${TAG} max_turns=${MT} ($(date -Is)) ==="
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

echo "=== D2c completo; restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B"
echo "=== D2C COMPLETO ($(date -Is)) ==="
