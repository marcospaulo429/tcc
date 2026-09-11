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

## Fila de execução (ordem de valor — top-3 do AC da rodada 12)

0. ⬜ **RE-TESE do paper em torno do achado fatorial** (escrita, 2–3 dias;
   4 → 5–6). O paper hoje conta duas histórias: título/abstract/conclusão
   vendem screening-off; §4.3 diz "artifact of the incomplete grid".
   Entregas: novo título; abstract ≤200 palavras com UM número primário;
   contribuições e conclusão coerentes (harness de contexto sem caminho
   direto p/ R: CDE = 0 em 56/57; crédito de harness é mediado; C_H =
   estimando correto p/ harness-only training; C_HM − C_M e C_Ha = CDEs,
   relevantes só p/ joint training; census gate preça a massa com CDE ≠ 0).
   Unificar as 3 prescrições incompatíveis: Prop. 1(iii), Cor. 2, regra
   v1.0(v). Remover "never separated" (App. B). Reenquadrar Act 4 como
   custo de estimação (outcome-only = MC do efeito total sem replay tax).
1. ⬜ **Compressão a 9pp + itens de custo zero** (1–2 dias): 2 figuras de
   dados no main text (scatter C_H vs C_Ha — 122 V1 + 48 V2 por regime/tipo;
   census/gate); F3 regenerada em 5.5"; F5 → Act 4; quadro-glossário de
   configs (g450/mt6/q8/...) e outcomes (s1/c0/X1/...); linha da 4ª célula
   na Tabela 1; reconciliar 30/40/52 tasks; **remover "Boclin"** (L511,
   L1980 — anonimato); recompilar (main.aux obsoleto) e verificar p9/p10;
   FIGURAS.md reescrito em inglês descrevendo as figuras reais.
2. ⬜ **Re-derivar gate e Act 4 no estimando fatorial + control variate**
   (~1 dia análise + ~1 dia GPU, via Slurm):
   (a) Tabela 3 / massa não-screened recalculada com I_fact/C_Ha nos 48 V2
       já medidos (0 rollouts; pré-registrar como análise descritiva);
   (b) 5º braço control-variate (outcome + crédito corrigido como baseline)
       × 3 seeds no setup do Act 4 (~1600 calls/seed) — pré-registrar;
   (c) quarta célula nas células externas (MBPP+/HumanEval+) e 8B/Mistral
       (~150 replays) — fecha "única tripla de suporte" do R3.
3. ⬜ Rodar a mesa (rodada 13) após 0+1; após 2, rodada 14.
4. ⬜ **Fase D — validação do ramo positivo do gate** (40–60 GPU-h; NÃO
   autorizada). Exige pool que passe o gate analítico do pré-reg 34.
5. ⬜ **Nomes de autores** no paper (pendente do usuário).
6. ⬜ Varredura de literatura #4 (research agent, zero GPU) antes da
   submissão — última em 2026-08-25. Incluir engajamento explícito com o
   experimento de treino de 2608.19760 (R2: posicionar dose-matching como
   replicação em outro eixo, não contribuição).
7. ⬜ `make reproduce` final + congelamento do artefato de release.

## Não mexer (AC rodada 12)

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
