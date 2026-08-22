#!/usr/bin/env bash
# Pós-C1 (autônomo): espera a cadeia dos 4 braços × 3 seeds terminar e roda:
# 1. audita_ch (CRÍTICO 1 do revisor): C_H recomputado como diff de dois replays greedy.
# 2. Verificação descritiva pós-hoc: 3 políticas fixas nas 10 tasks HELD-OUT
#    (item 4 do revisor; rotulada descritiva — não recalibra λ).
set -u
cd "$(dirname "$0")/.."
while pgrep -f c1_chain.sh >/dev/null; do sleep 300; done
echo "=== chain C1 terminou; iniciando pós-C1 ($(date -Is)) ==="
uv run python -m experiments.audita_ch --run-dir runs/c1_ch_s1 --n 60 --out runs/audita_ch.json
echo "=== audita_ch done rc=$? ==="
uv run python - <<'EOF'
# calibração descritiva no held-out (mesmo protocolo do calibrate, tasks 20:30)
import json
from pathlib import Path
from rl.train_c1 import CountingLLM, calibrate, load_task_split
from agent.llm import LLMClient
_, heldout = load_task_split("environment.tasks_all")
report = calibrate(heldout, CountingLLM(LLMClient()), Path("runs/c1_calibrate_heldout"), 25.0)
print(json.dumps({k: p["mean_R_eff"] for k, p in report["policies"].items()}, indent=2))
EOF
echo "=== POS-C1 COMPLETO ($(date -Is)) ==="
