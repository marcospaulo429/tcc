# Requisitos — Harness V2 "mini-SWE" (fase de pensamento, nada implementado)

Data: 2026-08-25. Status: **rascunho para decisão** — nenhuma linha de código até aprovarmos escopo.

## 1. Objetivo

Responder à objeção central dos painéis ("harness de 1 decisão binária, tasks de função
única") mostrando que a decomposição C(model)/C(harness)/I(H,M) sobrevive em um agente
com **múltiplos tipos de decisão de harness** operando em **tasks multi-arquivo**.

Não é SWE-bench. É a menor extensão que muda a classe do resultado.

## 2. O que reaproveitamos (assets confirmados)

| Asset | Estado | Sobrevive ao V2? |
|---|---|---|
| Replay por re-execução + fila forçada | validado (Teste 0: nulos exatos) | **Sim** — não depende de snapshot de estado; FS se reconstrói |
| Sanitização de não-determinismo (`sandbox._sanitize`) | validado | Sim, estender (novos tools) |
| Serving determinístico (vLLM greedy, sequencial, APC off) | validado 2× | Sim — risco novo só em contexto longo |
| Schema de decisão (`decision_type` arbitrário) | já genérico | Sim |
| Pipeline experimental (pré-reg → chain → drift-check → painel) | maduro | Sim |
| Screening pivotal + estágios de orçamento | validado | Sim — essencial (trajetórias mais longas) |

## 3. Requisitos funcionais

### RF1 — Pool de tasks "mini-SWE" (congelado)
- 40–60 tasks; cada task = repo pequeno (3–10 arquivos, 300–2.000 LOC) + bug injetado
  + suite pytest que falha no estado inicial e passa na solução canônica.
- Testes rodam em **< 10 s** por execução, sem rede, sem docker, deps só stdlib
  (ou pool de deps fixado no venv).
- Fontes candidatas (avaliar nesta ordem):
  1. Geração sintética: templates de mini-bibliotecas (parser, cache, grafo, CLI,
     state machine) com bugs injetados por mutação controlada — mesmo método do
     nosso gerador atual, escalado para multi-arquivo.
  2. Adaptação de bibliotecas reais pequenas (single-purpose, MIT) com bug injetado.
- **Calibração de dificuldade obrigatória:** taxa de sucesso do Qwen3-4B no pool
  deve ficar em 30–70% (piloto com ~20 tasks antes de congelar). Fora disso o
  reward não tem variância e o experimento morre.
- Validação automática: solução canônica passa 100%; estado inicial falha 100%;
  determinismo dos testes verificado (3 execuções idênticas).

### RF2 — Tools do modelo (ações do LLM, não do harness)
- `list_files()`, `read_file(path)`, `search(pattern)`, `edit(path, old, new)`
  (ou write-file completo — decidir no piloto), `run_tests()`.
- Toda saída de tool passa por sanitização antes de entrar no contexto.
- Parsing de tool call robusto e determinístico (formato já usado no V1).

### RF3 — Decisões do harness (cada uma logada e forçável no replay)
| ID | Decisão | Braços |
|---|---|---|
| D-ctx | gestão de contexto | keep / summarize-rule / truncate-obs |
| D-obs | formatação de observação | saída de testes íntegra / só sumário de falhas; arquivo íntegro / trecho |
| D-retry | tool call malformado ou erro | retry com feedback de erro / pular turno |
| D-test | rodar testes após edit | sempre / só sob pedido do modelo |
| D-term | terminação | submit quando testes passam / continuar até orçamento / early-stop por estagnação |
- Requisito de desenho: **cada tipo de decisão precisa demonstrar pivotalidade no
  piloto** (existir par de braços que muda R em ≥1 task). Tipo sem pivotalidade é
  reportado, não silenciosamente descartado.

### RF4 — Recorder/replay
- Sem mudança conceitual: cada decisão vira checkpoint com `state_before`,
  `available_actions`, `chosen_action`. Fila forçada já suporta tipos novos.
- Novo: `state_before` inclui hash do estado do FS do sandbox (para diagnóstico de
  divergência, não para restore).

## 4. Requisitos não-funcionais

- **RNF1 Determinismo:** Teste 0 V2 (replay nulo) deve reproduzir R exatamente, ou
  medir piso e ele ser ≪ efeitos. Go/no-go da fase 3.
- **RNF2 Contexto:** cap de contexto em 8k tokens (emenda 2026-08-25: servidor vLLM
  em produção roda com max_model_len 8192 e não será tocado — sequencialidade e
  determinismo validados valem para ESTA configuração; cap menor também torna
  D-ctx/D-obs mais pivotais).
- **RNF3 Custo por episódio:** alvo ≤ 3 min (10–30 chamadas LLM). Task que estoura
  orçamento de turnos termina com R=0 — isso é sinal, não erro.
- **RNF4 Sequencialidade GPU:** inalterada — tudo sequencial, chains com watcher.

## 5. Orçamento estimado (GPU, sequencial na 4090)

| Bloco | Rollouts/replays | GPU estimado |
|---|---|---|
| Piloto de calibração (20 tasks × 3 cfg) | ~60 episódios | 3–6 h |
| Teste 0 V2 (fidelity, 60 tasks × 2 cfg × 3) | ~360 | 0,5–1,5 dia |
| Baseline + coleta (60 tasks × 3 cfg × 2 seeds) | ~360 | 0,5–1,5 dia |
| Screening pivotal (só decisões de harness, ~6/traj) | ~1.500–2.200 replays | 2–4 dias |
| Counterfactuals por tipo de decisão (5 tipos) | ~500–800/tipo | 3–5 dias |
| **Total GPU** | ~8–12k | **~7–12 dias corridos de GPU** |

Census exaustivo é inviável (25+ decisões/traj) — estágio Selective desde o início,
como já previsto no protocolo de 3 estágios.

## 6. Cronograma (com o loop autônomo rodando bem)

| Fase | Entrega | Estimativa |
|---|---|---|
| F0 | Pré-registro + fechamento deste doc | 1–2 dias |
| F1 | Gerador mini-SWE + piloto de calibração + pool congelado | 3–5 dias |
| F2 | Tools + Harness V2 + recorder integrado + testes unitários | 3–5 dias |
| F3 | **Teste 0 V2 (go/no-go de determinismo)** | 2–4 dias |
| F4 | Screening + counterfactuals (GPU-bound) | 5–8 dias |
| F5 | Análise + integração no paper + painel | 3–4 dias |
| **Total** | | **~3–4 semanas; com margem de risco, 4–6 semanas** |

## 7. Riscos e mitigações

| Risco | Prob. | Mitigação |
|---|---|---|
| Modelo fraco demais p/ multi-arquivo (reward sem variância) | média-alta | piloto F1 calibra dificuldade ANTES de congelar; abortar barato |
| Não-determinismo do vLLM em contexto longo | média | Teste 0 V2 é go/no-go; fallback cap 8k |
| Só D-ctx ter crédito pivotal (repete a crítica "1-bit") | média | piloto testa pivotalidade de cada tipo; desenho de tasks força uso de D-retry/D-term |
| Testes flaky nos mini-repos | baixa | validação de determinismo 3× na geração do pool |
| Episódios longos estouram orçamento GPU | média | cap de turnos; cortar pool para 40 tasks |
| Trajetórias longas → screening caro | alta | screening só em decisões de harness; Selective desde o início |

## 8. Anti-escopo (explicitamente fora)

- SWE-bench real, docker, repos externos grandes.
- Múltiplas famílias de modelo no V2 (fica como lever separado, pré-reg próprio).
- Treino (Act equivalente) no V2 — só medição; treino é decisão posterior.
- Harness aprendido/neural — políticas continuam por regra, substituíveis.

## 9. Critérios de sucesso do bloco

1. Teste 0 V2 com nulos exatos (ou piso medido e desprezível).
2. ≥3 tipos de decisão de harness com crédito pivotal não-nulo no pool.
3. Decomposição C_M/C_H/I(H,M) estimada por tipo de decisão, com CI.
4. Resultado integrado ao paper substituindo a limitação "1-bit harness".
