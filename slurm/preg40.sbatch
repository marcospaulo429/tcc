#!/bin/bash
#SBATCH --job-name=preg40
#SBATCH --partition=h100n2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/raid/user_marcospaulo/tcc/runs/logs/preg40_%j.log
#SBATCH --signal=B:SIGUSR1@300
# Modelo de job de replay no cluster (ex.: pré-reg 40). Sobe vLLM (Qwen3-4B, APC OFF)
# na GPU alocada, roda gate→v1→v2→relatorio em série e derruba o servidor.
# Reentrante: cada stage é idempotente por chave (append_row/done_keys).
set -uo pipefail
cd /raid/user_marcospaulo/tcc
mkdir -p runs/logs runs/preg40

export HF_HOME=/raid/user_marcospaulo/.cache/huggingface
export UV_CACHE_DIR=/raid/user_marcospaulo/.cache/uv
export HF_HUB_OFFLINE=1
PORT=${PORT:-8321}
MODEL=Qwen/Qwen3-4B

echo "=== job $SLURM_JOB_ID node $(hostname) gpu=$CUDA_VISIBLE_DEVICES $(date -Is) ==="
nvidia-smi --query-gpu=index,name,memory.used --format=csv

cleanup () {
  echo "=== cleanup ($(date -Is)) ==="
  [ -n "${VLLM_PID:-}" ] && kill "$VLLM_PID" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT
trap 'echo "SIGUSR1: término em 5 min — stages são reentrantes, ressubmeta"; exit 2' SIGUSR1

.venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --max-model-len 8192 --gpu-memory-utilization 0.85 \
  --no-enable-prefix-caching --port "$PORT" --disable-log-requests \
  --seed 1234 > runs/logs/vllm_preg40_${SLURM_JOB_ID}.log 2>&1 &
VLLM_PID=$!
for i in $(seq 1 120); do
  curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" && break
  kill -0 "$VLLM_PID" 2>/dev/null || { echo "vLLM morreu"; tail -30 runs/logs/vllm_preg40_${SLURM_JOB_ID}.log; exit 1; }
  sleep 10
done
curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" || { echo "TIMEOUT vLLM"; exit 1; }
echo "vLLM up: $(.venv-vllm/bin/python -c 'import vllm;print(vllm.__version__)')"

for st in gate v1 v2 relatorio; do
  echo "=== stage $st ($(date -Is)) ==="
  .venv/bin/python -m experiments.quarto_braco --stage "$st" &
  STAGE_PID=$!
  wait "$STAGE_PID" || { echo "FALHA stage $st — retomável"; exit 1; }
done
echo "=== fim ($(date -Is)) ==="
