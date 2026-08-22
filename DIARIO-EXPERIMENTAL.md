# DIÁRIO EXPERIMENTAL — Cross-Layer Agentic RL

> Registro cronológico de hipóteses, testes, resultados e conclusões, para a escrita do artigo.
> Convenções: C(d) = R_orig − R_cf (positivo = decisão original era melhor que o counterfactual);
> dr = r_replay − r_orig (teste0); I(H,M) = C(H,M) − C(H) − C(M). Seed mestre 20260821.
> Limitações permanentes: **I1** = pontos de intervenção do harness não são aleatórios (dependem
> de onde o threshold dispara); **I2** = flip de contexto confundido com comprimento do contexto.

---

## 2026-08-21 — Validação v2 (harness threshold=600, tasks v2, 10 tasks)

### Contexto/decisões de desenho
- Agente 2 camadas: modelo (Qwen3-4B via vLLM, T=0, seed=1234, thinking off) decide `tool_call`
  (write_file/run_tests/finish); harness (regras) decide `context_policy` (keep/summarize),
  `retry`, `termination`. Reward = fração de testes pytest que passam no sandbox.
- Tasks v2 desenhadas com constantes arbitrárias críticas APÓS o char 240 do enunciado —
  o summarize trunca a task a 240 chars, destruindo informação irrecuperável. Reward gradual
  (testes independentes, imports dentro das funções de teste).
- Execução SEQUENCIAL sempre (batching concorrente no vLLM pode quebrar determinismo a T=0).

### Teste 0 — Replay fidelity (hipótese: intervenção nula reproduz R exatamente)
- 30 baselines + ~90 replays nulos. **Resultado: 30/30 exact, piso de ruído = 0.0**
  (pré-registro: piso = max|dr| sem timeouts de infra).
- Conclusão: replay determinístico funciona; qualquer |C| > 0 é sinal, não ruído.

### Teste 1 — C(harness) (hipótese: flip keep↔summarize tem efeito causal detectável)
- 23 pontos de flip. **Resultado: 6/23 com |C| > piso; direção keep→summarize: 40% não-zero,
  C até ±0.86; direção summarize→keep: C = 0 consistentemente** (consistente com I1 — quando o
  summarize já disparou, voltar não recupera a informação destruída).
- Conclusões: (a) decisões do harness têm contribuição causal mensurável; (b) NUNCA agregar
  direções — são estimandos diferentes; (c) o efeito é assimétrico por construção da informação.

### Teste 2 — C(model) (hipótese: trocar a ação do modelo por a′ da própria política tem efeito)
- a′ amostrado da política a T=0.8, 8 seeds (2001–2008), aceito se parse válido e JSON canônico
  difere do original. Pré-registro: análise por transição; exclusões (timeouts, turnos com retry,
  pontos sem a′).
- **Resultado: 13/20 estados SEM a′ (política quase determinística em estados de reparo — só
  estados iniciais de write_file têm entropia); 7 counterfactuals write_file→write_file, 2/7 com
  |C| > piso, máx 0.86.**
- Conclusões: (a) C(model) mensurável; (b) ACHADO: a entropia da política concentra-se nos
  estados iniciais; estados de verificação/reparo são unânimes — limita onde C(M) é estimável
  sem mudar o estimando (perturbação estruturada ≠ counterfactual da política).

### Teste 3 — I(H,M) (hipótese: interação ≠ 0 existe e é identificável)
- Protocolo: por ponto, 3 replays (C_H: flip só; C_M: a′ só, do estado ORIGINAL do tool_call —
  do-operator; C_HM: fila [flip, a′]). Validação: replays nulos de fila devem ser exatos.
- Pré-registros: confirmatório = direção keep→summarize; saturado = qualquer r_cf ∈ {0,1};
  sucesso = ≥1 ponto não-saturado com |I|>0 condicional a 100% de nulos exatos.
- **Resultado: nulos de fila 16/16 exatos; 4 pontos com I = −0.75..−0.88; 1 não-saturado
  (rate_limiter_bucket, I = −0.86).**
- **ACHADO CENTRAL (mecanismo de screening-off):** ao forçar a′, a ação do modelo BLINDA a
  decisão do harness — C_HM = C_M, logo I = −C_H. A interação observada é 100% desse regime.
- Conclusão: I é identificável e tem estrutura mecanística interpretável; mas falta observar
  o regime de SINERGIA (I > 0) — risco para o claim "I como sinal de primeira classe".

## 2026-08-21/22 — Replicação v2b (threshold=900, mesmas 10 tasks)

- Teste 0: 30/30 exact, piso 0.0. Teste 1: sinal nas DUAS direções desta vez
  (summarize→keep n=3, 2/3 não-zero, C negativo — contexto mantido ajudou). Teste 2: 2/7 não-zero,
  máx 0.29. Teste 3: 6 pontos confirmatórios I = −0.75..−1.0, 1 não-saturado, nulos 16/16.
- Conclusões: (a) resultados replicam noutra config de harness; (b) saturação de reward domina
  os descartes de I (~80%); (c) screening-off segue sendo o único regime observado.

## 2026-08-22 — Revisão adversarial do plano-mestre (subagente revisor)

12 problemas; os que mudaram o plano:
- **P1 (crítico):** I 100% screening-off → I parece "correção de dupla contagem", não sinal novo.
  → Tasks S desenhadas para sinergia + GATE 1: se I>0 não for mensurável, reposicionar o claim JÁ.
- **P2/P3 (críticos):** treino C1 precisa de braço com crédito corrigido por interação
  (senão é single-layer, ≈ CHILL-Harness) e dose-matching POR ROLLOUT TOTAL (incl. replays).
- **P4:** piso não transfere entre configs → teste0 completo POR config; grid não pode variar
  task_chars (quebraria o desenho das tasks); sequencialidade é premissa de identificação.
- **P6:** C(H)>0 por construção = circularidade → tasks-controle (constantes recuperáveis).
- **P7/P8:** estatística do critic (split e bootstrap POR TASK, zero-inflation, k fixo=10) e
  features pré-decisão vs pós-hoc.
- Consolidado em PLANO-EXECUCAO.md (gates adaptativos).

## 2026-08-22 — Fase 0

### 0.1 Anomalia de sufixo (v2/v2b tinham 2 "mismatches" reprodutíveis)
- Hipótese inicial: infidelidade do replay. **Refutada.**
- Causa raiz: retries do LLM são gravados ANTES do tool_call (dentro de `_call_and_parse`);
  o replay a partir do tool_call reexecuta a geração e reproduz os retries decisão a decisão
  (verificado: estados byte-idênticos, mesma sequência retry_once→give_up→finish). O contador
  de sufixo não incluía os irmãos. Corrigido em teste0.py.
- Conclusão: replay era 100% fiel; a contabilidade estava errada. (Lição: investigar anomalias
  ANTES de escalar — era barato e eliminou uma ameaça de validade.)

### 0.2 Tasks v3 (30 tasks no pool total)
- **Estrato S (5, sinergia por desenho):** constantes pós-240; 2 arquivos; asserts COMPOSTOS
  (≥2 constantes por valor esperado) para que o output do pytest (últimos 1200 chars, vaza asserts)
  NÃO permita recuperar constantes individuais. Predição: C_H≈0 e C_M≈0 isolados, C_HM>0 → I>0.
- **Estrato C (5, controle anti-circularidade):** constantes DENTRO dos primeiros 240 chars;
  texto pós-240 redundante. Predição: C_H ≈ 0 (flip inócuo por construção).
- **Estrato L (10, anti-saturação):** 3 arquivos, ≥10 testes, 5 moderadas + 5 difíceis.
- Risco anotado: testes de fronteira com inputs adjacentes (5399/5401) permitem inferir o
  threshold aproximado — vazamento parcial aceito (taxas/fees continuam irrecuperáveis).

### 0.3 Yield pré-registrado (base v2+v2b, por 10 trajetórias/config)
- C_H: 23 pts (8 nz) | C_M: 7 pts (2 nz) | I: 5.5 pts (**1 não-saturado**).
- Regra disparada (yield I < 0.5/traj): mais testes por task (v3), max-per-traj ↑ (t1/t2: 4; t3: 3).
- Metas do grid: C_H ≥ 200 (60 nz), C_M ≥ 60 (15 nz), I ≥ 50 (15 não-sat). Regra de parada:
  1 rodada extra de até 10 tasks L, depois parar e reportar saturação como limitação endógena.

## 2026-08-22 — Fase A (grid em execução)

- Grid: threshold ∈ {600, 450, 900} × 30 tasks (v2 + v3), cadeia teste0(completo)→1→2→3 por
  config; thr600 primeiro para decidir o GATE 1 cedo. Sequencial, max_turns=12.
- Bug pego na 1ª execução: registry não resolvia tasks v3 no replay (KeyError) — corrigido;
  30 baselines aproveitados (idempotência via done_keys).
- Baselines g600 por estrato: C = 1.00 (5/5), S = 0.98, L moderadas = 1.00, L difíceis =
  0.00–0.27, V2 = 0.61. Espectro bom: S/C resolvidas (pré-condição p/ sinergia e controle),
  L difíceis dão gradiente no extremo baixo.

### ACHADO METODOLÓGICO — prefix caching quebra fidelidade de replay (2026-08-22)
- 1ª execução do grid g600: piso de ruído = 0.417 (era 0.0 em v2/v2b!). 7/270 nulos quebrados,
  todos em pontos com retry (geração divergente); l_vending_machine idx5 quebrou nas reps 0 e 2
  mas NÃO na rep 1 → não-determinismo ENTRE requisições idênticas sequenciais.
- Diagnóstico: 8 requisições idênticas seguidas eram determinísticas ENTRE SI, mas o vLLM V1
  liga **prefix caching (APC) por default** — a numérica do prefill depende do estado do KV
  cache (hit vs recompute), e em greedy quase-empatado um token flipa. Baseline e replay têm
  históricos de cache diferentes → divergência reprodutível; reps do mesmo ponto podem ou não
  compartilhar prefixo cacheado → divergência entre reps.
- Por que v2/v2b não quebraram: 10 tasks, prompts menores — sorte (sem quase-empates); com 30
  tasks e estados maiores a probabilidade de flip aparece. O piso 0.0 de v2/v2b era contingente.
- CORREÇÃO: servidor reiniciado com `--no-enable-prefix-caching`; sanity de determinismo ok;
  runs contaminados arquivados em runs/_apc_contaminado/ (não usar); grid REINICIADO do zero.
- PARA O PAPER (setup + threats): premissa de identificação do piso é (config, servidor,
  requisições sequenciais, **APC desligado**). Sequencialidade sozinha NÃO basta — achado
  útil a quem for reproduzir replay-based credit com vLLM.
- Preview NÃO-utilizável dos dados contaminados (só como hipótese): apareceram padrões além do
  screening-off puro — l_log_parser I=+0.15 não-saturado, l_shipping_batch com C_HM≠C_M — sugere
  que o regime de sinergia/interação parcial pode aparecer nos dados limpos. A confirmar no GATE 1.

- Replays nulos g600: todos exatos até agora. [ATUALIZAR com summary por config]
- Infra paralela pronta enquanto o grid roda: credit/dataset.py (agregador, features pre/post),
  credit/critic.py (zero-inflado, split/bootstrap por task, baselines dose-matched),
  paper/main.tex + paper/FIGURAS.md (F1–F5 fixadas antes dos dados).

### GATE 1 (pendente — decide o claim central)
- Perguntas: (a) existe I > 0 não-saturado nas tasks S? (b) tasks C têm C_H ≈ 0?
- Desfechos pré-definidos: SIM → "I como sinal de treino, dois regimes"; NÃO → reposicionar para
  "decomposição cross-layer + correção de dupla contagem" (screening-off ainda sustenta C1-braço 3).

## Sobre benchmarks (pergunta do orientando, 2026-08-22)

- Nossas tasks são SINTÉTICAS E PRÓPRIAS, não benchmarks públicos. Motivo: o desenho experimental
  exige controle que benchmark público não dá — posição da informação no prompt (pós-240),
  recuperabilidade (estratos S/C/L), reward gradual anti-saturação, determinismo de replay.
- Implicação: NÃO fazemos comparação direta de success rate com papers externos; a comparação
  é INTERNA (métodos de crédito sobre o mesmo ambiente). Threat de validade externa registrado.
- Mitigação planejada: VERIFICADO (research agent, 2026-08-22, fontes arXiv abs/html):
  - CHILL-Harness → GAIA, SWE-bench Verified, Terminal-Bench (inviáveis p/ Qwen3-4B em ctx 8192);
    Co-Harness → AIME/HMMT (outro domínio); 2608.19760 → ALFWorld; CAR → SCMs sintéticos;
    HASE → tasks próprias. **Comparação direta de success rate: NÃO existe com nenhum vizinho.**
  - **Única âncora real: C3 v2 (2603.06859)** — usa **Qwen3-4B em MBPP+**, replay por checkpoint
    e reporta **credit fidelity (Spearman vs ground truth de replay: 0.260 vs 0.152 MAPPO)** —
    o mesmo esqueleto de métrica do nosso critic, decomposição diferente (agentes vs camadas).
  - Decisão: adicionar **MBPP+ adaptado a multi-turn (~100 tasks)** como validação externa do
    critic (Fase D), custo ~30–60M tokens (1–2 dias na 4090). Reportar fidelity lado a lado com
    C3 ("mesma métrica, decomposição diferente"), nunca como head-to-head.
  - Barra evidencial de review: reproduzir o protocolo de auditoria de 2608.19760 (rank corr.
    vs replay GT, dose-matching) — já incorporado nas Fases B/C do plano.
