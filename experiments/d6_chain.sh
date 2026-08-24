#!/usr/bin/env bash
# D6 (pré-registro 20): Qwen3-1.7B no pool MBPP+ (célula vazia: pressão no
# ambiente B com modelo in-window). Restaura o 4B ao final.
set -uo pipefail
cd "$(dirname "$0")/.."

start_vllm () {
  pkill -f "vllm.entrypoints.openai.api_server" || true
  sleep 10
  HF_HOME=~/hf_cache CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python \
    -m vllm.entrypoints.openai.api_server --model "$1" --max-model-len 8192 \
    --gpu-memory-utilization "$2" --port 8321 --disable-log-requests \
    --no-enable-prefix-caching > vllm.log 2>&1 &
  for i in $(seq 1 180); do
    curl -s localhost:8321/v1/models | grep -q "$1" && return 0
    sleep 10
  done
  echo "TIMEOUT esperando vLLM com $1"; return 1
}

export TCC_MODEL="Qwen/Qwen3-1.7B"
start_vllm "$TCC_MODEL" 0.85 || exit 1

for CFG in "mbpp17_g600:12" "mbpp17_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste0_${TAG}/summary.json" ]; then echo "=== pula teste0 ${TAG} ==="; continue; fi
  echo "=== D6 teste0 ${TAG} max_turns=${MT} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module environment.tasks_mbpp --threshold 600 --max-turns "$MT" \
    --points 3 --reps 3 || { echo "FALHA teste0 ${TAG}"; start_vllm "Qwen/Qwen3-4B" 0.85; exit 1; }
done

for TAG in "mbpp17_g600" "mbpp17_mt6"; do
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D6 cadeia ${TAG} ($(date -Is)) ==="
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 ${TAG}"
done

echo "=== D6 completo; restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B" 0.85
echo "=== D6 COMPLETO ($(date -Is)) ==="
