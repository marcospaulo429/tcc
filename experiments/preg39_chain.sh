#!/usr/bin/env bash
# Pré-reg 39: ramo positivo do gate — census 8B/pool35 + treino licenciado.
# Sequencial, idempotente por report/summary. Troca o serving para Qwen3-8B
# durante a fase inteira e restaura Qwen3-4B ao final (padrão do 38).
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

export TCC_MODEL="Qwen/Qwen3-8B"
export TCC_XFAM_OUT="runs/preg39/census"

restaura_4b () {
  echo "=== restaurando Qwen3-4B ($(date -Is)) ==="
  unset TCC_MODEL
  start_vllm "Qwen/Qwen3-4B" 0.85
}
trap restaura_4b EXIT

# --- Gate 1 (analítico, 0 GPU) ------------------------------------------------
if [ ! -f runs/preg39/gate1_report.json ]; then
  uv run python -m experiments.preg39 --stage gate1 || exit 1
fi
GATE1=$(.venv/bin/python -c "import json;print(json.load(open('runs/preg39/gate1_report.json'))['gate1_abre'])")
[ "$GATE1" = "True" ] || { echo "GATE 1 FECHADO (g0) — fim da fase"; exit 0; }

# --- servidor 8B ---------------------------------------------------------------
curl -s localhost:8321/v1/models | grep -q "Qwen3-8B" || start_vllm "Qwen/Qwen3-8B" 0.85 || exit 1
ps -eo cmd | grep api_server | grep -q "no-enable-prefix-caching" || { echo "APC LIGADO — aborta"; exit 1; }

# --- Gate 2: census (base→nulos→piso→screening→census→census_esc→gate2) --------
for st in base nulos piso screening census census_esc; do
  MARK="runs/preg39/census/.done_${st}"
  if [ -f "$MARK" ]; then echo "=== pula census $st ==="; continue; fi
  echo "=== census stage $st ($(date -Is)) ==="
  uv run python -m experiments.preg39 --stage "$st" \
    || { echo "FALHA stage $st — retomável"; exit 1; }
  touch "$MARK"
done
uv run python -m experiments.preg39 --stage gate2 || exit 1
PROSSEGUE=$(.venv/bin/python -c "import json;print(json.load(open('runs/preg39/gate2_report.json'))['prossegue_treino'])")
[ "$PROSSEGUE" = "True" ] || { echo "GATE 2 FECHADO (x0/c0) — fim da fase, sem treino"; exit 0; }

# --- treino licenciado: 4 braços × 3 seeds, 1600 chamadas/célula ---------------
LAMBDA=$(.venv/bin/python -c "import json;print(json.load(open('runs/preg39/pool39.json'))['lambda_star'])")
echo "λ* = ${LAMBDA}"
for ARM in outcome ch chm_cm zero; do
  for SEED in 1 2 3; do
    OUTD="runs/preg39/train/${ARM}_s${SEED}"
    if [ -f "${OUTD}/summary.json" ]; then echo "=== pula ${ARM} s${SEED} ==="; continue; fi
    echo "=== treino ${ARM} s${SEED} ($(date -Is)) ==="
    uv run python -m rl.train_v2 --arm "${ARM}" --seed "${SEED}" \
      --tasks-module environment.tasks_swe35 \
      --pool-json runs/preg39/pool39.json --budget-calls 1600 \
      --lambda-cost "${LAMBDA}" --out "${OUTD}" \
      || echo "FALHA ${ARM} s${SEED} (segue a cadeia)"
  done
done

# --- contabilidade dual + relatório final ---------------------------------------
uv run python -m experiments.preg39 --stage dual || exit 1
uv run python -m experiments.preg39 --stage final || exit 1
echo "=== cadeia 39 completa ($(date -Is)) ==="
