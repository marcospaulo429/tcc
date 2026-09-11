# PROXIMOS-PASSOS.md — pós-mesa rodada 12 (paper pós-40 revisado ISOLADO)

> Atualizado em 2026-09-10. Paper no template ICLR 2026; ledger com 40
> itens. **Texto principal ultrapassou as 9 páginas** com a integração do
> desfecho 40. Última versão de 9pp exatas: fe70253.
> **Mesa isolada (só lê paper/, Fable 5.1): rodada 11 (pré-40) ≈4.0; rodada 12
> (pós-40) ≈3.7 Reject.** A rodada 10 (7/10) lia o diário — descartar como
> referência. Detalhes no DIARIO (2026-09-10).

## Estado

- **Desfecho 40 = s1** (9e3d670 DIARIO; paper neste commit): quarto braço
  fatorial R(h′,a) — auditor (Boclin) confirmado: 56/57 pontos screened
  de folga com R(h′,a) = R exato; I_fact = 0; C_H ≠ C_Ha em 83/122 V1
  (68%). Consequência: **I é contraste total-vs-direto, não interação
  fatorial**; screening na folga = artefato da grade incompleta. Fora da
  folga e em observation_policy (V2) há componente genuína. Integrado em:
  abstract, intro (parágrafo dos três braços + contribuição Finding),
  Fig. 1 (braço H relabelado como live — era bug de exposição; 4º braço
  Ha adicionado), §sec:interaction (parágrafo novo), Remark rem:factorial
  no Apêndice formal, T0 (tab:claims) e ledger (#40). Linguagem:
  "artifact of the incomplete factorial grid"; NUNCA "interação não
  existe".
- Paper reestruturado em **três claims** (702f225): Measurement / Finding /
  Decision rule. Gate reenquadrado como **veto validado** (falso-negativo
  demonstrado no 8B), licença explicitamente conjectural.
- **Desfecho 38 = X1+E1** (d042d06, 648d06f): Mistral-7B sob harness V2
  congelado — smoke 1.00 (vs 0.57 no V1 JSON; pré-reg 35 reclassificado como
  fronteira do protocolo V1, não da família), piso 48/48+48/48 exato, s3,
  gate reproduz o padrão Qwen nas 4 contabilidades (primário abre 0.321,
  estrito fecha 0.184), a′_s mesmo bucket b3 (3/6, n=6, suporte).
  Linguagem: "no longer confined to a single model family" — NUNCA
  "generalizes across families".
- Fixes editoriais do round 10 aplicados (e5f1001, fe70253): termination
  cross-family = acordo por construção (duais last-mover); a′_s n=6 com CI
  atravessando buckets; taxas cross-family declaradas confundidas por
  seleção; linha Mistral em tab:synthesis e T0; ledger 34→38; célula única
  em §8.1.

## Plano completo até a submissão (pós-rodada 13-pré, 2026-09-10)

Tese re-escopada (aceita pela mesa como direção, ≈4.7 se só reescrita):
**"NDE = 0 é propriedade do tipo de decisão × horizonte de consumo da
informação; o crédito de harness de contexto é (quase) todo mediado pela
ação do modelo; o census gate mede a fração com NDE ≠ 0."** Nomenclatura:
I = I_fact − PE (porção eliminada, VanderWeele) — NUNCA "não identificado".
Título provisório: *"Harness Credit Is Mostly Mediated: Four-Arm Replay
Separates Total from Direct Effect in a Two-Layer Coding Agent"*.

Trajetória de nota esperada: 3.7 (atual) → 4.7 (re-tese) → 5–5.5 (+ pré-reg
41) → 5.5–6 (+ pré-reg 42 replicando) → 6–7 (+ Fase D). Meta: ≥5.5 na
rodada 13 da mesa antes de decidir a Fase D.

### Fase 0 — Pré-condições de infra (Slurm, obrigatório antes de qualquer replay)
- ⬜ Copiar `runs/` da 4090 para `/raid/$USER/tcc/runs/` (rsync; checar
  sha256 de `runs/preg40/report.json` e dos `teste0_*`).
- ⬜ Job `slurm/gate_nulo_h100.sbatch` (h100n2, gpu:1): vLLM 0.8.5.post1,
  APC off, série; 16 replays nulos V1 + 16 V2 → **piso deve ser 0.0 exato**.
  Registrar no DIARIO: job id, partição, GPU, versão vLLM, resultado.
  Se piso ≠ 0 → parar, investigar (ASLR/APC/concorrência, App. J) — sem gate
  não há Fase 2.
- Responsável: `runner` (executa/monitora), eu (interpreto o gate).

### Fase 1 — Pré-reg 41: análises de custo zero (0 GPU; dados já existem)
Registrar endpoints no DIARIO ANTES de olhar os dados.
- (a) Tabela 2×2 (folga, pivotal): C_H ≠ 0 × C_Ha = 0, com distribuição de
  |C_H| (mediana, IQR, máx). Endpoint: fração NDE = 0 entre pivotais de folga
  com C_H ≠ 0. Vira o **número primário do abstract**.
- (b) Teste de consistência do modelo de mediação: R(h′, a′_s) vs R_H nos
  44 pontos do pré-reg 26 (a′_s ≈ f(h′) amostrado). Endpoint: fração de
  igualdade exata; discordâncias anatomizadas.
- (c) Anatomia dos 8 pontos observation_policy V2 com NDE ≠ 0 (4/12) e do
  api_router I_fact = 0.375: horizonte de consumo da informação (turno em
  que é usada) como variável explicativa — evidência A FAVOR da tese
  re-escopada, não exceção.
- (d) Tabela 3 / massa não-screened recalculada com I_fact e C_Ha nos 48 V2.
- (e) Diagnóstico do pré-reg 31 (outcome ≥ C_H a episódios iguais em 3/3
  seeds): densidade do sinal (fração de decisões por episódio com C_H ≠ 0)
  e variância do estimador de gradiente; hipótese: sinal exato porém esparso
  vs. sinal ruidoso porém denso. Sem explicação aqui, Claim 3 sai da tese.
- (f) n efetivo: pares únicos (task, ponto) por célula, reportado ao lado
  de cada contagem.
- Responsáveis: `impl` (script `experiments/preg41.py`, testes em
  `tests/`), `revisor` (ameaças: seleção de pivotais, dupla contagem V1/V2),
  eu (pré-reg, interpretação).

### Fase 2 — Pré-reg 42: quarta célula fora da tripla (~150 rollouts, Slurm)
- Hipótese: em pontos screened de folga, R(h′,a) = R (NDE = 0) replica fora
  de V1/4B. Variável: célula (MBPP+ 11 pivotais 4B; HumanEval+ 42 pivotais;
  8B folga 28). Baseline: 56/57 de V1. Métrica: fração NDE = 0 por célula.
- Endpoints pré-registrados: s1 ≥ 0.90 (replica); s2 0.60–0.90 (parcial,
  reportar por tipo); **s3 < 0.60 → tese vira "artefato de desenho do pool
  V2/L" e o paper reporta como limitação central** (ramo de falha
  declarado antes).
- Custo: ~81 replays + 16 nulos por célula ≈ 130–150 rollouts, 1 GPU,
  série; `slurm/preg42.sbatch` a partir de `slurm/preg40.sbatch`;
  JSONL idempotente + `--signal=B:SIGUSR1@300`.
- Responsáveis: `impl` (generalizar `quarto_braco.py` para célula
  parametrizada), `revisor` (comparabilidade de pivotais entre pools),
  `runner` (job), eu (gate + desfecho no ledger).

### Fase 3 — Re-tese do paper (escrita; só após 41, idealmente após 42)
- Título novo; abstract ≤ 200 palavras, UM número primário (de 41a) + a
  fração externa (de 42).
- Contribuições reescritas: (1) medição — quatro braços a piso zero
  separam efeito total de direto; (2) achado — NDE = 0 para decisões de
  contexto de consumo imediato, NDE ≠ 0 onde a informação vive em turnos
  posteriores, gate mede a fração; (3) prescrição — harness-only: C_H ou
  outcome (mesmo estimando; replay não compensa — explicar 31); joint: só
  CDEs separam camadas, medir a fração NDE ≠ 0 antes.
- Unificar Prop. 1(iii), Cor. 2 e regra v1.0(v) em torno de total vs.
  direto; Remark 3 renomeado I = I_fact − PE; reenquadrar Act 4 (custo de
  estimação, retirar "bias"); pré-reg 40 como caso documentado do artefato
  de três braços (seção honesta, não título); remover "never separated"
  (App. B), "explica 2608.19760" → "consistente com a leitura de dose",
  "Boclin" (L511, L1980); conclusão reescrita citando a quarta célula.
- Responsável: eu. `quick` para mecânica (bib, refs cruzadas).

### Fase 4 — Compressão a 9pp + custo zero
- 2 figuras de dados no main text: scatter C_H vs C_Ha (122 V1 + 48 V2 +
  células de 42, por regime/tipo) e census/gate; F3 em 5.5"; F5 → Act 4;
  quadro-glossário de configs/outcomes; linha da 4ª célula na Tabela 1;
  reconciliar 30/40/52 tasks; FIGURAS.md em inglês; recompilar (main.aux
  obsoleto), verificar p9/p10 com pdftotext.
- Responsável: `quick`/`impl` (figs.py), eu (cortes).

### Fase 5 — Auditoria interna + mesa rodada 13 (gate de decisão)
- `revisor` sobre 41/42 e sobre a coerência claims ↔ ledger ↔ abstract.
- Mesa `iclr` rodada 13 (isolada). **Decisão:** ≥ 5.5 → Fase 7; 5–5.5 →
  Fase 6 se houver GPU; < 5 → rever tese antes de gastar GPU.

### Fase 6 — Ramo positivo (CONDICIONAL, não autorizado; 40–60 GPU-h)
- Opção barata primeiro: 5º braço control-variate × 3 seeds no setup do
  Act 4 (~1600 calls/seed) — testa a prescrição harness-only.
- Fase D propriamente: treino harness-only (ou joint) numa célula onde
  C_Ha ≠ C_H (observation_policy V2), pré-registrado; exige pool que passe
  o gate analítico do pré-reg 34 (≥10 tasks margem ≥0.10 — 4 tentativas
  falharam). Endpoint: estimando prescrito vence outcome a episódios iguais.
  Sem isso, a regra continua só vetando.

### Fase 7 — Submissão
- Varredura de literatura #4 (`research`, zero GPU): CHILL/CAR/C3/
  Co-Harness + busca por "mediation"/"natural direct effect" em agentes.
- Nomes de autores; checagem de anonimato (grep por nomes, paths, URLs).
- `make reproduce` + congelamento do release; ledger 42 itens fechado.
- Mesa rodada 14 (final) → submeter.

### Riscos de validade a declarar no paper
- Pool V2/L desenhado para consumo imediato → NDE = 0 pode ser artefato
  de desenho (mitigação: Fase 2; declarar em Limitações).
- n efetivo ~20 pares únicos em V1 folga (reportar sempre ao lado do 56/57).
- Uma tripla (Qwen3-4B, harness V1/V2, sandbox); Mistral só sob V2.
- Piso zero em H100 ≠ piso zero em 4090 até revalidado (Fase 0).
- Pré-reg 31 contradiz a prescrição harness-only até explicado (Fase 1e).
- Múltiplas comparações: FDR ledger atualizado para 42 itens.

## Não mexer (AC rodadas 12–13-pré)

§4.1 + App. J (piso zero, reconciliação por run, incidentes ASLR/APC/
concorrência); Fig. 1 atual (4 braços); Remark 3 (I = I_fact − (C_H − C_Ha));
ledger e claims table (só linhas afetadas pela re-tese); controles a′/a′_s.

## Lembretes de rigor

- Registrar pré-reg no DIARIO ANTES de qualquer contato com dados; desfechos
  (incl. falhas) entram no ledger.
- APC OFF em replays; requisições em série (piso 0.417 com APC é achado, não
  detalhe).
- I1/I2 (direções de flip são experimentos distintos; filtro de elegibilidade
  enviesa p/ turnos tardios) valem também no V2.
- Timeouts de pytest: excluídos do piso, reportados à parte.
- 9pp: cada corte rende 60–80% do estimado (reflow); Table 2 em p5 é
  sensível a ±1 linha; verificar fronteira p9/p10 com pdftotext após cada
  lote ("(Appendix L)." / "A Master Claim Table").

## Setup operacional

Ver README.md (comando do vLLM, venvs, make test/reproduce, compilação do
paper). Servidor Qwen3-4B costuma já estar de pé na porta 8321 — checar
`curl -s localhost:8321/v1/models` antes de subir outro.
