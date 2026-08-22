# PROXIMOS-PASSOS.md — validação completa das 3 quantidades (C(H), C(M), I(H,M))

> Atualizado em 2026-08-22 (noite autônoma, RTX 4090). **As três quantidades da hipótese central têm sinal causal mensurável, replicado em duas configs de harness.**

## Resultados da validação (2026-08-21/22)

| Quantidade | v2 (threshold 600) | v2b (threshold 900, replicação) |
|---|---|---|
| Replay fidelity (piso) | 30/30 exato, piso 0.0 | 30/30 exato, piso 0.0 |
| **C(harness)** — Teste 1 | 6/23 \|C\|>0; keep→summarize 40% não-zero, C até ±0.86 | 10/23 \|C\|>0; **sinal nas 2 direções** (keep→summarize 40%; summarize→keep 2/3, C negativo: resumir era prejudicial) |
| **C(model)** — Teste 2 | 2/7 \|C\|>0 (write_file→write_file), max 0.86 | 2/7, max 0.29 |
| **I(H,M)** — Teste 3 | 4 pontos, I=−0.75..−0.88, 1 não-saturado; nulos de fila 16/16 | 6 pontos, I=−0.75..−1.0, 1 não-saturado; nulos 16/16 |

**Achados p/ o artigo:**
1. **Mecanismo de I(H,M) — screening-off:** em todos os pontos, a ação forçada do modelo (a′ carrega as constantes p/ solution.py) *blinda* a decisão de contexto do harness: C_HM = C_M, logo I = −C_H. Interação fortemente subaditiva — exatamente o sinal que crédito de camada única não captura e o argumento central contra treinar as camadas com créditos independentes.
2. **Política quase-determinística em estados de reparo:** 13/20 pontos sem a′ em 8 seeds a T=0.8 (auditado: não é bug de seed; até T=1.2 é idêntico em estados de reparo, enquanto prompts abertos variam). A entropia da política concentra-se nos primeiros write_file. Implicação: C(model) só é amostrável onde a política tem entropia — reportar como limitação/achado.
3. Saturação de reward (r_cf ∈ {0,1}) domina os pontos de I (3/4 e 5/6) — o critério pré-registrado de exigir ponto não-saturado segurou a inferência.
4. Limitações I1/I2 do Teste 1 continuam valendo; em v2b a direção summarize→keep persistiu (contexto fica abaixo do threshold 900 após o flip) e mostrou C≠0.

## Próximos passos

1. **Escala:** mais tasks (v3) e mais trajetórias por task p/ dataset de counterfactuals — as 3 quantidades agora têm pipeline validado (testes 1/2/3 são os geradores de dataset).
2. **Critic:** treinar preditor de C(H), C(M), I contra ground truth de replay (dose-matched, confrontar arXiv:2608.19760).
3. **Joint RL (GRPO)** com crédito cross-layer vs baselines (outcome-only, model-only, harness-only, independent).
4. Diversidade de a′: proposta além de frozen-policy sampling p/ estados de baixa entropia (perturbação estruturada), como ablation.

## Setup na 4090 (estado atual, funcionando)

- **vLLM 0.8.5.post1 + transformers 4.51.3** em `.venv-vllm` (Python 3.12). vLLM 0.27 NÃO funciona aqui (FlashInfer JIT exige nvcc). Cache HF do host é root-owned → `HF_HOME=~/hf_cache`:
  ```bash
  HF_HOME=~/hf_cache CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-4B --max-model-len 8192 --gpu-memory-utilization 0.85 \
    --port 8321 --disable-log-requests > vllm.log 2>&1 &
  ```
- Cadeia completa de validação (reproduzível; summaries em `experiments/results/`):
  ```bash
  uv run python -m experiments.teste0 --tasks-module environment.tasks_v2 --out runs/teste0_v2 --points 3 --reps 1 --threshold 600 --max-turns 12
  uv run python -m experiments.teste1 --baseline runs/teste0_v2/baseline --out runs/teste1_v2 --max-per-traj 3 --floor-from runs/teste0_v2/summary.json
  uv run python -m experiments.teste2 --baseline runs/teste0_v2/baseline --out runs/teste2_v2 --max-per-traj 3 --floor-from runs/teste0_v2/summary.json
  uv run python -m experiments.teste3 --baseline runs/teste0_v2/baseline --out runs/teste3_v2 --max-per-traj 2 --samples-from runs/teste2_v2/samples.jsonl --floor-from runs/teste0_v2/summary.json
  # replicação: mesmos comandos com --threshold 900 e sufixo _v2b
  ```

## Lembretes de rigor (do revisor — manter no artigo)

- I1: direções keep→summarize e summarize→keep são experimentos DISTINTOS (harness determinístico pode desfazer a intervenção); nunca agregar.
- I2: filtro de elegibilidade seleciona turnos tardios (viés); reportar distribuição de turn/tokens dos pontos.
- Timeouts de pytest são artefato de infra: excluídos do piso, reportados à parte (`final_timed_out`).
- 3 replays com nº de decisões ≠ sufixo original mas mesmo reward (task `group_anagrams`) — catalogado, investigar se reaparecer em escala.
