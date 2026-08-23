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
