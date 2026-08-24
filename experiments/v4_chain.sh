#!/usr/bin/env bash
# D4 (pré-registro 17): pool v4 curado à competência do Qwen3-8B.
# teste0 no pool inteiro (2 configs) -> curação (regra pré-registrada) ->
# teste2/3 nos baselines curados. Restaura o 4B ao final.
set -uo pipefail
cd "$(dirname "$0")/.."

start_vllm () {  # $1 = modelo, $2 = gpu-memory-utilization
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

export TCC_MODEL="Qwen/Qwen3-8B"
start_vllm "$TCC_MODEL" 0.92 || exit 1

for CFG in "v4_g600:12" "v4_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste0_${TAG}/summary.json" ]; then echo "=== pula teste0 ${TAG} ==="; continue; fi
  echo "=== D4 teste0 ${TAG} max_turns=${MT} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module environment.tasks_v4 --threshold 600 --max-turns "$MT" \
    --points 3 --reps 3 || { echo "FALHA teste0 ${TAG}"; exit 1; }
done

echo "=== D4 curação ($(date -Is)) ==="
uv run python -m experiments.cura_v4 --from-tag v4_g600 --apply-tags v4_g600 v4_mt6 \
  || { echo "CURADORIA FALHOU (pré-registro 17)"; start_vllm "Qwen/Qwen3-4B" 0.85; exit 1; }

for CFG in "v4cur_g600" "v4cur_mt6"; do
  TAG="$CFG"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D4 cadeia ${TAG} ($(date -Is)) ==="
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 ${TAG}"
done

echo "=== D4 completo; restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B" 0.85
echo "=== D4 COMPLETO ($(date -Is)) ==="
