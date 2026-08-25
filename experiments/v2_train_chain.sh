#!/usr/bin/env bash
# Pré-reg 32: cadeia do treino V2 (estágio A calibração+seleção; estágio B 4×3).
# Idempotente por summary.json/report; sequencial (RNF4); APC off já no servidor.
set -uo pipefail
cd "$(dirname "$0")/.."

# gate: servidor de pé com o modelo certo e APC off
curl -s localhost:8321/v1/models | grep -q "Qwen3-4B" || { echo "vLLM 4B fora do ar"; exit 1; }
ps -eo cmd | grep api_server | grep -q "no-enable-prefix-caching" || { echo "APC LIGADO — aborta"; exit 1; }

# --- Estágio A: calibração (3 políticas fixas × 60 tasks) -------------------
if [ ! -f runs/v2_train/calibrate/calibrate_report.json ]; then
  echo "=== estágio A: calibrate ($(date -Is)) ==="
  .venv/bin/python - <<'PY'
import json, importlib, pathlib
tasks = sorted(t["task_id"] for t in importlib.import_module("environment.tasks_swe").TASKS)
pathlib.Path("runs/v2_train").mkdir(parents=True, exist_ok=True)
pathlib.Path("runs/v2_train/all60.json").write_text(json.dumps({"train": tasks, "heldout": []}))
PY
  uv run python -m rl.train_v2 --arm calibrate --pool-json runs/v2_train/all60.json \
    --out runs/v2_train/calibrate --lambda-cost 1.0 || { echo "FALHA calibrate"; exit 1; }
fi

# --- Estágio A: seleção analítica de λ* e pool (sem GPU) --------------------
if [ ! -f runs/v2_train/pool.json ]; then
  echo "=== estágio A: seleção λ*/pool ($(date -Is)) ==="
  uv run python -m experiments.margem_v2 || exit 1   # aborta reportável se n<10
fi
LAMBDA=$(.venv/bin/python -c "import json;print(json.load(open('runs/v2_train/pool.json'))['lambda_star'])")
echo "λ* = ${LAMBDA}"

# --- Estágio B: 4 braços × 3 seeds, 1600 chamadas por célula ----------------
for ARM in outcome ch chm_cm zero; do
  for SEED in 1 2 3; do
    OUT="runs/v2_train/${ARM}_s${SEED}"
    if [ -f "${OUT}/summary.json" ]; then echo "=== pula ${ARM} s${SEED} ==="; continue; fi
    echo "=== treino ${ARM} s${SEED} ($(date -Is)) ==="
    uv run python -m rl.train_v2 --arm "${ARM}" --seed "${SEED}" \
      --pool-json runs/v2_train/pool.json --budget-calls 1600 \
      --lambda-cost "${LAMBDA}" --out "${OUT}" \
      || echo "FALHA ${ARM} s${SEED} (segue a cadeia)"
  done
done
echo "=== cadeia completa ($(date -Is)) ==="
