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

### GATE 1 (DECIDIDO 2026-08-22, dados limpos g600 — pós-fix APC)
- Qualidade: piso 0.0 (270 nulos, 0 mismatches), nulos de fila do teste3 exatos → tudo interpretável.
- (b) Controles: c_* com C_H = 0 em 11/12 pontos → **o método distingue flip inócuo de flip
  destrutivo; circularidade de construto (P6) respondida.** Exceção instrutiva: c_temp_label
  turn 0 com C=+0.22 mesmo com TODA a informação nos primeiros 240 chars (auditado no prompt) —
  o efeito é COMPORTAMENTAL (prompt truncado muda a geração), não informacional. Nuance p/ paper:
  C(H) captura efeito causal total, não só o canal informacional.
- (a) Sinergia: **NÃO observada. C_HM = C_M exato em 21/21 pontos** — screening-off nos dois
  sinais (I=−0.86 quando flip prejudicial; I=+0.15/+1.00 quando benéfico, ex.: summ→keep que
  salva a task). As 5 tasks S não produziram I>0 não-trivial.
- **ANATOMIA (auditada nos replays de rate_limiter_bucket):** dois mecanismos compõem o
  screening-off total:
  1. *Completude informacional do do-operator:* a′ amostrado do estado ORIGINAL carrega as
     constantes no conteúdo do write_file — a ação forçada re-injeta a informação que o flip
     destruiu → C_HM=C_M por quase-necessidade no nosso espaço de ações.
  2. *Transiência da intervenção:* o harness downstream (regra de threshold, viva no replay)
     re-dispara summarize 1–2 turnos depois de qualquer jeito (verificado: braço M summariza no
     turno 2) — o flip só desloca o timing da destruição.
- **DECISÃO (pré-registrada):** claim central reposicionado para "decomposição causal
  cross-layer por decisão + screening-off como mecanismo dominante de interação + correção de
  dupla contagem no treino (C1 braço 3)". A anatomia vira a figura central F3.
- **HIPÓTESE NOVA (GATE-1b, pré-registro):** sinergia I>0 deve emergir sob PRESSÃO DE ORÇAMENTO:
  em tasks onde a recuperação é possível mas cara (asserts vazam constantes ← estilo v2),
  C_H≈0 (recupera com folga), C_M≈0 (a′ inócuo com contexto), mas flip+a′ juntos consomem
  turnos demais → C_HM>0 → I>0. Variável manipulada: max_turns 12→6. Baseline: mesmas tasks
  com max_turns 12. Métrica: I não-saturado > 0. Custo: ~10 baselines + ~60 replays. Rodar
  APÓS o grid (nunca concorrente — sequencialidade é premissa).

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

## 2026-08-22 — Review ICLR simulado (subagente iclr, criado a pedido do orientando)

- Score global 6/10 (borderline → accept condicional ao GATE 3). Diagnóstico: infraestrutura de
  medição e anatomia do screening-off estão sólidas; a significância depende do que ainda não
  rodou (critic, C1, MBPP+).
- **Weakness mais perigosa (W1):** sob screening-off puro, crédito marginal C_HM−C_M ≡ 0 →
  braço 3 pode ser indistinguível de "não treinar", pagando 3 replays por isso. **Ação tomada
  IMEDIATA (antes do C1 rodar):** braço 4 "zero" implementado em rl/train_c1.py (crédito ≡ 0,
  θ congelado, 0 replays, mesma dose de episódios) + grad_norm logado por episódio (contra a
  explicação "variância menor, não crédito", W6). Pré-registros 9 e 10 adicionados ao plano.
  GATE 3 agora exige braço 3 > braço 4.
- **W2 (N de I pequeno, 3 pts não-saturados/config):** teste certo do claim mecanístico é o
  sign test sobre C_HM=C_M EXATO (N=21+/config), não a magnitude dos não-saturados. Pré-registrado.
- **W3 (um modelo):** screening-off pode ser artefato da baixa entropia do Qwen3-4B. Nova
  ablation D2c: réplica do teste 3 com Qwen3-1.7B, thr600, ~10 tasks (~1 dia/4090).
- **W5 (trivialidade):** parte do screening-off (a′ re-injeta informação) é propriedade
  ESTRUTURAL do estimando, não achado — D1 vai separar: mecanismo 1 com argumento formal,
  mecanismo 2 (re-disparo downstream do harness vivo) como achado empírico, com fração
  quantificada nos replays já coletados.
- O que o review mandou NÃO atacar mais: fidelidade do replay, controles de circularidade,
  pré-registros, justificativa das tasks sintéticas, ausência de sinergia (GATE-1b basta).
- Pergunta de rebuttal mais difícil hoje: "por que pagar 3 replays se o crédito marginal é 0?"
  → resposta empírica virá do GATE 3 (braço 3 vs braço 4).

## 2026-08-22 — Fase A COMPLETA + GATE-1b + GATE 2 (pipeline pós-grid)

### Fase A fechada (grid 3 configs × 30 tasks + GATE-1b mt6)
- **Piso 0.0 em TODAS as configs** (g600/g450/g900/mt6: 270+270+270+270 nulos, exact_rate 1.0;
  nulos de fila do teste3: 61+64+61+61, 0 inexatos).
- Yields vs metas pré-registradas: C_H **248 pts / 92 nz** (meta 200/60 ✓✓); I **78 pts /
  18 não-sat** (meta 50/15 ✓); C_M **66 pts / 13 nz** (meta 60/15: n ✓, nz 13<15 —
  déficit marginal ACEITO, gargalo endógeno já conhecido: a′ inamostrável em ~70% dos estados;
  regra de parada NÃO disparada: rodada extra não mudaria a conclusão do critic, ver GATE 2).
- **Anomalia residual (threat menor, registrada):** 3/1080 replays nulos (só g450,
  l_grade_report) têm 1 retry a MAIS numa rep que noutra — não-determinismo residual a nível
  de token no vLLM mesmo com APC off; o retry recupera a MESMA ação e o reward é exato (dr=0).
  Piso em R não afetado. Nota p/ threats: o piso é definido em R, não em tokens.

### GATE-1b — DECIDIDO: screening-off é DEPENDENTE DE REGIME (achado central novo)
- Hipótese pré-registrada: sob pressão de orçamento (max_turns 12→6), o modelo perde a folga
  para "reparar" a intervenção → screening-off quebra e I≠trivial aparece.
- **Resultado: com folga (g600/g450/g900), screening exato C_HM=C_M em 57/57. Sob pressão
  (mt6), 18/21 — as 3 exceções TODAS no mt6 (P(acaso)=0.0175, hipergeométrico), incluindo:**
  - **sinergia genuína não-saturada** (l_vending_machine, turn 3: C_H=−0.09, C_M=−0.09,
    C_HM=0.00, I=+0.18 — cada intervenção isolada piora, as duas juntas se anulam);
  - aditividade pura (l_log_parser: I=0.00 com C_HM≠C_M);
  - interação positiva saturada (api_router: I=+0.38).
- Sign test do claim mecanístico (pré-registro 10): screening 75/78, P(X≥75|p=0.5)=2.6e-19.
- **Consequência p/ o claim (melhora!):** não é "screening-off sempre" (que soava degenerado) —
  é "screening-off domina quando o modelo tem orçamento para reagir; interação emerge sob
  pressão de orçamento". Regime é MANIPULÁVEL experimentalmente (max_turns) → F3 ganha um
  painel de regime. C1 treina com max_turns=6 (default) = regime onde crédito marginal ≠ 0.

### GATE 2 — critic vs baselines dose-free (resultado HONESTO, misto)
- C_H (n=248, 30 tasks, GroupKFold por task, bootstrap clusterizado):
  - Critic gbm: AUROC 0.846 [0.76,0.91]; linear: Spearman clusterizado 0.718 [0.62,0.81].
  - **Baselines triviais empatam no ranking:** position 0.752, context_size |−0.796| —
    ou seja, para RANKEAR C_H, heurísticas simples bastam; a vantagem do critic aprendido está
    só na DETECÇÃO de crédito não-zero (AUROC 0.846 vs 0.735/0.785), com ICs sobrepostos.
  - precision@10 ≈ 0 em todos (extremos são difíceis para todos). random: AUROC 0.495 ✓ sanidade.
- C_M (n=66): critic FALHA (AUROC ~0.5, ICs enormes) — data-starved, esperado.
- I (n=12 <20): pulado por pré-registro.
- **Leitura honesta (alinhada a 2608.19760):** nesta escala, critic aprendido ≈ heurísticas
  para ranking; o achado real é que C_H é ESTRUTURADO (position e context_size carregam quase
  todo o sinal de ranking — context_size anti-correlaciona ρ=−0.80, ligação direta com I2).
  Reportar como resultado negativo parcial + análise de estrutura, NÃO como contribuição de
  critic. A contribuição de treino (C1) não depende do critic: usa replay direto.

### D1/W5 — Sub-mecanismos do screening-off quantificados (experiments/analise_mecanismos.py)
- 75 pontos de screening exato; 52 "blindados" (C_H ≠ 0, o caso interessante).
- **mech1 (re-injeção estrutural):** nos 24 pontos com dicionário de constantes (tasks v3),
  **23/24 têm a′ re-injetando ≥1 constante crítica** — confirma: propriedade do estimando
  do-operator (a′ amostrada do estado PRÉ-intervenção carrega a informação), argumentável
  formalmente. 28 pontos v2 sem dicionário (limitação anotada: extrair constantes v2 depois).
- **mech2 (re-disparo empírico):** 22/52 — o harness vivo dispara summarize ≤2 decisões
  depois no braço M de qualquer forma (a intervenção só antecipa). 9 pontos têm ambos.
- 1 ponto com nenhum dos dois (l_log_parser mt6, |C_H|=0.08 — efeito pequeno, outra via).
- Consequência p/ F3: pizza/barras dos mecanismos por regime; mech1 formal + mech2 empírico.

### Fase C1 iniciada
- Calibração de λ lançada (pré-registro: UMA vez, antes de qualquer treino; valida que
  keep-always NÃO é ótimo sob R_eff com λ=1). 3 políticas fixas × 20 tasks de treino.
- **Resultado da calibração: λ=1 insuficiente** (keep_always domina: R=0.598/2.129 tok vs
  thr600 R=0.544/1.815 tok vs summ R=0.206/0.861 tok). Como R_eff é LINEAR em λ, a escolha
  foi analítica sobre os MESMOS dados (sem recoleta, sem iterar em treino — pré-registro
  honrado): cruzamento thr600>keep em λ*=17.2; **λ=25 fixado** — nesse ponto a política
  intermediária é a melhor das três (0.090 vs 0.066 keep vs −0.009 summ), i.e., existe ótimo
  não-trivial aprendível. Registrado ANTES de qualquer braço rodar.
- Cadeia lançada (experiments/c1_chain.sh): 4 braços × 3 seeds, SEED-MAJOR (comparação
  completa dos braços já na 1ª seed), budget 2000 chamadas/braço, idempotente.

### C1 seed 1 — prévia (outcome/ch/chm_cm prontos; zero rodando)
- Held-out (10 tasks, greedy): outcome R=0.847/R_eff=0.237 (571 eps); **ch COLAPSA:
  R=0.054/R_eff=−0.464 (278 eps)**; chm_cm R=0.847/R_eff=0.237 (104 eps).
- **Mecanismo do colapso do ch (verificado nos logs, não especulação):** 264/403 créditos
  positivos (média +0.106), θ_bias 0.3→3.3 monotônico ENQUANTO R de treino caía 0.374→0.142.
  Cadeia causal: assimetria de irreversibilidade (flip summarize→keep não recupera reward
  quando a informação já foi destruída) + custo de tokens do flip com λ=25 ⇒ C_H_eff > 0
  para summarize em trajetórias já perdidas ⇒ REINFORCE reforça summarize ⇒ mais destruição
  ⇒ feedback positivo. É a dupla contagem prevista no pré-registro — só que em forma de
  colapso, não de ruído.
- **Por que chm_cm resiste (auditoria dos créditos):** créditos genuínos C_HM−C_M são
  majoritariamente negativos (42/50, média −0.22) — condicionar na ação do modelo cancela o
  componente "trajetória já estava perdida" e sobra o sinal certo ("resumir piora"). Os 125
  fallbacks→C_H (71%, a′ não encontrado) têm média +0.076 mas NÃO envenenam: são estados de
  baixa entropia (reparo/verificação), distribuição diferente dos pontos que alimentam a
  armadilha no ch. Dose de veneno menor + 50 créditos genuínos fortes = θ→−4 (keep).
- Cautelas pré-registradas para a escrita: (a) chm_cm EMPATA com outcome (não "vence") —
  claim é robustez ao modo de falha, dose-matched; (b) falta braço zero e seeds 2–3;
  (c) efeito pode depender de λ (custo é o combustível da armadilha) — candidata a ablation;
  (d) fração de fallback (71%) tem que ser reportada.

### C1 seed 1 COMPLETA — GATE 3 preliminar (aguarda seeds 2–3)
- **zero: R=0.847/R_eff=0.237 (656 eps) — IDÊNTICO a outcome e chm_cm.** O controle W1 fez
  exatamente o que o reviewer previu: neste ambiente, a política inicial greedy (θ=0) já
  equivale ao ótimo simples (keep-ish), então NENHUM braço demonstra ganho sobre "não treinar".
- Leitura preliminar do GATE 3 (seed 1): braço 3 > braço 2 ✓ (0.237 vs −0.464, colapso);
  braço 3 > braço 4 ✗ (empate exato). Pelo desfecho pré-definido: o claim de treino muda de
  "crédito marginal ajuda" para **"crédito single-layer é ATIVAMENTE nocivo (colapsa abaixo
  de não-treinar); crédito corrigido por interação é seguro (não colapsa)"** — segurança,
  não vantagem. Efeito de teto: o ótimo de custo do ambiente é trivial (keep), não há o que
  aprender além de evitar o veneno.
- Disciplina: NÃO vamos recalibrar λ após ver resultados (pré-registro proíbe). Se quisermos
  demonstrar vantagem positiva do crédito marginal, será um experimento NOVO pré-registrado
  (C1b, ambiente com ótimo não-trivial — ex.: tasks com contexto longo onde keep estoura o
  orçamento), decidido APÓS as seeds 2–3.
- Seeds 2–3 rodando (decidem se o colapso do ch replica — esse é o resultado central).



### Auditoria do revisor sobre C1 (2026-08-22, subagente revisor) — 2 CRÍTICOS
- **CRÍTICO 1 (risco de artefato no resultado central):** o C_H do braço ch compara
  r_eff da trajetória ORIGINAL (continuação amostrada da política estocástica de
  coleta, ~50% summarize ⇒ barata em tokens) vs r_eff do replay do FLIP (continuação
  greedy = keep-always ⇒ cara). Sob λ=25 isso dá crédito positivo a summarize por um
  canal que NÃO é irreversibilidade — o colapso pode ser (em parte) artefato do
  estimador. chm_cm é imune (diff de dois replays greedy cancela o mismatch).
  → Pré-registro 11 criado; `experiments/audita_ch.py` recomputa C_H em 60 pontos
  como diff de dois replays greedy (dry-run validou o mapeamento dos 278 episódios;
  403 créditos: 264 pos / 68 neg / 71 zero). Roda automaticamente após a chain
  (experiments/pos_c1.sh, PID 3514926), junto com a calibração descritiva no
  held-out (item 4 do revisor).
- **CRÍTICO 2:** braço zero NÃO é "política inicial" — com tie-break `p > 0.5` e
  θ=0, greedy ⇒ keep_context SEMPRE. O controle é "keep-always sem treino".
  Corrigir a descrição no paper e no diário (feito aqui): o empate exato
  outcome=chm_cm=zero significa que esses braços convergem/permanecem em keep-always.
- **IMPORTANTE (itens 3–6):** (3) split held-out alfabético contém 5 tasks s_ e 0 c_
  ⇒ magnitude do colapso no held-out é inflada; GATE 3 reportará por estrato.
  (4) teto (keep ótimo) só verificado no treino ⇒ pos_c1.sh roda 3 políticas fixas
  no held-out (descritivo). (5) margem thr600−keep da calibração (λ=25) testada por
  bootstrap pareado (10k, seed 20260821): **+0.024, IC95 [−0.026, +0.079],
  P(diff≤0)=0.19 — NÃO significativa** ⇒ o teto era semi-previsível ex-ante;
  fortalece o caso do C1b e entra na escrita como limitação declarada.
  (6) variância de seeds no held-out é degenerada (greedy determinístico) ⇒ GATE 3
  final analisado por sinal/magnitude de θ e replicação do colapso, não por IC de
  médias idênticas.
- Verificado correto pelo revisor: simetria da contabilidade de tokens,
  forced_actions, reprodutibilidade do split, aritmética de λ*, empates exatos =
  identidade comportamental (prompt_tokens por task idênticos).

### C1 COMPLETA (3 seeds × 4 braços) — GATE 3 FALHA; história muda (2026-08-22)
- Held-out é BINÁRIO (greedy determinístico): keep-always → R=0.847/R_eff=0.237;
  summarize-always → R=0.054/R_eff=−0.464. Atrator final por seed×braço:
  outcome k/k/s, ch s/s/k, chm_cm k/s/s, zero k/k/k.
- **GATE 3 pré-registrado FALHA:** chm_cm > zero é FALSO (colapsa 2/3); chm_cm vs ch
  indistinguível (2/3 vs 2/3 colapsos, em seeds diferentes). A leitura da seed 1
  ("single-layer nocivo, corrigido seguro") NÃO replicou — era ruído de seed.
- Leitura honesta consolidada: REINFORCE (lr=0.5) numa paisagem de DOIS atratores
  com ótimo trivial (keep) é instável sob QUALQUER um dos três sinais de crédito;
  o único braço que nunca colapsa é o não-treinado (que já nasce no ótimo por
  construção do tie-break). Nenhum sinal demonstra vantagem nem segurança
  diferencial neste ambiente. Resultado NEGATIVO para o claim de treino no
  ambiente atual — reportar como está (pré-registro obriga).
- Sinal do C_H também instável entre seeds: frac positivos 0.66/0.63/0.35
  (s3 majoritariamente negativo → convergiu keep). A "armadilha de assimetria"
  da seed 1 não é determinística — depende da amostra inicial de episódios.
- Implicações: (a) o resultado central do paper volta a ser a DECOMPOSIÇÃO +
  screening-off dependente de regime (Fases A/B/D1), que está sólido; (b) C1 vira
  seção de "treino é instável com ótimo trivial" + motivação para C1b (ambiente
  com ótimo não-trivial, pré-registro novo) se houver tempo; (c) auditoria do
  CRÍTICO 1 (audita_ch, rodando) decide se o viés positivo de C_H em s1/s2 é
  artefato de mismatch de continuação — relevante para explicar a instabilidade.
- Artefatos: experiments/results/2026-08-22_c1_summary.json (12 células).

### Pós-C1: auditoria do CRÍTICO 1 + calibração held-out (2026-08-22 noite)
- **Auditoria audita_ch (pré-registro 11): C_H do braço ch NÃO é artefato de
  mismatch de continuação.** 60 pontos recomputados como diff de dois replays
  greedy (316 chamadas LLM): concordância de sinal 58/60, ZERO flips +→−,
  diff médio corrigido−logado = −0.0015. Pelo desfecho pré-definido, o viés
  positivo é genuíno — a instabilidade do treino não vem do estimador.
  Artefatos: experiments/results/2026-08-22_audita_ch.json.
- **Calibração descritiva no held-out (item 4 do revisor) DERRUBA o teto:**
  keep 0.237, summarize −0.464, **thr600 0.398**. O ótimo trivial (keep) só
  existe no TREINO; no held-out uma política de limiar dá +0.16 sobre keep.
  Leitura refinada do resultado negativo: não é só "ótimo trivial" — é que
  NENHUM braço aprendeu comportamento de limiar (a classe logística expressa
  thr600 via feature tokens/1000, mas o REINFORCE colapsa nos extremos via
  bias). Diagnóstico: updates dominados pelo termo de bias (feature 1 constante)
  >> termos de features; candidato a C1b barato: reduzir lr do bias ou
  normalizar features — MAS isso é experimento NOVO, pré-registro obrigatório.
  Artefato: experiments/results/2026-08-22_calibrate_heldout.json.
- Próximo: review ICLR simulado do pacote completo (pedido explícito do usuário),
  depois decidir C1b (agora com motivação forte: ótimo não-trivial JÁ EXISTE no
  held-out; generalização keep→thr600 é aprendível em princípio) vs D2c.

### Review ICLR nº 2 (pacote completo) + C1b lançado (2026-08-22 noite)
- Review 2 (subagente iclr): **6.5 borderline** (novidade 7, rigor 8, signif 5.5).
  Veredito central: o negativo do C1 é MATA-PAPER na forma atual porque é
  confundido por OTIMIZAÇÃO ("vocês testaram um otimizador quebrado, não
  crédito") — o diagnóstico do bias não salva, só o C1b salva. Rota recomendada
  com 1 semana de 4090: **C1b (3-4d) + D2c (1d)**; D2b vira limitação declarada.
  Ambos os desfechos do C1b são publicáveis: braços aprendem thr-like → paper
  entrega o título (7.5–8); ninguém difere → negativo IDENTIFICADO (~7).
  W3 nova: sinergia genuína é n=1 → dose-resposta max_turns ∈ {4,8} (meio dia).
  W4: reenquadrar critic como análise de estrutura + testar por estrato.
  "Não atacar": fidelidade, controles c_*, auditoria 58/60, dose-matching, APC.
- **Pré-registro 12 (C1b) escrito ANTES de rodar:** mesmíssimo protocolo do C1,
  muda SÓ otimização: (a) centering fixo a priori (tokens/1000 − 0.6 [default da
  família de harness], demais − 0.5 [ponto médio]); (b) lr 0.1; (c) clip norma 1.0.
  Desfecho primário: algum braço com held-out R_eff > 0.30 em ≥2/3 seeds.
  Implementação: center em rl/policy.py (CENTER_C1B), clip em train(), flag
  --c1b. 292 testes verdes (2 novos: centering não toca bias; passo ≤ lr·clip).
- **C1b chain LANÇADA** (experiments/c1b_chain.sh, 4 braços × 3 seeds, log
  runs/c1b_chain.log). Depois: D2c (Qwen3-1.7B) e dose-resposta W3.

### C1b COMPLETA — negativo IDENTIFICADO (2026-08-23)
- Desfecho primário (pré-registro 12) FALHA: nenhuma célula > 0.30; todas em
  0.237 (keep) ou −0.464 (colapso). Ninguém aprendeu o limiar que existe
  (thr600 = 0.398 no held-out).
- Mas o negativo agora é IDENTIFICADO (não mais confundido por otimização):
  (a) otimização sã e estável — outcome 3/3 keep com θ na DIREÇÃO certa
  (bias<0, peso tokens>0; crossover implícito 2.5k/5.8k/4.1k tokens — direção
  correta, magnitude insuficiente: os episódios raramente visitam estados >2.5k
  tokens, então não há gradiente além do crossover observado);
  (b) colapsos: outcome 0/3, ch 1/3, chm_cm 1/3 (ambos na s2), zero 0/3 —
  braços de crédito seguem MENOS estáveis que outcome mesmo com otimização sã
  (evidência fraca, n=3, mas consistente com C1);
  (c) frac créditos+ do ch normalizou p/ ~0.5 (0.48/0.56/0.44) sob a nova
  dinâmica — o viés extremo do C1 (0.66) era dependente da trajetória de θ.
- Leitura p/ o paper (desfecho b do review 2): "mesmo com otimização sã,
  REINFORCE nesta classe de política não descobre o comportamento de limiar
  aprendível em princípio; nenhum sinal de crédito muda isso; sinais de crédito
  single-layer e corrigido adicionam risco de colapso (1/3 vs 0/3)". O gargalo
  final é EXPLORAÇÃO (estados informativos raros), não crédito nem otimização —
  cadeia diagnóstica completa em dois atos, ambos pré-registrados.
- Artefato: experiments/results/2026-08-23_c1b_summary.json. GATE 3 fechado
  em definitivo (negativo em dois estágios, identificado).
- Próximo: dose-resposta W3 (max_turns ∈ {4,8}, 4B ainda carregado) → D2c
  (Qwen3-1.7B, troca de modelo no vLLM) → W4 critic por estrato (CPU).

### W4: critic por estrato (CPU-only, 2026-08-23)
- Pergunta do review 2: o critic ganha das heurísticas onde context_size não
  separa? **NÃO.** Dentro dos estratos (GroupKFold por task preservado, n_boot
  200, descritivo): L: gbm 0.747 vs position 0.741 vs |ctx| 0.741 (empate);
  V2: gbm 0.693 vs |ctx| 0.796 (heurística ganha); S: tudo satura (AUROC 1.0,
  crédito uniforme no estrato); L+V2: gbm 0.667/AUROC 0.811 vs |ctx| 0.77/0.81.
- Decisão de escrita (a executar na fase E): cortar a promessa de critic do
  abstract de vez; seção B vira "análise de estrutura do crédito": C_H é
  majoritariamente previsível por tamanho de contexto + posição, consistente
  com o mecanismo de destruição de informação (limitação I2 vira achado).
- Heurísticas por estrato (sp(|C|,·)): ctx −0.51 global, mas −0.91 em S vs
  −0.47/−0.58 em V2/L — a previsibilidade é ela própria dependente de estrato.
- Artefato: experiments/results/2026-08-23_critic_por_estrato.json.

### W3 dose-resposta COMPLETA (pré-registro 13) — monotonicidade FALHA, claim binário FORTALECE (2026-08-23)
- Pisos 0.0 e nulos exatos nas 2 configs novas (61+61). Quebras C_HM≠C_M por
  config: mt12 0/21, mt8 4/22, mt6 3/21, mt4 1/22.
- **Hipótese direcional pré-registrada (monotônica com pressão) FALHA**
  (Cochran-Armitage p=0.38). Forma observada: U invertido — quebras concentram
  em pressão INTERMEDIÁRIA. Interpretação exploratória (não pré-registrada):
  sob mt4 o orçamento é tão curto que quase toda trajetória falha de qualquer
  jeito (saturação semântica: flip não muda R que já é ruim), mascarando I.
- **Claim binário do GATE-1b FORTALECE:** folga (g600+g450+g900) 0/57 vs
  pressão (mt4+6+8) 8/65, hipergeométrico unilateral **p=0.0052** — agora com
  3 configs de cada lado (antes 57 vs 21). Reescrever no paper: "quebras de
  screening-off ocorrem apenas sob pressão de orçamento (0/57 vs 8/65), com
  relação não-monotônica na intensidade da pressão" — mais honesto e mais
  interessante que a monotonicidade.
- Estabilidade estrutural: os MESMOS pontos quebram entre configs
  (l_log_parser idx8 em 3/3; api_router idx1 e l_vending_machine idx11 em 2/3)
  — quebras são propriedade de decisões específicas, não ruído.
- Artefato: experiments/results/2026-08-23_w3_dose_resposta.json. F3 vira
  curva de 4 configs com anotação dos pontos recorrentes.

### D2c COMPLETA — replicação parcial com Qwen3-1.7B (2026-08-23)
- Hipóteses do pré-registro 14: (a) piso 0.0 **REPLICA** (0 nulos inexatos nas
  2 configs — premissa de identificação não é específica do 4B); (b) folga
  **REPLICA** (0/11 quebras, screening-off exato); (c) pressão **INCONCLUSIVA**:
  0/12 quebras, mas saturação 11/12 (vs ~70% no 4B) e yield reduzido — sob a
  taxa do 4B, P(0 em 12)≈0.21. Não é refutação; é falta de poder.
- Mecanismo do confound: o 1.7B falha mais tasks → r_orig menor → flip não
  piora o que já é ruim → saturação mascara I. É o MESMO fenômeno do mt4 no
  W3 (U invertido) — consistência interna entre os dois achados: a janela de
  detecção de interação exige competência intermediária (nem folga total, nem
  fracasso generalizado). Vira parágrafo de discussão, não limitação solta.
- vLLM restaurado para Qwen3-4B automaticamente (verificado).
- Artefato: experiments/results/2026-08-23_d2c_replicacao.json.

### Review ICLR nº 3 (pacote final) + análises W-B/W-C + fase E iniciada (2026-08-23)
- **Review 3: 7/10, borderline lean accept** (rigor 9!). Único MATA-PAPER restante
  era ESCRITA: título/abstract vendiam "Training with" que o paper não entrega.
- **W-C (análise decisiva, CPU): janela de competência parcialmente demonstrada.**
  Condicionando à não-saturação: folga 0/12 vs pressão 6/19 (p=0.037); o nulo do
  1.7B fica TOTALMENTE explicado (q17_mt6 tinha 1 ponto não-saturado — zero
  poder); o U invertido do mt4 é parcialmente mediado por saturação (taxa
  condicionada 0.045→0.143; ordem mt8 0.5 > mt6 0.33 > mt4 0.14 persiste).
  Veredito: mecanismo demonstrado p/ D2c, hipótese parcial p/ mt4 — discussão.
- **W-B: inferência clusterizada por task é fraca e reportamos ambas:** 3 tasks
  quebram sob pressão vs 0 na folga, sign test p=0.125; point-level p=0.005.
  Artefato: experiments/results/2026-08-23_wc_wb_analises.json.
- **Fase E executada no tex:** título novo ("When the Model Screens Off the
  Harness: Per-Decision Cross-Layer Causal Credit in LLM Agents"); abstract com
  ambos os p-valores, qualificador de modelo único e sem "provably"; T1 célula
  "treina com I" → "tested† (identified negative)"; apêndice "Pre-Registration
  Ledger" (14 pré-registros, incluindo os 3 que falharam); W-D (incompatibilidade
  com benchmarks públicos + enquadramento methods paper) esboçado em Threats.
- Restante da fase E: prosa das seções, figuras F1–F5, refs.bib, ledger em tabela.

### Review ICLR nº 4 (draft completo) + correções W1-W7 (2026-08-23)
- **Review 4: 7.5/10, lean accept** (clarity 6→8). Achou 3 imprecisões que a
  prosa introduziu (anatomia 23/22/9/1 "de 52" não fecha — denominador certo é
  23/24 anotados p/ mech1 e 22/52 p/ mech2; "pooled 0.718 (GBM)" — 0.718 é do
  linear; abstract invertia o referente 0.398/0.237). Todas corrigidas.
- **W6 (análise CPU decisiva): starvação de exploração DEMONSTRADA.**
  0 de 13.498 decisões context_policy em TODOS os braços/seeds visitaram
  estados ≥2500 tokens (máx 1532). A região onde thr600 paga é NÃO-VISITADA,
  inclusive no braço outcome com dose cheia (1789 episódios vs 786/319).
  Fecha a pergunta difícil do reviewer ("crédito viu 6× menos dados?"):
  mais dados da mesma distribuição não ajudariam.
- **W5 (honesto): contraste condicionado também é fraco clusterizado** —
  sign-flip pareado 4 tasks p=0.25, permutação de labels p=0.18. Reportado
  no paper ao lado dos p point-level.
- Contagem de nulos VERIFICADA nos artefatos: 1.695 nulos exatos (1.230
  teste0 + 401 anexos 4B + 64 no 1.7B); F1 e prosa corrigidas (antes: números
  inventados 1.253/23). Anomalia dos 3 retries declarada com def. do piso em R.
- Contribuições viraram lista enumerada; T1 100% inglês; ledger com resizebox.
- Artefato: experiments/results/2026-08-23_w5_w6_review4.json.
- Paper compila limpo (tectonic), 0 citações não resolvidas, 292 testes ok.

### Review ICLR nº 5 (verificação) + reenquadramento coverage (2026-08-23)
- **Review 5: 7.5/10, accept (lean).** Todas as 7 correções do review 4
  verificadas contra artefatos. Novidade 7, rigor 8.5, significance 6.5,
  clarity 8.
- **W-NOVA corrigida: "exploration" → "training-distribution state coverage".**
  O dado do W6 prova INALCANÇABILIDADE, não sub-exploração: o braço zero
  (keep-always de facto, 1910 episódios) capa em 1532 tokens — nenhuma política
  de contexto alcança ≥2500 tokens nas 20 tasks de treino; thr600 só paga em
  tasks held-out (l_vending_machine 5933 tokens). Reenquadrado em abstract,
  contribuições, §Training/Diagnosis e conclusão, com a defesa explícita:
  split alfabético fixado ANTES de conhecermos o gap.
- **P1 corrigido:** conjuntos 78/75/52 definidos — 78 pontos I (57 folga +
  21 mt6), 75/78 screening exato (o sign test do pré-reg 10 É essa contagem
  contra nulo 50/50; minha prosa duplicava o fato em dois claims), 52
  blindados (C_H≠0 apagado pelo flip conjunto), 24 anotados.
- **P2 corrigido:** AUROC 0.785 declarado como heurística |ctx| com sinal
  invertido.
- Paper compila limpo, 0 citações não resolvidas.

### Review ICLR nº 6 (confirmação) + correção de unidades W-A/W-B (2026-08-23)
- **Review 6: 7.5, accept (lean), condicionado a W-A (obrigatória) e W-B.**
  P1/P2/W-NOVA verificadas ok contra artefatos.
- **W-A confirmada por verificação própria: 5.933 era custo CUMULATIVO do
  episódio, não contexto por decisão.** Held-out keep-always capa em 1.200
  tokens por decisão (verificado nos logs de calibração) — abaixo do máx de
  treino (1.532). O Diagnosis foi reescrito em 3 passos: (1) limiares
  aprendidos (2,5k–5,8k) inalcançáveis em QUALQUER lugar ⇒ políticas
  aprendidas são keep-always em comportamento; (2) onde as políticas diferem
  no treino (thr600 dispara >600 tokens, região visitada), margem de reward
  é n.s. (+0.024, IC95 [−0.026,+0.079], P(≤0)=0.19 — W-B incluída, era o
  fecho que faltava); (3) dominância held-out do thr600 vem de estrutura de
  custo cumulativo que o treino nunca torna consequente.
- Claim reenquadrado: "binding constraint is the training task distribution"
  (não mais "state coverage", que era vulnerável). Propagado em abstract,
  contribuições, Diagnosis e conclusão.
- Paper compila limpo; 292 testes ok.
- **Estado do loop: 3 reviews consecutivos em 7.5; correções restantes são
  cosméticas (\todo autores, estilo ICLR oficial). Loop encerrado por
  convergência.**

## 2026-08-23 — Frente teórica (pós-review 6)
- Adicionada §"Screening-off, formally" (sec:formal) em main.tex: Prop. 1
  (identidade de dupla contagem: C_HM − C_M = C_H + I sempre; sob screening,
  C_H = −I exato; regra de correção = C_HM − C_M, o sinal do braço 3),
  Lema 1 (coalescência: em agente determinístico, estados iguais em qualquer
  passo ⇒ sufixos idênticos ⇒ C_HM = C_M com igualdade exata — explica os
  zeros exatos), Remark (pivotalidade: pontos não-pivotais têm todos os
  créditos ≡ 0; formaliza janela de competência e o nulo do 1.7B),
  Corolário (sinal do braço single-layer em regime blindado é inteiramente −I).
- Cuidado epistêmico: mecanismos (23/24, 22/52) são eventos indutores de
  coalescência (empíricos); só o lema é teorema. Corrigido antes do reviewer.
- Contribuições e abstract atualizados. Compila limpo, 0 refs quebradas.

## 2026-08-23 — Review 7 (7.5) e correções da seção formal
- Review 7 achou 2 erros lógicos reais (E-1: corolário afirmava que sinal
  single-layer é "correto em pontos quebrados" — falso, erra por I em todo
  ponto com I≠0, o próprio l_vending_machine inverte o sinal; E-2: "igualdade
  de reward certifica coalescência" — afirmação do consequente) + 2 imprecisões
  (E-3 pivotalidade "single flip"→"qualquer intervenção"; E-4 lema vale para R,
  não R_eff). Todos corrigidos.
- W-2 executado (experiments/w7_coalescencia.py, 0 rollouts): verificação de
  coalescência de trace nos 75 pontos screened. Resultado: 73/75 coalescem
  comportamentalmente (72 já no turno da intervenção), 29/75 atingem igualdade
  ESTRITA de estado (messages+workspace byte-idênticos) em 1–4 turnos; os 2
  que não coalescem (l_log_parser idx 10, g600 e mt6) são exatamente colisões
  de reward — o caso que E-2 previu, agora medido e declarado no paper.
  0 violações de determinismo de sufixo (após normalizar endereços ASLR e
  nomes de sandbox que vazam no output do pytest).
- W-3: "theorem" rebaixado (Prop.1 = "elementary algebra... value is the
  correction rule"). W-5: \todo da T1 resolvido — research agent verificou
  células contra fontes primárias: CHILL usa replay pareado OFFLINE p/ treinar
  estimador amortizado (célula ✓^off), CAR mede interação step-step
  intra-camada (célula --^s), fusão Co-Harness/HASE ok, HarnessCompass fora ok.
  refs.bib: autores reais do CHILL preenchidos.
- Compila limpo, 0 refs quebradas, 292 testes verdes.

## 2026-08-23 — Review 8: 8.0 (accept) + fix W1
- Review 8 verificou toda a aritmética contra o JSON e subiu para **8.0
  (accept)**: soundness 8.5, novelty 7.5, significance 6.5, clarity 8.5.
  Veredicto: teto sem GPU = 8.0; acima exige MBPP+ multi-turn e/ou 2º modelo
  powered (~1–2 GPU-dias cada, orçamento fechado, declarados em Threats).
- W1 (única superfície restante) corrigida: enunciado Corollary 2
  (coalescência comportamental no turno da intervenção ⇒ R_M=R_HM, via
  "context ops não tocam o ambiente"); contagem honesta em todo o paper:
  29/75 = hipótese do lema verificada estritamente, 72/75 = explicados pelos
  argumentos enunciados (29 ⊆ 72), 3 residuais declarados (2 colisões de
  reward + 1 ponto saturado com coalescência em profundidade 3, consistente
  mas não coberto). Abstract/contribuições: "hypothesis we verify" →
  "occurrence we verify".

## 2026-08-23 — D2d (pré-registro 15): replicação Qwen3-8B
- Cadeia q8_g600 (mt12) + q8_mt6 (mt6) + escalada q8_mt4 (disparou: <5
  não-saturados conf no mt6). Piso 0.0 e nulos exatos nas 3 configs (a ✓).
- Folga (q8_g600): 0 quebras não-saturadas (b ✓), MAS saturação endógena
  domina: 27/28 pontos saturados (8B resolve o pool no teto R=1.0) — evidência
  fraca, reportada como saturation-limited.
- Pressão (q8_mt6): 1 quebra não-saturada (l_door_controller cp_idx 3) > 0
  (c ✓ marginal). q8_mt4: 0/2, consistente com U invertido do 4B (pré-reg 13).
- Screening exato (todos os pontos): 23/28, 28/34, 28/35 por config; ponto
  não-saturado screened com I=-0.6154 em q8_mt4 (C_H=+0.6154 = -I, Prop. 1).
- Gradiente de competência 1.7B (nulo) → 4B (quebras sob pressão) → 8B
  (saturação domina): consistente com o Remark de pivotalidade; sem pooling.
- Yields 8B maiores (28/34/35 cf vs 21 no 4B g600). Análise em
  experiments/results/2026-08-23_replicacao.json.

## 2026-08-23 — D3 (pré-registro 16): segundo ambiente MBPP+ multi-turn
- 1º lançamento quebrou: environment/registry.py não resolvia tasks_mbpp
  (KeyError no replay). Fix 1 linha + teste (305 verdes), relançado idempotente.
- (a) Piso 0.0 ✓: 1080 nulos dedicados + 214 acoplados, TODOS exatos, em
  benchmark externo. Total do projeto: 4033 nulos exatos.
- (b) Folga: screening-off replica 31/31 (todos os pontos) ✓.
- (c) Pressão: 0 quebras não-saturadas em 6 pontos elegíveis — INCONCLUSIVO
  por saturação (59/66 saturados; 4B forte demais p/ MBPP+), como no D2c.
  Screening total no MBPP+: 66/66 exato, incluindo ponto não-saturado com
  I=-0.4 (dupla contagem viva em benchmark externo).
- Secundário (transfer critic A→B): NULO — Spearman pooled 0.03 (linear) /
  -0.08 (gbm), AUC 0.30/0.50, MAE pior que baseline constante; alvo B
  zero-inflado (86/94 zeros). Reportado como está: critic amortizado não
  cruza ambientes, consistente com o bar de 2608.19760.

## 2026-08-23 — Review 9 (7.5) e correção W1: escudo invertido no 8B
- Review 9 verificou artefatos e achou W1 real: eu reportava o 8B só sob
  métrica condicionada por saturação (raw: 5/28 quebras em FOLGA, taxas
  planas 18-20% entre regimes) enquanto o 4B usa raw nos headlines. Argumento
  do reviewer correto: clipping em {0,1} só contrai |C_HM-C_M| — saturação
  mascara nulos, não fabrica quebras.
- Investigação (experiments/analise_q8_shield.py, 0 rollouts): as 5 quebras
  de folga do 8B têm estrutura comum C_H=1.0, C_M=0.0, C_HM≈0.9 (I≈-0.1) —
  ESCUDO INVERTIDO (C_HM≈C_H). Mecanismo fecha com a anatomia: nas mesmas
  tasks, a′ do 4B re-injeta 5/5, 5/5, 6/6 constantes críticas (screened);
  a′ do 8B re-injeta 0/5, 0/6, 0/8, 0/5 (quebra). O escudo é propriedade do
  PAR modelo-harness, competence-dependent — achado, não sujeira.
- Paper corrigido: abstract e threat reescritos com taxas raw e mecanismo;
  ledger 15 held→partial; 59/66→60/66 (W3); transfer explicitado como C_M
  (W4); replicacao.json regenerado com todas as tags (W5).

## 2026-08-23/24 — Review 10: 8.0 (accept); itens de custo zero p/ 8.5 aplicados
- Review 10 auditou as correções do W1 e subiu para 8.0 (nov 8, rigor 8.5,
  sig 7.5, clareza 8.5). Veredicto: com itens 1-4 (custo zero), 8.5 é o
  score defensável e o TETO do pacote atual; acima exige pool curado à
  competência do 8B (~40-60 GPU-h), mantido como limitação declarada.
- Itens aplicados: (1) ledger "14 predictions"→16 (2 lugares); (2)
  analise_q8_shield.py estendido a mt6/mt4 — as 5 tasks de quebra da folga
  RECORREM identicamente (mesma estrutura por task) nas duas configs de
  pressão (recurrence 5/6 e 5/7), artefato regenerado; (3) declarado 4/5
  (invoice_pricing sem constantes anotadas) + regra de matching (substring
  do literal no a′ serializado); (4) I≈-0.1 → I∈[-0.2,-0.1].

## 2026-08-24 — Campanha noturna: D4 (curação falhou), D4b pré-registrado e armado
- Pré-reg 17 (D4): pool tasks_v4 (24 tasks h_, constantes pós-240, canônica
  24/24) rodado no 8B. Curação pré-registrada (janela (0.05,0.95), ≥12)
  FALHA: 17/24 baselines em 1.00 — perfil "pipeline aritmético de
  constantes" é fácil demais p/ o 8B. 7 fracionárias: donation 0.15,
  customs 0.23, sku 0.23, hotel 0.42, cargo 0.62, telco 0.69, turnstile
  0.77. Reportar como falha no ledger (desfecho previsto no pré-registro).
- Pré-reg 18 (D4b, ANTES de gerar o v5): pool v5 = 20 tasks x_ no perfil
  fracionário (FSM/protocolos, matching/alocação, validadores/parsers,
  ledgers, rating por intervalos). Curação idêntica na UNIÃO v4∪v5,
  baselines v4 reutilizados (determinístico), ÚLTIMA tentativa. Pool
  entregue e validado (canônica 20/20; suíte 551 verdes).
- Paper: lacuna explícita no Related Work + T1 com coluna "structure across
  models tested" e linha do replay audit; precedente 2608.19760 citado
  junto ao claim de inversão ("competence, not scale"). Novelty check do
  shield inversion: NOVO (risco médio-baixo), 7 vizinhos verificados.

## 2026-08-24 (madrugada) — D4b: curação PASSOU; quebras in-window replicam; mecanismo binário NÃO
- Fix ASLR validado em produção: 792/792 nulos exatos pós-fix (4 configs,
  piso 0.0 em todas). Fidelidade fechada.
- Curação (pré-reg 18): 22/44 na janela (7 v4 + 15 v5) ≥ 12 → PASSOU.
- Hipóteses: (a) piso 0.0 ✓; (b) Fisher mecanismo FALHOU (folga: 0 pontos
  ativos re-injetam, tabela degenerada p=1.0; pressão: 2/3 quebras COM
  re-injeção, p=0.94 direção oposta); (c) direcional FALHOU (pressão 3/31 =
  9.7% < folga 3/27 = 11.1% — plano, replica o "flat" do D2d).
- Resultado substantivo: quebras raw do 8B REPLICAM em pool curado
  in-window, incluindo quebra NÃO-saturada em folga (x_hours_bank:
  C_H=+0.25, C_M=-0.17, C_HM=0.00, I=-0.08) — fecha de vez a objeção de
  clipping/saturação. h_hotel_folio e x_hours_bank quebram em AMBOS os
  regimes com estrutura idêntica (recorrência de novo).
- Estrutura heterogênea: a assinatura do D2d (C_H=1.0, C_M=0.0, C_HM≈0.9)
  não recorre; cargo_manifest rastreia harness (C_HM=.46 vs C_H=.62),
  hotel_folio rastreia modelo (C_HM=.08 vs C_M=0). Mecanismo de re-injeção:
  explica os pontos anotados do D2d mas NÃO é necessário nem suficiente no
  pool curado — reportar como falha pré-registrada do teste (b).
- Artefatos: 2026-08-23_v4b_mecanismo.json, 2026-08-24_replicacao.json,
  runs/v5_curation.json.

## 2026-08-24 (madrugada) — Review 11: 8.5 (teto atingido); anatomia W2; D5 lançado
- Review 11 auditou todos os números do D4/D4b contra os artefatos (zero
  discrepâncias) e deu 8.5 accept (nov 8, rigor 9.0, sig 7.0, clar 8.0):
  teto do review 10 ATINGIDO, não excedido. Acima exige controle simétrico
  (4B no pool curado) e anatomia das quebras.
- Fixes W1/W3–W8 aplicados (contrastes escopados por pool, Fisher
  degenerado declarado, confound de família nomeado, §floor 2/5.257,
  F3 com barras curadas).
- Anatomia W2 (0 rollouts): base uniforme (summarize destrói ~100% das
  constantes; H-flip destrutivo em 6/6) + 2 padrões (resgate parcial por a′
  com constantes → conjunto intermediário; a′ benéfico anulado → conjunto
  volta ao original). Pontos recorrentes idênticos entre regimes: quebra é
  propriedade do ponto, não do regime.
- D5 pré-registrado (item 19) ANTES de rodar e lançado: 4B nas mesmas 22
  tasks curadas (q4cur_g600/q4cur_mt6), desfechos c1/c2/c3 declarados.

## 2026-08-24 (madrugada, cont.) — D5 integrado; review 12 (8.5) → review 13 (9.0 accept oral); D6 lançado
- D5 (controle simétrico): desfecho c2 — 4B TAMBÉM quebra no pool curado
  (4/16 folga, 2/23 pressão, quase todas não-saturadas; I=+0.77 turnstile,
  I=-1.42 hotel_folio); hipótese (b) de saturação-em-falha FALHOU (1/16,
  3/23). Claim re-escopado ao triple (modelo, harness, task); contraste
  pool-matched do D2d preservado; 396/396 nulos exatos (total 5.221).
- Review 12: 8.5, achou 1 contradição real (frase do claim antigo) e 1
  invariante superafirmado (turnstile não-idêntico entre regimes) —
  corrigidos + glosa pré-registrada de c2 citada por extenso no paper.
- Review 13 (mesmo reviewer): auditoria dígito a dígito OK → **9.0 accept
  (oral candidate)**. Residuais p/ 9.5: denominador do "6" (feito),
  gramática (feito), anatomia D5 (feita: flips de RESTAURAÇÃO
  summarize→keep são 3/4 dos pontos únicos do 4B — direção ausente no 8B;
  3º padrão "flips benéficos que se destroem em conjunto"; magnitude de I
  baseline-relativa em ponto recorrente), e célula vazia do desenho →
  D6 pré-registrado (item 20, ANTES de rodar) e lançado: 1.7B no MBPP+
  (mbpp17_g600/mt6), desfechos c1/c2/c3 declarados.

## 2026-08-24 (~6h) — D6 integrado; reviews 14 (9.3) e 15 (9.5 accept oral). META >9 SUPERADA.
- D6 (1.7B×MBPP+): desfecho c3 (inconclusivo por potência, gate ≥5 não-sat
  aplicado como pré-registrado: 2/22); bônus: piso 1.080/1.080 exato e
  screening raw 44/44 nos 2 regimes — 2ª célula do benchmark externo com
  screening incondicional. Célula de pressão do env B declarada vazia após
  2 tentativas honestas. Totais: 6.301 nulos exatos (2/6.733 contando
  pré-fix). Ledger: 20 pré-registros, 4 failed, 6 partial.
- Review 14: 9.3 — achou regressão factual real (3/4→2/4 pontos únicos de
  restauração na anatomia D5, propagada do relatório do impl; verificada
  por mim contra o JSON e corrigida) + 2 escopos. Review 15 (mesmo
  reviewer): condições cumpridas → **9.5, accept (oral candidate)**.
- GPU restaurada ao 4B pela cadeia. Suíte 552 verdes. Paper compila limpo,
  0 refs quebradas.
- Pendentes conhecidos (não bloqueiam): \todo{autores}, estilo ICLR
  oficial, anatomia de traço 1.7B (opcional).

## 2026-08-24 — Teste 4: sensibilidade de re-amostragem de a′ (pré-reg 21) — DESFECHO s1 (ESTÁVEL)
- Pré-reg 21 commitado (e7fb544) ANTES de rodar; script experiments/teste4_resample.py;
  população: 56 instâncias pivotais do census 4B; 3 schedules disjuntos (3001–8, 4001–8,
  5001–8); 168 tentativas → 152 a′ encontradas (16 sem alternativa: 6/4/6 por schedule),
  81% distintas do a′ publicado; 304 replays + 401 chamadas de amostragem; 0 timeouts.
- SLACK: 99/101 draws informativos screened (0.980, CI95 cluster-task [0.944, 1.0])
  ≥ 0.90 ⇒ desfecho pré-declarado s1. Restrito a a′ genuinamente novos: 79/81.
- Os 2 não-screened: (1) l_log_parser idx10 g600 s3000 — o residual de colisão já
  declarado, 1 de 3 draws; (2) invoice_pricing idx18 g900 s4000 — quebra de sinergia
  genuína em 1 de 3 draws (I=+1.57; os outros 2 screenam). Screening num ponto é
  propriedade dominante-mas-não-certa da distribuição de alternativas.
- PRESSÃO (mt6): as 3 quebras publicadas quebram de novo em TODOS os redraws (9/9)
  ⇒ quebra é propriedade do ponto, não do draw. mt6 informativos: 42/51 screened.
- Integrado no paper (abstract, §interaction novo parágrafo, §threats reescrito,
  claims table + ledger linha 21, custo de protocolo). Ledger agora 21 itens.
- Também nesta sessão: estatisticas_pivotais.py e margem_calibracao.py (regeneração
  com drift-check; CI da margem canônico agora [−0.029, +0.079] — o publicado antes
  veio de bootstrap ad hoc não versionado, corrigido no paper).

## 2026-08-24 — Rodada 4: batch A forense + pré-regs 22/23/24 + incidentes de concorrência
- Batch A zero-GPU (ee51bc9), auditoria forense da rodada 3: split
  discovery/confirmation (g600 descoberta 14/14; confirmação 39/42; estrito
  pós-registro 27/30); spec do Cochran-Armitage no drift-check (scores 0..3,
  unilateral crescente, z=0.3012 p=0.3816 — reproduz exato; o "não reproduzi"
  do estatístico da rodada 3 era spec errada dele, mas a culpa era nossa por
  não declarar a spec); harmful flip definido (58/60, 2 desacordos benignos);
  correção do apêndice ("verifiably precede" era falso para o item 10 — g600
  terminou 34 min antes do commit; agora declarado); analise_selecao.py:
  pontos retidos são precoces em ambos os modelos e retidos do 8B MAIS rasos
  que os do 4B (turn 0.65 vs 1.55, d≈0.3–0.5) ⇒ composição DESFAVORECE o
  contraste 0% vs 18% — achado favorável, no paper; abstract ≤200 palavras;
  tabela-síntese modelo×pool×regime; make reproduce (4 scripts drift-fail).
- Pré-regs commitados ANTES dos dados: 22 (célula ls600 — summarizer por LLM
  greedy no harness; piso + screening s1/s2/s3) e 23 (célula estocástica
  temp 0.8 — 5 pontos mt6, 12 seeds, braços null/M/HM, D=C_HM−C_M com CI
  bootstrap) em 97cb19b; 24 (C1c re-treino com pool margem-verificada,
  estágio A seleção + estágio B 4 braços × 3 seeds dose-matched 1600 calls)
  em 31fbc8e.
- INCIDENTES DE CONCORRÊNCIA (2×, ambos meus): (1) o bash da primeira cadeia
  sobreviveu a um kill parcial e avançou para o teste5 em paralelo com o
  teste0_ls600 relançado → nulo NÃO-exato reprodutível (l_discount_chain
  idx0, dR=+0.67 em ambas as reps, divergência no 2º call do retry).
  Diagnóstico: concorrência de batching no vLLM, não violação genuína da
  premissa do summarizer. Quarentena: runs/_ls600_concorrente,
  runs/_teste5_concorrente. (2) `margem_pool --help` EXECUTOU o estágio A
  (faltava argparse) em paralelo com a cadeia relançada → quarentena
  runs/_concorrente2; argparse adicionado e commitado. Lições: setsid +
  set -e na cadeia; nunca invocar módulos de experiments sem checar
  entrypoint. O incidente virou parágrafo no paper (stress-test acidental
  da premissa de sequencialidade: concorrência basta para quebrar o piso,
  de forma REPRODUTÍVEL — dR idêntico nas duas reps).
- Cadeia r4 definitiva (12:04): teste0_ls600 → teste3_ls600 →
  teste5_estocastico → margem_pool, estritamente sequencial.

## 2026-08-24 — C1c (pré-reg 24): DESFECHO s2 — o terceiro atrator
- Estágio A: margem medida nas 52 tasks únicas; pool = 16 com margem>0
  (held-out: keep −1.181, thr600 −0.746, margem +0.435). Estágio B: 4 braços
  × 3 seeds, 1600 calls dose-matched, otimização do C1b.
- RESULTADO: os 9 runs treinados (outcome, ch, chm_cm) convergem TODOS para
  summarize-always — R_eff=−0.143 com R=0.000 — enquanto zero (keep-always
  de facto) resolve 45% pagando −1.181. O treino está CERTO: neste pool de
  tasks longas sob λ=25, a falha barata universal é o ótimo verdadeiro do
  objetivo declarado (resolver custa ≈ a própria reward em tokens). O
  objetivo estava mal-especificado, não o algoritmo nem o crédito.
- Lição de desenho na forma final: margem verificada entre DUAS políticas
  nomeadas não basta — precisa ser verificada contra TODOS os atratores
  fixos expressáveis pela classe (summarize-always domina ambas), e λ tem
  que deixar resolver ser lucrativo. Secundário: braços de crédito chegam
  ao mesmo endpoint com ~9× menos episódios (756–825 vs 82–87) a dose
  igual de calls.
- Integrado: Act 3 em §training, ledger linha 24 (partial), claims row,
  contagens 24 itens. Commit 1ebfa34. D7 (HumanEval+) disparou em seguida
  automaticamente.

## 2026-08-24 — D7 (pré-reg 25): terceiro ambiente HumanEval+ — replicação limpa
- Pool congelado antes de rodar (60 tasks, 164 processadas, 0 descartadas,
  canônicas 100% no sandbox; fix de formato: assinaturas sem anotações typing).
- (a) piso 0.0: 1.080 nulos dedicados + 214 attached, todos exatos.
- (b)+(c): screening 76/76 pontos, 42/42 PIVOTAIS screened, 0 quebras nas
  duas configs; pressão inconclusiva por saturação (2 não-saturados < 5,
  gate pré-declarado) — desfecho c3, partial, mesmo padrão do MBPP+.
- Totais canônicos: 9.296 nulos (7.728+1.568), ever-run 9.728; agora
  3 modelos × 3 ambientes. Integrado: validade externa, tab:synthesis,
  tab:nulls, claims, ledger linha 25 (25 itens), drift-checks atualizados
  (reconcilia_nulos, estatisticas_pivotais he 21/21×2). make reproduce
  verde, 563 testes, 0 refs quebradas.

## 2026-08-24 — Teste 6 (pré-reg 26): estimando a′ₛ — DESFECHO s2, claim reescopada
- Motivação: 3/5 reviewers da rodada 4 apontaram a célula como decisiva
  ("o headline pode estar embutido no estimando").
- População: 44 instâncias pivotais keep→summarize dos 4 census; a′ₛ amostrado
  do estado SUMARIZADO (re-injeção impossível por construção); 0 falhas de
  amostragem, 0 timeouts, 44/44 a′ₛ distintos do a′ publicado.
- SLACK: 24/31 informativos screened (0.774, CI cluster-task [0.69, 0.88]) —
  bin s2 pré-declarado. Os 7 de-screened têm TODOS a mesma assinatura
  C_M=0, C_HM≈C_H — exatamente o canal de re-injeção desligado (validação
  mecanística). PRESSÃO: os 2 breaks keep→summarize de mt6 SCREENAM sob a′ₛ
  → break-ness também é propriedade do par (ponto, alternativa).
- Leitura: os dois estimandos BRACKETAM o fenômeno — a′ completo: 53/56;
  a′ₛ pobre: 24/31. Screening é real em ambos; a COMPLETUDE do escudo
  depende do acesso informacional da alternativa. Claim central reescopada
  no abstract e em threats. Ledger linha 26 (partial), claims row.

## 2026-08-24 — C1d / Act 4 (pré-reg 27): objetivo são — PRIMEIRA separação dos braços
- λ*=5 (grade {2,5,10,25}, analítico, pré-treino); pool 12 tasks onde thr600
  domina ESTRITAMENTE keep E summ; janela held-out verificada: keep 0.392,
  thr600 0.455, summ −0.031.
- RESULTADO (3/3 seeds): outcome 0.440–0.443 (R=0.661, escapa do keep) >
  ch 0.398–0.405 > chm_cm = keep = zero 0.392. Desfecho s2 + secundário
  FALHOU INVERTIDO — e a inversão é o achado: o crédito corrigido, por ser
  corretamente ZERO nos pontos screened, remove exatamente o gradiente que
  o viés do C_H fornecia; a dose-match cobra o imposto do replay (70–139
  episódios vs 280 do outcome) e o outcome vence limpo.
- Resposta identificada à pergunta motivadora: neste stack, crédito por
  replay custa mais compute do que o sinal adiciona, e corrigir o viés
  remove o pouco sinal que o viés dava. Replay é para MEDIR, não para
  treinar. Integrado: Act 4, abstract, ledger 27 (partial), claims row.

## 2026-08-25 — Piloto V2 mini-SWE (pré-reg 28 + adendos 28a/28b): GO nos 4 estágios
- Objetivo: go/no-go da infraestrutura V2 (harness multi-decisão, tasks
  multi-arquivo) antes das fases F2–F5 do REQUISITOS-HARNESS-V2.md.
  Resultados NÃO entram nas claims do paper (infraestrutura).
- Estágio 1 (CPU): pool 20/20 aprovadas (5 famílias × 4 variantes, repos
  4–6 arquivos, canônica 100%, reward inicial em (0,1), determinismo 3×);
  congelado em environment/tasks_swe.py.
- Rodada 1 (protocolo JSON): NO-GO mecânico — 0/20 sucessos com reward
  médio 0.802; Qwen3-4B greedy sem thinking NUNCA emite write_file com
  conteúdo em JSON (0 em 437 tool_calls; probes mínimos confirmam: até com
  ordem explícita responde run_tests/finish; loop determinístico de
  read_file até o cap de turnos). Estágio 3 GO já na rodada 1 (5/5 reruns
  byte-idênticos + 5/5 nulos exatos) — a maquinaria de replay V2 é sólida
  independentemente do comportamento do modelo. Artefatos:
  runs/piloto_v2_round1/.
- Recalibração 28a (protocolo): texto plano LIST/READ/WRITE/TEST/FINISH
  com WRITE em DUAS FASES (fase 2 pede bloco ```python``` em lista
  temporária; contexto persistente evolui só pela serialização canônica —
  invariante de replay preservado). thr 4500 (razão tokens reais/estimados
  ≈1.12; overflows com 7000/5500). ACHADO REPORTÁVEL em si: a fronteira
  modelo/harness inclui o PROTOCOLO DE AÇÃO — uma decisão de harness
  (formato do envelope) muda a taxa de write de 0% para normal no mesmo
  modelo. Conecta com a tese central: decisões do harness têm efeito
  causal de primeira ordem.
- Rodada 2: estágio 2 GO (10/20 = 0.50 na janela [0.30,0.70], malformado
  0.0, mediana 8.3 s); estágio 3 GO (10/10).
- Estágio 4 rodada 1: 2 tipos com flip < 3. Heurística de context_policy
  só amostrou summarize→keep (dR=0 ou overflow de contexto — overflow é
  consequência causal do flip sem R mensurável no serving 8k, reportado à
  parte); retry sem candidatos (malformado 0.0 — não recalibrável sem
  induzir malformação artificial).
- Recalibração 28b (seleção): priorizar keep→summarize não-vácuo.
  Resultado final estágio 4: GO — 3 tipos com flip: context_policy 3/8
  (dR +0.25, +0.2 e −0.0833: ambos os sinais), observation_policy 4/5
  (dR até +0.40 — compact_output AJUDA: menos ruído de traceback no
  contexto), termination 1/5 (dR −0.0833). test_schedule 0/5 (negativo
  honesto: defer_test não muda R porque o modelo roda TEST por conta).
- VEREDITO FINAL: GO. Fases F2–F5 do V2 desbloqueadas (pool 60, Teste 0
  V2 completo, census multi-decisão). Custo total do piloto: ~3 rodadas
  × ~10 min de GPU + probes (≪ orçamento de 2h previsto).
- Limitações do piloto: (i) episódios rápidos (mediana 8.3 s) sugerem
  tasks ainda fáceis para o 4B em metade do pool; (ii) flips de
  observation_policy concentrados no início do episódio (index 5);
  (iii) retry nunca exercitado no V2 real.

## 2026-08-25 — Census multi-decisão V2 (pré-reg 29 + adendos 29a/29b): desfecho s3, gate F4–F5 ABRE

### Setup
- Pool 60 congelado (15 famílias × 4; 20 do piloto byte-idênticas; 40 novas
  validadas 40/40 de primeira). Configs: v2_folga (thr4500/mt25/keep6) e
  v2_pressao (thr2500/mt12/keep4). Cadeia sequencial: base → nulos →
  screening → census → escalonamento (29b) → relatório.

### Resultados por estágio (verificados nos rows crus; report == recomputado)
- **Base (120 eps):** folga sucesso 0.483 (janela), 3 overflows de contexto
  reportados; pressão sucesso 0.10 mas reward médio 0.811 (variância parcial
  alta — mt12 corta episódios). Medianas 8.0 s / 1.7 s.
- **Teste 0 V2: 117/117 nulos exatos** (incl. 3 trajs com retry). O piso zero
  sobrevive à mudança de classe (multi-arquivo, 5 tipos de decisão, protocolo
  plain-text, duas configs).
- **Screening (693 replays): 114 pivotais; os 5 tipos são pivotais na folga**
  — retry 2/2 (primeira vez no projeto), test_schedule 4 (dR até −0.64),
  context 27/112, observation 25/108, termination 30/69. A objeção
  "harness de 1 decisão" está respondida no dado.
- **Census (48 pontos válidos):** screening por tipo — context 0.609 (n=23),
  observation 0.667 (n=12), termination 0.100 (n=10, todos duais 29a),
  test_schedule 0.333 (n=3). **Nenhum tipo ≥0.90. Desfecho s3** (quebra
  geral). frac não-screened = 0.50 → **gate F4–F5 abre** (limiar 0.20).
  I(H,M) ≠ 0 em 29/48, magnitudes até −0.73/+0.60.
- Estratos de temperatura (29b): 0.8 → 0.538 (n=26); 1.2 → 0.455 (n=22);
  divergência 0.084 < 0.15 → análise pooled é primária, como pré-registrado.

### Dois adendos mecânicos (registrados antes de retomar, dados intactos)
- **29a:** flip terminal (continue→terminate) torna o braço HM degenerado —
  R_HM ≡ R_H por determinismo. Interpretação: dual do fenômeno central, o
  HARNESS faz screening do MODELO. Os 10 pontos de termination do census são
  todos deste tipo (screen 0.100 = o a′ quase sempre importa quando o episódio
  continua, e nunca importa quando o harness o corta).
- **29b:** o sampler a′ do V1 (temp 0.8) falha em 87/114 pontos no protocolo
  plain-text — ações de 2–4 tokens têm distribuição quase determinística
  (achado reportável: o envelope da ação afeta o ESTIMANDO, não só a taxa de
  write). Escalonamento a temp 1.2 recupera 22; 65 pontos ficam sem a′ e são
  contados como exclusão.

### Interpretação (para o paper)
- **O screening-off é regime-dependente também na direção construtiva:** no
  stack V1 (single-file, 1 decisão dominante) a regra no-free-lunch fechou o
  gate e 4 atos de treino confirmaram; no stack V2 (multi-arquivo, 5 decisões)
  a mesma regra ABRE o gate — 50% de massa pivotal não-screened. A proposição
  prop:nfl ganha os dois ramos demonstrados empiricamente.
- Nota de validade: com n=48 e exclusão de 65 pontos sem a′, as taxas por tipo
  têm IC largo; test_schedule (n=3) não sustenta claim próprio. s3 avaliado
  conforme o literal do pré-reg (sem exigência n≥5); com filtro n≥5 o desfecho
  não muda (context/observation/termination todos <0.75 com n≥10).
- Treino F4–F5 continua FORA desta submissão (anti-escopo do V2): o gate
  aberto é reportado como predição testável, não como licença executada.

### Custo
- Cadeia inteira: ~75 min de GPU (base 12 min, screening ~35 min, census+esc
  ~25 min) — ordens de magnitude abaixo do orçamento de 7–12 dias do doc de
  requisitos.

## 2026-08-26 — PRÉ-REGISTRO 31: braço outcome-only EPISODE-MATCHED no Ato 4 (confound R1-W1 do painel rodada 7)

### Motivação (registrada antes de qualquer dado)
No Ato 4 (pré-reg 27), o outcome-only venceu a dose-matched de chamadas LLM,
mas treinou com 279–284 episódios contra 137–139 (ch) e 68–70 (chm_cm). O
painel (R1-W1) aponta o confound: a vitória pode ser (a) "o viés do C_H é
load-bearing mas o imposto do replay domina" OU (b) puro tamanho de amostra.
Controle: outcome-only com o MESMO nº de episódios dos braços de crédito.

### Desenho (custo ~42 episódios greedy, sem treino novo)
O treino é determinístico dado (arm, seed): θ é atualizado sequencialmente e
train_log.jsonl grava θ após cada episódio. Logo o braço episode-matched é o
θ do run outcome existente FATIADO no episódio N — idêntico ao que um run
parado em N produziria (nenhuma dependência futura). Só a avaliação held-out
é nova.
- **Fatias (por seed):** ch-match N = 139/139/137 (s1/s2/s3) → θ = linha
  episode_idx N−1 de runs/c1d_outcome_s{s}/train_log.jsonl.
  chm_cm-match N = 70/68/70 (secundário).
- **Avaliação:** rl.train_c1.evaluate, held-out = 6 tasks de
  runs/c1d_margem/pool.json (resolvidas via environment.registry), greedy,
  center=CENTER_C1B, λ=5.0, seed = seed do braço (1/2/3) — protocolo
  idêntico ao c1d.
- **Fidelity check (gate de validade):** re-avaliar θ final do outcome s1
  (linha 283); deve reproduzir heldout mean_R_eff = 0.440. Se divergir,
  ABORTA e investiga não-determinismo do serving antes de interpretar.
- Referências fixas (do c1d, não recomputadas): outcome full 0.440–0.443;
  ch 0.398–0.405; chm_cm = keep = zero = 0.392.

### Desfechos declarados (primário = ch-match)
- **o1 (leitura do Ato 4 sobrevive):** outcome_em > 0.405 (máx do ch) em
  ≥2/3 seeds → a vitória do outcome NÃO é tamanho de amostra; "bias is
  load-bearing + imposto do replay" fica identificado sem confound.
- **o2 (leitura de amostra):** outcome_em < ch por-seed em ≥2/3 seeds → a
  vitória do Ato 4 era contabilidade de episódios; por-episódio o crédito
  C_H é MELHOR sinal que outcome — reescreve a conclusão do Ato 4 (o
  imposto do replay vira a história inteira, não o viés load-bearing).
- **o3 (intermediário):** outcome_em ∈ [0.392, 0.405] em ≥2/3 seeds →
  outcome precisa de mais episódios que o crédito p/ escapar do atrator
  keep; nuance reportada, conclusão do Ato 4 enfraquecida mas não invertida.
- Secundário (chm_cm-match, 70/68/70): mesmas comparações contra 0.392.
- Sem teste de hipótese formal (3 seeds, 6 tasks): reportar per-seed e
  per-task, mesma convenção do Ato 4.

### Numeração
Pré-reg 30 fica RESERVADO para os controles de estimando V2 (re-amostragem
de a′ + a′_s no census), conforme PROXIMOS-PASSOS.md; 31 é registrado antes
por ser o item nº 1 do AC.

### DESFECHO pré-reg 31 (2026-08-26, mesmo dia): o1 — a leitura do Ato 4 SOBREVIVE
- Fidelity gate: re-eval do θ final outcome s1 reproduziu held-out R_eff
  0.4402141608 com IGUALDADE EXATA (38 chamadas). Determinismo do protocolo
  de avaliação confirmado dias depois do c1d, mesmo servidor.
- **ch-match (primário, N=139/139/137):** outcome_em = 0.4100 / 0.4498 /
  0.3984 vs ch = 0.4046 / 0.4046 / 0.3984. outcome_em > máx(ch) em 2/3
  seeds → **o1**. No s3, outcome_em = ch com igualdade EXATA (as duas
  políticas greedy convergiram ao mesmo comportamento held-out).
  outcome_em ≥ ch em 3/3.
- **chm-match (secundário, N=70/68/70):** 0.4096 / 0.4372 / 0.3917 vs
  keep=0.3917. Acima do atrator em 2/3 (s3 = keep, igualdade exata) —
  mesmo com METADE dos episódios, outcome escapa do keep onde o braço
  corrigido nunca escapou.
- Nuance honesta: variância entre seeds maior no corte 139 (0.398–0.450)
  que no run completo (0.440–0.443) — esperado com menos dados; s2
  episode-matched (0.4498) supera até o run completo (não-monotonia de
  REINFORCE).
- **Conclusão: a vitória do outcome-only no Ato 4 NÃO é artefato de tamanho
  de amostra.** Episode-matched, o outcome ainda ≥ C_H em 3/3 e > em 2/3;
  a leitura "viés load-bearing + imposto do replay" fica identificada sem o
  confound R1-W1. Custo: 44 chamadas × 7 células ≈ 260 chamadas LLM, ~12 min.
- Artefatos: runs/ato4_em/ (summary.json + 7 células), experiments/ato4_em.py.

## 2026-08-26 — PRÉ-REGISTRO 32: treino V2 (F4–F5) — o ramo ABERTO do no-free-lunch, exercitado

### Licença e accounting do gate (fixados EX ANTE, antes de qualquer rollout)
O census (pré-reg 29) abriu o gate F4–F5 sob 3/4 contabilidades. A
contabilidade PRIMÁRIA desta fase, fixada agora: **pontos medidos sem duais
degenerados = 15/38 = 0.39 ≥ 0.20 → gate ABERTO** (recomendação do painel
rodada 7; os duais 29a são degenerados por construção, R_HM ≡ R_H). As
outras 3 contabilidades ficam reportadas, não decisórias. Isto revoga o
anti-escopo "treino fora do V2" do REQUISITOS-HARNESS-V2.md — decisão
tomada com o gate aberto e pré-registrada aqui.

### Predição sob teste
Prop. nfl / Cor. gate: com massa pivotal não-screened ≥ 0.20, crédito por
decisão PODE adicionar sinal sobre outcome-only à mesma dose. O V1 (gate
fechado) confirmou o ramo fechado em 4 atos; este é o primeiro teste do
ramo aberto. Falha aqui NÃO quebra a regra (a regra é um teto, não um
piso) — mas confirma que ela não é vazia só quando fecha; desenho e
desfechos abaixo tornam qualquer resultado publicável.

### Desenho — Estágio A (calibração analítica, protocolo do Ato 4/pré-reg 27)
- Config v2_folga (thr4500/mt25/keep6), pool 60 congelado
  (environment.tasks_swe), Qwen3-4B greedy, APC off, sequencial.
- 3 políticas fixas × 60 tasks (rl.train_v2 calibrate): keep_always
  (thr 10^9), summarize_always (thr −1), default (thr4500). Uma passada;
  R e prompt_tokens por task permitem recompute analítico de R_eff(λ)
  para qualquer λ sem GPU nova.
- Grade λ ∈ {1, 2, 5, 10, 25}. Task ELEGÍVEL sob λ: default domina
  ESTRITAMENTE keep_always E summarize_always em R_eff(λ). λ* = λ que
  maximiza elegíveis (empate → menor λ). Pool de treino: elegíveis
  ordenadas por margem mínima de dominância desc, cap 16, mínimo 10
  (senão ABORTA — reportável). Ranks pares = treino, ímpares = held-out.
- Regra idêntica ao pré-reg 27 exceto o par de atratores (V2: thr4500).

### Desenho — Estágio B (treino, 4 braços × 3 seeds)
- rl.train_v2: braços outcome / ch / chm_cm / zero; budget 1600 chamadas
  LLM por célula (dose-matched, TODA chamada conta: episódios + replays +
  a′); seeds 1/2/3; lr 0.1, clip 1.0, CENTER_V2, k_credit 2; λ = λ* do
  estágio A; avaliação greedy no held-out.
- **Contabilidade dual desde o desenho (lição do pré-reg 31):** ao final,
  o braço outcome é TAMBÉM avaliado fatiado nos nº de episódios dos braços
  ch e chm_cm por seed (θ do train_log; protocolo idêntico ao 31, mesmo
  fidelity gate de re-eval exata do θ final do outcome s1).
- chm_cm: fallback p/ C_H quando a′ não encontrado (sampler V2 com
  escalação; taxa de fallback é resultado reportável — census: 87/114 a
  temp 0.8).

### Desfechos declarados (primário: held-out mean R_eff, comparação por seed)
- **s1 (ramo aberto confirmado):** ch OU chm_cm > outcome em ≥2/3 seeds
  SOB AS DUAS contabilidades (dose-matched E episode-matched).
- **s2 (aprendizado sem ordenação de crédito):** ≥1 braço escapa dos dois
  atratores fixos, mas crédito ≤ outcome em ≥2/3 em qualquer contabilidade.
- **s3 (sem aprendizado/colapso):** nenhum braço > max(atratores) em 2/3.
- Secundário: chm_cm ≥ ch por seed (o crédito corrigido não pode perder
  para o viesado onde a massa não-screened domina — predição da prop).
- Convenção de sempre: 3 seeds, per-seed e per-task reportados, sem
  p-valor de fachada.

### Custo estimado e riscos
- Estágio A: 180 episódios (~2.000–5.000 chamadas, 1–3 h GPU).
- Estágio B: 12 células × 1.600 chamadas ≈ 19.200 chamadas (~6–20 h GPU,
  sequencial). Watcher por chain script; células idempotentes.
- Riscos: (i) elegibilidade < 10 → aborta reportável (landscape sem sala
  p/ política treinável); (ii) episódios V2 longos podem reduzir nº de
  episódios/célula — a contabilidade dual mitiga; (iii) saturação de
  reward em parte do pool 60 (metade fácil demais p/ 4B) — a seleção por
  margem endereça.

### Emenda 32a (2026-08-26, registrada ANTES de retomar; nenhum dado do estágio A foi produzido)
- FATO: calibrate abortou na 1ª task com BadRequestError — keep_always
  estoura o max_model_len 8192 do serving (fenômeno já conhecido: 3
  overflows na base do census; lá, replays com overflow eram EXCLUÍDOS por
  "consequência causal sem R mensurável").
- REGRA NOVA (só para treino/calibração/avaliação do pré-reg 32): overflow
  de contexto = episódio FALHO com R=0 e tokens = tokens de prompt
  efetivamente pagos até o estouro. Justificativa: no treino o agente vive
  NESTA config de serving (RNF2: cap 8k é parte do ambiente); uma política
  que estoura o contexto falha a task de verdade — é exatamente o custo
  causal que λ deve precificar. A regra de EXCLUSÃO do census permanece
  válida lá (estimando de medição ≠ estimando de treino; documentado).
- Replays de crédito que estouram sob o flip: mesmo tratamento (R=0 do
  replay) — o flip causou o estouro; crédito mede a consequência.
- Episódio com overflow não tem trajetória completa → braços de crédito
  não amostram pontos nesse episódio (sem replay possível); braço outcome
  usa o decision_log da política (φ/ação) normalmente.
- Implementação: rl/train_v2.py (collect_episode, calibrate,
  _replay_with_policy) + testes; commit antes de retomar a cadeia.

### DESFECHO do pré-reg 32 (2026-08-26): ABORT no estágio A — critério registrado disparou
- Calibração (3 políticas × 60 tasks, 20 min GPU) completou; emenda 32a em
  ação: keep_always estoura o contexto em 40/60 tasks (R=0, tokens pagos →
  mean_R_eff = −0.088). summarize_always: 0.534; default (thr4500): 0.331.
- Sob a grade λ ∈ {1,2,5,10,25}: elegíveis 3/1/0/0/0 < 10 → ABORT
  (runs/v2_train/pool_32_aborted.json).
- DIAGNÓSTICO (análise sem GPU sobre os mesmos dados): em R cru o default é
  o MELHOR (0.849 vs 0.810 summ / 0.332 keep) — o landscape TEM sala; a
  grade de λ é que estava mal escalada. Herdamos {1..25} do V1, mas
  episódios V2 custam ~3.500–8.000 prompt tokens/turno (vs ~600–900 do V1):
  em λ=1, 0.03–0.08 de R_eff por 1k tokens engole a margem de R do default.
  λ ∈ {0.02..0.2} → 10 tasks onde default domina estritamente ambos os
  atratores. Lição registrada: λ deve ser escalado pela magnitude de tokens
  do ambiente, não transportado entre stacks.

### PRÉ-REGISTRO 33 (2026-08-26) — treino V2, estágio A re-seleção com λ re-escalado
- MUDANÇA ÚNICA vs pré-reg 32: grade λ ∈ {0.02, 0.05, 0.1, 0.2, 0.25, 0.5};
  empate em nº de elegíveis → MAIOR λ (precificação de custo mais forte com
  a mesma sala). Todo o resto herda o pré-reg 32 na íntegra: mesma regra de
  elegibilidade (default estritamente domina keep_always E summarize_always),
  cap 16 / mínimo 10 (senão ABORT), ranks pares treino / ímpares held-out,
  braços outcome/ch/chm_cm/zero × seeds 1–3, 1600 chamadas/célula, lr 0.1,
  clip 1.0, CENTER_V2, k_credit 2, contabilidade dual (budget + fatias
  episode-matched via experiments/v2_em.py), desfechos s1/s2/s3 e
  secundário chm_cm ≥ ch, emenda 32a.
- INSUMO: o MESMO calibrate_report.json do estágio A do 32 (R e
  prompt_tokens por task são independentes de λ; nenhum episódio novo).
  Nenhum dado de TREINO foi tocado — a re-seleção é analítica e anterior a
  qualquer treino, exatamente o padrão do Ato 4 (seleção analítica de λ*).
- Transparência: esta é uma correção pós-abort de desenho, não de resultado;
  o abort do 32 permanece no ledger como desfecho. Previsão pelos dados de
  calibração: λ* = 0.2, pool = 10 (margens mín. 0.009–0.31).
- Riscos: (i) margens finas (10º = 0.0087) → separação de braços pode ficar
  abaixo do ruído de 5 tasks held-out; (ii) λ pequeno enfraquece o preço do
  custo no objetivo — mitigado pelo empate→maior λ; (iii) mesmos riscos do 32.

### DESFECHO do pré-reg 33 (2026-08-26): s3 — colapso no atrator summarize_always
- Estágio A (herdado do 32) + seleção re-escalada: λ* = 0.2, pool 10
  (viáveis 10/10/10/10/9/6 na grade 0.02–0.5), 5 treino / 5 held-out.
- Estágio B (12 células × ~1600 chamadas, ~75 min GPU total): TODOS os
  braços que aprendem (outcome s1/s3, ch 3/3, chm_cm 3/3) convergem
  TOKEN-EXATO para summarize_always no held-out (R_eff 0.8307, R e
  prompt_tokens idênticos per-task ao atrator). outcome s2 fica no atrator
  keep_always (−0.0923, 5/5 overflow — regra 32a precificando). zero 3/3 =
  keep_always (θ=0 → tie-break greedy = keep).
- Atratores held-out (λ=0.2): keep −0.0923 < summarize 0.8307 < default
  (thr4500) 0.8890. NENHUM braço > max(atratores) em nenhuma seed →
  **s3 declarado** (sem aprendizado além de atrator fixo). Em 2/3 vs 3/3
  não muda o bin.
- Contabilidade episode-matched (experiments/v2_em.py; fidelity gate OK,
  0.8307378303030303 reproduzido exato): fatias do outcome em N=32/33/32
  (ch) e 24/23/24 (chm) → mesmos valores dos braços plenos exceto
  chm_match_s1 = 0.3014 (política mista transitória). Não altera o bin.
- Secundário (chm_cm ≥ ch por seed): satisfeito trivialmente (iguais).
- ANATOMIA do colapso: ‖θ‖ final dos braços de crédito ≈ 0.02–0.06 — o
  "aprendizado" é sair do fio-de-navalha do tie-break em θ≈0 para o lado
  summarize; nenhum braço encontra a política seletiva (default) que o
  pool margin-verified garante ser expressível e estritamente dominante.
  Diferença vs Ato 4 V1: lá a seleção por margem produziu separação de
  braços; aqui o gap default−summarize (0.058 held-out) é fino demais
  para ~24–79 episódios com lr 0.1. Eco do Ato 3 (colapso em atrator),
  agora do lado BOM do custo: summarize_always é quase-ótimo neste
  landscape com cap 8k — overflow domina o objetivo.
- LEITURA p/ paper: o ramo aberto foi EXERCITADO: o gate licenciou, o
  treino rodou, e o resultado é um negativo identificado de outro tipo —
  colapso em atrator antes de a ordenação de crédito virar testável. As
  duas rodadas (V1 fechado: outcome vence; V2 aberto: colapso comum)
  sustentam a mesma prescrição: census + calibração de landscape ANTES de
  pagar por crédito. Custo total 33: ~19.400 chamadas, ~1h15 GPU.

## 2026-08-27 — PRÉ-REGISTRO 30: controles de estimando do census V2 (re-amostragem de a′ + a′_s)

### Motivação (registrada ANTES de qualquer rollout)
O census V2 (pré-reg 29) classificou 48 pontos com UM draw de a′ por ponto
(temp 0.8, esc 1.2 — adendo 29b mostrou que o envelope plain-text torna o
sampler quase determinístico). Objeções: (i) a classificação
screened/não-screened pode depender do draw único; (ii) o a′ vem do estado
NÃO-transformado — no V1, o estimando a′_s (estado sumarizado) de-screenou
parte dos pontos (pré-reg 26, s2). Este pré-reg espelha os controles 21 e 26
do V1 no stack V2.

### Parte A — re-amostragem de a′ (espelha pré-reg 21)
- População: os 48 pontos válidos do census (rows mescladas passe1+esc de
  runs/census_v2/{census_rows,census_esc_rows}.jsonl, error==None).
- 2 schedules disjuntos de seeds: A1=4001–4008, A2=5001–5008; temperatura
  IGUAL à do ponto no census (a_prime_temp 0.8 ou 1.2), mesmo
  sample_alternative_v2, mesmo j.
- Draw informativo := amostra encontrada E ação canônica ≠ a′ do census
  (draw idêntico ⇒ classificação idêntica por determinismo; contado à parte,
  sem replay, FORA da métrica de estabilidade). Sem amostra → sem_a_prime_re.
- Por draw informativo: braços M e HM com o novo a′ (mesma _fila_dupla /
  build_flip_queue do census; HM analítico nos duais 29a); screened_exato_re
  := (R_HM == R_M). C_H reusado do screening.
- Métrica primária: estabilidade = frac de draws informativos com
  screened_exato_re == screened_exato do census.
- Métrica de headline: por schedule, substituir a′→draw (onde informativo,
  senão manter o original) e recomputar desfecho s1/s2/s3 (avalia_desfecho)
  e a célula primária do gate (medidos sem duais, limiar 0.20).

### Parte B — a′_s do estado sumarizado (espelha pré-reg 26)
- População: pontos context_policy válidos do census com flip
  keep_context→summarize_context (a crítica só se aplica a essa direção).
- msgs_s = summarize_messages(d_i.state_before["messages"], keep_last,
  task_chars da config DA trajetória, summarizer da config) — o estado que o
  modelo veria sob h′; a′_s = sample_alternative_v2(llm, msgs_s, ação
  original de j), seeds 6001–6008, temp do ponto.
- 2 replays por a′_s (M_s e HM_s); screened_s := (R_HMs == R_Ms);
  informativo := algum de (C_H, C_Ms, C_HMs) ≠ 0.

### Desfechos declarados
- Parte A (primário): r1 = estabilidade ≥0.90 E desfecho s3 + gate primário
  mantidos nos 2 schedules → census robusto ao draw único. r2 = estabilidade
  <0.90 mas desfecho e gate mantidos → nuance pontual, headline intacto.
  r3 = desfecho OU gate mudam em ≥1 schedule → claim do census re-escopa
  para "estimando single-draw" (equally reportable).
- Parte B (secundário): sobre pares informativos, taxa screened_s: b1 ≥0.90 /
  b2 ∈[0.75,0.90) / b3 <0.75 (de-screening pelo estimando, como no V1 26).
- Exclusões reportadas: sem_a_prime_re/sem_a_prime_s, draws idênticos,
  spans com retry, context_overflow — mesmas categorias do census.
- Sem teste formal; reportar contagens, por tipo e por schedule.

### Custo estimado
≤96 amostragens (A) + ≤23 (B); ≤192+46 replays ≈ 30–60 min GPU, sequencial,
servidor de sempre (8321, APC off). Script: experiments/v2_controles.py,
idempotente por (parte, cfg, task_id, index, schedule).

### DESFECHO do pré-reg 30 (2026-08-27): Parte A r2, Parte B b3
- **Parte A (re-amostragem, 96 draws):** 56 idênticos ao a′ do census
  (58% — o sampler plain-text é quase determinístico mesmo re-seedado,
  consistente com 29b), 17 sem a′, 23 informativos. Estabilidade da
  classificação = 17/23 = **0.739 < 0.90**; 6 flips (4 screen→break,
  2 break→screen, espalhados por 3 tipos). MAS o headline é robusto:
  sob os DOIS schedules o desfecho recomputado é s3 e o gate primário
  (medidos sem duais) segue aberto (A1 0.474, A2 0.368 vs 0.395 original;
  limiar 0.20 com folga). → **r2**: a classificação PONTUAL depende do
  draw; o veredito agregado (s3 + gate aberto) não.
- **Parte B (a′_s, 23 pontos context keep→summarize):** 21 informativos,
  screened_s = 8/21 = **0.381 → b3** (vs 24/31=0.774 no V1, pré-reg 26).
  ASSINATURA NOVA: os 13 de-screened têm TODOS I_s = 0.0 EXATO com
  C_H ≠ 0 — sob a′_s os efeitos das camadas são ADITIVOS (R_Ms − R_HMs
  = C_H), não screening (R_HMs = R_Ms). No V1 o de-screening tinha
  assinatura de re-injeção; no V2, sob o estimando do estado pobre, o
  harness credit deixa de ser double-counted: as camadas se tornam
  independentes. Reforça a tese estimando-dependência: QUAL identidade
  vale no ponto (C_H=−I screening vs I=0 aditividade) é função do
  estimando de a′.
- Custo real: ~17 min GPU (96+23 amostragens, ~90 replays), bem abaixo
  do estimado. Artefatos: runs/v2_controles/{a_rows,b_rows}.jsonl,
  summary.json; log runs/logs/v2_controles.log.
- Leitura conjunta p/ o paper: os controles de estimando do V2 CONFIRMAM
  o veredito do census sob re-draw (r2) e REESCOPAM a interpretação dos
  pontos screened: no estimando a′_s a decomposição vira aditiva (I=0),
  o caso em que crédito single-layer é correto. A prescrição (census por
  estimando antes de billar crédito) sai fortalecida.
- Precisão (nota adicionada em seguida): dos 13 não-screened sob a′_s,
  9 eram screened no census (de-screening genuíno) e 4 já eram breaks;
  a assinatura I_s = 0.0 exato vale para os 13.

## 2026-08-27 — Análise descritiva (zero-GPU): composição dos 66 pontos pivotais excluídos do census V2
- Sem novos rollouts (não é pré-reg; análise de seleção, espelho V2 da
  análise do V1). Script experiments/analise_exclusao_v2.py; saída
  runs/census_v2/analise_exclusao.json.
- 66 excluídos = 65 sem a′ (mesmo após escalonamento 29b) + 1 span com
  retry. Composição vs os 48 medidos: |ΔR| do flip COMPARÁVEL (mediana
  0.167 vs 0.182; média 0.183 vs 0.173) — a exclusão NÃO esconde efeitos
  menores; mas os excluídos são mais CEDO (turn mediano 2 vs 7) e com
  contexto menor (919 vs 2.098 tokens); termination (26) e observation
  (23) sobre-representados; retry excluído por inteiro (2/2).
- Leitura: o census V2 sobre-representa estados tardios e de contexto
  grande — onde o sampler tem entropia para achar a′. Direção do viés:
  neutra para o tamanho de efeito, mas os pontos mais precoces (onde o V1
  mostrou pivotalidade profunda) ficam não-medidos. Caveat honesto no
  app:estimand do paper.

## 2026-08-27 — PRÉ-REGISTRO 34: gate de poder (formalização, aplicação retroativa e sonda de otimização)

### Motivação (painel rodada 8)
- R1-W1: o pré-reg 33 licenciou treino num landscape cujo gap held-out
  default−summarize era 0.058 — a prescrição (census+calibração) verifica
  DOMINÂNCIA mas não PODER (margem vs. ruído ao budget dado).
- R3-W2/Q1: o colapso s3 é, nos dados atuais, indistinguível de "lr 0.1
  com 23–79 episódios não resolve margens de 0.06" — artefato de
  otimização, não propriedade do crédito. Remédio proposto: pool
  re-selecionado por margem ≥0.15 OU lr menor + mais episódios.

### Parte A — analítica (0 GPU, determinística, artefato congelado)
- Insumo: runs/v2_train/calibrate/calibrate_report.json (3 políticas ×
  60 tasks, congelado no pré-reg 33). Recomputação determinística — sem
  amostragem, logo sem proteção de pré-registro a ganhar; declaramos por
  honestidade que a inspeção exploratória (hoje) motivou o desenho e que
  os números abaixo são os que serão reportados.
- **Gate de poder (formalização registrada):** treino só é licenciado se
  o pool tiver ≥ MIN_POOL (=10, o mesmo do 32/33) tasks com margem de
  dominância min(default−keep, default−summarize) em R_eff(λ) ≥ 0.10
  (primário; 0.15 e 0.08 reportados como sensibilidade), em algum λ da
  grade registrada no 33.
- **Resultado (aplicação retroativa):** elegíveis a ≥0.10: máx 3 tasks
  (λ=0.02); a ≥0.15: 3; a ≥0.08: 8. NENHUM λ atinge nem o mínimo
  relaxado (6). O pool do 33 rodou com margens 0.009–0.307 (só 1 task
  ≥0.10) e 23–79 episódios/braço. → O gate de poder teria VETADO o
  pré-reg 33; mais forte: o pool exigido pelo remédio do R3 (margem
  ≥0.15) NÃO EXISTE neste landscape, em nenhum λ. O abort é do
  ambiente, não da seleção — evidência direta para o design brief
  (benchmark precisa de margem verificável entre atratores expressíveis).

### Parte B — sonda de otimização (estocástica, GPU)
- Pergunta: o colapso do 33 sobrevive ao melhor cenário do otimizador?
  Aplica exatamente o remédio alternativo do R3: lr 5× menor E budget
  2× maior, no mesmo pool/λ* do 33 (única configuração existente).
- Células: braços outcome e chm_cm, seed 1, lr=0.02, budget 3200 calls,
  λ*=0.2, pool runs/v2_train/pool.json, mesmíssimo protocolo do 33
  (emenda 32a incluída). Saída: runs/v2_train34/{outcome,chm_cm}_lr002.
- Desfechos declarados ANTES de rodar:
  - p1: ambos colapsam de novo em atrator fixo (heldout R_eff a ±0.02 de
    um dos 3 atratores calibrados) → colapso robusto a lr E budget;
    combinado à Parte A: "não é o lr, não é o budget, e a margem não
    existe no landscape" — s3 vira negativo identificado com anatomia
    completa.
  - p2: os braços separam (heldout entre braços difere >0.05 e ≥1 braço
    fora de todos os atratores ±0.02) → s3 reinterpretado como artefato
    de otimização; correção reportável no paper (major).
  - p3: um colapsa e o outro não → anatomia por braço, reportar como está.
- Custo estimado: 2 células × 3200 calls ≈ 2–3 h GPU, sequencial,
  servidor 8321 (APC off), idempotente por summary.json.

### DESFECHO do pré-reg 34 Parte B (2026-08-27): p1 — colapso robusto a lr e budget
- outcome lr=0.02, 3200 calls, 151 episódios: heldout R_eff = −0.09228
  = keep-always EXATO (o atrator catastrófico).
- chm_cm lr=0.02, 3215 calls, 47 episódios: heldout R_eff = 0.8307378
  = summarize-always EXATO.
- **p1 confirmado** (ambos a ±0.02 de atrator calibrado; na prática, exatos).
  O remédio "lr menor + mais episódios" (R3) não separa braços neste
  landscape.
- Anatomia (honesta): θ final ≈ 0 nos DOIS braços (‖θ‖∞ ≤ 0.055) — com
  lr 0.02 o sinal disponível mal move a política; o comportamento greedy
  da política quase-nula degenera num lado fixo, e os braços caem em
  LADOS OPOSTOS (outcome no ruim, chm_cm no bom) por sensibilidade a
  updates minúsculos, não por aprendizado. Não interpretar a ordenação
  chm_cm > outcome desta sonda como vitória de crédito: é ruído de
  inicialização efetiva, 1 seed, e nenhum braço aprendeu política
  condicional.
- Leitura conjunta 34 A+B: "não é o lr, não é o budget, e a margem não
  existe no landscape" — o colapso do 33 é propriedade do landscape
  (margens ≤0.058 em 9/10 tasks do pool), não do otimizador. O gate de
  poder (Parte A) entra na prescrição do paper; o 33 teria sido vetado.
- Custo real: ~23 min GPU (2 células). Artefatos runs/v2_train34/,
  log runs/logs/prereg34b.log.

### Fase exploratória de desenho do landscape 35 (2026-08-27/28): encerrada SEM registro — o gate de poder veta as 4 iterações
Declarado exploratório desde o início (pré-congelamento; nenhum treino rodou,
nenhum pré-reg 35 foi registrado — o gate do pré-reg 34 nunca abriu).
Objetivo: construir pool de 24 tasks (12 poison + 12 free) onde a política
condicional "keep se n_writes==0, senão summarize" domine TODAS as fixas
(keep/summarize/default-4500) por ≥0.10 em ≥10 tasks em algum λ.

- **It. 1** (blob grande + boot_note): veneno morde summarize (P: 12/12 a
  R≤0.6) mas NÃO o default — o modelo lê pouco e o threshold nunca cruza
  pré-write. F sem overflow. Margem mix: 0.016.
- **It. 2** (F com 4 estágios verbosos): keep estoura como desenhado, mas
  4 estágios excedem a competência do 4B — oráculo/default travam em R=0.6
  gastando 50–100k tokens. Margem do oráculo: negativa em todo λ.
- **It. 3** (P exige síntese spec+boot; F com esperado oculto): tudo
  afunda (P keep 0.17; F ~0.03 em todas; 22/24 overflows sob keep).
  Síntese de duas fontes está acima da competência do modelo.
- **It. 4** (dificuldade só de leitura: fix copiável na spec; F com bugs
  óbvios e diff visível): P finalmente funciona na direção certa
  (keep 0.67 > summ/def 0.40), MAS as F revelam patologia nova: após o
  primeiro summarize o modelo entra em loop (list→read→write normaliza,
  8+ ciclos, NUNCA re-roda testes — a informação de falha foi destruída
  junto com o contexto) e estoura 8192 até sob summarize (12/12) e
  default (11/12). R=0.0 nas F para TODAS as políticas. Margem do
  oráculo: negativa em todo λ; 0/24 tasks com margem ≥0.10.

Leitura conjunta (1 seed, greedy, descritivo): no stack (Qwen3-4B, harness
V2), mesmo desenhando adversarialmente COM conhecimento do mecanismo, não
existe pool que passe o gate. Os modos de falha são comportamentais do
modelo — gap binário de competência (it.2–3) e loop pós-summarize (it.4)
— não parâmetros de task. Fortalece o pré-reg 34 construtivamente e vira
requisito do design brief: a margem tem que ser verificada contra o
comportamento do modelo, não estimada da estrutura da task.
Caminho aberto (não exercitado): repetir o gate com Qwen3-8B — a
patologia de loop pode ser específica do 4B.
Custo: ~4×40 min GPU (calibrações+oráculos, runs/v2_land35{,b,c,d}/).

### Gate de poder com Qwen3-8B no pool it.4 (2026-08-26): exploratório — o gate
estrito veta de novo (0/24), mas por uma razão estrutural nova e informativa
Exercita o caminho aberto do fechamento acima. Mesmo pool congelado da it.4
(runs/v2_land35d/all24.json), mesmas 3 políticas fixas + oráculo condicional
θ=[40,0,0,0,120], 1 seed, greedy. Servidor trocado para Qwen/Qwen3-8B (mesmas
flags; HF_HOME=/home/marcos/hf_cache é obrigatório). Artefatos:
runs/v2_land35_8b/.

Resultados (λ=1.0): keep R=0.542/r_eff=0.373; summ 0.458/−0.223; default
0.508/−0.234; **oráculo 0.708/0.533**.
- **Hipótese da banda parcialmente confirmada:** o loop pós-summarize do 4B
  desaparece. Nas F, o 8B divide: f_00 solúvel por todas; f_02/05/07/11
  solúveis EXATAMENTE pelo mecanismo desenhado (keep overflowa, summarize
  resolve, margem +0.95 vs keep cada); 7/12 insolúveis sob todas (overflow
  universal). As 12 F são estruturalmente idênticas (mesmo bug, mesmo
  template, só a seed dos dados) — o split é a borda da banda de
  competência por seed, não um parâmetro de desenho.
- **Primeira paisagem em que o alvo condicional domina estritamente todas
  as fixas na média:** +0.16 de r_eff sobre a melhor fixa (keep) em λ=1.
- **Mas o gate estrito registrado veta: 0/24 tasks com margem ≥0.10 vs
  melhor-fixa-por-task, em todo λ ∈ {0, 0.1, 0.2, 0.5, 1, 2}.** Razão
  estrutural: o oráculo comete-se na primeira decisão consultada e
  degenera token-exato numa das fixas em cada task (margens +0.0000).
  Um alvo que só exerce condicionalidade ENTRE tasks nunca passa um
  critério per-task-vs-melhor-fixa — o critério é impassável por
  construção para essa classe de alvo.
- Na versão por atrator (margem vs CADA fixa): vs summarize 12 tasks
  ≥0.10; vs keep apenas 4 (as f_02/05/07/11). Gargalo: 4 < 10.

Leitura honesta: nenhum treino se justifica ainda (gate fechado sob o
critério registrado; redefinir o critério post hoc para abrir o gate é
exatamente o que a disciplina do paper proíbe). Dois aprendizados para o
design brief: (i) o critério de margem do item 3 precisa ser especificado
POR ATRATOR e no nível em que o sinal de treino enxerga (média de r_eff),
senão conflita condicionalidade intra-task com inter-task; (ii) existe um
caminho construtivo concreto — enriquecer as F com variantes da classe
f_02 (dentro da banda do 8B) até ≥10 tasks com margem vs keep — mas
exigiria re-registro explícito do critério por atrator ANTES de qualquer
treino. Custo: ~75 min GPU (calibração 72 eps + oráculo 24 eps).

### Tier 0 pós-review externo (2026-08-26): três análises zero-GPU, pós-hoc declaradas
Motivação: review externo independente apontou como críticas mais fortes
(1) seleção por a' (53–73% descartados), (2) dependência do estimando a′/
Shapley, (3) multiplicidade sem correção. Três análises sobre dados já
coletados, sem rollout novo:
- **Bounds de Manski (bounds_selecao_t0.py):** gate V2 com duais abre até
  sob imputação adversarial de TODOS os 66 excluídos (24/114 = 0.211 ≥
  0.20) — a seleção por a' não pode ter fabricado a abertura. Sem duais os
  extremos cruzam o limiar (0.132/0.711): indeterminado, consistente com o
  paper fechar nessa contabilidade. V1 slack: pior caso 0.31; "maioria
  screened" exige só 28% dos excluídos screened.
- **Shapley 2-player (shapley_quartetos_t0.py):** sobre todos os quartetos
  (V1 g450/600/900+mt4/6/8, V2 census): φ_H = ½(C_H + C_HM − C_M); em 91
  pontos screened com C_H≠0, Shapley cobra exatamente C_H/2 — não elimina
  o double counting, reparte-o; I é o diâmetro do leque de atribuições.
- **FDR (fdr_ledger_t0.py):** BH+Holm sobre os 6 testes computados no
  paper: só p=0.005 sobrevive (Holm 0.03); p=0.037 não (Holm 0.19).
Integrações no paper: multiplicidade exata (app:estimand), bound de pior
caso no Scope do V2, Shapley empírico na teoria (§ do prop:dc). 9pp
intactas. Framing do abstract auditado: sem mudança necessária.
Custo: 0 rollouts.

### PRÉ-REGISTRO 35 (2026-08-26, antes de qualquer rollout com o modelo): census cross-family — Mistral-7B-Instruct-v0.3
Motivação: review externo aponta que todos os modelos são da família Qwen3;
transporte cross-family nunca foi medido. Este é o experimento que nenhuma
análise de dados existentes cobre.

**Hipótese:** screening-off sob folga não é específico da família Qwen.
**Manipulada:** família do modelo (mistralai/Mistral-7B-Instruct-v0.3,
única variável trocada; harness V1 congelado, thr600, tasks_all 30).
**Protocolo:** espelho exato do pré-reg 15 (q8_chain): teste0 (baseline +
piso nulo, points 3, reps 3) → teste2 (amostragem a′, max-per-traj 4) →
teste3 (census conjunto, max-per-traj 3), em g600 (folga) e mt6 (pressão).
Endpoints idênticos: fração screened raw e reward-pivotal, piso nulo.
**Smoke test declarado (antes do pipeline, sem análise de screening):**
3 episódios para verificar taxa de parse de ações ≥80%; se falhar, trocar
para deepseek-coder-6.7b-instruct e re-declarar aqui antes de rodar.
**Gate de poder (herdado do pré-reg 25):** <5 pontos pivotais não-saturados
em uma célula ⇒ célula declarada inconclusiva, sem leitura direcional.
**Desfechos declarados:** (a) screens ≥0.90 nos pivotais de folga (padrão
V1/Qwen-4B) ⇒ screening transporta cross-family; (b) quebras a taxa
plana nos dois regimes (padrão 8B) ⇒ screening depende de capacidade, não
de família; (c) célula inconclusiva pelo gate ⇒ reportar como janela de
competência não alcançada, sem claim. Qualquer outro padrão: descritivo.
**Piso:** nulos exatos obrigatórios; se o piso ≠ 0 com o Mistral, o census
não é interpretável e o desfecho é "piso quebrou" (reportado como achado
de infraestrutura, sem leitura causal).
**Custo estimado:** ~500–900 rollouts, ~4–6h GPU (paridade com o q8).

**Adendo 35a (2026-08-26, antes de qualquer rollout válido do pré-reg 35;
único contato com o modelo: 1 chamada rejeitada com HTTP 400, zero tokens
gerados):** o chat template do Mistral exige alternância estrita
user/assistant e rejeita as mensagens user consecutivas do loop V1
(prompt + boot_note; observações). Correção de infraestrutura: fusão de
mensagens consecutivas do mesmo role na borda do cliente
(TCC_MERGE_ROLES=1, opt-in; paths Qwen inalterados). Conteúdo
informacional idêntico; a estrutura de renderização difere da dos runs
Qwen e o census Mistral é comparável apenas a si mesmo nesse aspecto.
Smoke e protocolo do pré-reg 35 inalterados.

**Adendo 35b (2026-08-26, antes de qualquer rollout válido; único contato
com o Mistral: o smoke declarado):** o smoke do Mistral-7B-Instruct-v0.3
rodou (após o shim 35a) e FALHOU pelo critério declarado: taxa de parse
0.57 (8 ok, 6 retries; corte 0.80), rewards 0.00 nos 3 episódios.
Conforme declarado no pré-reg 35, troca para o fallback
**deepseek-ai/deepseek-coder-6.7b-instruct** (ungated; chat template
aceita roles consecutivos — shim 35a desnecessário e desligado, o
rendering fica estruturalmente igual ao dos runs Qwen). Tags: dsc_g600 /
dsc_mt6. Protocolo, endpoints, gate de poder e desfechos declarados
inalterados. O smoke roda de novo com o deepseek; se falhar também, novo
adendo antes de qualquer decisão.

**Adendo 35c (2026-08-26, antes de qualquer rollout válido com o novo
candidato):** o smoke do deepseek-coder-6.7b-instruct também FALHOU
(taxa 0.33; corte 0.80). Probe diagnóstico (experiments/probe_parse.py,
1 chamada por task, outputs crus inspecionados): o modelo ignora
completamente o protocolo JSON de ações e responde prosa + blocos de
código — nem um parser balanceado alternativo encontra ação válida.
Ou seja: não é bug do nosso parser (regex greedy foi descartado como
causa); é não-aderência ao formato. Terceiro e último candidato
declarado: **microsoft/Phi-3.5-mini-instruct** (ungated, 3.8B — pareado
em escala com o Qwen3-4B; template aceita roles consecutivos, sem shim).
Tags: phi_g600 / phi_mt6. Protocolo, endpoints, gate e desfechos
inalterados. **Desfecho declarado se o Phi também falhar o smoke:** o
census cross-family é irrealizável sob o harness V1 congelado — a adesão
ao formato de instrução é ela mesma família-dependente; isso vira achado
de escopo reportado no paper (a questão do screening cross-family
permanece aberta), sem afrouxar o harness e sem quarto candidato.

### DESFECHO 35 (2026-08-26): census cross-family IRREALIZÁVEL sob o harness V1 congelado
Os três candidatos declarados falharam o smoke de adesão ao protocolo
(corte 0.80): Mistral-7B-v0.3 **0.57** (com shim 35a), deepseek-coder-6.7b
**0.33** (probe: prosa + código, ignora o protocolo de ações por completo
— parser descartado como causa), Phi-3.5-mini **0.43**. Regra de parada
declarada no 35c disparou: sem quarto candidato, sem afrouxar o harness.
Leitura: sob harness congelado, a adesão ao formato de ação — precondição
da medida — é ela mesma família-dependente. O escopo Qwen3 das claims
passa de "não medido" a **restrição medida**; transporte cross-family de
screening permanece aberto (medi-lo exigiria adaptação de harness por
família, que confundiria a própria comparação). Integrado no paper:
§threats (1 frase), app:replication (parágrafo), ledger (linha 35).
Custo total: 3 smokes + 1 probe ≈ 40 chamadas; zero rollouts de census.
4B restaurado e servindo.

### PRÉ-REGISTRO 36 (2026-08-26, antes de rodar): distribuição de a′ nos pontos do census V2
Motivação: review externo — um único draw de a′ torna C(d) uma quantidade
dependente do draw; 30A mediu estabilidade par-a-par com 2 schedules
(17/23 estáveis), mas não caracterizou a DISTRIBUIÇÃO por ponto.

**Hipótese:** o veredito screened/não-screened por ponto é uma propriedade
do ponto, não do draw — a distribuição de vereditos sob redraws de a′ é
concentrada.
**Manipulada:** apenas a seed do sampler de a′ (5 schedules novos e
disjuntos: S3=7001–7008, S4=8001–8008, S5=9001–9008, S6=10001–10008,
S7=11001–11008), nos mesmos 48 pontos medidos do census V2, mesma
temperatura por ponto, mesmo procedimento (sample_alternative_v2).
**Draws por ponto no pool de análise:** census + A1 + A2 (já medidos,
pré-reg 30A) + S3–S7 = até 8. Draw válido := encontrado e braços M/HM sem
erro; draw idêntico ao a′ do census (canônico) herda o veredito do census
sem replay novo (replay é determinístico). Duais (29a) e exclusões do
census herdados.
**Endpoint primário:** U = fração dos pontos com ≥2 draws válidos cujo
veredito é UNÂNIME. Desfechos: d1 U≥0.80 (veredito robusto ao draw);
d2 0.60≤U<0.80 (sensível — reportar distribuição por ponto e veredito por
voto majoritário); d3 U<0.60 (dependência de a′ domina — deprecia o
veredito pontual em favor de statement distribucional no paper).
**Secundários (descritivos):** headline (desfecho s3 + gate medidos sem
duais, corte 0.20) recomputado (i) por schedule novo e (ii) sob voto
majoritário por ponto; nº de a′ canônicos distintos por ponto; flips por
tipo de decisão.
**Piso:** coberto pelos nulos exatos já medidos nas mesmas configs (como
no 30A); sem re-run de teste0.
**Custo estimado:** ≤240 tentativas de draw, ~250–450 replays, 6–12h GPU
(4B já servido).

### PRÉ-REGISTRO 37 (2026-08-26, antes de rodar): pressão externa de-saturada — censo exaustivo in-window no MBPP+
Motivação: review externo — o contraste folga→pressão→quebra nunca teve
poder num ambiente externo (D3: 4B saturado em sucesso; D6: 1.7B saturado
em fracasso, 2/22 não-saturados). Poder existente in-window nos census
MBPP+ atuais: 1 ponto não-saturado por célula (gate exige ≥5).

**Hipótese:** com poder real, o padrão V1 transporta ao MBPP+: screening
sob folga, quebras sob pressão.
**Manipulada:** nada de novo no agente — só a POPULAÇÃO de medição: censo
EXAUSTIVO de pontos (max-per-traj 99) restrito às tasks na janela de
competência (baseline da própria config em (0.05,0.95)), sobre os
baselines JÁ CONGELADOS de runs/teste0_mbpp_{g600,mt6} (zero rollout de
baseline novo). Tasks declaradas — g600 (10): mbpp_111, 276, 410, 420,
606, 620, 7, 769, 792, 809; mt6 (11): as mesmas + mbpp_563.
**Protocolo:** teste2 (amostragem a′, max-per-traj 99) → teste3 (census,
max-per-traj 99) sobre baseline filtrado por symlink; pontos que
coincidirem com os já medidos em teste3_mbpp_* são re-medidos pelo mesmo
procedimento determinístico (sem herança manual). Piso: coberto pelos
nulos exatos já medidos nessas configs; teste0 não re-roda.
**Gate de poder (herdado do pré-reg 25):** ≥5 pontos pivotais
não-saturados por célula; célula abaixo disso = inconclusiva, sem leitura.
**Desfechos declarados (se as duas células passarem o gate):**
e1 — folga screena ≥0.90 nos pivotais e taxa de quebra sob pressão >
folga: padrão V1 transporta; e2 — ambas screenam ≥0.90: ambiente externo
blinda inclusive sob pressão (refina o escopo do contraste de regime);
e3 — folga quebra (<0.75): screening não transporta ao MBPP+ nem sob
folga. Entre 0.75–0.90 ou padrões mistos: descritivo, sem claim.
**Custo estimado:** ~350–500 replays, 6–10h GPU (4B). Roda após a coleta
do pré-reg 36 (GPU sequencial).

### DESFECHO 36 (2026-08-26): distribuição de a′ — d2 (sensível no ponto, invariante no agregado)
Coleta S3–S7 completa: 240 tentativas, 56 informativas (a′ novo), 139
idênticas ao a′ do census, 44 sem alternativa, 1 erro de replay; mediana
de 8 draws válidos por ponto. **U = 36/46 = 0.783 → d2_sensivel** (por
0.017; corte d1 era 0.80). Estrutura:
- A distribuição de a′ é CONCENTRADA: mediana 1 a′ canônico distinto por
  ponto (máx 6) — na maioria dos pontos o sampler só encontra o mesmo a′.
- Flips por tipo: context_policy 7/21, test_schedule 2/3, observation 1/12,
  termination 0/10 (o veredito de termination é imune ao draw).
- Conforme declarado para d2, veredito por voto majoritário: desfecho s3
  inalterado; gate medidos sem duais 0.4211 → ABRE.
- Headline por schedule novo: s3 e gate aberto em 5/5 schedules
  (frac 0.421–0.500). A conclusão agregada é invariante ao draw.
Leitura: C(d) pontual herda a variância do sampler em ~1/5 dos pontos
(concentrada nos tipos de contexto), mas nenhuma conclusão do paper
depende de um draw específico — o que o review pedia para caracterizar.
Custo real: ~115 replays (bem abaixo do estimado; 139 idênticos grátis).

### DESFECHO 37 (2026-08-26): pressão externa de-saturada — INCONCLUSIVO pelo gate nas duas células
Censo exaustivo (max-per-traj 99) nas tasks in-window do MBPP+: g600 17
pontos medidos (8 pivotais, 4 não-saturados), mt6 13 (7 pivotais, 1
não-saturado). **Gate de ≥5 não-saturados falha nas duas células** —
inconclusivo, sem leitura direcional, conforme declarado. Descritivo:
15/15 pivotais screened (incluindo 5/5 não-saturados); TODA a massa
não-saturada vem de uma única task (mbpp_7). Leitura: o censo exaustivo
ESGOTOU a rota de de-saturação por população — mesmo restringindo a tasks
com baseline in-window, os pontos counterfactuais do MBPP+ saturam (a
task ou resiste a qualquer flip ou colapsa com todos). O contraste de
regime com poder num ambiente externo exige ambiente novo (não outra
análise do MBPP+), fora do escopo desta rodada. Custo real: ~90 replays.

### PRÉ-REGISTRO 38 (2026-08-26, antes de rodar): cross-family sob harness V2 congelado (protocolo texto plano)
Motivação: mesa redonda 9 + review externa — crítica 6 (Qwen-only)
documentada mas não fechada. Insight: o desfecho 35 é específico do
PROTOCOLO JSON do V1. O V2 usa protocolo de ação em TEXTO PLANO
(LIST/READ/WRITE/TEST/FINISH) por razões INDEPENDENTES e anteriores a
qualquer desenho cross-family: adendo 28a (Qwen3-4B, 0 write_file em
437 tool_calls sob envelope JSON; recalibração registrada antes do
census 29). Logo existe um harness já congelado, já usado no census
principal, plausivelmente executável por famílias não-Qwen.

**Hipótese:** a ESTRUTURA causal transporta de família: (i) fenômeno —
a célula nova reproduz o desfecho registrado da célula Qwen/v2_folga
(s3: heterogeneidade por tipo; gate medidos-sem-duais aberto); (ii)
acoplamento — sob a′_s a taxa screened cai ao bucket b3 (<0.75) com
de-screening para aditividade (I_s=0), como no Qwen (0.381, pré-reg 30B).
**Manipulada:** SÓ a família do modelo. Congelados no commit 63bf249:
HarnessV2 v2_folga default, EpisodeV2/parser plain-text, tasks_swe (60),
serving idêntico (vLLM 8321, APC off, max-model-len 8192, greedy
seed 1234), a′ temp 0.8 seeds 2001–2008 + escalonamento 1.2/3001–3008
(29b), a′_s seeds 6001–6008 (30B), seleção 28b (≤2/tipo, ≤6/traj).
**Candidatos (ordem fixa, sem 3º, sem ajuste por modelo pós-resultado):**
1. mistralai/Mistral-7B-Instruct-v0.3; 2. deepseek-ai/deepseek-coder-6.7b-instruct
(máxima distância comportamental; review externa). Se ambos passarem o
smoke, o census roda no 1º da ordem (orçamento de uma célula).
**Transporte declarado:** TCC_MERGE_ROLES=1 (canonicalização do adendo
35a) aplicado apenas a template com alternância estrita (Mistral); a
sequência canônica de mensagens é idêntica — não é mudança de harness.
**Smoke gate (forma idêntica ao 35):** 3 episódios nas tasks declaradas
swe_agendador_v1, swe_cache_v1, swe_config_merge_v1, config v2_folga;
taxa = tool_call não-forçado / (ok + retries) ≥ 0.80. Falhou → próximo
candidato.
**Gate de validade do instrumento (antes de qualquer leitura):** piso da
célula nova = nulos full-forced (60) + piso greedy NOVO (replay com flip
nulo no 1º candidato de screening por trajetória, sufixo greedy, ≤60
replays): exatos ≥0.95 e desvios listados; abaixo → X4 (instrumento não
transporta; célula sem leitura de screening).
**Pipeline (1º aprovado):** base 60×v2_folga → nulos → piso greedy →
screening 28b → census a′ (2 passes 29b) → braço a′_s (30B, context
keep→summarize) → relatório. Estágios retomáveis; comparador declarado =
célula Qwen/v2_folga (context 0.50 n18, obs 0.60 n10, test 0.33 n3,
term 0.00 n7; desfecho s3; gate 0.50 abre) e 30B (screened_s 0.381, b3).
**Desfechos declarados:** X1 = desfecho s3 E gate aberto (fenômeno
transporta no nível do desfecho registrado); X2 = s1/s2 ou gate fecha
(dependência de família DENTRO do mesmo harness/protocolo — a tripla
ganha o eixo família; igualmente publicável). Estimando, independente:
E1 = bucket a′_s b3 (acoplamento transporta); E2 = outro bucket
(acoplamento dependente de família). X3 = ambos falham smoke (fronteira
de adesão a protocolo persiste em texto plano; 35 NÃO é reclassificado).
X4 = piso falha. Compromisso de linguagem: qualquer resultado positivo
será reportado como "no longer confined to a single model family",
nunca "generalizes across families".
**Custo estimado:** smoke ~0,5–1h/modelo; pipeline ~700–1000 replays,
12–20h GPU (7B na 4090). Tudo sequencial; 4B restaurado ao final.

### ADENDO 38a (2026-08-26, infraestrutura, antes de qualquer veredito de smoke): episódio truncado por contexto
Primeira execução do smoke Mistral: 2/3 episódios COMPLETOS com reward
0.90/0.91 (o modelo opera o protocolo V2), crash no 3º por 400 de estouro
de contexto no serving de 8k — a MESMA exceção que a célula Qwen/v2_folga
sofre em 3/60 tasks do base (29); propriedade do stack, não da família.
O smoke não estava preparado para episódio abortado (exceção não tratada
→ a cadeia leu como reprovação, INCORRETO). Correção de infraestrutura:
episódio truncado entra na contagem com as decisões até o abort; métrica
e gate INALTERADOS (taxa = ok/(ok+retry) ≥ 0.80). Nenhum veredito de
smoke foi determinado antes desta correção; a cadeia foi interrompida
antes de qualquer contato com o candidato 2. Re-execução do zero.

### DESFECHO 38 (2026-08-27): X1 + E1 — estrutura E acoplamento não mais confinados a uma única família
Candidato 1 (Mistral-7B-Instruct-v0.3) passou o smoke com taxa 1.00
(66 parses, 0 retries) — o protocolo texto plano do V2 é operável pela
família nova, confirmando que a reprovação do 35 era do protocolo JSON
do V1, não da fronteira de família. Candidato 2 nunca foi tocado
(orçamento de uma célula, conforme registrado). Pipeline completo em
~3h de GPU (bem abaixo do estimado).
**Instrumento transporta (não-X4):** nulos 48/48 exatos; piso greedy
48/48 exatos = 1.00 ≥ 0.95. O piso zero é propriedade do stack, não da
família Qwen.
**Base:** 60 tasks v2_folga, 48 trajetórias válidas (12 erros de estouro
de contexto a 8k — mesma classe dos 3/60 do Qwen, adendo 38a), taxa de
sucesso 0.15, reward médio 0.665.
**Census (X1):** screening 287 replays → 49 pontos pivotais; census 43
válidos (6 excluídos por overflow; **0 por falta de a′** — o sampler do
Mistral sempre achou alternativa, vs 65/114 do Qwen; composição de
seleção difere e será reportada). Desfecho **s3** (nenhum tipo screena
≥0.90): observation 0.619 (n=21), context 0.833 (n=6), termination 0.133
(n=15), test_schedule 1.0 (n=1). Gate por contabilidade, mesmo padrão
qualitativo do Qwen — abre em três, fecha na mais estrita:
medidos-com-duais 22/43=0.512 ABRE; **medidos-sem-duais (primário)
9/28=0.321 ABRE** (Qwen 0.50); pivotal-com-duais 22/49=0.449 ABRE;
pivotal-sem-duais 9/49=0.184 fecha (Qwen 0.13 fecha). Termination é o
tipo que menos screena nas duas famílias (0.13 vs 0.00 do Qwen).
→ **X1: fenômeno transporta no nível do desfecho registrado.**
**a′_s (E1):** 6 alvos context keep→summarize, 6 ok; taxa screened_s
0.5 → **bucket b3** (Qwen 0.381, b3), com de-screening na direção
prevista. n=6 é pequeno (o census do Mistral tem só 6 pontos de contexto
vs 18 do Qwen) — reportar como suporte, não como estimativa fina.
→ **E1: acoplamento transporta no nível do bucket registrado.**
**Leitura (compromisso de linguagem):** o fenômeno — heterogeneidade s3,
gate aberto nas contabilidades medidas e fechado na mais estrita,
de-screening sob a′_s — **is no longer confined to a single model
family**. NÃO é "generalizes across families": uma célula, um harness,
um ambiente. O 35 fica reclassificado: fronteira de adesão ao protocolo
JSON do V1, não fronteira de família. Custo real: ~450 replays + 60
episódios, ~3h GPU. Qwen3-4B restaurado no serving ao final da cadeia.
