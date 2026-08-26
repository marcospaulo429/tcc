#!/usr/bin/env bash
# Pré-registro 35 (+ adendos 35a/35b): census cross-family.
# 35b: Mistral-7B-v0.3 falhou o smoke declarado (parse 0.57 < 0.80) → fallback
# declarado deepseek-coder-6.7b-instruct. Espelho do q8_chain (pré-reg 15):
# smoke de parse → teste0/2/3 em g600 e mt6. Restaura o Qwen3-4B ao final.
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

export TCC_MODEL="deepseek-ai/deepseek-coder-6.7b-instruct"
# 35b: template do deepseek aceita roles consecutivos — sem shim de merge.
unset TCC_MERGE_ROLES
start_vllm "$TCC_MODEL" 0.90 || exit 1

# Smoke declarado no pré-reg 35: 3 episódios, taxa de parse >=80%, sem análise de screening.
echo "=== smoke de parse ($(date -Is)) ==="
uv run python -m experiments.smoke_parse_m7 || { echo "SMOKE FALHOU — abortar e re-declarar"; start_vllm "Qwen/Qwen3-4B" 0.85; exit 1; }

for CFG in "dsc_g600:12" "dsc_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== preg35 ${TAG} max_turns=${MT} ($(date -Is)) ==="
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

echo "=== preg35 completo; restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B" 0.85
echo "=== PREG35 COMPLETO ($(date -Is)) ==="
