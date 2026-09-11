#!/bin/bash
#SBATCH --job-name=preg42
#SBATCH --partition=h100n2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/raid/user_marcospaulo/tcc/runs/logs/preg42_%j.log
#SBATCH --signal=B:SIGUSR1@300
# Pré-reg 42: quarta célula R(h′,a) nas células externas. Parametrizado por env:
#   MODEL       (default Qwen/Qwen3-4B)  — também exportado como TCC_MODEL
#   GATE_CELLS  (default g450,g600,g900,mbpp_g600,mbpp_mt6,he_g600,he_mt6)
#   RUN_CELLS   (default mbpp_g600,mbpp_mt6,he_g600,he_mt6)
# Ex. 8B: sbatch --export=ALL,MODEL=Qwen/Qwen3-8B,GATE_CELLS=q8_g600,q8_mt4,q8_mt6,RUN_CELLS=q8_g600,q8_mt4,q8_mt6 slurm/preg42.sbatch
set -uo pipefail
cd /raid/user_marcospaulo/tcc
mkdir -p runs/logs runs/preg42

export HF_HOME=/raid/user_marcospaulo/.cache/huggingface
export UV_CACHE_DIR=/raid/user_marcospaulo/.cache/uv
export HF_HUB_OFFLINE=1
PORT=${PORT:-8321}
export TCC_BASE_URL="http://127.0.0.1:${PORT}/v1"
MODEL=${MODEL:-Qwen/Qwen3-4B}
export TCC_MODEL="$MODEL"
GATE_CELLS=${GATE_CELLS:-g450,g600,g900,mbpp_g600,mbpp_mt6,he_g600,he_mt6}
RUN_CELLS=${RUN_CELLS:-mbpp_g600,mbpp_mt6,he_g600,he_mt6}
GPU_UTIL=${GPU_UTIL:-0.85}

echo "=== job $SLURM_JOB_ID node $(hostname) gpu=$CUDA_VISIBLE_DEVICES model=$MODEL $(date -Is) ==="
echo "gate_cells=$GATE_CELLS run_cells=$RUN_CELLS"
nvidia-smi --query-gpu=index,name,memory.used --format=csv
# GPU compartilhada (partição mix): vLLM só pode reservar a fração ainda livre
read -r USED TOTAL < <(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits -i 0 | tr -d ',')
GPU_UTIL=$(python3 -c "u=($TOTAL-$USED-3000)/$TOTAL; print(f'{min(float(\"$GPU_UTIL\"), u):.2f}')")
echo "gpu used=${USED}MiB total=${TOTAL}MiB -> gpu-memory-utilization=$GPU_UTIL"

cleanup () {
  echo "=== cleanup ($(date -Is)) ==="
  [ -n "${VLLM_PID:-}" ] && kill "$VLLM_PID" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT
trap 'echo "SIGUSR1: término em 5 min — stages são reentrantes, ressubmeta"; exit 2' SIGUSR1

.venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --max-model-len 8192 --gpu-memory-utilization "$GPU_UTIL" \
  --no-enable-prefix-caching --port "$PORT" --disable-log-requests \
  --seed 1234 > "runs/logs/vllm_preg42_${SLURM_JOB_ID}.log" 2>&1 &
VLLM_PID=$!
for i in $(seq 1 120); do
  curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" && break
  kill -0 "$VLLM_PID" 2>/dev/null || { echo "vLLM morreu"; tail -30 "runs/logs/vllm_preg42_${SLURM_JOB_ID}.log"; exit 1; }
  sleep 10
done
curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" || { echo "TIMEOUT vLLM"; exit 1; }
echo "vLLM up: $(.venv-vllm/bin/python -c 'import vllm;print(vllm.__version__)')"

echo "=== stage gate ($(date -Is)) ==="
.venv/bin/python -m experiments.preg42 --stage gate --cells "$GATE_CELLS" &
wait $! || { echo "GATE FALHOU"; exit 1; }
echo "=== stage run ($(date -Is)) ==="
.venv/bin/python -m experiments.preg42 --stage run --cells "$RUN_CELLS" &
wait $! || { echo "FALHA run — retomável"; exit 1; }
echo "=== stage relatorio ($(date -Is)) ==="
.venv/bin/python -m experiments.preg42 --stage relatorio
echo "=== fim ($(date -Is)) ==="
