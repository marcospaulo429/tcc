# Cross-Layer Agentic RL — TCC

Crédito causal por decisão em agentes LLM de duas camadas (modelo + harness),
medido por **replay contrafactual determinístico** com piso de ruído zero.
Paper alvo: ICLR 2027. Fonte em [paper/main.tex](paper/main.tex) (template
ICLR 2026, 9 pp. de texto principal + apêndices A–L).

## Mapa do repositório

| Caminho | O quê |
|---|---|
| `agent/` | Loop do agente. V1: `loop.py`, `harness.py`, `llm.py`. V2 (mini-SWE, 5 tipos de decisão, protocolo texto-plano): `loop_v2.py`, `harness_v2.py` |
| `trajectories/` | `schema.py` (decisões tipadas), `recorder.py`, `replay.py` (fila de ações forçadas) |
| `interventions/` | Amostragem de alternativas do modelo a′ (`model.py` V1, `model_v2.py` V2 com escalação de temperatura) |
| `environment/` | `sandbox.py`, `registry.py` e pools de tasks: `tasks*.py` (v2/v3/v4/v5, curated, margem, MBPP+ `tasks_mbpp.py`, HumanEval+ `tasks_he.py`, mini-SWE `tasks_swe.py`) |
| `credit/` | `dataset.py` (consolida counterfactuals), `critic.py` (critic vs heurísticas dose-matched), `transfer.py` (transferência entre ambientes) |
| `rl/` | `policy.py` (política logística do harness), `train_c1.py` (4 braços dose-matched do treino V1) |
| `experiments/` | Cadeias de experimento (`teste0..6`, `census_v2.py`, `piloto_v2.py`, análises, `*_chain.sh`); estatísticas publicadas reproduzíveis via `make reproduce` |
| `scripts/` | Geradores de pools (`gera_tasks_*.py`) e famílias mini-SWE (`scripts/miniswe/`) |
| `runs/` | Artefatos brutos de execução (gitignored; fonte do `make reproduce`); logs soltos em `runs/logs/` |
| `tests/` | Suíte pytest (585+ testes) — `make test` |
| `paper/` | `main.tex`, `refs.bib`, `figs.py` (gera `figures/*.pdf`), template ICLR |
| `.github/agents/` | Definições dos subagentes (main, impl, revisor, research, runner, quick, iclr) |

## Documentos (ordem de leitura)

1. **README.md** (este) — índice e operação.
2. **[PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md)** — estado atual + o que vem agora. **Atualizar a cada marco.**
3. **[DIARIO-EXPERIMENTAL.md](DIARIO-EXPERIMENTAL.md)** — ledger append-only de pré-registros e desfechos. **Registrar ANTES de coletar dados; nunca editar entradas passadas; não renomear** (docstrings e o paper citam este arquivo).
4. **[PLANO-EXECUCAO.md](PLANO-EXECUCAO.md)** — plano por gates + pré-registros 1–29 (trilha de auditoria; docstrings citam itens por número; **não renomear**).
5. **[PLANO.md](PLANO.md)** — visão original do projeto (histórico).
6. **[REQUISITOS-HARNESS-V2.md](REQUISITOS-HARNESS-V2.md)** — desenho do harness V2 (mini-SWE).
7. **[paper/FIGURAS.md](paper/FIGURAS.md)** — inventário de figuras.

## Operação

- **Venvs:** `.venv` (uv, análise/experimentos: `uv run ...`) e `.venv-vllm`
  (serving; vLLM 0.8.5.post1 + transformers 4.51.3, Python 3.12 — vLLM 0.27 não
  funciona nesta máquina).
- **Servir o modelo** (RTX 4090 única; checar `nvidia-smi` antes):
  ```bash
  HF_HOME=~/hf_cache CUDA_VISIBLE_DEVICES=0 nohup .venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-4B --max-model-len 8192 --gpu-memory-utilization 0.85 \
    --no-enable-prefix-caching --port 8321 --disable-log-requests > vllm.log 2>&1 &
  ```
  **APC (prefix caching) deve ficar DESLIGADO em replays** — com APC o piso de
  ruído sobe a 0.417. Requisições em série, nunca concorrentes contra o mesmo
  servidor.
- **Testes:** `make test`. **Reprodução das estatísticas publicadas:**
  `make reproduce` (falha se qualquer número divergir; não usa GPU).
- **Paper:** `cd paper && ~/.local/bin/tectonic main.tex` (pdflatex não está
  instalado). Limite ICLR: 9 páginas de texto principal.

## Convenções

- Pré-registro no DIARIO antes de qualquer dado; falhas são resultados.
- Commits em português, prefixos `infra:`/`exp:`/`agent:`/`docs:`, pequenos e atômicos.
- Artefatos brutos em `runs/` (gitignored); números publicados sempre
  reconciliáveis por `make reproduce`.
- Logs soltos vão para `runs/logs/` (exceto `vllm.log`, que o servidor ativo escreve).