# PROXIMOS-PASSOS.md — pós-painel rodada 7 (paper em formato ICLR, 9 pp)

> Atualizado em 2026-08-27. Paper no template ICLR 2026, texto principal em
> exatamente 9 páginas (commit 975af1b). Painel simulado rodada 7:
> **R1=6, R2=6, R3=6 — AC: Accept (poster).** Pré-regs 30, 31, 32 (ABORT) e
> 33 executados e integrados ao paper (ledger com 33 itens).

## Estado

- As três quantidades (C_H, C_M, I) medidas com piso zero em V1; 4 atos de
  treino no ramo fechado do no-free-lunch; census V2 (pré-reg 29) abriu o gate
  F4–F5 no stack mini-SWE (frac não-screened 0.50).
- Critic vs heurísticas dose-matched: empate no pooled, vantagem em detecção
  de screening (AUROC 0.846); transferência V1→V2 falha (resultado honesto).
- Reprodutibilidade: `make reproduce` reconcilia todos os números publicados.

## Top-5 do AC (rodada 7) — status

1. ✅ **Pré-reg 31 (episode-matched, V1):** outcome ≥ C_H 3/3 seeds a episódios
   iguais (0.450 vs 0.398); confound morto, veredito do Ato 4 mantido.
2. ✅ Reenquadramento "regime-dependent" → dependência tripla (texto, ef656ec).
3. ✅ Tabela-síntese promovida ao texto principal §4.3 (ef656ec).
4. ✅ Contribuição 3 resolvida RODANDO o treino V2: pré-reg 32 ABORT na
   calibração (grade de λ da V1 mal-escalada — λ não transporta entre stacks);
   pré-reg 33 (λ*=0.2, 10 tasks margin-verified) → desfecho **s3, colapso de
   atrator**: todos os braços de aprendizado convergem token-exact para
   summarize-always (heldout 0.831 vs 0.889 do alvo dominante) antes de
   qualquer ordenação de crédito ser testável. "Both branches exercised
   through training" agora é literal (4a9f96d).
5. ⬜ Célula não-Qwen — experimento caro, opcional, sem plano no momento.

## Fila de execução (ordem)

1. ✅ **Pré-reg 30 — controles de estimando V2:** Parte A **r2** (estabilidade
   pontual 0.739 <0.90, mas s3 + gate abertos sob os 2 schedules de re-draw);
   Parte B **b3** (screened_s 8/21=0.381; os 13 não-screened têm I_s=0 EXATO
   — aditividade, o regime onde crédito single-layer é correto). Integrado:
   app:estimand, §8, ledger row 30 (975af1b).
2. (Opcional) Análise zero-GPU da composição dos 65 pontos excluídos do
   census V2.
3. (Decidido: NÃO por ora) Pré-reg 34 — treino V2 mais longo/lr menor; s3
   fica como resultado honesto, só revisitar se revisor exigir.
4. (Opcional, caro) Célula não-Qwen (item 5 do AC).

## Lembretes de rigor

- Registrar pré-reg no DIARIO ANTES de qualquer contato com dados; desfechos
  (incl. falhas) entram no ledger.
- APC OFF em replays; requisições em série (piso 0.417 com APC é achado, não
  detalhe).
- I1/I2 (direções de flip são experimentos distintos; filtro de elegibilidade
  enviesa p/ turnos tardios) valem também no V2.
- Timeouts de pytest: excluídos do piso, reportados à parte.

## Setup operacional

Ver README.md (comando do vLLM, venvs, make test/reproduce, compilação do
paper). Servidor Qwen3-4B costuma já estar de pé na porta 8321 — checar
`curl -s localhost:8321/v1/models` antes de subir outro.
