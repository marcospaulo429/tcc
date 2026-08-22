# PLANO-EXECUCAO.md — do sinal validado ao artigo (ICLR 2027)

> Criado 2026-08-22 após revisão adversarial do plano (12 problemas incorporados).
> Regra de ouro: cada fase tem um GATE com critério de decisão; o plano ADAPTA nos gates, não no final.

## Claim central do artigo (e seu risco)

**Claim:** I(H,M) por decisão — medido por replay counterfactual — é informativo e necessário: crédito de camada única supercredita decisões blindadas (screening-off) e ignora dependências (sinergia), e corrigir por I melhora o treino.

**Risco conhecido (P1 do revisor):** 100% dos pontos de I observados são screening-off (I = −C_H). Se sinergia positiva não for mensurável, o claim reposiciona para "anatomia da interação + crédito corrigido por dupla contagem" — decisão no GATE 1, não na semana 4.

## Fase 0 — Pré-requisitos (imediato)

- 0.1 ✅→ Investigar anomalia `group_anagrams` (replays com nº de decisões ≠ sufixo, mesmo reward) — causa raiz antes de escalar. [P9]
- 0.2 Tasks v3 (delegar impl), três estratos POR DESENHO:
  - **S (sinergia, 5 tasks):** a′ plausível do modelo só funciona SE o contexto preservado contiver a informação (dependência model→harness; predição: I > 0 mensurável).
  - **C (controle, 5 tasks):** constantes críticas RECUPERÁVEIS de arquivos do workspace (predição: C_H ≈ 0 — o método deve distinguir; mata circularidade de construto). [P6]
  - **L (longas, 10 tasks):** padrão v2 (constantes irrecuperáveis além do char 240), ≥8 turnos típicos, mais testes por task (≥8) p/ reduzir saturação de reward. [endógeno à saturação — reportar como escolha de desenho]
- 0.3 Cálculo de yield a partir de v2/v2b (pontos elegíveis/não-saturados por trajetória) → dimensionar grid; regra de parada pré-registrada. [P5]

**GATE 0:** tasks v3 verdes na suíte + yield estimado. Se yield de I não-saturado < 0.5/trajetória, aumentar max-per-traj e nº de testes por task antes do grid.

## Fase A — Dataset de counterfactuals (grid REDUZIDO) [P4, Q4]

- Grid: threshold ∈ {450, 600, 900} apenas (task_chars=240 e keep_last=4 FIXOS — alinhados ao desenho das tasks). Tasks: v2 (10) + v3 (20). max_turns=12.
- A1. **teste0 COMPLETO por config** (piso é propriedade de (config, servidor, sequencialidade)); requisições sempre sequenciais — condição de identificação pré-registrada. [P4]
- A2. teste1/2/3 como geradores: max-per-traj 4 (teste1/2), 3 (teste3).
- A3. Deduplicar trajetórias por hash (configs onde threshold não ativa → idênticas); reportar N efetivo. [P10]
- A4. Agregador: `credit/dataset.py` consolida (decisão, features, C_H | C_M | I, config, task, estrato) num parquet/JSONL único. Features em DOIS conjuntos pré-registrados: `pre` (computáveis antes da decisão: turn, context_tokens, n_messages, tests_passed_so_far, action_type, estrato/task) e `post` (só análise: tokens_after, ΔR decomposto). [P8]
- Pool entre configs SEMPRE com config como covariável; nunca agregar direções nem transições. Frações de descarte (saturação, vácuo, timeout, sem-a′) reportadas por config. [pré-registro (f)]

**GATE 1 (o mais importante):** existe I > 0 (sinergia) mensurável nas tasks S?
- SIM → claim central mantido: "I como sinal de treino, dois regimes (screening-off e sinergia)".
- NÃO → reposicionar: "decomposição causal cross-layer + correção de dupla contagem"; C1(iii) continua válido (screening-off basta p/ supercrédito).
- Também: tasks C com C_H ≈ 0 confirmam que o método distingue (senão, investigar construto).

## Fase B — Critic contra ground truth [P7, P8]

- B1. Targets separados: classificador |C|>0 + regressor condicional (zero-inflation). [P7a]
- B2. Split por TASK (nunca por ponto); bootstrap clusterizado por task; k de precision@k FIXADO em k=10 antes de ver dados. [P7b,c]
- B3. Modelos: ridge/logistic + gradient boosting sobre features `pre`. Baselines dose-matched: logprob da ação, heurística de posição (turn), LLM-judge (mesmo nº de chamadas). [resposta a 2608.19760]
- B4. Honestidade pré-registrada: se o critic não bater baselines, reportar como resultado (o paper sobrevive pela anatomia de I + C1).

**GATE 2:** Spearman clusterizado e precision@10 vs baselines → decide se o critic entra como contribuição ou como resultado negativo honesto.

## Fase C — Crédito em treino (LLM frozen; C2 é stretch) [P2, P3]

- C1. Harness treinável: política logística (features `pre`: context_tokens, turn, tests_passed) com temperatura, decide context_policy. **TRÊS braços obrigatórios:**
  1. outcome-only (REINFORCE com R final);
  2. crédito C(H) puro por decisão (replay on-policy: 1 replay counterfactual por decisão amostrada, DURANTE o treino);
  3. **crédito corrigido por interação** (C(H,M)-based: mesmo replay do braço 2 + replay conjunto — desconta supercrédito de decisões blindadas). ← braço que faz o claim cross-layer mesmo com LLM frozen.
- Dose-matching: curvas por ROLLOUT TOTAL (episódios + replays gastos no crédito), não por episódio. [P3]
- Métricas: success rate final + área sob a curva de aprendizado; 3 seeds de treino; tasks held-out.
- C2 (stretch): LoRA GRPO no Qwen3-4B com C(M). Só se C1 fechar antes do dia 21.

**GATE 3:** braço 3 > braço 2 em eficiência? → título/claim final do artigo.

## Fase D — Ablations (cortáveis nesta ordem) [Q4]

- D1. Anatomia de I: taxonomia screening-off vs sinergia com exemplos (OBRIGATÓRIA — vira figura central).
- D2. Generalização: critic treinado em threshold 600 → testado em 450/900; tasks held-out.
- D3. Budget de counterfactuals (1/2/4/8) — PRIMEIRA a cortar (CHILL/CAR cobrem).

## Fase E — Artigo (começa JÁ, não na semana 4) [P11]

- E1. `paper/` com esqueleto LaTeX + figuras-alvo definidas ANTES dos experimentos das fases B–C:
  F1 fidelity/piso; F2 distribuição de C por camada e direção; F3 anatomia de I (screening-off vs sinergia); F4 critic vs baselines; F5 curvas C1 (3 braços, dose-matched).
- E2. Threats: I1/I2, saturação endógena, entropia da política (a′ inamostrável), tasks sintéticas, 1 modelo/1 ambiente, acoplamento a′ entre C(M) e I [não contar como evidência independente], sequencialidade do vLLM.

## Pré-registros consolidados

1. Piso por config; execução sequencial como premissa. 2. Yield e regra de parada da Fase A. 3. Estatística do critic (cluster por task, zero-inflation, k=10). 4. Features pre vs post. 5. Perturbação estruturada de a′ = estimando distinto (só ablation, nunca pooled). 6. Dose-matching de C1 por rollout total. 7. Direções/transições jamais agregadas. 8. Saturação fora dos critérios confirmatórios.

## Cronograma (gates > datas)

| Semana | Fase | Gate |
|---|---|---|
| 0 (agora) | 0 + esqueleto E1 | GATE 0 |
| 1 | A (grid 3 configs × 30 tasks) | GATE 1 → decide claim |
| 2 | B (critic) + D1 | GATE 2 |
| 3 | C1 (3 braços) + D2 | GATE 3 → decide título |
| 4 | E (escrita) + C2 se sobrar | submissão interna |
