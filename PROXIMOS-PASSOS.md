# PROXIMOS-PASSOS.md — retomada na RTX 4090

> Handoff da sessão de 2026-08-21 (DGX V100). Estado: Teste 0 ✅ concluído, Teste 1 v1 ⚠️ inconclusivo (subpotenciado), Teste 1 v2 parcialmente preparado.

## Estado atual (commitado até `e861ccf`)

| Item | Status |
|---|---|
| Schema + recorder + replay engine | ✅ pronto, 37 testes verdes |
| Sandbox + 10 tasks v1 | ✅ pronto |
| Agente V1 (Qwen3-4B via vLLM, loop 2 camadas) | ✅ pronto |
| **Teste 0 — replay fidelity** | ✅ **PASSOU: 90/90 exato, piso de ruído 0.0** (`experiments/results/2026-08-21_teste0_summary.json`) |
| Teste 1 v1 — sinal causal do harness | ⚠️ inconclusivo: só 4 pontos elegíveis, C=0 em todos. Tasks curtas demais — sem poder estatístico. NÃO é resultado negativo. |
| Registry de task sets + experimentos parametrizáveis | ✅ commitado |
| `environment/tasks_v2.py` (tasks multi-turno) | ❌ **FALTA** — spec abaixo |

## O que falta (em ordem)

### 1. Criar `environment/tasks_v2.py` — tasks que dão poder ao Teste 1

O Teste 1 v1 falhou porque: (a) o agente resolve em 2-3 turnos; (b) o contexto nunca cresce a ponto do summarize importar; (c) toda informação é recuperável de `solution.py`. As tasks v2 precisam de:

- **≥6 turnos típicos** para resolver (multi-arquivo ou multi-etapa).
- **Informação não-recuperável do workspace**: o enunciado revela restrições em partes (ex.: specs entregues em mensagens sucessivas de "cliente", valores de configuração ditos uma vez no meio do episódio) — se o summarize descartar, o agente não tem onde reler.
- Mesmo formato do `tasks.py` v1: `task_id`, `prompt`, `test_code` (pytest autocontido, determinístico), `starter_code`, + `get_task()`. 10 tasks.
- Teste de referência igual ao v1: solução correta → reward 1.0, starter → 0.0 (ver `tests/test_environment.py` como modelo).
- **Delegar ao subagente `impl`** com spec fechada (o main não implementa task set).

### 2. Rodar Teste 0 rápido nas tasks v2 (sanity, ~30 rollouts)

O piso 0.0 foi medido nas tasks v1. Revalidar nas v2 (mais turnos = mais chances de divergência):

```bash
uv run python -m experiments.teste0 --tasks v2 --out runs/teste0_v2 --points 3 --reps 1
```

(reps=1 é suficiente: o determinismo já foi demonstrado com reps=3 no v1.)

### 3. Rodar Teste 1 v2 — a validação que buscamos

```bash
uv run python -m experiments.teste1 --tasks v2 --baseline runs/teste0_v2/baseline \
  --out runs/teste1_v2 --max-per-traj 3 --summarize-threshold 600
```

- Threshold 600 (vs 1200 default) força mais decisões de summarize.
- Meta: ≥30 pontos de intervenção. Se <20 elegíveis, aumentar `--max-per-traj` e nº de trajetórias baseline por task (rodar teste0_v2 com mais episódios).
- **Critério pré-registrado:** sinal causal do harness confirmado se fração não-trivial de pontos com |C| > piso do teste0_v2 (piso esperado 0.0 → qualquer C≠0 conta, MAS reportar por task e por direção; ver docstring de `experiments/teste1.py` para as limitações I1/I2 que DEVEM ir no artigo).

### 4. Análise e decisão

- Se C(harness) ≠ 0 em pontos suficientes → **hipótese validada, artigo continua**: próximo passo é C(model) (intervenção em tool_calls: forçar ação alternativa amostrada) e depois I(H,M) (intervenção conjunta) — a contribuição central.
- Se C = 0 em tudo mesmo com poder → investigar antes de desistir: summarize está descartando informação de verdade? (auditar `tokens_before/after` nos records `context_policy`); tasks têm variância de reward? Se sim e ainda C=0, considerar o resultado negativo honesto (publicável) e pivotar p/ interação model-side.

### 5. Depois da validação (pipeline do artigo)

Ordem do PLANO.md §8: coletar trajetórias em escala → dataset de counterfactuals (C(model), C(harness), I(H,M)) → critic (validado contra ground truth, dose-matched — confrontar arXiv:2608.19760) → joint RL (GRPO). Baselines e ablations já especificados no PLANO.

## Setup na 4090 (diferenças vs DGX)

1. **vLLM:** a 4090 (Ada, SM89) suporta bf16 e FlashAttention — pode remover `--dtype half`:
   ```bash
   uv venv .venv-vllm && VIRTUAL_ENV=$PWD/.venv-vllm uv pip install vllm setuptools
   # na 4090 pode usar vLLM recente; se usar vllm==0.8.5.post1, fixar transformers==4.51.3
   CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
     --model Qwen/Qwen3-4B --max-model-len 8192 --gpu-memory-utilization 0.85 \
     --port 8321 --disable-log-requests > vllm.log 2>&1 &
   ```
2. **Projeto:** `uv sync` e `uv run pytest tests/ -q` (deve dar 37+ verdes) antes de qualquer experimento.
3. **24 GB de VRAM**: Qwen3-4B fp16/bf16 cabe com folga em 8k de contexto.
4. Experimentos são **idempotentes** (retomam de onde pararam via `done_keys`) e rodam sequenciais de propósito (determinismo). Não paralelizar rollouts.
5. Ao terminar, copiar summaries para `experiments/results/` com data no nome e commitar (disciplina: commits pequenos, português, prefixo `exp:`/`infra:`).

## Lembretes de rigor (do revisor — manter no artigo)

- I1: direções keep→summarize e summarize→keep são experimentos DISTINTOS (harness determinístico pode desfazer a intervenção); nunca agregar.
- I2: filtro de elegibilidade seleciona turnos tardios (viés); reportar distribuição de turn/tokens dos pontos.
- Timeouts de pytest são artefato de infra: excluídos do piso, reportados à parte (`final_timed_out`).
- 3 replays com nº de decisões ≠ sufixo original mas mesmo reward (task `group_anagrams`) — catalogado, investigar se reaparecer em escala.
