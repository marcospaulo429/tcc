# PROXIMOS-PASSOS.md — pós-validação (Teste 1 v2 ✅)

> Atualizado em 2026-08-21 (RTX 4090). **Hipótese do sinal causal do harness VALIDADA.**

## Resultado da validação (2026-08-21, 4090)

| Item | Status |
|---|---|
| `environment/tasks_v2.py` (10 tasks multi-turno, constantes críticas além de task_chars=240) | ✅ commitado, 88 testes verdes |
| **Teste 0 v2** — replay fidelity nas tasks v2 | ✅ **30/30 exato, piso 0.0** (`experiments/results/2026-08-21_teste0_v2_summary.json`) |
| **Teste 1 v2** — sinal causal do harness | ✅ **VALIDADO**: 23 counterfactuals, 0 timeouts, 6/23 (26%) com \|C\| > piso; direção keep→summarize: n=15, 40% não-zero, C até ±0.86; direção summarize→keep: n=8, C=0 em todos (consistente com I1 — harness determinístico re-decide summarize no turno seguinte). (`experiments/results/2026-08-21_teste1_v2_summary.json`) |

Leituras do resultado (reportar no artigo):
- Os 6 pontos acima do piso estão nos turnos 0–1 (tokens 279–414): forçar summarize cedo trunca o enunciado e destrói constantes irrecuperáveis — exatamente o mecanismo desenhado nas tasks v2. I2 continua: a elegibilidade agora seleciona turnos **iniciais** (prompt > 240 chars torna o flip não-vácuo desde o turno 0).
- 1 ponto com C negativo (−0.14, `inventory_restock`): summarize forçado *melhorou* o resultado — sinal de que o crédito tem os dois sinais, não é artefato de degradação monotônica.
- summarize→keep com C=0 em n=8 NÃO é ausência de efeito da camada: é o desenho I1 (efeito medido = "summarize adiado 1 turno").

## Próximos passos (pipeline do artigo, PLANO.md §8)

1. **C(model)**: intervenção em `tool_call` — forçar ação alternativa amostrada (frozen policy sampling à la C3). Requer definir a distribuição de propostas (re-amostrar o LLM com temperatura > 0 no ponto, ou perturbação estruturada da ação).
2. **I(H,M)**: intervenção conjunta harness+model no mesmo ponto — a contribuição central.
3. Escalar coleta: mais trajetórias por task (seeds/temperaturas variadas) p/ dataset de counterfactuals.
4. Critic supervisionado contra ground truth de replay (dose-matched, confrontar arXiv:2608.19760).
5. Joint RL (GRPO).

## Setup na 4090 (estado atual, funcionando)

- **vLLM 0.8.5.post1 + transformers 4.51.3** em `.venv-vllm` (Python 3.12). vLLM 0.27 NÃO funciona aqui (FlashInfer JIT exige nvcc; não há CUDA toolkit no host). Cache HF do host é root-owned → usar `HF_HOME=~/hf_cache`:
  ```bash
  HF_HOME=~/hf_cache CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-4B --max-model-len 8192 --gpu-memory-utilization 0.85 \
    --port 8321 --disable-log-requests > vllm.log 2>&1 &
  ```
- Comandos usados na validação (flags reais; o handoff antigo citava `--tasks`, o correto é `--tasks-module`):
  ```bash
  uv run python -m experiments.teste0 --tasks-module environment.tasks_v2 \
    --out runs/teste0_v2 --points 3 --reps 1 --threshold 600 --max-turns 12
  uv run python -m experiments.teste1 --baseline runs/teste0_v2/baseline \
    --out runs/teste1_v2 --max-per-traj 3 --floor-from runs/teste0_v2/summary.json
  ```

## Lembretes de rigor (do revisor — manter no artigo)

- I1: direções keep→summarize e summarize→keep são experimentos DISTINTOS (harness determinístico pode desfazer a intervenção); nunca agregar.
- I2: filtro de elegibilidade seleciona turnos tardios (viés); reportar distribuição de turn/tokens dos pontos.
- Timeouts de pytest são artefato de infra: excluídos do piso, reportados à parte (`final_timed_out`).
- 3 replays com nº de decisões ≠ sufixo original mas mesmo reward (task `group_anagrams`) — catalogado, investigar se reaparecer em escala.
