# PLANO-EXECUCAO.md — do sinal validado ao artigo (ICLR 2027)

> Criado 2026-08-22 após revisão adversarial do plano (12 problemas incorporados).
> Regra de ouro: cada fase tem um GATE com critério de decisão; o plano ADAPTA nos gates, não no final.

## Claim central do artigo (e seu risco)

**Claim:** I(H,M) por decisão — medido por replay counterfactual — é informativo e necessário: crédito de camada única supercredita decisões blindadas (screening-off) e ignora dependências (sinergia), e corrigir por I melhora o treino.

**Risco conhecido (P1 do revisor):** 100% dos pontos de I observados são screening-off (I = −C_H). Se sinergia positiva não for mensurável, o claim reposiciona para "anatomia da interação + crédito corrigido por dupla contagem" — decisão no GATE 1, não na semana 4.

## Fase 0 — Pré-requisitos (imediato)

- 0.1 ✅ RESOLVIDO: anomalia de sufixo era contabilidade, não infidelidade — retries irmãos do tool_call (gravados antes dele) são reexecutados pelo replay e contam no sufixo. Replay reproduziu decisão a decisão. Corrigido em teste0.py. [P9]
- 0.2 Tasks v3 (delegar impl), três estratos POR DESENHO:
  - **S (sinergia, 5 tasks):** a′ plausível do modelo só funciona SE o contexto preservado contiver a informação (dependência model→harness; predição: I > 0 mensurável).
  - **C (controle, 5 tasks):** constantes críticas RECUPERÁVEIS de arquivos do workspace (predição: C_H ≈ 0 — o método deve distinguir; mata circularidade de construto). [P6]
  - **L (longas, 10 tasks):** padrão v2 (constantes irrecuperáveis além do char 240), ≥8 turnos típicos, mais testes por task (≥8) p/ reduzir saturação de reward. [endógeno à saturação — reportar como escolha de desenho]
- 0.3 ✅ Yield medido (v2+v2b, por 10 trajs): C_H 23 pts (8 nz), C_M 7 pts (2 nz), I 5.5 pts (**1 não-saturado**). Regra disparada: yield I não-saturado 0.1/traj < 0.5 → tasks v3 com ≥8 testes + max-per-traj t3 2→3, t1/t2 3→4. Metas revisadas: C_H≥200 (60 nz), C_M≥60 (15 nz), I≥50 (15 não-saturados). Regra de parada e custo (~1400 rollouts): experiments/results/2026-08-22_yield_fase0.json. [P5]

**GATE 0:** tasks v3 verdes na suíte + yield estimado. Se yield de I não-saturado < 0.5/trajetória, aumentar max-per-traj e nº de testes por task antes do grid.

## Fase A — Dataset de counterfactuals (grid REDUZIDO) [P4, Q4]

- Grid: threshold ∈ {450, 600, 900} apenas (task_chars=240 e keep_last=4 FIXOS — alinhados ao desenho das tasks). Tasks: v2 (10) + v3 (20). max_turns=12.
- A1. **teste0 COMPLETO por config** (piso é propriedade de (config, servidor, sequencialidade)); requisições sempre sequenciais — condição de identificação pré-registrada. [P4]
- A2. teste1/2/3 como geradores: max-per-traj 4 (teste1/2), 3 (teste3).
- A3. Deduplicar trajetórias por hash (configs onde threshold não ativa → idênticas); reportar N efetivo. [P10]
- A4. Agregador: `credit/dataset.py` consolida (decisão, features, C_H | C_M | I, config, task, estrato) num parquet/JSONL único. Features em DOIS conjuntos pré-registrados: `pre` (computáveis antes da decisão: turn, context_tokens, n_messages, tests_passed_so_far, action_type, estrato/task) e `post` (só análise: tokens_after, ΔR decomposto). [P8]
- Pool entre configs SEMPRE com config como covariável; nunca agregar direções nem transições. Frações de descarte (saturação, vácuo, timeout, sem-a′) reportadas por config. [pré-registro (f)]

**GATE 1 (DECIDIDO 2026-08-22, g600 limpo):** sinergia NÃO observada — C_HM=C_M exato em 21/21 (screening-off nos dois sinais). Controles c_* com C_H=0 em 11/12 ✓ (constructo validado). **Claim reposicionado:** "decomposição causal cross-layer + screening-off como mecanismo dominante + correção de dupla contagem no treino". Anatomia auditada: (1) a′ do estado original re-injeta a informação destruída; (2) harness vivo re-dispara summarize downstream (intervenção transiente). **GATE-1b (novo, pré-registrado no diário):** testar sinergia sob pressão de orçamento (max_turns 12→6, ~70 rollouts) após o grid.

## Fase B — Critic contra ground truth [P7, P8]

- B1. Targets separados: classificador |C|>0 + regressor condicional (zero-inflation). [P7a]
- B2. Split por TASK (nunca por ponto); bootstrap clusterizado por task; k de precision@k FIXADO em k=10 antes de ver dados. [P7b,c]
- B3. Modelos: ridge/logistic + gradient boosting sobre features `pre`. Baselines dose-matched: logprob da ação, heurística de posição (turn), LLM-judge (mesmo nº de chamadas). [resposta a 2608.19760]
- B4. Honestidade pré-registrada: se o critic não bater baselines, reportar como resultado (o paper sobrevive pela anatomia de I + C1).

**GATE 2:** Spearman clusterizado e precision@10 vs baselines → decide se o critic entra como contribuição ou como resultado negativo honesto.

## Fase C — Crédito em treino (LLM frozen; C2 é stretch) [P2, P3]

### C1 — desenho fechado (2026-08-22, pós-GATE 1)
- **Política treinável:** logística π_θ(summarize | φ) nos pontos de context_policy;
  φ = [1, context_tokens/1000, turn/max_turns, tests_passed_frac, n_writes_so_far/3].
  Demais decisões do harness (retry, termination) permanecem regras fixas. LLM frozen (T=0, seed).
- **Objetivo com pressão de custo (pré-registrado; sem ele "keep sempre" é trivialmente ótimo):**
  R_eff = R_testes − λ·(prompt_tokens_totais/100000), λ=1 (≈0.1 por 10k tokens; calibrar UMA vez
  para que a regra fixa thr600 não seja ótima, ANTES de qualquer treino — nunca depois).
- **Braços (REINFORCE, baseline = média móvel de R_eff):**
  1. *outcome-only:* todo ponto cp recebe advantage (R_eff − b̄).
  2. *C(H) puro:* K=2 pontos cp/episódio amostrados; crédito = C_H via 1 replay flip on-policy
     (política atual, DURANTE o treino); demais pontos sem update.
  3. *corrigido por interação:* mesmos K pontos; crédito = C_HM − C_M (contribuição marginal do
     harness condicional à ação do modelo; = 0 sob screening-off) via a′ (8 seeds) + 2 replays.
     Sem a′ encontrado → crédito = C_H (sem evidência de mediação; custo da amostragem contado).
  4. *zero (controle W1 do review ICLR, pré-registrado ANTES de rodar C1):* crédito ≡ 0 →
     θ congelado, 0 replays, mesmo orçamento de episódios. Neutraliza "o ganho do braço 3 é
     só masking/menor variância": se braço 3 ≯ braço 4 dose-matched, o crédito marginal não
     carrega informação além de "não atualizar" — e reportamos isso como resultado.
- **Variância de gradiente por braço:** `grad_norm` logado por episódio (grátis) — evidência
   direta contra a explicação "variância menor, não crédito" (W6).
- **Dose-matching (pré-registrado):** orçamento B de ROLLOUTS TOTAIS por braço (episódios +
  replays de crédito; chamadas de amostragem de a′ contadas como rollout/12 ≈ custo médio por
  turno). Curvas por rollout acumulado. 3 seeds de treino. Tasks: 20 treino / 10 held-out
  (estratificado). Métricas: R_eff e success rate em held-out, AUC da curva.
- **Predição pré-registrada:** braço 2 supercredita decisões blindadas (screening-off) →
  gradiente ruidoso; braço 3 zera crédito blindado e concentra update onde há efeito marginal
  real. Falseável: braço 3 paga 2× por crédito; se a correção não ajudar, perde dose-matched.


- C1. Harness treinável: política logística (features `pre`: context_tokens, turn, tests_passed) com temperatura, decide context_policy. **TRÊS braços obrigatórios:**
  1. outcome-only (REINFORCE com R final);
  2. crédito C(H) puro por decisão (replay on-policy: 1 replay counterfactual por decisão amostrada, DURANTE o treino);
  3. **crédito corrigido por interação** (C(H,M)-based: mesmo replay do braço 2 + replay conjunto — desconta supercrédito de decisões blindadas). ← braço que faz o claim cross-layer mesmo com LLM frozen.
- Dose-matching: curvas por ROLLOUT TOTAL (episódios + replays gastos no crédito), não por episódio. [P3]
- Métricas: success rate final + área sob a curva de aprendizado; 3 seeds de treino; tasks held-out.
- C2 (stretch): LoRA GRPO no Qwen3-4B com C(M). Só se C1 fechar antes do dia 21.

**GATE 3:** braço 3 > braço 2 em eficiência? E braço 3 > braço 4 (controle zero)? → título/claim final do artigo.

## Fase D — Ablations (cortáveis nesta ordem) [Q4]

- D1. Anatomia de I: taxonomia screening-off vs sinergia com exemplos (OBRIGATÓRIA — vira figura central).
  Inclui (W5 do review): quantificar nos replays JÁ COLETADOS a fração de screening-off por
  sub-mecanismo (re-injeção de informação pela a′ = propriedade estrutural do estimando, com
  argumento formal; re-disparo downstream do harness vivo = achado empírico). Teste do claim
  mecanístico = sign test sobre "C_HM = C_M exato" (usa TODOS os pontos, N=21+ por config,
  não só os não-saturados) (W2).
- D2. Generalização: critic treinado em threshold 600 → testado em 450/900; tasks held-out.
- D2b. **Validação externa (verificada 2026-08-22): MBPP+ adaptado a multi-turn, subset ~100 tasks** — única âncora comparável (C3 v2 usa Qwen3-4B em MBPP+ e reporta credit fidelity Spearman vs replay GT = 0.260); reportar nossa fidelity lado a lado (mesma métrica, decomposição camadas vs agentes). Custo ~1–2 dias/4090. Prioridade: depois de C1, antes de D3.
- D2c. **Réplica com 2º modelo (W3 do review ICLR):** teste 3 (I) com Qwen3-1.7B (mesma infra vLLM),
  só thr600, ~10 tasks (30 baselines + ~80 replays, ~1 dia/4090). Pergunta: screening-off reaparece?
  SIM → mecanismo é do desenho da intervenção, não do modelo (generalidade). NÃO → limitação
  declarada com evidência. Prioridade: entre D2 e D2b — melhor gasto marginal contra "um modelo".
- D3. Budget de counterfactuals (1/2/4/8) — PRIMEIRA a cortar (CHILL/CAR cobrem).

## Fase E — Artigo (começa JÁ, não na semana 4) [P11]

- E1. `paper/` com esqueleto LaTeX + figuras-alvo definidas ANTES dos experimentos das fases B–C:
  F1 fidelity/piso; F2 distribuição de C por camada e direção; F3 anatomia de I (screening-off vs sinergia); F4 critic vs baselines; F5 curvas C1 (3 braços, dose-matched).
- E2. Threats: I1/I2, saturação endógena, entropia da política (a′ inamostrável), tasks sintéticas, 1 modelo/1 ambiente, acoplamento a′ entre C(M) e I [não contar como evidência independente], sequencialidade do vLLM.

## Pré-registros consolidados

1. Piso por config; execução sequencial como premissa. 2. Yield e regra de parada da Fase A. 3. Estatística do critic (cluster por task, zero-inflation, k=10). 4. Features pre vs post. 5. Perturbação estruturada de a′ = estimando distinto (só ablation, nunca pooled). 6. Dose-matching de C1 por rollout total. 7. Direções/transições jamais agregadas. 8. Saturação fora dos critérios confirmatórios. 9. Braço 4 (zero) como controle de masking do C1; GATE 3 exige braço 3 > braço 4 (pré-registrado 2026-08-22, antes de qualquer treino). 10. Claim mecanístico do screening-off testado por sign test sobre C_HM=C_M exato (todos os pontos, não só não-saturados).

## Review ICLR simulado (2026-08-22, subagente iclr) — resumo acionável

- Score global 6 (borderline → accept condicional a GATE 3). Novidade 7, rigor 7.5, significância 5→7 se C1 fechar.
- [MATA-PAPER] W1 braço 4 zero → **implementado + pré-registrado** (rl/train_c1.py). W2 N de I pequeno → grid + GATE-1b + sign test (pré-registro 10).
- [SCORE-DOWN] W3 um modelo → D2c (Qwen3-1.7B). W4 distância p/ CHILL → braço 2 enquadrado como reprodução de CHILL no nosso ambiente + tabela T1. W5 trivialidade do screening-off → D1 separa propriedade estrutural (mecanismo 1, com argumento formal) de achado empírico (mecanismo 2). W6 variância → grad_norm logado + braço 4.
- [POLIMENTO] W7 piso como medição sob premissas (não garantia) + parágrafo próprio p/ achado APC. W8 c_temp_label no corpo do paper, não footnote.
- Pergunta de rebuttal mais difícil: "se C_HM−C_M ≡ 0 nos pontos medidos, por que pagar 3 replays em vez de não treinar o harness nesses pontos?" → resposta empírica = GATE 3 (braço 3 vs braço 4).

## Cronograma (gates > datas)

| Semana | Fase | Gate |
|---|---|---|
| 0 (agora) | 0 + esqueleto E1 | GATE 0 |
| 1 | A (grid 3 configs × 30 tasks) | GATE 1 → decide claim |
| 2 | B (critic) + D1 | GATE 2 |
| 3 | C1 (3 braços) + D2 | GATE 3 → decide título |
| 4 | E (escrita) + C2 se sobrar | submissão interna |
