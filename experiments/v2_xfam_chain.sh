#!/usr/bin/env bash
# Pré-registro 38: cross-family sob harness V2 congelado (protocolo texto plano).
# Candidatos em ordem fixa: Mistral-7B-v0.3 (com TCC_MERGE_ROLES=1, adendo 35a)
# → deepseek-coder-6.7b (sem shim). Smoke >=0.80; 1º aprovado roda o pipeline
# completo. Sem 3º candidato, sem ajuste por modelo. Restaura Qwen3-4B ao final.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p runs/logs

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

run_pipeline () {  # $1 = tag
  export TCC_XFAM_OUT="runs/v2_xfam_$1"
  for st in base nulos piso screening census census_esc aprime_s relatorio; do
    echo "=== xfam $1 stage $st ($(date -Is)) ==="
    uv run python -m experiments.census_v2_xfam --stage "$st" \
      || { echo "FALHA stage $st — pipeline interrompido (retomável)"; return 1; }
  done
}

APROVADO=none

echo "=== candidato 1: Mistral-7B-Instruct-v0.3 ($(date -Is)) ==="
if start_vllm "mistralai/Mistral-7B-Instruct-v0.3" 0.85; then
  export TCC_MODEL="mistralai/Mistral-7B-Instruct-v0.3" TCC_MERGE_ROLES=1
  if uv run python -m experiments.smoke_v2_xfam; then
    APROVADO=mistral
    run_pipeline mistral || echo "pipeline mistral incompleto"
  else
    echo "SMOKE mistral FALHOU"
  fi
fi

if [ "$APROVADO" = none ]; then
  echo "=== candidato 2: deepseek-coder-6.7b-instruct ($(date -Is)) ==="
  unset TCC_MERGE_ROLES
  if start_vllm "deepseek-ai/deepseek-coder-6.7b-instruct" 0.85; then
    export TCC_MODEL="deepseek-ai/deepseek-coder-6.7b-instruct"
    if uv run python -m experiments.smoke_v2_xfam; then
      APROVADO=deepseek
      run_pipeline deepseek || echo "pipeline deepseek incompleto"
    else
      echo "SMOKE deepseek FALHOU — desfecho X3 (ambos falham)"
    fi
  fi
fi

unset TCC_MODEL TCC_MERGE_ROLES || true
echo "=== restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B" 0.85
echo "=== PREG38 FIM: aprovado=$APROVADO ($(date -Is)) ==="
