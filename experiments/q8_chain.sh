#!/usr/bin/env bash
# D2d (pré-registro 15): segundo modelo POWERED — Qwen3-8B, thr600, 30 tasks, mt12 + mt6.
# Troca o modelo do vLLM (porta 8321), roda o pipeline e RESTAURA o 4B ao final.
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

for CFG in "q8_g600:12" "q8_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D2d ${TAG} max_turns=${MT} ($(date -Is)) ==="
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

# Escalada única pré-registrada: se não-saturados confirmatórios < 5 em q8_mt6, roda q8_mt4.
NEED_MT4=$(uv run python - <<'EOF'
import json
try:
    d = json.load(open("runs/teste3_q8_mt6/summary.json"))
    c = d["by_direction"].get("keep_context->summarize_context", {})
    ns = c.get("n", 0) - c.get("n_saturated", 0)
    print("yes" if ns < 5 else "no")
except Exception:
    print("no")
EOF
)
if [ "$NEED_MT4" = "yes" ]; then
  echo "=== D2d escalada q8_mt4 (pré-registro 15) ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_q8_mt4" \
    --tasks-module environment.tasks_all --threshold 600 --max-turns 4 \
    --points 3 --reps 3 || echo "FALHA teste0 q8_mt4"
  uv run python -m experiments.teste2 --baseline "runs/teste0_q8_mt4/baseline" \
    --out "runs/teste2_q8_mt4" --floor-from "runs/teste0_q8_mt4/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 q8_mt4"
  uv run python -m experiments.teste3 --baseline "runs/teste0_q8_mt4/baseline" \
    --out "runs/teste3_q8_mt4" --floor-from "runs/teste0_q8_mt4/summary.json" \
    --samples-from "runs/teste2_q8_mt4/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 q8_mt4"
fi

echo "=== D2d completo; restaurando Qwen3-4B ($(date -Is)) ==="
start_vllm "Qwen/Qwen3-4B" 0.85
echo "=== D2D COMPLETO ($(date -Is)) ==="
