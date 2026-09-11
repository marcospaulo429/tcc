#!/bin/bash
#SBATCH --job-name=preg44
#SBATCH --partition=h100n2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/raid/user_marcospaulo/tcc/runs/logs/preg44_%j.log
#SBATCH --signal=B:SIGUSR1@300
# Pré-reg 44: braço C_H com passo reescalado (lr ×5) no setup do Act 4.
# Ordem: (g1) gate nulo fresco 6 replays → (g2) replicação ch lr0.1 s1 (deve dar
# held-out 0.4046 exato) → ch lr0.5 seeds 1,2,3. Cada etapa só roda se o
# summary.json ainda não existir (reentrante).
set -uo pipefail
cd /raid/user_marcospaulo/tcc
mkdir -p runs/logs runs/preg44

export HF_HOME=/raid/user_marcospaulo/.cache/huggingface
export UV_CACHE_DIR=/raid/user_marcospaulo/.cache/uv
export HF_HUB_OFFLINE=1
PORT=${PORT:-8321}
export TCC_BASE_URL="http://127.0.0.1:${PORT}/v1"
MODEL=Qwen/Qwen3-4B
export TCC_MODEL="$MODEL"
GPU_UTIL=${GPU_UTIL:-0.85}
POOL=runs/c1d_margem/pool.json
COMMON="--tasks-module environment.tasks_margem --pool-json $POOL --budget-calls 1600 --lambda-cost 5 --c1b"

echo "=== job $SLURM_JOB_ID node $(hostname) gpu=$CUDA_VISIBLE_DEVICES model=$MODEL $(date -Is) ==="
nvidia-smi --query-gpu=index,name,memory.used,driver_version --format=csv
read -r USED TOTAL < <(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits -i 0 | tr -d ',')
GPU_UTIL=$(python3 -c "u=($TOTAL-$USED-3000)/$TOTAL; print(f'{min(float(\"$GPU_UTIL\"), u):.2f}')")
echo "gpu used=${USED}MiB total=${TOTAL}MiB -> gpu-memory-utilization=$GPU_UTIL"

cleanup () {
  echo "=== cleanup ($(date -Is)) ==="
  [ -n "${VLLM_PID:-}" ] && kill "$VLLM_PID" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT
trap 'echo "SIGUSR1: término em 5 min — etapas são reentrantes, ressubmeta"; exit 2' SIGUSR1

.venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --max-model-len 8192 --gpu-memory-utilization "$GPU_UTIL" \
  --no-enable-prefix-caching --port "$PORT" --disable-log-requests \
  --seed 1234 > "runs/logs/vllm_preg44_${SLURM_JOB_ID}.log" 2>&1 &
VLLM_PID=$!
for i in $(seq 1 120); do
  curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" && break
  kill -0 "$VLLM_PID" 2>/dev/null || { echo "vLLM morreu"; tail -30 "runs/logs/vllm_preg44_${SLURM_JOB_ID}.log"; exit 1; }
  sleep 10
done
curl -s "localhost:$PORT/v1/models" | grep -q "$MODEL" || { echo "TIMEOUT vLLM"; exit 1; }
echo "vLLM up: $(.venv-vllm/bin/python -c 'import vllm;print(vllm.__version__)')"

echo "=== (g1) gate nulo fresco ($(date -Is)) ==="
TCC_PREG42_OUT=runs/preg44/gate .venv/bin/python -m experiments.preg42 --stage gate --cells g450,g600,g900 &
wait $! || { echo "GATE FALHOU"; exit 1; }

run_arm () {  # $1=out dir, resto = args extras
  local out=$1; shift
  if [ -f "$out/summary.json" ]; then echo "skip $out (já existe)"; return 0; fi
  echo "=== $out ($(date -Is)) ==="
  .venv/bin/python -m rl.train_c1 --arm ch $COMMON --out "$out" "$@" &
  wait $! || { echo "FALHA $out — retomável"; exit 1; }
}
echo "=== (g2) replicação ch lr0.1 seed 1 na H100 ==="
run_arm runs/preg44/ch_lr01_s1_h100 --seed 1
.venv/bin/python -c "
import json; d=json.load(open('runs/preg44/ch_lr01_s1_h100/summary.json'))
r=round(d['heldout']['mean_R_eff'],4); print('g2 held-out', r, 'episodes', d['episodes'], 'ESPERADO 0.4046 / 139', 'OK' if r==0.4046 else 'DIVERGE')"
for s in 1 2 3; do
  run_arm runs/preg44/ch_lr05_s$s --seed $s --lr-scale 5.0
done
echo "=== resumo ($(date -Is)) ==="
for d in runs/preg44/ch_*; do
  .venv/bin/python -c "
import json,sys; d=json.load(open('$d/summary.json'))
print('$d', 'lr', d['lr'], 'episodes', d['episodes'], 'calls', d['llm_calls_total'], 'heldout', round(d['heldout']['mean_R_eff'],4), 'theta', [round(x,3) for x in d['theta']])"
done
echo "=== fim ($(date -Is)) ==="
