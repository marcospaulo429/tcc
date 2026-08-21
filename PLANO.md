# Cross-Layer Agentic RL — Plano do Projeto (TCC)

> Documento-mestre do projeto. Última atualização: 2026-08-21.
> Contexto operacional do agente: [.github/agents/main.agent.md](.github/agents/main.agent.md) e [.github/agents/research.agent.md](.github/agents/research.agent.md).

## 1. A ideia em uma frase

Medir, via **replay counterfactual** de trajetórias, a contribuição causal *separada* das decisões do **modelo (LLM)** e das decisões do **harness** (summarize context, spawn subagent, retry, termination) para o sucesso de uma tarefa — incluindo o termo de **interação** entre camadas — e usar esses sinais como crédito para **treinamento conjunto (joint RL)** das duas camadas.

## 2. Hipótese central

> Decisões do modelo e decisões do harness têm contribuições causais diferentes para o sucesso de uma tarefa, e essas contribuições podem ser estimadas via counterfactuals e usadas para treinamento conjunto (cross-layer credit assignment).

Formalização:

- Crédito causal de uma decisão: `C(d_t) = R_original − R_counterfactual` (replay a partir de t trocando só d_t).
- Interação entre camadas: `I(H,M) = C(H,M) − C(H) − C(M)` (sinergia positiva ou interferência negativa).

**Não assumimos que isso funciona.** A primeira pergunta científica é: *existe sinal causal mensurável nas duas camadas?*

## 3. Posicionamento na literatura (varredura de 2026-08-21)

Todos os blocos da ideia já existem **separadamente**. A interseção está aberta:

| Paper | arXiv | O que cobre | Risco p/ novidade |
|---|---|---|---|
| C3 "Exact Is Easier" | 2603.06859 | Crédito counterfactual **exato** por restauração de estado + leave-one-out (multi-agent LLM). **Nosso baseline metodológico.** | ALTO |
| Co-Harness | 2607.22688 | Joint harness+pesos (alternado, LLM-critic textual, sem crédito causal). **Baseline de joint optimization a bater.** | ALTO |
| HASE | 2607.03935 | Co-evolve pesos+harness+soluções num único processo agentic RL | ALTO |
| LEMON | 2605.14483 | GRPO + sinal counterfactual localizado p/ orquestração (camada única) | MÉDIO |
| Harness MDP offline RL | 2607.05458 | Harness como política aprendível (LLM frozen) | MÉDIO |
| CCI "More Is Not Always Better" | 2605.05716 | Interação/Shapley entre componentes de scaffold (estático, não por decisão) | MÉDIO |
| ClawGym II | 2608.16798 | Black-box RL através de harnesses, mix-harness training | BAIXO (infra) |
| Survey credit assignment | 2604.09459 | Identificação por restored-state, **replay fidelity** | Leitura obrigatória |

**Lacuna aberta (nossa contribuição):**
1. Decomposição de crédito causal C(model) vs C(harness) **na mesma trajetória**.
2. **I(H,M) cross-layer por decisão** como sinal de treino.
3. Critic de crédito **validado contra ground truth de replay**, usado em joint RL.
4. Orçamento ativo de counterfactuals (exhaustive → selective → active).

**Novelty risk: MÉDIO. Janela curta (meses).** O pitch NÃO é "counterfactual credit" nem "joint training" — é a decomposição cross-layer com interação, validada contra ground truth.

## 4. Arquitetura do sistema

```
                         TASK
                           │
                  ┌────────▼────────┐
                  │ Harness Policy  │  ← decisões: summarize/keep/truncate context,
                  └────────┬────────┘    spawn_subagent, retry, terminate
                           │
                  ┌────────▼────────┐
                  │   LLM Policy    │  ← decisões: tool calls, argumentos, código
                  └────────┬────────┘
                           │
                     Environment (sandbox de coding, reward via testes)
                           │
                        Reward
                           │
                  Cross-Layer Critic
                    /             \
           model credit      harness credit  (+ interação I(H,M))
                    \             /
                     └─── RL Update (joint)
```

Toda decisão (das duas camadas) é registrada com: `decision_id`, `decision_type` (model|harness), `state_before`, `available_actions`, `chosen_action`, observação, timestamps, custos (tokens/execução), parent/children, reward final. Formato JSONL.

## 5. Estrutura do repositório (alvo)

```
agent/            # model/, harness/, tools/, environment/
trajectories/     # schema.py, recorder.py, replay.py
interventions/    # model.py, harness.py, executor.py
credit/           # outcome.py, step.py, counterfactual.py, cross_layer.py
rl/               # grpo.py, joint.py, trainers.py
research_agent/   # search.py, extract.py, compare.py, novelty.py
benchmarks/       # clawgym/, harnessbench/, custom/
experiments/      # baseline/, counterfactual/, joint/, ablations/
configs/
paper/
```

Referências externas (usar como referência, **não forkar**): HarnessX (arquitetura de harness), ClawGym (tasks/trajectories/código de RL), HarnessBench (avaliação de harnesses), Agent Lightning (proxy/rollout para RL).

## 6. Princípios de implementação

1. **Infraestrutura antes de algoritmo.** Primeira entrega: `trajectory schema + recorder + replay engine`.
2. **Toda decisão é explícita e logável** (as duas camadas).
3. **Replay determinístico é o milestone zero.** Reexecutar de qualquer ponto trocando só uma decisão.
4. **Orçamento de counterfactuals em 3 estágios** — nunca reexecução exaustiva em escala.
5. **Interação entre camadas é sinal de primeira classe.**
6. **Agente simples primeiro.** Harness V1: context manager, tool selector, retry policy, termination.

## 7. Primeiros testes (ordem obrigatória)

### Teste 0 — Replay fidelity (pré-condição)

- **Hipótese:** replay com intervenção nula reproduz o mesmo R.
- **Métrica:** taxa de reprodução exata; onde divergir, catalogar fonte. Com temperatura > 0, medir a **variância de R sob intervenção nula** — isso define o **piso de detecção**: só afirmamos efeito causal se |C(d)| > piso.
- **Custo:** ~10 tasks × 3 pontos de replay × 3 repetições ≈ 90 rollouts.
- **Por quê:** ruído de replay vira viés direto no crédito. O survey 2604.09459 trata replay fidelity como condição de identificação.

### Teste 1 — Sinal causal do harness

- **Hipótese:** trocar `summarize_context` ↔ `keep_context` em um ponto produz C(d) distinguível do piso do Teste 0.
- **Variável manipulada:** só essa decisão; resto congelado.
- **Baseline:** distribuição de C sob intervenção nula.
- **Métricas:** média/variância de C(d); fração com |C| > piso; long-horizon check (divergência imediata ou N turns depois).
- **Custo:** ~20 tasks × 5 trajetórias × 2 pontos × 2 contrafactuais ≈ 400 rollouts.
- **Por que harness primeiro:** o efeito causal de decisões do *modelo* já é quase consenso (step-level credit); o lado incerto da hipótese é o harness. Testar o lado que pode matar a tese mais cedo e mais barato.

**Riscos de validade já mapeados:** confound de comprimento de contexto (registrar tokens, condicionar análise); pontos de intervenção não aleatórios (amostrar uniformemente); uma task dominar o sinal (reportar por task).

**Decisão de design pendente (o Teste 0 decide):** temperatura 0/seed fixa (determinismo forte) vs. temperatura real + múltiplas amostras (C vira esperança; C3 usa esta via frozen policy sampling).

## 8. Protocolo experimental completo

| Etapa | Objetivo |
|---|---|
| 1 | Baseline LLM + fixed harness |
| 2 | Coletar trajectories |
| 3 | Dataset de counterfactuals |
| 4 | Medir C(model) |
| 5 | Medir C(harness) |
| 6 | Medir I(H,M) |
| 7 | Treinar critic de contribuição causal |
| 8 | Joint RL |
| 9 | Ablations |
| 10 | Generalização p/ outro harness |
| 11 | Generalização p/ outro ambiente |
| 12 | Análise de eficiência |

**Baselines:** outcome-only GRPO · model-only credit · harness-only credit · independent optimization · **ours** (cross-layer + interaction + joint).

**Fases de treino:** (0) base model → (1) LLM trainable/harness frozen → (2) LLM frozen/harness trainable → (3) joint sem cross-layer credit → (4) joint + cross-layer credit → (5) + interaction.

**Ablations previstas:** tipo de crédito (outcome/step/counterfactual/cross-layer) · camadas (model/harness/both) · com/sem interaction · budget de counterfactuals (1/2/4/8) · tamanho do modelo (4B/8B) · complexidade do harness (simple/medium/complex).

## 9. Métricas

- **Performance:** success rate, Pass@1.
- **Credit quality:** correlação (predicted vs. counterfactual real), ranking correlation, top-k causal decisions.
- **Eficiência:** success/rollout, success/token, success/GPU-hour, success/counterfactual.
- **Generalização:** train harness A → test harness B; environment A → B.

## 10. Compute

- **Ambiente de trabalho (verificado 2026-08-21):** servidor compartilhado tipo DGX-1 — 8× Tesla V100-SXM2 32GB, 503 GiB RAM, 80 cores. Infra, Testes 0/1, treino do critic e joint RL (fases 7-8) rodam aqui.
- **GPUs sem reserva:** antes de qualquer job, checar `nvidia-smi`, escolher GPU livre e fixar `CUDA_VISIBLE_DEVICES=<idx>`. Preferir jobs de 1 GPU (Qwen3 4B/8B cabe em 32GB com LoRA/quantização).
- **Modelos:** Qwen3 4B para desenvolvimento/experimentos iniciais; 8B quando justificado. Nunca começar com modelos grandes.
- **Sandbox:** ambiente de coding isolado (containers), reward via pytest.

### Frota de agentes (paralelização do trabalho)

Definida em [.github/agents/](.github/agents/): `main` (orquestrador, Fable 5) delega para `impl` (implementação com spec fechada, Fable 5, paralelizável em módulos disjuntos), `revisor` (auditoria adversarial read-only, Fable 5), `research` (vigilância de literatura, Fable 5), `runner` (executar/monitorar jobs e GPU, modelo rápido) e `quick` (tarefas mecânicas, modelo rápido). Decisões de arquitetura, desenho experimental e commits ficam sempre no `main`.

## 11. Research Agent (vigilância de literatura)

Parte permanente do projeto (definido em [.github/agents/research.agent.md](.github/agents/research.agent.md)). Três modos: **Discovery** (papers novos), **Verification** ("qual paper existente é mais próximo desta contribuição?" — tentar matar a ideia), **Alert** (POTENTIAL CONFLICT se alguém fechar a lacuna 1+2+3). Repetir varredura a cada 2-3 semanas.

## 12. Disciplina de trabalho

- **Commits:** a cada entrega importante, mensagens em português, prefixo por área (`infra:`, `exp:`, `agent:`, `docs:`), pequenos e atômicos.
- **Ordem inviolável:** schema → recorder → replay → intervention engine → Teste 0 → Teste 1 → (só então) crédito e RL.
- **Todo experimento declara:** hipótese, variável manipulada, baseline, métrica, custo em rollouts.
- **Riscos de validade** (overfit ao harness A, leakage de reward, counterfactuals não comparáveis) sinalizados sempre.

## 13. Critérios de kill/pivot

- Se o Teste 0 mostrar piso de ruído alto demais → investir em determinismo (seeds, temperatura, sandbox hermético) antes de prosseguir.
- Se o Teste 1 mostrar C(harness) ≈ ruído → a hipótese principal cai; o resultado negativo ("decisões de harness não têm contribuição causal isolável") ainda é publicável e a infraestrutura sobrevive.
- Se um paper fechar a lacuna 1+2+3 → pivotar para a parte ainda aberta (ex.: budget ativo de counterfactuals, generalização cross-harness).
