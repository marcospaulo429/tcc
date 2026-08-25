# PROXIMOS-PASSOS.md — pós-painel rodada 7 (paper em formato ICLR, 9 pp)

> Atualizado em 2026-08-26. Paper no template ICLR 2026, texto principal em
> exatamente 9 páginas (commit 9fa8e96). Painel simulado rodada 7:
> **R1=6, R2=6, R3=6 — AC: Accept (poster).**

## Estado

- As três quantidades (C_H, C_M, I) medidas com piso zero em V1; 4 atos de
  treino no ramo fechado do no-free-lunch; census V2 (pré-reg 29) abriu o gate
  F4–F5 no stack mini-SWE (frac não-screened 0.50).
- Critic vs heurísticas dose-matched: empate no pooled, vantagem em detecção
  de screening (AUROC 0.846); transferência V1→V2 falha (resultado honesto).
- Reprodutibilidade: `make reproduce` reconcilia todos os números publicados.

## Top-5 do AC (rodada 7) — o que sobe a nota

1. **Braço outcome-only episode-matched no Ato 4 (V1)** — único experimento
   "devido": o braço outcome-only atual difere em nº de episódios; matar o
   confound. → pré-reg 31. (R1-W1; move R1 de 6 p/ 7–8.)
2. Reenquadrar "regime-dependent" → dependência tripla (estimando, protocolo
   de ação, classe de task); p clusterizado 0.125 (n=3 tasks) não sustenta o
   claim forte. (R3-W1; só texto.)
3. Promover tabela-síntese e F3 de volta ao texto principal (conflita com o
   limite de 9 pp — exige troca de espaço). (R2-W1; só texto.)
4. Suavizar contribuição 3: ramo aberto foi MEDIDO, não treinado. (R1-W2/R3-W3;
   texto — ou resolver rodando o treino V2, ver abaixo.)
5. Célula não-Qwen (outro modelo) como evidência de generalização. (R2-W3;
   experimento caro, opcional.)

## Fila de execução (ordem)

1. **Pré-reg 31 — braço episode-matched (V1, Ato 4):** outcome-only com o MESMO
   nº de episódios dos braços com crédito (139 eps × 3 seeds, ~1600 chamadas).
   Registrar no DIARIO antes de rodar.
2. **Pré-reg 32 — treino V2 (F4–F5, ramo aberto):** gate accounting fixado EX
   ANTE (pontos medidos sem duais: 15/38 = 0.39 → abre), braços dose-matched
   E episode-matched desde o desenho (lição do V1), desfechos declarados.
   Se rodar, a contribuição 3 vira "ambos os ramos exercitados" de verdade.
3. **Pré-reg 30 — controles de estimando V2:** re-amostragem de a′ + a′
   estruturado (a′_s) nos 48 pontos do census (contra a objeção 29b).
4. Itens de texto (2, 3, 4 do AC) — na próxima passada do paper.

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
