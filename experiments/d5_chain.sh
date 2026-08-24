#!/usr/bin/env bash
# D5 (pré-registro 19): controle simétrico — Qwen3-4B nas 22 tasks curadas.
# Pressupõe vLLM já servindo Qwen/Qwen3-4B na 8321 (restaurado pela cadeia D4b).
set -uo pipefail
cd "$(dirname "$0")/.."

export TCC_MODEL="Qwen/Qwen3-4B"
curl -s localhost:8321/v1/models | grep -q "Qwen3-4B" || { echo "vLLM sem 4B"; exit 1; }

# teste0 nas tasks curadas: pool = união v4∪v5 filtrada pelas sobreviventes.
# experiments.teste0 aceita --tasks-module; usamos um módulo dinâmico via
# environment.tasks_curated (gerado abaixo) para conter só as 22.
uv run python - << 'EOF'
import json, pathlib
surv = json.load(open("runs/v5_curation.json"))["survivors"]
code = (
    '"""Pool curado D4b/D5 (gerado por d5_chain.sh a partir de runs/v5_curation.json)."""\n'
    "from environment import tasks_v4 as _v4, tasks_v5 as _v5\n\n"
    f"_SURV = {surv!r}\n"
    "_ALL = {t['task_id']: t for t in _v4.TASKS + _v5.TASKS}\n"
    "TASKS = [_ALL[tid] for tid in _SURV]\n"
    "STRATA = {tid: 'H' for tid in _SURV}\n"
    "CRITICAL_CONSTANTS = {tid: (_v4.CRITICAL_CONSTANTS | _v5.CRITICAL_CONSTANTS).get(tid, []) for tid in _SURV}\n\n"
    "def get_task(task_id: str) -> dict:\n"
    "    return _ALL[task_id]\n"
)
pathlib.Path("environment/tasks_curated.py").write_text(code)
print("environment/tasks_curated.py:", len(surv), "tasks")
EOF

for CFG in "q4cur_g600:12" "q4cur_mt6:6"; do
  TAG="${CFG%%:*}"; MT="${CFG##*:}"
  if [ -f "runs/teste0_${TAG}/summary.json" ]; then echo "=== pula teste0 ${TAG} ==="; continue; fi
  echo "=== D5 teste0 ${TAG} max_turns=${MT} ($(date -Is)) ==="
  uv run python -m experiments.teste0 --out "runs/teste0_${TAG}" \
    --tasks-module environment.tasks_curated --threshold 600 --max-turns "$MT" \
    --points 3 --reps 3 || { echo "FALHA teste0 ${TAG}"; exit 1; }
done

for TAG in "q4cur_g600" "q4cur_mt6"; do
  if [ -f "runs/teste3_${TAG}/summary.json" ]; then echo "=== pula ${TAG} ==="; continue; fi
  echo "=== D5 cadeia ${TAG} ($(date -Is)) ==="
  uv run python -m experiments.teste2 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste2_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --max-per-traj 4 || echo "FALHA teste2 ${TAG}"
  uv run python -m experiments.teste3 --baseline "runs/teste0_${TAG}/baseline" \
    --out "runs/teste3_${TAG}" --floor-from "runs/teste0_${TAG}/summary.json" \
    --samples-from "runs/teste2_${TAG}/samples.jsonl" \
    --max-per-traj 3 || echo "FALHA teste3 ${TAG}"
done

echo "=== D5 COMPLETO ($(date -Is)) ==="
