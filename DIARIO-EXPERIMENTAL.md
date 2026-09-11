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

### PRÉ-REGISTRO 39 (2026-08-27, antes de qualquer rollout novo): o ramo positivo do gate — critério de margem por atrator + census + treino licenciado (Qwen3-8B, pool it.4 congelado)

**Pergunta registrada (framing do review externo):** um gate positivo
realmente prediz que replay credit é economicamente útil para treino?
NÃO é "provar que nosso método funciona": é validar OU falsificar o ramo
positivo da decision rule. Qualquer desfecho declarado abaixo é
publicável.

**Motivação.** O falso-negativo do 8B (entrada exploratória de
2026-08-26): o gate per-task-vs-melhor-fixa veta 0/24 mesmo quando o
alvo condicional domina TODA política fixa na média (+0.16 r_eff),
porque um alvo que só exerce condicionalidade entre tasks não pode
passar um critério per-task. O paper promete "the per-attractor
correction awaits registration" — este é o registro. A correção é
registrada ANTES de qualquer treino, sobre artefatos congelados; a
inspeção exploratória de 2026-08-26 motivou o desenho e os números do
gate analítico já são conhecidos (declarado por honestidade; o que o
pré-registro protege é o census e o treino, que são novos).

**Insumos congelados (nenhum novo rollout para o gate analítico):**
- Pool: runs/v2_land35d/all24.json — as 24 tasks INTEIRAS (12 F + 12 P
  de environment.tasks_swe35), sem re-seleção, sem cherry-picking.
- Calibração 8B: runs/v2_land35_8b/calibrate_report.json (keep_always,
  summarize_always, default/thr4500 × 24 tasks, greedy, λ recomputável
  analiticamente de R e prompt_tokens).
- Alvo condicional expressível: θ_oracle=[40,0,0,0,120] com CENTER_V2
  (keep se n_writes=0, summarize senão), runs/v2_land35_8b/oraculo_report.json.
- Modelo: Qwen/Qwen3-8B, mesmas flags de serving (max-model-len 8192,
  APC OFF, sequencial, HF_HOME=~/hf_cache, gpu-mem 0.85). Config
  harness: thr4500/mt25/keep6 (a mesma da calibração congelada).

**GATE 1 — poder, por atrator, no nível do sinal de treino (analítico, 0 GPU).**
- Critério registrado: margem_λ(atrator) = mean R_eff(λ) do alvo
  condicional − mean R_eff(λ) do atrator, sobre as 24 tasks, para CADA
  um dos 3 atratores fixos calibrados (os pontos de colapso alcançáveis
  pela classe de política). Grade λ ∈ {0.1, 0.2, 0.5, 1.0, 2.0} (λ=0
  excluído: sem preço de custo não há estimando de eficiência).
  λ* = argmax_λ min_atrator margem_λ (empate → menor λ).
- ABRE se min_atrator margem_λ*(·) ≥ 0.10. Sob greedy + APC off a
  margem é determinística (piso zero) — "resolvível ao budget" =
  exatamente reproduzível, sem exigência amostral.
- Desfecho g0 (fecha em todo λ): STOP, negativo reportável — a correção
  por atrator não basta neste landscape.
- Sensibilidade reportada (não decisória): 0.15 e 0.08.

**GATE 2 — census de screening com contabilidade registrada (GPU, novo).**
A prescrição do paper (§8.4 iii) exige o census ANTES de pagar pelo
treino com crédito; esta célula (8B, harness V2, pool 35) nunca foi
censeada. Protocolo espelho do pré-reg 29/38 (census_v2):
- Base: 24 episódios sob HarnessV2 default (thr4500/mt25/keep6), greedy.
  Episódios com context overflow: EXCLUÍDOS do census (estimando de
  medição, regra do 29) e reportados — a regra 32a (R=0) vale só para o
  estimando de treino.
- Piso (gate de instrumento, espelho do 38): 1 null replay por
  trajetória válida a partir da 1ª decisão context_policy; exige ≥0.95
  de reprodução EXATA de R. Falha → x0 (célula não mensurável, STOP).
- Screening seletivo + census: FLIPS/ORDEM_TIPOS/MAX do pré-reg 29,
  round-robin, a′ via sample_alternative_v2 com escalação; duais
  last-mover (29a) marcados analíticos.
- Contabilidade PRIMÁRIA (a mesma fixada no 32): fração não-screened
  em pontos medidos SEM duais degenerados ≥ 0.20 → ABRE. As outras 3
  contabilidades reportadas, não decisórias.
- Desfecho c0 (census fecha com Gate 1 aberto): STOP antes do treino —
  dissociação registrada entre landscape treinável e crédito que
  compensa; o veto do census é exercido num landscape onde o poder
  existe. Publicável como caso A.

**TREINO LICENCIADO (só se Gate 1 E Gate 2 abrirem).**
- Split registrado (pool inteiro, sem seleção): estratos
  {f_mech = f_02/05/07/11 (resolvidas pelo mecanismo desenhado),
  f_easy = f_00, f_hard = 7 F restantes, p = 12 P}; dentro de cada
  estrato, ordenar por task_id; posições pares (0-index) → treino,
  ímpares → held-out. Resultado: 12 treino / 12 held-out, com 2 f_mech
  de cada lado. Split é função determinística do pool congelado.
- 4 braços × 3 seeds (1/2/3), protocolo IDÊNTICO ao pré-reg 32/33:
  outcome / ch / chm_cm / zero (controle não-treinado); rl.train_v2;
  budget 1600 chamadas LLM por célula (dose-matched: episódios +
  replays + a′ contam); lr 0.1, clip 1.0, k_credit 2, CENTER_V2;
  λ = λ* do Gate 1; emenda 32a em vigor (overflow = R=0 no treino).
- Contabilidade dual desde o desenho (lição do 31): braço outcome
  TAMBÉM avaliado fatiado nos nº de episódios dos braços ch e chm_cm
  por seed (re-eval greedy do θ no corte, fidelity gate do 31).
- Avaliação: held-out (12 tasks), greedy, R_eff(λ*), θ final por
  célula. Referências no held-out: 3 atratores + oráculo, computados
  por SUBSET dos artefatos congelados (greedy determinístico — sem GPU
  nova para referências).
- Taxa de fallback do a′ no 8B: resultado reportável (census 4B:
  87/114 a temp 0.8).

**Desfechos do treino declarados ANTES de rodar (primário: held-out
mean R_eff(λ*), comparação por seed):**
- **d1 (ramo positivo VALIDADO):** chm_cm > outcome em ≥2/3 seeds SOB
  AS DUAS contabilidades (dose- e episode-matched) E chm_cm held-out >
  max(atratores fixos held-out) nesses seeds (escapou do colapso).
- **d2 (ramo positivo FALSIFICADO informativamente):** ≥1 braço de
  aprendizado escapa dos atratores (held-out > max(atratores) em ≥2/3
  seeds) mas chm_cm ≤ outcome em ≥2/3 sob QUALQUER contabilidade →
  gate aberto ⇏ vitória do crédito; o gate permanece só-veto e o paper
  reporta a dissociação. Publicável como caso C.
- **d3 (colapso recorrente):** nenhum braço > max(atratores) em 2/3
  seeds → a correção por atrator ainda não basta; anatomia vai para o
  design brief. Publicável.
- Secundário (não decisório): chm_cm ≥ ch por seed; composição dos
  colapsos (qual atrator); taxa de overflow por braço.
- Linguagem registrada para QUALQUER desfecho: "in the pre-registered
  gate-open landscape, arm X achieved A vs. B across 3 seeds under
  matched episode/call budgets" — com média, per-seed, per-task,
  nº exato de chamadas LLM, nº de replays e custo adicional do census.
  NUNCA "credit training is better" sem escopo.

**Custo estimado:** Gate 1: 0 GPU. Gate 2: 24 episódios base + ~24
nulos + screening/census ~300–500 replays ≈ 3–5 h GPU (8B). Treino: 12
células × 1600 chamadas ≈ 19.200 chamadas ≈ 12–24 h GPU. Referências
held-out: 0 GPU (subset de artefatos). Total ≤ ~30 h GPU, dentro do
orçamento autorizado (40–60 h). Servidor: troca para Qwen3-8B durante a
fase inteira; Qwen3-4B restaurado ao final (padrão do 38).

**Riscos declarados:** (i) trajetórias-base do default com overflow em
excesso → census com N pequeno (reportado; se N válido < 12 tasks,
census vira x0 por poder do instrumento — limiar registrado agora);
(ii) episódios 8B mais lentos que o estimado → células podem parar por
max_episodes=none/budget (stopped_by reportado); (iii) colapso d3
mesmo com margem por atrator — desfecho previsto, não falha do desenho.

**ADENDO 39a (2026-08-27, antes de qualquer rollout):** a consequência
aritmética declarada no split ("Resultado: 12 treino / 12 held-out")
estava errada. A REGRA registrada (estratos, ordenação por task_id,
pares→treino, ímpares→held-out) produz 13 treino / 11 held-out: f_easy
tem 1 task (→treino), f_hard tem 7 (→4/3). A regra permanece
exatamente como registrada; corrigimos apenas a derivação. f_mech
continua 2/2. Também: environment.tasks_swe35 adicionado ao
environment/registry.py (_MODULES) — sem isso, NENHUM replay (census ou
braços de crédito) resolveria as tasks do pool 35; correção de infra
pré-dados, coberta pelos testes existentes.

**ADENDO 39b (2026-08-27, antes do census):** precisão sobre o piso: o
protocolo é o ESPELHO EXATO do estágio piso do 38 (null replay no 1º
candidato de screening da trajetória, sufixo greedy) — que é a decisão
context_policy de maior score quando existe (ORDEM_TIPOS começa por
context_policy), e outro tipo apenas em trajetórias sem candidato de
contexto. Gate inalterado: ≥0.95 exatos. Implementação:
experiments/preg39.py + experiments/preg39_chain.sh; Gate 1 já rodado
(analítico, 0 GPU): ABRE com λ*=0.1, margem mínima 0.166 (vs keep
0.166, vs summarize 0.3006, vs default 0.2568), robusto às
sensibilidades 0.15 e 0.08; split pela regra registrada = 13 treino /
11 held-out, f_mech 2/2.

**ADENDO 39c (2026-08-27, após leitura do gate 2, antes do desfecho):**
o gate 2 fechou pela regra registrada (desfecho mecânico c0), mas com
uma configuração que a regra não antecipou: a contabilidade primária
ficou com denominador VAZIO (0 pontos medidos sem duais) — os únicos 5
pontos mensuráveis do census são duais definicionais de termination.
Causa próxima: sample_alternative_v2 não encontrou a′ em 19/23 pontos
do passe 1 e 18/18 do escalonamento (~300 tentativas). Antes de
escrever o desfecho, rodamos uma SONDA pós-hoc declarada exploratória
e NÃO-decisória (experiments/anatomia39.py): reamostra a′ nos pontos
falhados gravando cada tentativa (inválida × igual-ao-original), sem
nenhum replay. Objetivo: distinguir instrumento (parse falha no 8B) de
fenômeno (modelo quase determinístico mesmo a temp 1.2). O desfecho c0
NÃO será revertido pela sonda; ela só qualifica a interpretação.
Custo: ~300 chamadas, sem replays. O treino segue NÃO executado (regra
registrada).

### DESFECHO 39 (2026-08-27): c0 — o veto do census disparou num landscape onde o poder existe; treino não executado

**Gate 1 (analítico, 0 GPU): ABRIU.** λ* = 0.1; margem mínima por
atrator do alvo condicional na média de R_eff = **0.166** (vs
keep_always 0.166, summarize_always 0.3006, default 0.2568), robusta às
sensibilidades 0.15 e 0.08. Split pela regra registrada (adendo 39a):
13 treino / 11 held-out, f_mech 2/2. A correção por atrator no nível do
sinal de treino faz o que prometia: destrava o falso-negativo do
critério per-task (que vetava 0/24).

**Gate 2 (census 8B, novo): FECHOU → c0 pela regra registrada; o treino
NÃO foi executado.** Instrumento válido: base 24 episódios → 17
trajetórias válidas (7 F com context overflow sob a config default,
excluídas e reportadas; ≥12 ✓), nulos 17/17 exatos, piso greedy 17/17
(1.00 ≥ 0.95). Screening: 92 flips medidos; dR≠0 por tipo:
termination 17/17, observation 4/29, test_schedule 1/17,
**context_policy 1/29**. Census: 23 pontos pivotais; a′ encontrado em
apenas 5 — TODOS duais definicionais de termination (braço HM
analítico, adendo 29a); 18/18 sem a′ mesmo na escalação a temp 1.2.
Contabilidade primária (medidos_sem_duais): **0/0 — denominador
vazio**, gate não abre → c0. As quatro células: com_duais 4/5 = 0.80
(abre); sem_duais 0/0 (nulo); pivotal_com 4/23 = 0.17 (fecha);
pivotal_sem 0/23 = 0.00 (fecha).

**Anatomia (sonda 39c, pós-hoc, não-decisória):** 320 amostragens de a′
(20 pontos × 2 temps × 8 seeds) + 144 resoluções de fase 2 = 464 saídas
do 8B. **Zero tentativas inválidas de parse, zero fase-2 sem bloco;
462/463 ações token-idênticas à original** (1 divergente, ~0.2%);
22/40 células ponto×temp com 8/8 idênticas. A ausência de a′ é
propriedade da célula (Qwen3-8B quase determinístico nos pontos j,
mesmo a temp 1.2), não falha do amostrador.

**Leitura registrada.** Nesta célula, a pivotalidade em R vive quase
inteira em termination (duais last-mover por construção); flips de
contexto mudam R em 1/29. A margem que abriu o Gate 1 é preço de
TOKENS (R_eff), não de R — e o census registrado rastreia mediação em
R. O c0 é exatamente a dissociação declarada no pré-registro: landscape
treinável (Gate 1 aberto) + nenhum contraste mensurável de mediação
(Gate 2 fechado) → o veto dispara e o treino não é pago. É o PRIMEIRO
exercício do ramo de veto da decision rule num landscape com poder
verificado — a licença deixou de ser conjectura de papel.

**Duas lições para o design brief (Apêndice L):** (i) o census de
screening deve medir a mediação NO MESMO estimando do sinal de treino
(R_eff precificado em λ*), não em R — um benchmark cujo sinal vive no
custo é invisível a um census de outcome; (ii) crédito mediado por a′
pressupõe entropia do modelo em j: com política quase determinística,
C_HM − C_M é não-identificável — a disponibilidade de a′ deve ser
reportada como diagnóstico de pré-condição da célula.

**Custos exatos.** Census: 24 episódios base + 17 replays de piso + 92
replays de screening + 5 replays M + ~328 amostragens de a′ ≈ 2h14 de
GPU (11:44→13:58). Sonda: 464 chamadas, 0 replays, ~1h30. Treino: NÃO
executado — ~19.200 chamadas (~12–24 h GPU) não pagas porque a regra
mandou não pagar. Fase D total ≈ 4h de GPU dos 40–60 autorizados.
Qwen3-4B restaurado no serving.

**Linguagem para o paper:** "In the pre-registered landscape where the
analytic per-attractor power gate opens (min margin 0.166 at λ* = 0.1),
the registered mediation census yielded zero measurable non-dual
points — the model is near-deterministic at the paired decision points
(462/463 identical resamples) — and per the pre-registered rule the
credit-training license was vetoed; no training was paid for." NUNCA
"o método falhou" nem "o método funciona": o que foi validado é o ramo
de veto da regra de decisão operando fora do landscape de calibração.

## ANÁLISE DESCRITIVA PÓS-DESFECHO 39 (não-decisional) — 2026-08-27

Declarada ANTES de tocar os dados. Motivada pela mesa de reviewers (R3-Q1 e AC):

1. **Pivotalidade do censo 39 recomputada em R_eff(λ*=0.1)** sobre os 92 flips de
   screening já pagos (zero rollouts novos). Contabilidade espelha o pré-reg 31:
   R_eff(ramo) = R − λ·prompt_tokens/1e5, com prompt_tokens do ramo flipado =
   prefixo pago das decisões ORIGINAIS [0:entry] + total do replay (entry = último
   ponto canônico ≤ index, como no build_flip_queue). Piso: mesmos nulos do estágio
   piso recomputados em R_eff (esperado: idênticos → piso exato preservado).
   Reportar por tipo: n(dR_eff≠0), mediana e máx |dR_eff|, comparados à margem do
   gate 1 (0.166). NÃO altera desfecho c0 (a ausência de a′ torna C_HM−C_M
   não-identificável em qualquer estimando); serve para separar as duas causas
   independentes do fechamento (entropia zero nos pontos pareados × censo
   registrado em R quando a margem vive em R_eff).
2. **Tabela de auditoria da regra de decisão** (paper, apêndice): célula × estado
   de cada gate × razão mecânica × desfecho × compute pago/economizado — dados já
   publicados no ledger, só consolidação.
3. **Hipótese registrável (design brief)**: anti-correlação estrutural power↔census
   quando o censo é registrado em R e a margem em R_eff; contra-exemplo parcial:
   V2-4B (censo abriu 0.39, power fechou). Enunciada como previsão, não testada aqui.

### Resultado da análise descritiva (R_eff nos 92 flips) — 2026-08-27

- **Piso preservado exato em R_eff**: 17/17 nulos com dR_eff = 0.0 (tokens
  reproduzem token-idênticos no replay nulo).
- **Conjunto pivotal idêntico**: os 23 pontos com |dR_eff| ≥ margem (0.166) são
  EXATAMENTE os 23 pivotais em R (termination 17, observation 4, test 1, context 1).
- **Efeito só-tokens é 2ª ordem**: entre os 69 flips com dR = 0, mediana
  |dR_eff| = 0.0035, máx = 0.0332 — 5× abaixo da margem do gate 1.
- **Leitura**: a preocupação "censo registrado em R quando a margem vive em R_eff"
  (R3-W1 da mesa) NÃO se materializa nesta célula: censear no estimando do treino
  não revela massa de mediação nova na escala da margem. O fechamento do gate 2
  fica com três sustentações independentes: (i) a′ inexistente (não-identificável
  em qualquer estimando), (ii) pivotalidade em R concentrada em duais de
  termination, (iii) recomputação em R_eff(λ*) sem massa nova. A hipótese de
  anti-correlação power↔census segue registrável para OUTRAS células, mas perde o
  mecanismo nesta. Artefatos: runs/preg39/releff_report.json, releff_rows.jsonl.

## ANÁLISE DESCRITIVA 2 PÓS-DESFECHO 39 (não-decisional) — 2026-08-27

Declarada ANTES de computar (schemas/contagens inspecionados, nenhum desfecho
lido). Motivada pela rodada 2 da mesa (R1-W2, R3-W1): completar a tab:audit a
custo zero de GPU.

1. **Power gate per-atrator post hoc na célula V1** (artefatos congelados
   c1c_margem/c1d_margem/pool.json): critério espelho do pré-reg 39 — margem do
   alvo condicional (thr600) sobre CADA atrator expressável (keep_always,
   summarize_always) em mean R_eff(λ), grade λ = a registrada do Act 4
   {2, 5, 10, 25}, λ* = argmax da margem mínima (empate → menor λ), ABRE sse
   margem mín ≥ 0.10. Conjuntos: (a) primário: todas as 52 tasks medidas nos
   reports de margem; (b) secundário: as 12 viáveis registradas (6 train +
   6 heldout). Desfechos possíveis: abre/fecha em cada conjunto; qualquer um é
   publicável e preenche a linha V1 da tab:audit. NÃO reabre decisão de treino
   (o treino V1 já rodou e está reportado).
2. **Censo em R_eff recomputado nas células V2-4B e Mistral-7B** (espelho da
   análise 1 do bloco anterior, generalizada): λ = 0.2 (λ* registrado do
   pré-reg 33; Mistral herda por ser o mesmo stack/magnitude de tokens),
   limiar de escala = 0.10 (margem registrada). Estágios: nulos (esperado
   dR_eff = 0), piso quando existir, screening (V2-4B: 690 flips; Mistral: 277).
   Métricas: identidade do conjunto {dR≠0} vs {|dR_eff| ≥ 0.10}, mediana/máx
   |dR_eff| dos flips com dR = 0 (efeito só-tokens). Testa se a inocuidade da
   recomputação (célula 8B) é geral ou não. Não altera nenhum desfecho
   registrado; alimenta a hipótese de anti-correlação e a linha correspondente
   da tab:audit.
3. **Polimentos declarados no paper** (sem dados novos): carimbo temporal da
   recomputação (pós-desfecho, pré-declarada, motivada pela mesa);
   "overdetermined" → dois mecanismos independentes com um cross-check em ambos
   os estimandos; nota prospectivo/retrospectivo na tab:audit.

### Resultados da análise descritiva 2 (2026-08-27)

**2.1 Power gate V1 post hoc** (`experiments/power_v1.py`,
`runs/preg39/power_v1_report.json`): no pool cheio (52 tasks) FECHA — melhor
min-margem 0.056 em λ=25 (margens sobre keep negativas em λ≤10). No pool
registrado de treino (12 viáveis) ABRE — min-margem 0.135 no λ*=5 registrado
(0.209 em λ=10). Leitura: a única célula em que a regra autoriza treino é a
célula onde o treino de fato rodou (Act 4) e colapsou para keep_always — o
gate filtra sinal identificável, não garante sucesso do otimizador
(necessário, não suficiente). Responde R1-W2: o ramo positivo FOI exercido
(retrospectivamente) e o desfecho já está no paper.

**2.2 Censo em R_eff, células V2-4B e Mistral** (`experiments/releff_cells.py`,
`runs/preg39/releff_cells_report.json`, λ=0.2, limiar 0.10): a identidade dos
conjuntos pivotais NÃO se mantém — V2-4B screening 114 (R) vs 116 (R_eff),
máx só-tokens 0.163; Mistral 49 vs 85, máx 0.164. Porém o piso de replay nulo
em R_eff nas mesmas células tem magnitude idêntica (máx 0.166 no 4B, 0.166 no
Mistral; piso greedy do Mistral = 0.0 exato): os cruzamentos só-tokens são
ruído de replay estocástico do estimando R_eff, não efeito da decisão trocada.
Conclusão honesta: o cross-check exato nos dois estimandos vale na célula
quase-determinística (8B, máx 0.033); nas células estocásticas um censo em
R_eff exigiria piso próprio. Nada registrado é alterado (censos foram
registrados em R; R_eff só entra nos power gates, que são médias por task).

## ANÁLISE DESCRITIVA 2.2b (não-decisional) — 2026-08-27

Declarada ANTES de computar. Motivada pela rodada 3 da mesa (R2-W1 = R3-W2:
"máx-vs-máx não é distribucional"). Extensão da análise 2.2, mesmos dados,
zero rollouts: para cada célula estocástica (V2-4B, Mistral), situar cada
cruzamento só-tokens (dR = 0 e |dR_eff| ≥ 0.10) na distribuição nula de
|dR_eff| da MESMA célula (replays nulos, análise 2.2): (a) quantil empírico
de cada cruzamento; (b) p de permutação = fração de nulos com |dR_eff| ≥ o
valor do cruzamento; (c) verificação individual (não só o máximo) de que cada
cruzamento está dentro do suporte nulo. Desfechos possíveis: cruzamentos
dentro do suporte/quantis não extremos (sustenta "ruído do estimando") ou
além do suporte (reportar e enfraquecer o escopo no paper). Qualquer um é
publicável. Requer persistir linhas por flip em releff_cells.py (mesmo
cômputo determinístico já executado).

### Resultado da análise 2.2b (2026-08-27)

(`experiments/releff_cells.py` estendido; `runs/preg39/releff_cells_report.json`)
Todos os cruzamentos só-tokens estão individualmente dentro do suporte nulo da
própria célula (V2-4B: 39/39 ≤ 0.166; Mistral: 44/44 ≤ 0.166). Quantis:
mediana do p de permutação 0.179 (4B) e 0.407 (Mistral); p < 0.05 em 4/39 e
1/44 — compatível com o esperado sob intercambialidade (≈2 por célula a 5%).
Diagnóstico mais forte: o próprio piso nulo cruza a escala 0.10 em 35/117
(30%, 4B) e 29/48 (60%, Mistral) dos replays — a escala registrada está
ABAIXO do piso de ruído de R_eff nessas células; qualquer censo nativo em
R_eff ali é não-potente sem piso próprio. Reverso (pivotal em R, < 0.10 em
R_eff): 37 (4B) e 8 (Mistral), mesma leitura. Sustenta "ruído do estimando"
distribucionalmente, não só por máximos.

## 2026-08-27 — PRÉ-REGISTRO 40 (antes de rodar): quarto braço da grade fatorial — R(h′,a)

Motivação: auditoria externa (Boclin). A grade fatorial 2×2 do ponto de
intervenção {(h,a),(h,a′),(h′,a),(h′,a′)} tem só 3 células medidas: o braço
C_H é R(h′, f(h′)) — modelo responde AO VIVO ao contexto flipado — ou seja,
um efeito total (direto + mediado), não a célula fatorial R(h′,a). A célula
R(h′,a) nunca foi executada, e sem ela I = C_HM − C_H − C_M não é interação
fatorial. (A Figura 1 do paper inclusive rotula errado o braço H como a_{t+1}
forçada — bug de exposição a corrigir independentemente do desfecho.)

**Predição do auditor (testável):** nos pontos screened de folga, a ação
original a foi gerada VENDO o contexto intacto e portanto re-injeta a
informação necessária (ex.: o valor lido de um arquivo) — logo R(h′,a) = R
e a interação fatorial legítima I_fact = C_HM − C_Ha − C_M = 0 (screening
como artefato da grade incompleta). Refutação: R(h′,a) < R em fração
relevante ⇒ a informação necessária vive no contexto de turnos POSTERIORES,
não dentro de a; screening tem componente genuíno de recuperação pelo modelo.

**População:** todos os pontos com C_M e C_HM medidos. V1: cf_results.jsonl
de teste3_{g450,g600,g900} (folga; 17+21+19=57) e teste3_{mt4,mt6,mt8}
(pressão; 22+21+22=65). V2: census_rows+census_esc_rows com C_M,C_HM
não-nulos (48; destes, 10 hm_analitico de termination têm quarto braço
TAMBÉM analítico: flip terminate em i encerra o episódio antes de j, logo
R(h′,a) ≡ R_H sem replay). Spans com retry excluídos (mesma recusa dos censos).

**Procedimento:** 1 replay greedy por ponto. Fila = decisões originais do
entry ao ponto do modelo, com flip do harness em i e a AÇÃO ORIGINAL a
(canônica, sem "forced") em j. V1: fila [cp: flip, tc: a] a partir de
cp_index — idêntica à fila nula já validada, exceto o flip. V2:
_fila_dupla(traj, i, flip, j, _canon(dj.chosen_action)). Mesmo servidor
vLLM (8321, Qwen3-4B, APC off, greedy seed 1234). Execução SEQUENCIAL —
paralelismo intra-GPU vetado pelo incidente _ls600_concorrente; a máquina
tem 1 GPU, então não há paralelismo entre instâncias (desvio declarado do
plano verbal "paralelizar": vetado pela premissa de determinismo).
Gate prévio: revalidação nula (2 pontos/config, fila nula), todos exatos,
senão aborta. Script: experiments/quarto_braco.py; rows em runs/preg40/.

**Desfechos declarados (primário = fração dos pontos screened de folga,
C_HM=C_M exato em g450/g600/g900, com R(h′,a) = R exato):**
- s1 (auditor confirmado): ≥ 0.90 ⇒ screening nos pontos de folga é
  majoritariamente artefato da grade incompleta; tese do paper reescrita
  para dominância do estimando/medição; I reinterpretado como contraste de
  efeito total, não interação fatorial.
- s2 (misto): 0.50–0.90 ⇒ mapa por ponto (artefato vs recuperação real);
  paper reporta as duas componentes.
- s3 (auditor refutado): < 0.50 ⇒ screening tem componente genuíno de
  recuperação pelo modelo; tese original fortalecida.
Secundários: distribuição de I_fact = C_HM − C_Ha − C_M por config/tipo;
comportamento nos 8 pontos de quebra da pressão; C_Ha (efeito direto do
harness) vs C_H (efeito total) — divergência mede quanto o braço vivo
mistura mediação. Custo: ~160 replays + 12 nulos. Reportamos qualquer desfecho.

### DESFECHO 40 (2026-08-30): quarto braço R(h′,a) — s1, auditor (Boclin)
CONFIRMADO nos pontos screened de folga

**Gate nulo: PASSOU.** 16/16 replays de revalidação nula exatos (12 V1 =
2 pontos × 6 configs; 4 V2 = 2 pontos × 2 configs) — execução autorizada.

**Endpoint primário: s1.** 57 pontos screened de folga (C_HM = C_M exato,
g450/g600/g900): **56/57 com R(h′,a) = R exato → fração 0.9825 ≥ 0.90.**
A predição do auditor está confirmada na folga: a ação original a, gerada
VENDO o contexto intacto, re-injeta a informação necessária; trocar a
decisão do harness em i e forçar a ação original em j restaura o reward.
O screening nos pontos de folga é majoritariamente ARTEFATO DA GRADE
INCOMPLETA, não recuperação genuína pelo modelo.

**Secundários (registrados conforme o pré-reg):**
- V1 folga por config: g450 17/17 exatos (I_fact = 0 em todos); g900
  19/19; g600 20/21 (única quebra da folga, |I_fact| = 0.0769).
- V1 pressão (mt4/mt6/mt8, 65 pontos): 8 quebras listadas em
  v1_quebras_pressao (api_router cp0 em mt6/mt8 com I_fact = 0.375 mesmo
  com exact_ha — ponto NÃO screened; l_log_parser e l_vending_machine com
  R(h′,a) < R). Fora da folga, R(h′,a) < R em fração relevante: a
  informação necessária às vezes vive no contexto de turnos POSTERIORES
  — a componente genuína existe, mas não nos pontos screened.
- Divergência efeito total vs direto: C_H ≠ C_Ha em **83/122 pontos V1
  (68%)** — o braço vivo C_H mistura mediação na maioria dos pontos;
  C_Ha (direto) é o estimando fatorial correto.
- V2 (48 pontos, 0 erros de replay): context_policy 13/23 exatos
  (I_fact médio +0.018, máx 0.364); observation_policy 4/12 exatos
  (máx |I_fact| = 1.0 — tipo mais instável); termination 10/10
  analíticos (flip encerra antes de j ⇒ R(h′,a) ≡ R_H por construção;
  9/10 com I_fact = 0); test_schedule 2/3.

**Leitura registrada (consequência s1, pré-declarada no pré-reg 40).**
I = C_HM − C_H − C_M NÃO é interação fatorial: C_H é efeito TOTAL
(modelo responde ao vivo ao contexto flipado) e a célula R(h′,a) mostra
que, na folga, I_fact = C_HM − C_Ha − C_M = 0. I passa a ser lido como
contraste entre efeito total e soma dos efeitos diretos — medida de
QUANTO o braço vivo mistura mediação (68% dos pontos V1), não sinal de
interação causal. A tese do paper se desloca para dominância do
estimando/medição, conforme declarado.

**Pendências abertas por este desfecho:** (i) Figura 1 rotula o braço H
como a_{t+1} forçada — bug de exposição, a corrigir INDEPENDENTEMENTE
do desfecho (já declarado no pré-reg); (ii) reinterpretação de I no
texto principal (Measurement/Finding) e no Apêndice da grade fatorial;
(iii) linguagem: screening nos pontos de folga = "artefact of the
incomplete factorial grid"; NUNCA "interação não existe" — fora da
folga e em observation_policy há componente genuína.

**Custos exatos.** 186 rollouts sequenciais (16 nulos de gate + 122
replays V1 + 38 replays V2; os 10 termination V2 são analíticos, sem
replay), 176 trajetórias de replay gravadas em runs/preg40/replays/,
janela registrada 20:09→20:16 (mesma sessão do pré-reg, APC off, greedy
seed 1234, Qwen3-4B porta 8321). Artefatos: runs/preg40/{gate,v1,v2}_rows.jsonl
+ report.json.

## 2026-09-10 — Mesa ICLR rodadas 11 e 12 (agente `iclr` reescrito: Fable 5.1, ISOLADO em paper/)

Mudança de protocolo: a mesa agora só lê `paper/` (condição do reviewer
real). Rodadas 1–10 liam o diário e eram otimistas por vazamento (rodada
10: 7/10 accept). Notas caem para o patamar realista.

**Rodada 11 (paper pré-40, commit ce183cf):** R1 4 / R2 3 / R3 5 → AC
≈4.0 Reject. R1 detectou SOZINHO, pela Fig. 1 ("live") + Remark de
mediação, a célula fatorial ausente R(h′,a) — validação independente da
auditoria Boclin/pré-reg 40.

**Rodada 12 (paper pós-40, commit 2f1bef6):** R1 4 (Soundness 2) / R2 3
(Soundness 2) / R3 4 (Presentation 1) → AC ≈3.7 Reject. Consenso: o
quarto braço RESOLVE a weakness técnica (célula medida, Fig. 1 certa,
Remark 3 com I = I_fact − (C_H − C_Ha) correto), mas o paper NÃO absorveu
as consequências — está internamente contraditório:
- Título/abstract/conclusão vendem screening-off como finding; §4.3 e
  Contribuição 2 dizem "artifact of the incomplete grid". Conclusão nem
  menciona a quarta célula. Abstract cresceu para ~400 palavras com as
  duas teses.
- Prop. 1(iii), Cor. 2 e regra v1.0(v) ("never bill C_H") contradizem a
  nota de escopo do App. B ("C_H is the estimand when only the harness
  trains") e §4.3 ("C_Ha is the correct factorial estimand") — TRÊS
  prescrições incompatíveis do que bilhar.
- Leitura de R1/R2 (a mais dura, e provavelmente certa): pela Cor. 1
  ("context ops não modificam o ambiente"), CDE do harness a ação fixa é
  zero sempre que a ação já resolve a task → C_Ha = 0 em 56/57 é quase
  teorema de desenho; "double-counting" = efeito indireto renomeado;
  Act 4 comparou efeito total (C_H, correto p/ harness-only) com CDE zero
  por desenho e chamou de "bias load-bearing". Leitura correta do Act 4:
  outcome-only (MC do efeito total, sem replay tax) > C_H (mesmo
  estimando + tax) > CDE (zero) — achado sobre custo de estimação, não
  sobre crédito.
- Itens de custo zero NÃO corrigidos desde a 11: F3 ilegível (10.8" em
  linewidth), F5 = Act 2 (Act 4 sem figura), FIGURAS.md obsoleto, sem
  glossário de configs/outcomes, zero figuras de dados no main text,
  30/40/52 tasks sem reconciliação, "never separated" obsoleto em App. B,
  main.aux não recompilado (9pp não verificável), nome "Boclin" em
  submissão anônima (L511, L1980).
- Bib: as 5 chaves da rodada 11 corrigidas ✓.

**Top-3 do AC (Δnota/custo):**
1. RE-TESE em torno do achado fatorial (escrita, 2–3 dias; 4 → 5–6): novo
   título; abstract ≤200 palavras com UM número primário; contribuições/
   conclusão coerentes: para decisões de contexto o harness não tem caminho
   direto para R (CDE = 0 em 56/57), todo crédito de harness é mediado,
   C_H (efeito total) é o estimando correto para harness-only training,
   C_HM − C_M e C_Ha são CDEs relevantes só para treino conjunto; census
   gate preça a massa com CDE ≠ 0. Reescrever Prop. 1(iii), Cor. 2, regra
   (v); remover "never separated".
2. Compressão + custo zero (1–2 dias): scatter C_H vs C_Ha (122 V1 + 48
   V2, por regime/tipo) e figura census/gate no main text; F3 em 5.5";
   F5 → Act 4; quadro-glossário; linha da 4ª célula na Tabela 1;
   reconciliar 30/40/52; remover nome; recompilar e garantir ≤9pp;
   FIGURAS.md reescrito.
3. Re-derivar gate e Act 4 no estimando fatorial + control variate
   (~1 dia análise + ~1 dia GPU): (a) Tabela 3 / massa não-screened
   recalculada com I_fact/C_Ha nos 48 V2 já medidos (0 rollouts);
   (b) 5º braço control-variate (outcome + crédito corrigido como
   baseline) × 3 seeds no setup do Act 4; (c) quarta célula nas células
   externas (MBPP+/HumanEval+) e 8B/Mistral (~150 replays).

**Não mexer:** §4.1 + App. J (piso zero, reconciliação, incidentes), Fig. 1
atual (4 braços), Remark 3, ledger/claims table (só linhas afetadas),
controles a′/a′_s.

**Pergunta mais difícil pro rebuttal:** "Dado R(h′,a) = R em 56/57 e Cor. 1,
o que o census gate mede que não é conhecido a priori do TIPO de decisão?
E se C_H é o estimando correto para harness-only (App. B), em que sentido
o arm 2 era 'biased'?"

**Rodada 13-pré (mesmo dia) — tese "harness como mediador" submetida como
claim.** Veredito: direção certa, ≈4.7 se só reescrita. Correções acatadas:
(1) I é identificado — I = I_fact − PE (porção eliminada); NUNCA "não
identificado"; (2) NDE = 0 em folga é quase consequência da Cor. 1 + desenho
do pool V2/L (informação consumida na próxima ação) → re-escopar: "NDE = 0
é propriedade do tipo de decisão × horizonte de consumo; o gate mede a
fração com NDE ≠ 0" (observation V2 4/12 e api_router I_fact = 0.375 viram
evidência a favor); (3) retirar "explica 2608.19760" (ALFWorld, sem
harness); (4) pré-reg 31 (outcome ≥ C_H a episódios iguais, 3/3 seeds)
contradiz a prescrição harness-only — precisa de explicação (sinal exato
esparso vs. ruidoso denso) ou Claim 3 cai. Testes de custo zero apontados:
tabela 2×2 folga×pivotal com |C_H|; R(h′,a′_s) vs R_H nos 44 pontos do
pré-reg 26 (consistência do modelo de mediação). Título sugerido: "Harness
Credit Is Mostly Mediated: Four-Arm Replay Separates Total from Direct
Effect in a Two-Layer Coding Agent". Plano completo em PROXIMOS-PASSOS.md.

## 2026-09-10 — PRÉ-REGISTRO 41 (antes de rodar): análises de custo zero para a tese "crédito de harness mediado"

Zero rollouts. Só leitura de runs/ já gravados (cópia da 4090 extraída hoje
de tcc_runs_full.tgz, 43.708 arquivos; sha do preg40/report.json conferido
contra o desfecho 40). Script: experiments/preg41.py → runs/preg41/report.json.
Nomenclatura: NDE := C_Ha (efeito direto controlado do harness, ação fixa);
TE := C_H (efeito total, braço vivo); I = I_fact − PE com PE = C_H − C_Ha.

**(a) Tabela 2×2 folga × pivotal (V1, g450/g600/g900, 57 pontos do preg40).**
Cruzamento pivotal (TE ≠ 0) × direto-nulo (NDE = 0). Endpoint primário:
m = fração dos pivotais de folga com NDE = 0 (mediação pura: TE ≠ 0 ∧
NDE = 0). Desfechos: m1 ≥ 0.90 (mediação pura dominante — vira o número
primário do abstract); m2 0.60–0.90 (mista; reportar por config/task); m3
< 0.60 (mediação não domina; a tese re-escopada cai para "NDE = 0 só nos
não-pivotais", que é trivial). Reportar |TE| (mediana, IQR, máx) nos
pivotais com NDE = 0 e n de pares únicos (task, cp_index). Secundário: mesma
tabela em pressão (mt4/6/8, 65 pontos) e em V2 por tipo (48 pontos).

**(b) Consistência do modelo de mediação (44 pontos do pré-reg 26, a′_s).**
a′_s ≈ f(h′) amostrado do estado sumarizado. Se o harness age só via ação,
R(h′, a′_s) ≈ R(h′, f(h′)) = R_H. Teste: k = fração com r_cf_hm == r_orig −
C_H exato. Desfechos: k1 ≥ 0.75 (consistente — a′_s é proxy válido de f(h′)
e o efeito total é reproduzido pela via mediada); k2 0.50–0.75 (parcial —
a′_s amostrado a temp > 0 diverge de f(h′) greedy; reportar por regime); k3
< 0.50 (inconsistente — sinaliza caminho direto ou a′_s inválido). Reportar
por regime (folga/pressão) e as discordâncias anatomizadas (ΔR, direção).

**(c) Horizonte de consumo da informação (V2, 48 pontos; V1 pressão, 8
quebras).** Hipótese (R2): NDE ≠ 0 ocorre quando a informação destruída em
i é consumida DEPOIS de j. Proxy operacional pré-declarado: H = nº de
decisões tool_call após j até o fim do episódio original (horizonte
restante). Teste exploratório: Mann-Whitney unilateral H(NDE ≠ 0) >
H(NDE = 0), α = 0.05, sem gate — reportado como descritivo. Anatomia dos 8
pontos observation_policy com NDE ≠ 0 e do api_router (I_fact = 0.375).

**(d) Tabela 3 / massa não-screened no estimando fatorial (V2, 48).** Por
tipo: fração I_fact = 0, fração NDE = 0, fração TE ≠ NDE. Descritivo; entra
no paper como coluna adicional, sem mudar o veredito s3 do census (que é
sobre C_HM vs C_M).

**(e) Diagnóstico do pré-reg 31 (Ato 4, c1d_*, 3 seeds).** Por que o braço
C_H (estimando exato) não vence outcome-only a episódios iguais? Medidas
pré-declaradas: densidade do sinal s = fração de decisões por episódio com
crédito ≠ 0 no braço C_H vs outcome (outcome: todas as decisões do episódio
recebem R); variância entre episódios do sinal por decisão; nº de
atualizações não-nulas acumuladas por seed. Hipótese: s ≪ 1 (sinal exato
mas esparso) — outcome-only paga a "tax" de ruído mas atualiza todas as
decisões. Descritivo; se s > 0.5 a hipótese cai e Claim 3 é reescopado.

**(f) n efetivo.** Pares únicos (task, cp_index) e tasks únicas por célula,
reportados ao lado de cada contagem do paper.

## 2026-09-10 — PRÉ-REGISTRO 42 (antes de rodar): quarta célula R(h′,a) fora da tripla V1/4B

Motivação: R3 (rodada 13-pré) — 56/57 vem de um pool sintético (V2/L)
desenhado para consumo imediato da informação; NDE = 0 pode ser artefato de
desenho. Teste: replicar a quarta célula nas células externas já censadas.

**População (primária, Qwen3-4B, todas 100% screened no census):**
teste3_{mbpp_g600, mbpp_mt6, he_g600, he_mt6} — 31+35+38+39 = 143 pontos,
dos quais 49 pivotais (TE ≠ 0). **Secundária (Qwen3-8B):** teste3_{q8_g600,
q8_mt4, q8_mt6} — 28+35+34 = 97 pontos (79 screened, 74 pivotais); exige
download do Qwen3-8B (não estava no cache desta máquina; iniciado hoje).
**Terciária (Qwen3-1.7B, só se sobrar janela):** mbpp17_*, q17_*.
Ordem de execução: pivotais primeiro, depois não-pivotais; chain reentrante.

**Procedimento:** idêntico ao pré-reg 40 V1 (fila [cp: flip, tc: a
original] a partir de cp_index; LLMClient max_tokens=1200 como no census;
greedy seed 1234; APC off; série; 1 GPU). Máquina NOVA: H100 via Slurm
(partição h100n2), vLLM 0.8.5.post1. Script: experiments/preg42.py; job
slurm/preg42.sbatch; rows em runs/preg42/.

**Gate (Fase 0, condição de identificação na H100):** revalidação nula —
2 pontos por config com fila 100% original (V1 g450/g600/g900 + as 4
células externas + q8 quando servido) → TODOS exatos (ΔR = 0.0), senão
aborta e investiga (App. J). Registrar job id, GPU, versão vLLM.

**Desfechos declarados (primário = fração dos PIVOTAIS screened das 4
células externas 4B com R(h′,a) = R exato):**
- s1 ≥ 0.90: mediação replica fora do pool sintético — tese deixa de ser
  "uma tripla".
- s2 0.60–0.90: parcial — reportar por célula/ambiente; tese re-escopada
  por ambiente.
- s3 < 0.60: NDE = 0 é artefato de desenho do pool V2/L — o paper reporta
  como LIMITAÇÃO CENTRAL e a tese volta a "medição + caso documentado".
Secundários: mesma fração nos não-pivotais (esperado ≈1 trivialmente), por
célula, 8B, distribuição de I_fact, nº com TE ≠ NDE, n de pares únicos.
Custo: ~143 + 97 replays + ~22 nulos ≈ 260 rollouts sequenciais.
Reportamos qualquer desfecho.

### DESFECHO 41 (2026-09-10): m1 + k1 — mediação pela próxima ação domina na folga; horizonte prediz onde não domina

Script experiments/preg41.py (11 testes), report runs/preg41/report.json.
Contagens brutas conferidas à mão contra runs/preg40/v1_rows.jsonl.

**(a) Tabela 2×2 folga V1 (57 pontos):** pivotais (TE ≠ 0) 37 → NDE = 0 em
**36/37 (m = 0.973, m1)**; não-pivotais 20/20 NDE = 0. |TE| nos 36:
mediana 0.875, IQR [0.84, 0.90], máx 1.0. n efetivo: 29 pares únicos
(task, cp_index), 20 tasks. Por cfg: g450 17/17, g600 12/13 (única
quebra: l_log_parser, TE = −0.154, NDE = +0.077), g900 7/7. **Número
primário do abstract: 36/37.** Pressão (65): pivotais 39/46 (0.848),
não-pivotais 19/19. V2 (48, todos pivotais): 19/48 (0.396); por tipo:
context 13/23, observation 4/12, test_schedule 2/3, **termination 0/10**.
Leitura: termination TEM caminho direto por construção (encerra o
episódio) e dá NDE ≠ 0 em 10/10 — controle positivo embutido da tipologia;
context ops não têm (Cor. 1) e dão NDE = 0 em 36/37 na folga.

**Nuance de interpretação (registrar no paper):** C_Ha fixa SÓ a ação
imediata a_j; as decisões posteriores respondem ao vivo. Logo NDE = 0 lê-se
"o efeito do harness é integralmente carregado pela próxima ação do
modelo"; NDE ≠ 0 em decisões de contexto NÃO é caminho direto (Cor. 1) —
é efeito carregado por ações posteriores. O que a quarta célula mede é
**quanto do efeito passa pela próxima ação**, e a resposta depende do
horizonte.

**(b) Consistência da mediação (pré-reg 26, 44 pontos):** R(h′, a′_s) =
R_H exato em **36/44 (k = 0.818, k1)**; folga 0.807, pressão 0.846. As 8
discordâncias têm todas Δ > 0 (R(h′,a′_s) > R_H; grade_curve ×4,
csv_normalizer ×3, c_temp_label ×1): a′_s amostrado a temp > 0 acha ação
melhor que o greedy f(h′) — divergência de amostragem, não caminho direto.

**(c) Horizonte (H = nº de tool_calls após j):** NDE ≠ 0 tem horizonte
maior em todas as populações: V2 total mediana 8 vs 1 (U = 357, p =
0.042); V1 pressão 3 vs 1 (p = 0.004); V1 folga 8 vs 1 (p = 0.049, n = 1);
**V2 context_policy 6.5 vs 1 (p = 0.011)**. observation_policy: sem
diferença (12 vs 15, p = 0.43) — o efeito de formatação da observação
passa por várias ações posteriores independentemente do horizonte.
termination: n/a. Confirma a re-escopagem do R2: NDE = 0 é propriedade de
tipo × horizonte de consumo.

**(d) V2 no estimando fatorial (48):** I_fact = 0 em 0.479 (vs screened
C_HM = C_M em 0.50); TE ≠ NDE em 0.396; por tipo: context I_fact = 0 em
0.435, observation 0.25, termination 0.90, test_schedule 0.33. O veredito
s3 do census não muda; a coluna entra como informação adicional.

**(e) Diagnóstico do pré-reg 31 (c1d, 3 seeds):** braço C_H: 1.89
créditos/episódio sobre 4.87 pontos → **densidade 0.39** (outcome: 1.0);
|crédito| mediana 0.039 (máx 1.10); 3.2 chamadas LLM por crédito (chm_cm:
9.6); grad_norm mediana **0.062 vs 0.295** no outcome (≈5×). Explicação
mecânica, sem "bias": a episódios iguais, o braço exato atualiza 39% das
decisões com passo ~5× menor ao mesmo lr → ~12× menos massa de atualização
por episódio; outcome-only atualiza todas as decisões com sinal ruidoso
mas denso e grande. É eficiência de otimização/estimação, coerente com
Claim 3 (mesmo estimando, custo maior) — mas a prescrição "bille C_H" só é
vantajosa se o passo for reescalado; o paper deve dizer isso.

**(f) n efetivo:** V1 folga 29 pares/20 tasks; pressão 27 pares. Células
externas (para o pré-reg 42): mbpp 31+35 pts (3+5 pivotais), he 38+39
(20+21), q8 28+35+34 (22+26+26). Entra ao lado de cada contagem no paper.

## 2026-09-11 — Noite de loop até a mesa: Fases 2–5 (preg42 pendente, re-tese fechada, 9pp, auditoria)

**Máquina:** cluster Slurm `dgx-H100-02` (h100n2), 8/8 GPUs alocadas por
outros usuários a noite inteira. `runs/` presente (cópia da 4090). Jobs
`preg42` já estavam na fila desde 2026-09-10 23:40 (32249 = 4B default;
32250 = 8B): estado PD (Resources/Priority), start estimado pelo Slurm
**2026-09-28** — sem GPU esta noite. **Pré-reg 42 fica PENDENTE**; nada
foi olhado (runs/preg42/ não existe). Ledger #42 permanece "running"; o
paper declara o ramo de falha na seção Threats. Toolchain instalada sem
sudo: tectonic em ~/.local/bin (cache em /raid), PyMuPDF via uvx
(previews em runs/fig_preview/). `impl` instalou matplotlib no .venv via
`uv pip` (pyproject intocado) para regenerar figuras.

**Fase 3+4 (commit 6fe1dfa):** re-tese fechada e compressão: scoreboard →
App. Shield (com linha da 4ª célula 56/57 + 36/37), síntese → App.
Replication, gate V2 + Scope + last-mover + 8B false negative → novo App.
"V2 Census: Gate Accounting and Scope"; §7 condensado; glossário de
configs/outcomes = Tabela 1; Fig. 2 = scatter TE×NDE (122 V1 + 48 V2),
Fig. 3 = census em leitura de mediação (fração NDE≠0 por população/tipo,
linha 0.20); F3 em duas linhas 5.5"; F5 = Act 4 (c1d_*) com controle
episode-matched (ato4_em); tasks reconciliadas (30 designed, split 20/10;
22 curated; 52 únicas); 56/57 ↔ 36/37 explicado uma vez; Threats ganhou
parágrafo "pool design + pré-reg 42 com ramo de falha declarado";
FIGURAS.md reescrito em inglês. Compilação (tectonic): **Conclusão termina
na p9**; só o Reproducibility Statement (não contado pela ICLR) cai na p10;
32 pp no total; 0 refs quebradas; grep de anonimato limpo.

**Fase 5a — auditoria `revisor` (preg41/42 + coerência).** Achados aceitos
e corrigidos:
1. **ERRATA (bloqueante) no DESFECHO 41(a)/(f) acima:** "29 pares únicos /
   20 tasks" refere-se aos **57** pontos de folga; os **37 pivotais**
   colapsam em **16 pares únicos (task, cp_index) / 14 tasks, 15/16 com
   NDE = 0 (0.938, ainda m1)**. E o per-cfg correto é **g450 12/12, g600
   12/13, g900 12/12** (17 e 7 eram n total g450 e npiv g900 — erro de
   transcrição meu; report.json sempre esteve certo). preg41.py agora
   reporta `piv_pares_unicos`, `piv_tasks_unicas`, `piv_pares_nde0`,
   `m_por_par`; paper (intro, §4.4, Threats, claims, ledger #41) corrigido.
2. **"12×" era dupla contagem:** grad_norm em train_c1.py é a norma do
   gradiente SOMADO do episódio (já incorpora densidade). Razão honesta:
   0.295/0.062 ≈ **4.8×** por episódio. Paper: "~5×".
3. **Cor. arm2 qualificada:** −I = C_H em todo ponto screened; = PE só onde
   C_Ha = 0 (36/37). l_log_parser é screened com C_Ha = 0.077 (−I = −0.154,
   PE = −0.231).
4. **Horizonte V1 incluía não-pivotais** (NDE = 0 trivial). Sensibilidade
   só-pivotal adicionada ao report: V1 pressão p = **0.0008** (7 vs 39;
   mais forte), V1 folga p = 0.026 (n = 1). V2 context p = 0.011 já era
   só-pivotal (V2 não tem não-pivotais). Tabela 2 e ledger anotados.
5. **preg42 `_resumo`** agora reporta pivotais não-screened
   (`n_pivotal_nao_screened`, `n_exact_ha_pivotal_nao_screened`) — no q8
   (79/97 screened) esses pontos ficavam fora do primário sem serem
   mostrados. Endpoint primário INALTERADO (pré-registrado: pivotal ∧
   screened); a coluna é secundária descritiva.
Verificados sem problema: pivotal = C_H ≠ 0 vem do census (independente de
C_Ha); 36/44 comparável (mesma row, mesma direção); max_tokens = 1200 em
teste3 externo, preg40 V1 e preg42 (comparáveis); cf_results externos têm
C_H/C_M/C_HM; sem resíduos de linguagem ("never separated", "not
identified", "explains 2608", "generalizes across families"); refs de
tabela/figura simbólicas e corretas após a reorganização. Item menor
aberto: regra v1.0(v) não diz qual CDE usar quando C_Ha ≠ C_HM − C_M.

**Correção do registro acima:** os jobs 32249/32250 RODARAM em
2026-09-11 12:54 (o Slurm liberou GPU antes do estimado), 4 min após o
commit f33684a. O texto "preg42 pendente" era verdadeiro na hora do commit;
o desfecho vem abaixo.

**Fase 5b — Mesa ICLR rodada 14 (isolada, paper/ em f33684a, SEM o 42):**
R1 5 / R2 5 / R3 3 → AC ≈ **4.33** (Reject/borderline; subiu de 3.7).
Top-3 do AC: (1) concluir o pré-reg 42 (então bloqueado por GPU); (2)
reenquadrar como "proximal vs distal mediation" — pela Cor. behav, para
context ops a mediação por ALGUMA ação do modelo é dada por construção,
logo "mostly mediated" soa tautológico; o conteúdo empírico é QUAL ação
carrega o efeito (próxima vs posteriores) e o horizonte — e mover V2/regra
para apêndice, trazer F1/F5 ao corpo (0 GPU); (3) braço C_H com passo
reescalado × 3 seeds no setup do Act 4 (GPU; testa a prescrição
harness-only). Pergunta mais difícil: "Dada a Cor. behav, o que sobra de
empírico em 'mediated' além de proximal vs distal?" Não mexer: piso/App.
J, Fig. 1, Remark 3, ledger. Ações: (1) feita (DESFECHO 42 abaixo); (2)
feita em 82c92e5 (abstract/intro/§4.4(ii)/conclusão nomeiam proximal vs
distal; regra (v) nomeia os dois CDEs); (3) pendente de GPU e de
pré-registro (43).

### DESFECHO 42 (2026-09-11): s1 — a mediação pela próxima ação replica fora da tripla V1/4B (48/49 externo; 8B 51/57 screened, 0/17 não-screened)

**Execução (Slurm, nó dgx-H100-02, partição h100n2, vLLM 0.8.5.post1,
APC off, série, greedy seed 1234, max_tokens 1200):** job **32249** (GPU 0,
Qwen3-4B, porta 8321, 6m14s, exit 0): gate + 4 células externas; job
**32250** (GPU 1, Qwen3-8B, porta 8322, 4m54s, exit 0): só `q8_g600` —
`sbatch --export=ALL,GATE_CELLS=a,b,c` quebra a lista nas vírgulas, então
q8_mt4/q8_mt6 não rodaram (exemplo no .sbatch corrigido). Job **32303**
(q8_mt4 + q8_mt6, porta 8322) submetido 15:26 e concluído 15:31 — o
secundário 8B abaixo já é completo. Rollouts: 20 gate + 143 + 97 = 260; 0
timeouts, 0 erros. Rows: runs/preg42/{gate_rows,rows}.jsonl;
report.json. Contagens conferidas à mão contra runs/teste3_*/cf_results.jsonl
(n, pivotais e screened por célula batem: mbpp_g600 31/3/31, mbpp_mt6
35/5/35, he_g600 38/20/38, he_mt6 39/21/39, q8_g600 28/22/23, q8_mt4
35/26/28, q8_mt6 34/26/28).

**Gate nulo (condição de identificação na H100): 20/20 exatos, ΔR = 0.0**
(2 pontos × {g450, g600, g900, mbpp_g600, mbpp_mt6, he_g600, he_mt6,
q8_g600, q8_mt4, q8_mt6}). Piso zero transporta da 4090 para a H100 em
ambos os modelos.

**Primário (4B externo, pivotal ∧ screened, endpoint pré-registrado):
48/49 = 0.980 → s1.** Por célula: mbpp_g600 3/3, mbpp_mt6 4/5, he_g600
20/20, he_mt6 21/21. n efetivo: 49 pontos = **29 pares únicos (task,
cp_index) / 29 tasks; 28/29 pares exatos em toda célula**. |TE| mediana
0.80 nos 49 (he 0.625, mbpp 0.83–0.86). 43/49 saturados (R = 1.0) — as
células externas são o regime saturado que o census já descrevia; a
mediação replica nele. Única quebra: **mbpp_7 cp0 em mt6**: C_H = 0.4,
C_Ha = 0.4, C_M = 0, C_HM = 0 → I_fact = −0.4: a ação original a NÃO
re-injeta sob h′ (NDE = TE, mediação zero pela próxima ação), mas o a′
amostrado re-injeta (C_HM = 0). Mesmo padrão do l_log_parser V1: a
informação é consumida depois de j.

**Secundários 4B:** não-pivotais 91/94 exatos; as 3 exceções têm TE = 0 e
NDE ≠ 0 (mbpp_7 cp12 g600 C_Ha = 0.4; he_4 cp0 g600 0.222 e mt6 0.111):
ao vivo o modelo compensa o flip (TE = 0), mas com a ação original fixa o
flip custa — mascaramento do efeito total, não caminho direto. TE ≠ NDE
em 51/143; I_fact = 0 em 139/143 (os 4 ≠ 0 são exatamente as 4 quebras
acima, máx |I_fact| 0.4).

**Secundário 8B (q8_g600 + q8_mt4 + q8_mt6 = 97 pontos; jobs 32250 e
32303 — este último GPU 1, porta 8322, 4m09s, exit 0, gate q8_mt4/q8_mt6
4/4 exatos → gate total 20/20):** pivotal ∧ screened **51/57 = 0.895**
(21 pares únicos/18 tasks; 18/21 pares exatos em toda config) — no limiar
s1/s2 do secundário (o endpoint primário é só 4B externo). Por célula:
g600 16/17, mt4 18/20, mt6 17/20. As 6 quebras screened são 3 tasks:
l_log_parser cp0 ×3 (C_H = 1.0, C_Ha = 0.77–0.85, C_M = C_HM = 1.0),
api_router cp0 ×2 (C_H = 1.0, C_Ha = 0.125, C_M = C_HM = 1.0) e
l_door_controller cp6 mt6 (C_H = 0.23, C_Ha = 0.08). Em 5/6 o ponto é
"screened" porque AMBOS os braços com a′ falham a task inteira (C_M = C_HM
= 1.0): screening por saturação em falha do braço M, não por re-injeção —
e aí a quarta célula mostra NDE ≈ TE (efeito quase todo não mediado pela
próxima ação). **Pivotal ∧ não-screened: 0/17 exatos** — os 17 pontos
onde o 8B quebra o shield (as 5 tasks cp0 do pré-reg 15 em 3 configs +
l_door_controller cp0/cp3) têm NDE ≠ 0 em 17/17, com I_fact = 0 exato em
15/17 (aditivo: C_HM = C_Ha, C_M = 0) e os 2 restantes = l_door_controller
(I_fact = −0.08, +0.46, a sinergia não-saturada já reportada). Leitura: no
8B, não-screened ⇒ NDE ≠ 0 (17/17) e screened ⇒ NDE = 0 (51/57): a "massa
não-screened" do census coincide com a massa de efeito direto — coerência
entre as duas leituras do census (Cor. gate). Não-pivotais 23/23. I_fact
= 0 em 88/97; TE ≠ NDE em 74/97. Saturação: 54/57 pivotais screened com R
= 1.0.

**Custo total:** 20 gate + 240 replays = 260 rollouts, ~15 min de GPU H100
em 3 jobs (32249, 32250, 32303), 0 GPU-h de treino, 0 timeouts, 0 erros.
Ledger #42 → held (s1 no primário; 8B secundário 0.895 no limiar). Entra
no paper: abstract (uma frase), §4.4 parágrafo externo, Tab. 2 (linhas
externas + 8B), Fig. 2/3 (células do 42), App. Replication (8B quarta
célula), ledger, claims table, Threats (o ramo s3 não se materializou;
limitação passa a ser "regime saturado" e "uma família").

## 2026-09-11 — Mesa ICLR rodada 15 (isolada, paper/ em 82c92e5, COM o 42 e o reenquadramento proximal/distal)

R1 6 (Soundness 3) / R2 5 / R3 6 → AC **5.67, Borderline** (r14 4.33 →
5.67). Consenso: instrumento e identidade I = I_fact − PE são a
contribuição defensável; o 42 fecha "artefato do pool"; o vocabulário
proximal/distal está coerente. A objeção que decide (R1-1): se a ação em j
é a ÚLTIMA que toca o ambiente, C_Ha = 0 é CONSEQUÊNCIA da Cor. behav, não
medição — Tab. 2 mostra mediana H = 1 nos pontos com NDE = 0, logo a
maioria dos 36/37 e 48/49 pode ser "a decisão de sumarizar antecede a
escrita final". R2-1: o experimento que o texto pede (passo reescalado no
braço C_H) não foi feito. R3: abstract com ~15 números; 40 vs 42 no ledger;
"3,668 nulls" inconsistente com Tab. nulls (3.824 ou 3.240); FIGURAS.md
descreve linha de Tab. 2 que não existe; stack H100 não pinado; custo de
40–42 fora da tally.

**Top-3 do AC:** (1) [0 GPU] estratificar por horizonte: distribuição de H
nos 37+49 pivotais, fração H ≤ 1, taxa de NDE = 0 em H ≥ 2, Mann–Whitney
por permutação de task, Holm na família, atualizar "Multiplicity" e
abstract; (2) [2–4 GPU-h] Act 4 com passo reescalado no braço C_H (lr×~5
ou normalização de vantagem, 3 seeds, mesma dose); (3) [0 GPU] passagem
de coerência (título "Proximally"; abstract ≤ 200 palavras/≤ 6 números;
40→42; 3.668; FIGURAS.md ↔ Tab. 2; stack H100; tally 40–42; Contribution
3 "one act after three diagnosed failures"; Tab. 2 "n=1"; claims cross-ref).
**Não mexer:** §4.1/Tab. nulls, Fig. 1, Remark 3/Prop. dc, números de
screening e split, frase "measurement claim unchanged".
**Pergunta mais difícil:** "Em quantos dos 36 pontos mediadores a ação
seguinte é a última que toca o ambiente? Se for a maioria, o que
'mediação proximal' acrescenta a 'sumarizar antecede a escrita final'?"

## 2026-09-11 — PRÉ-REGISTRO 43 (antes de rodar): estratificação por horizonte — mediação proximal medida vs. implicada pela Cor. behav

Zero rollouts; releitura de runs/preg40/{v1,v2}_rows.jsonl,
runs/preg42/rows.jsonl e das trajetórias originais (runs/teste0_*/baseline,
census V2). Script: experiments/preg43.py → runs/preg43/report.json.

**Motivação (R1, rodada 15).** Se após a ação a_j não há mais nenhuma
ação que modifique o ambiente, então R(h′, a) = R decorre da Cor. behav
(context ops não tocam o ambiente; a_j forçada iguala o estado final) —
NDE = 0 é implicado pelo desenho, não medido. A quarta célula só é
informativa onde existe pelo menos uma ação posterior que poderia
divergir ao vivo.

**Variáveis pré-declaradas (da trajetória ORIGINAL, após o índice j da
tool_call pareada):** H = nº de decisões tool_call após j (como no 41);
**H_w = nº de tool_calls `write_file` após j** (únicas ações que alteram o
estado que R lê; `run_tests`/`read_file`/`finish` não alteram o sandbox).
Estrato "implicado" := H_w = 0. Estrato "informativo" := H_w ≥ 1.
Sensibilidade: repetir com H_env = nº de tool_calls ≠ finish após j.

**Populações:** V1 folga pivotal (37), V1 pressão pivotal (46), externo 4B
pivotal ∧ screened (49), 8B pivotal (74: 57 screened + 17 não), V2 context
(23), V2 observation (12). V2 termination excluída (caminho direto por
construção). Para V2 o j é o campo `j` das rows; H_w conta `write_file`
nas tool_calls originais após j.

**Endpoint primário:** taxa de NDE = 0 entre pivotais com H_w ≥ 1, no
pool V1 folga ∪ externo 4B (as duas populações do headline), e por
população. Desfechos: **h1 ≥ 0.75** — a mediação proximal é medida, não
implicada, na maioria dos pontos informativos: o headline fica, com "k/n
at H_w ≥ 1" ao lado do 36/37 e 48/49; **h2 0.50–0.75** — parcial: o
abstract passa a carregar o número estratificado e o título ganha
"Proximally" com escopo; **h3 < 0.50** — a mediação proximal é
majoritariamente last-mover: o paper reenquadra ("a decisão de sumarizar
só importa imediatamente antes da escrita final"), o headline desce a
medição + Cor. behav e a contribuição empírica passa a ser o horizonte/
tipo. Reportamos qualquer desfecho.

**Checagem de implicação:** no estrato H_w = 0, NDE = 0 deve valer em
100% dos pontos de contexto (é teorema sob determinismo). Qualquer
violação é reportada como colisão de reward / falha de premissa, não
como mediação.

**Secundários:** (i) fração de pontos com NDE = 0 que estão em H_w = 0
(quanto do headline é implicado); distribuição de H e H_w por população;
(ii) Mann–Whitney unilateral H(NDE ≠ 0) > H(NDE = 0) com p por
**permutação em nível de task** (rótulo NDE permutado entre tasks, pontos
da mesma task movem juntos, 20.000 permutações, semente 43), família de 6
testes (V1 folga, V1 pressão, V2 total, V2 context, V2 observation,
externo 4B) com Holm; (iii) o mesmo para H_w. O p = 0.011 do abstract
sai ou vira descritivo conforme (ii).

**Custo:** 0 GPU. Entra no ledger como #43 seja qual for o desfecho.

### DESFECHO 43 (2026-09-11): h1 — a mediação proximal é medida, não implicada, no estrato informativo (21/23); mas 63/84 do headline estão no estrato last-mover

Script experiments/preg43.py (6 testes em tests/test_preg43.py), report
runs/preg43/report.json. 0 rollouts; 0 pontos sem trajetória; asserts
(37/36, 49/48, 23/13, 12/4, 74/51) passaram. Vocabulário de tool_calls
confirmado: V1/externo {write_file, run_tests, finish}; V2 {read_file,
run_tests, list_files, write_file} — `write_file` é a única ação que altera
o estado que R lê nos dois stacks, então H_w está bem definido em ambos.

**Pool headline (V1 folga ∪ externo 4B, 86 pivotais, 84 com NDE = 0):**
H_w = 0 em 63/86 (0.733); **dos 84 pontos com NDE = 0, 63 (0.75) estão no
estrato last-mover** (a ação pareada é a última escrita do episódio
original) — o R1 tinha razão na proporção. **Endpoint primário: NDE = 0
em 21/23 = 0.913 no estrato H_w ≥ 1 → h1.** Por população: V1 folga 12/13
(0.923), externo 9/10 (0.900). Sensibilidades: H ≥ 2: 23/25 (0.920);
H_env ≥ 1: 84/86. Distribuições: V1 folga H_w {0:24, 1:9, 2:3, 4:1};
externo {0:39, 1:2, 2:6, 5:2}; V1 pressão {0:28, 1:14, 2:3, 3:1}.

**Outras populações (endpoint H_w ≥ 1):** V1 pressão 11/18 (0.611); **8B
2/25 (0.080)** — no 8B, onde há escrita posterior, a mediação é quase toda
distal (coerente com 17/17 NDE ≠ 0 nos não-screened do 42); V2 context
6/14 (0.429); V2 observation 4/11 (0.364). Ou seja: o 36/37 do 4B no
estrato informativo é 12/13, enquanto o 8B no mesmo estrato é 2/25 — a
mediação proximal é propriedade do modelo × pool, e a quarta célula
discrimina isso.

**Checagem de implicação (NDE = 0 em H_w = 0):** 1.0 em V1 folga (24/24),
V1 pressão (28/28), externo (39/39) e 8B (49/49). **V2: 3 violações**
(context 7/9: swe_expressoes_v3 folga cp41 C_Ha = −0.083, swe_csvtable_v4
pressão cp19 −0.091; observation 0/1: swe_versoes_v4 pressão cp5 −0.10) +
termination 0/2 (direto por construção). Interpretação — e correção da
minha própria premissa do pré-registro: **H_w = 0 no episódio ORIGINAL não
torna NDE = 0 um teorema**. A Cor. behav exige sufixos de ação idênticos
nos DOIS ramos; com a_j forçada e o resto ao vivo, o ramo h′ pode
acrescentar uma escrita que o original não tinha. Logo, no estrato
"implicado", NDE = 0 ainda é uma medição de que o ramo h′ não acrescentou
escrita relevante — verificada em 140/140 pontos V1/externo/8B e violada
em 3/9+1 pontos V2 (R(h′,a) > R: o modelo, vendo o contexto sumarizado,
escreveu mais e acertou mais). O paper deve dizer as duas coisas: 75% do
headline está no estrato onde a mediação é o esperado sob a Cor. behav
(mas não garantido), e 21/23 no estrato onde ela é informativa.

**Testes de horizonte (família de 6, H; p analítico → Holm | p permutação
por task → Holm):** V1 folga 0.026 → 0.104 | 0.073 → 0.44; **V1 pressão
0.0008 → 0.0047** | 0.40 → 0.97; V2 total (38, sem termination) 0.031 →
0.104 | 0.27 → 0.97; **V2 context 0.011 → 0.056** | 0.099 → 0.49; V2
observation 0.43 | 0.89; externo 0.037 → 0.104 | 0.24 → 0.97. Com H_w: V1
pressão 1.2e-5 → 7e-5 (analítico); nada sobrevive à permutação por task
(estatística em nível de task: diferença de médias de mediana(H) entre
tasks com/sem algum NDE ≠ 0; 20.000 perms, seed 43). **Conforme
pré-registrado, o p = 0.011 sai do abstract e vira descritivo**; o único
teste que sobrevive a Holm (V1 pressão, analítico) não sobrevive ao
cluster por task. A direção é uniforme nas 6 populações (mediana H maior
onde NDE ≠ 0), o que se reporta como padrão descritivo, não como teste.

**Custo:** 0 GPU. Ledger #43 → held (h1 no primário; premissa de
implicação corrigida; horizonte rebaixado a descritivo). Entra no paper:
título ("Mostly Proximally Mediated"), abstract (21/23 ao lado do 36/37;
p sai), §4.4 (estrato last-mover e informativo; 8B 2/25), Tab. 2 (coluna
H_w ≥ 1), App. estimand "Multiplicity" (família de horizonte + Holm +
permutação), ledger #43, claims table.

## 2026-09-11 — PRÉ-REGISTRO 44 (antes de rodar): braço C_H com passo reescalado no setup do Act 4 (R2, rodada 15)

Motivação: §6 afirma que o braço C_H perde para outcome-only por um gap
de eficiência de otimização (densidade 0.39 × grad_norm ~5× menor,
DESFECHO 41e) "que um passo reescalado poderia fechar" — hipótese não
testada (R2-1, rodada 15). Testamos a única mudança que a hipótese
prescreve.

**Desenho:** idêntico ao Act 4 (pré-reg 27; rl/train_c1.py): braço `ch`,
pool runs/c1d_margem/pool.json (6 treino / 6 held-out), λ = 5, centering
c1b, clip_norm 1.0, orçamento 1600 chamadas LLM (dose-matched), seeds 1/2/3,
avaliação held-out idêntica. **Única mudança: lr 0.1 → 0.5** (×5 = razão
das medianas de grad_norm 0.295/0.062 ≈ 4.8, arredondada e declarada
antes). Implementação: flag `--lr-scale` em train_c1.py aplicada após o
`--c1b` (que fixa lr 0.1). Nada mais muda; nenhum segundo lr será tentado
sem novo pré-registro.

**Máquina:** H100 via Slurm (slurm/preg44.sbatch), vLLM 0.8.5.post1, APC
off, série, greedy seed 1234. Os comparadores do Act 4 foram medidos na
4090; para descartar o hardware como confundidor, o job roda ANTES do
braço novo: (g1) gate nulo fresco — 6 replays (g450/g600/g900 × 2, fila
100% original) → todos ΔR = 0.0 exato, senão aborta; (g2) **replicação do
braço `ch` lr 0.1 seed 1 na H100** — deve reproduzir held-out R_eff =
0.4046 (e episodes = 139) EXATAMENTE; se não reproduzir, o resultado do
braço novo é reportado com a etiqueta "hardware não controlado" e a
divergência anatomizada.

**Comparadores (fixos, do Act 4 e do pré-reg 31):** outcome-only
dose-matched 0.4402 / 0.4402 / 0.4430; outcome episode-matched 0.410 /
0.450 / 0.398; C_H lr 0.1 0.4046 / 0.4046 / 0.3984; C_HM − C_M = keep
0.3917; atratores held-out thr600 0.4546, keep 0.3917, summ −0.0310.

**Endpoint primário:** held-out R_eff do braço `ch` lr 0.5 por seed, contra
os mesmos seeds. Desfechos declarados:
- **r1:** ≥ outcome-only dose-matched em ≥ 2/3 seeds → a prescrição
  "bille C_H com passo reescalado" recebe evidência positiva: o sinal
  exato paga sua taxa quando o passo compensa a esparsidade (primeiro
  resultado positivo de treino; um ato, um pool).
- **r2:** > C_H lr 0.1 em ≥ 2/3 seeds, mas r1 falha → mecanismo (passo)
  confirmado como PARCIAL; a taxa de replay continua decisiva; o texto
  diz "parcialmente fechável".
- **r3:** ≤ C_H lr 0.1 em ≥ 2/3 seeds → a explicação por passo cai; a
  frase "a re-scaled step could close" é retirada e o gap fica sem
  mecanismo identificado (Claim 3 perde "mechanism identified").
- **r4 (instabilidade):** colapso a atrator fixo (held-out a ≤ 0.005 de
  keep 0.3917 ou de summ −0.031, θ correspondente) em ≥ 2/3 seeds → lr
  grande demais; reportado como tal, sem re-tuning.
Ordem de precedência se ambíguo: r4 > r1 > r2 > r3.

**Secundários:** nº de episódios (esperado ≈ 139, dose fixa), trajetória
de θ, held-out por task, grad_norm mediano, comparação com o
episode-matched. **Custo:** 6 nulos + 4 × ~1600 chamadas ≈ 6.400 chamadas,
1 GPU H100, estimativa 1–2 GPU-h. Reportamos qualquer desfecho; entra no
ledger como #44.

**Auditoria `revisor` do pré-reg 43 + coerência (2026-09-11, pós-84c54f0).**
Verificado limpo: índice j (estrito `> idx`, a escrita pareada nunca é
contada); premissa "H_w = 0 não é teorema" confirmada nos replays (os 3
violadores V2 têm 0 escritas no original e o ramo h′ acrescentou 2/1/1
escritas ao vivo; amostra de 6 pontos V1 H_w = 0: 6/6 sem escrita
adicional); família de Holm = pré-reg; Tab. 2 recomputada e consistente;
140/140 = 24+28+39+49 ✓. Corrigido: (1) **n efetivo do 21/23 = 14/16 pares
únicos / 13/15 tasks** (dedup por (task, cp_index) entre g450/g600/g900 e
g600/mt6; h1 sobrevive: 0.875 por par) — adicionado no abstract, §4.4,
claims e ledger #43; (2) a permutação usa estatística em nível de task
(diferença de médias de mediana(H)), mais grossa que o MW por pontos que
o pré-reg nomeou — desvio agora declarado no App. Multiplicity, junto com
o **piso estrutural** do p de permutação (1 task rotulada em 14 → p_min =
0.071 na folga; 1/29 = 0.034 no externo): esses p são conservadores por
construção; (3) "pre-reg 41c" → "41(c), re-analysed under 43"; (4)
"140/140 V1 points" → "V1-stack points (designed, external, 8B)"; (5)
abstract reduzido (~230 palavras). Menor, não corrigido: rows V2 do preg40
não gravam o caminho do replay (rastreabilidade por grep do task_id).

## 2026-09-11 — Mesa ICLR rodada 16 (isolada, paper/ em e627167) — NOTAS PERDIDAS

A rodada 16 rodou sobre e627167 (pós-auditoria do 43), mas a sessão do
orquestrador caiu antes de as notas serem gravadas aqui ou na memória de
sessão. Não há registro numérico de R1/R2/R3/AC desta rodada — declaramos
a lacuna em vez de reconstruir notas. O que sobreviveu foi o lote de
correções em andamento (diff não commitado em paper/main.tex), do qual se
inferem as objeções atendidas: (1) título re-escopado para "Where Harness
Credit Is Proximally Mediated — and Where It Is Not" (a mesa leu "mostly"
como generalização além da pilha primária); (2) abstract nomeia a pilha
(harness scriptado + Qwen3-4B) e onde a mediação é distal (8B 2/25, V2
context 13/23, termination); (3) termination rebaixada de "positive
control" para "structural control" — os 10 duais são analíticos (R_Ha ≡
R_H), não falsificáveis; (4) mecanismo do Act 4 (esparsidade × passo)
rotulado "candidate, identified but not yet tested" até o desfecho 44;
(5) contribuição 4 ("the record") fundida na 3; (6) Tab. 2 troca as
medianas de H por uma coluna "Reading" (proximal/mixed/distal); (7) λ*
do 8B (0.1) declarado no setup. Commit 6266cb6 (conclusão na p9).
Lição operacional: gravar as notas da mesa no DIARIO ANTES de qualquer
edição — a partir da rodada 17 isso é a primeira ação após o veredito.

## 2026-09-11 — Mesa ICLR rodada 17 (isolada, paper/ em 6266cb6)

R1 6 (Soundness 3) / R2 5 (Contribution 2) / R3 6 (Presentation 2) → AC
**5.67, Borderline** (= r15; soundness subiu, mas o 43 tornou visível que
a manchete tem n informativo de 16 decisões — "custo da honestidade, não
regressão"). Atendidas desde a r15 (não reciclar): artefato do pool (42),
última escrita (43), horizonte rebaixado, re-escopo do título, termination
estrutural, mecanismo "untested".

**Objeções vivas:** R1-1 manchete (36/37, 48/49) vs conteúdo medido 21/23
= 14/16 decisões, CI por decisão [0.62, 0.98] cruza h2 → abrir abstract e
Contrib. 2 pelo estrato informativo; R1-2 limiares do 43 pós-hoc porém
rotulados "confirmed, h1" → "pre-specified analysis, post-hoc thresholds,
estimate + CI"; R1-3 contraste 8B "distal" pode ser confundido com
horizonte (8B mais raso → mais escritas a jusante; H_w binarizado; App. F
promete medianas e só dá p) → coluna mediana H_w na Tab. 2; R1-4
"outcome-only PG é MC de C_H" sem derivação → lema de uma linha; R1-5 duas
definições de pivotal (38 vs 37); R1-6 dizer se algum C_H foi recomputado
na H100. R2-1 prescrição (regra v) sobre mecanismo não testado — rodar 44
ou REMOVER a cláusula do passo; R2-2 regra só veta, nunca exercida
positivamente → dizer no abstract/Contrib. 3; R2-3 realismo do harness
(uma decisão binária) na Contrib. 2; R2-4 Act 4 sem tamanho do held-out
nem valores por seed no principal. R3-1 abstract com 11 números → 3;
R3-2 §4.3 + glossário de códigos carregam o paper antigo (~1,3 pp) →
parágrafo + App. C; R3-3 Fig. do treino (App. G) deveria estar no
principal no lugar do census; R3-4 Fig. 2 densa; R3-Q3 Mistral sem
quarta célula — por quê.

**Top-3 do AC:** (1) [0 GPU] re-manchete pelo estrato informativo,
abstract com 3 números, §4.3 comprimido, Fig. treino ao principal
(Δ≈+0.33); (2) [GPU] pré-reg 44 — qualquer desfecho; se não entrar,
remover a cláusula "re-scaling the step" da regra (v) (Δ≈+0.33); (3)
[0 GPU] mediana H_w na Tab. 2 controlando o 8B, relabel do 43, lema
outcome-only ∝ C_H (Δ≈+0.15–0.33).
**Não mexer:** §4.1/Tab. nulls, Fig. 1, Prop. dc + Remark factorial,
ledger/Tab. 3, termination estrutural, "Design of the pool", ramo de
falha do 42.
**Pergunta mais difícil:** "Com 63/84 da manchete entalhados pela última
escrita e o estrato informativo em 14/16 decisões com CI [0.62, 0.98],
o que distingue 'mediação proximal é a regra neste stack' de 'pools
projetados e saturados raramente deixam escritas depois do ponto
pivotal'?"
**Teto por edição: ≈ 6.0–6.33.** Para 7: 44 (qualquer desfecho) + H_w
controlando o 8B + re-manchete. Para 8: exercício POSITIVO da regra
(célula com ambos os gates abertos e crédito conjunto vencendo outcome a
dose igual) OU harness realista com ≥ 50 decisões informativas — ambos
fora do orçamento atual (Fase D, não autorizada).

## 2026-09-11 — ADENDO 43a (descritivo, registrado antes de computar): taxa de NDE = 0 por valor exato de H_w

Motivação: R1-3 (rodada 17) — o contraste 8B (2/25) vs 4B (21/23) no
estrato H_w ≥ 1 pode ser confundido com horizonte se os pontos do 8B
tiverem mais escritas a jusante. Análise: zero rollouts; releitura dos
mesmos pontos do pré-reg 43 (runs/preg43 recomputado). Para cada
população (V1 folga, V1 pressão, ext4b, q8, V2 context, V2 observation):
tabela k/n de NDE = 0 por valor exato de H_w ∈ {0, 1, 2, ≥3}, mediana de
H_w no estrato H_w ≥ 1, e o contraste 8B vs 4B **pareado em H_w = 1**
(mesmo horizonte de escrita). Descritivo — sem limiar declarado, sem
teste; entra na Tab. 2 como coluna "median H_w (H_w ≥ 1)" e no App. F.
Leitura pré-declarada: se a mediana de H_w do 8B em H_w ≥ 1 for ≤ a do
4B e a taxa em H_w = 1 já separar os modelos, o contraste NÃO é
confundido com horizonte; se o 8B tiver H_w maior, o paper diz que
"distal" no 8B é confundido com horizonte e retira o contraste da
manchete.

### DESFECHO 43a (2026-09-11, descritivo): o contraste 8B não é confundido com horizonte

experiments/preg43.py (chave `adendo_43a_por_Hw` em runs/preg43/report.json;
6 testes passam). NDE = 0 (k/n) por valor exato de H_w:
- V1 folga: H_w=0 24/24; =1 **9/9**; =2 3/3; ≥3 0/1. Mediana H_w em ≥1: 1.
- ext4b: 0 39/39; =1 2/2; =2 5/6; ≥3 2/2. Mediana em ≥1: 2.
- q8 (8B): 0 49/49; =1 **2/20**; =2 0/5. Mediana em ≥1: 1.
- V1 pressão: 0 28/28; =1 11/14; =2 0/3; ≥3 0/1.
- V2 context: 0 7/9; =1 6/14. V2 observation: 0 0/1; =1 3/8; =2 1/2; ≥3 0/1.
- Pool headline (folga ∪ ext4b): 0 63/63; =1 11/11; =2 8/9; ≥3 2/3.
Leitura pré-declarada: a mediana de H_w do 8B no estrato informativo (1)
é ≤ a do 4B (1 na folga, 2 no externo) e a fração H_w = 0 é comparável
(66% vs 65%/80%); pareado em H_w = 1 exatamente, 8B 2/20 vs 4B 9/9 (folga)
e 2/2 (externo). O contraste 8B vs 4B NÃO é confundido com horizonte de
escrita — entra na Tab. 2 (coluna mediana H_w) e no App. F. Também
visível: na V1 pressão a mediação proximal cai com H_w (11/14 → 0/3 →
0/1), a única população onde o horizonte ordena monotonicamente.

**Auditoria `revisor` do lote r17 (2ff0126).** Corrigido: abstract dizia
"2/25 at matched write horizon" (2/25 é H_w ≥ 1; o pareado é 2/20) →
2/20; "reward-pivotal" → "harness-pivotal" no abstract; "as construction
predicts" → "leads one to expect" (3 ocorrências — coerente com "default,
not a theorem"); ledger #43 "3 V2 context points" → "3 V2 non-termination
points (2 context, 1 observation)"; caption Tab. 2 idem; "vs. 280" →
"284/280/279" (episódios do braço outcome por seed); nota de escopo do
Lema pg explicita que o Act 4 usa média móvel global de R_eff (não V(s))
e regra (v) diz "expectation is C_H up to a positive factor"; rodapé sobre
uma registração adicional (44) "filed and unrun at submission time".
Rastreabilidade (achado 3): preg43.py agora emite
`n_efetivo_Hw_ge1_headline` (21/23 CP [0.7196, 0.9893]; 14/16 decisões
CP [0.6165, 0.9845]; 13/15 tasks) e `adendo_43a_por_Hw` desagregado por
benchmark (mbpp mediana 2, n≥1 = 6; he mediana 2, n≥1 = 4) e por
blindagem do 8B (screened 2/8, non-screened 0/17, ambos mediana 1) —
todos os números da Tab. 2 agora rastreiam ao report.json. Achado 10
(precedência registro→computação do 43a não auditável por hash): o
registro e o desfecho do 43a foram commitados juntos (commit "exp: adendo
43a"); a ordem no arquivo é a única evidência — declarado aqui.

## 2026-09-11 — Mesa ICLR rodada 18 (isolada, paper/ pós-2ff0126 + auditoria)

R1 6 / R2 5 (Contribution 2) / R3 6 (Presentation 2) → AC **5.67,
Borderline** (piso mais firme: nenhuma objeção de soundness aberta; só n
e mecanismo). Atendidas da r17 (não reciclar): manchete pelo estrato
informativo, 8B pareado em H_w, rótulo do 43, Lema pg, regra (v),
veto-only, Act 4 split/seeds, custo do censo, glossário pivotal, Mistral/
H100, Fig. do treino no principal, §4.3 curto.

**Objeções novas/vivas:** R1-1 "distal no 8B" é majoritariamente as
quebras de shield do pré-reg 15 reetiquetadas: 17 non-screened = 7
decisões únicas, 6 screened com NDE≠0 = 3 tasks; o "2/20 em H_w=1" é
~2/≤10 decisões únicas → decompor 8B em screened/non-screened POR DECISÃO
ÚNICA na Tab. 2/43a/abstract ("2/8 among screened, 0/17 at shield
breaks"). R1-2 liderar com 14/16 e IC no abstract. R1-3 Lema pg diz
A(h) = π(h′)C_H < C_H em módulo, logo a norma 5× maior do outcome é
RUÍDO (baseline global + outras decisões), não sinal — "passo
reescalado" não é a única hipótese; exploração por ruído é outra →
reportar π̄(h′) nas decisões treinadas e decompor a norma; declarar as
duas hipóteses no 44. R1-4 deriva reward-/harness-pivotal (L93, L717);
"at every point … last write" não escopado ao V1. R2-1 (mata Contrib. 3)
44 não rodado — §6 é replicação de audit2026. R2-2 Act 4: tabela 6 tasks
× 4 braços × 3 seeds (a separação pode ser UMA task). R2-4 custo por
ponto UTILIZÁVEL. R2-5 §4.3 sem exemplo concreto (um ponto com seus 4 R).
R3-1 1.7B tem censo (23 designed + 44 MBPP+) e nenhuma 4ª célula, não
declarado (~90 rollouts, <1 h H100). R3-2 abstract deve dizer "13
designed, 10 external (saturated)". R3-4 PIOROU: frase-manchete do
abstract com 60 palavras/3 parentéticos; Intro repete abstract; Contrib.
2 virou lista. R3-5 "shield" órfão (definido só no App. C). R3-6 Fig. 2
overplotting → histograma marginal de C_Ha. R3-7 ledger ilegível impresso.

**Top-3 do AC:** (1) [0 GPU] decomposição do 8B por decisão única,
tabela por task do Act 4, unificar pivotal, definir/trocar "shield",
escopar last-write ao V1, declarar 1.7B sem 4ª célula (Δ≈+0.3 → 6/6/6);
(2) [<1 h H100] 4ª célula na 1.7B (designed + MBPP+) (Δ≈+0.3–0.5 R3);
(3) [GPU] pré-reg 44 com as duas hipóteses (Δ≈+1 R2).
**Não mexer:** §4.1, estrutura da Tab. 2, App. B, rótulo "estimate + CI",
veto-only, estratificação H_w e "leads one to expect", T0/ledger/audit,
"This is a measurement paper".
**Pergunta mais difícil:** "Retirados os 17 non-screened (quebras do
pré-reg 15, C_Ha≠0 mecanicamente), o que resta de 'distal no 8B' em
decisões únicas? Resposta honesta hoje: 2/8 pontos screened, ~3–5
decisões — e o paper não tem esse número escrito."
**Teto:** só edição 6.0; com (2)+(3) ≈ 6.7; para 8: pool com H_w≥1
dominante e ≥30 decisões únicas, OU exercício positivo da regra, OU 4ª
célula no Mistral — próxima versão, fora do orçamento.

## 2026-09-11 — PRÉ-REGISTRO 45 (antes de rodar): quarta célula R(h′,a) na Qwen3-1.7B (terceiro modelo na pergunta V1)

Motivação: R3-1 (rodada 18) — a 1.7B tem censo (designed 23 pts; MBPP+
44 pts) e nenhuma quarta célula. População: teste3_{q17_g600, q17_mt6,
mbpp17_g600, mbpp17_mt6} = 11+12+22+22 = **67 pontos**, todos screened
(C_HM = C_M), **26 pivotais** (C_H ≠ 0: 4+4+9+9). Procedimento idêntico
ao pré-reg 42 (experiments/preg42.py, células TERTIARY_17B já
parametrizadas; TCC_PREG42_OUT=runs/preg45; job slurm/preg45.sbatch a
partir de preg42.sbatch com MODEL=Qwen/Qwen3-1.7B; H100 via Slurm; vLLM
0.8.5.post1; APC off; série; greedy seed 1234; max_tokens 1200).
**Gate:** 2 replays nulos por config (8) → todos ΔR = 0.0 exato, senão
aborta. Modelo baixado hoje para o cache HF (não estava).

**Endpoint primário:** fração dos 26 pivotais com R(h′,a) = R exato.
Desfechos: **t1** ≥ 0.90 (replica — proximal em terceiro modelo Qwen);
**t2** 0.60–0.90 (parcial; reportar por célula e por H_w); **t3** < 0.60
(a 1.7B se comporta como o 8B: distal — a tese fica "4B-específica no
V1", limitação central). Secundários (descritivos): não-pivotais
(esperado ≈ 1), I_fact = 0, estratificação por H_w (adendo 43a
recomputado incluindo a célula), n de decisões únicas. Custo: 8 nulos +
67 replays = 75 rollouts (~5 GPU-min H100). Reportamos qualquer desfecho;
entra no ledger como #45 (o #44 continua na fila, job 32318).
Atenção: a 1.7B satura em falha na pressão (11/12) — os pivotais são
poucos; n efetivo será reportado ao lado.
Job **32342** (`slurm/preg45.sbatch`, h100n2, gpu:1, porta 8323) submetido
2026-09-11 — PD (Priority); 32318 (pré-reg 44) continua PD (Resources).
