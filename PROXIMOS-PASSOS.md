# PROXIMOS-PASSOS.md — pós-painel rodada 10 (desfecho 38 integrado)

> Atualizado em 2026-08-27. Paper no template ICLR 2026, texto principal em
> exatamente 9 páginas (commit fe70253). Painel simulado rodada 10:
> **7/10 accept** (soundness 3.5/4, presentation 3/4, contribution 3/4,
> confidence 4/5). Ledger com 38 itens.

## Estado

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

## Fila de execução (ordem de valor)

1. ⬜ **Fase D — validação do ramo positivo do gate** (40–60 GPU-h; NÃO
   autorizada). Única weakness estrutural restante (W4: a licença nunca foi
   exercida com sucesso; caminho de 7→8). Exige pool que passe o gate
   analítico do pré-reg 34 (≥10 tasks com margem ≥0.10 — 4 tentativas
   falharam); desenho no Appendix L (design brief). Pré-registrar antes.
2. ⬜ **Nomes de autores** no paper (pendente do usuário).
3. ⬜ Varredura de literatura #4 (research agent, zero GPU) antes da
   submissão — última em 2026-08-25.
4. ⬜ `make reproduce` final + congelamento do artefato de release
   (o paper promete infraestrutura + ledger de 38 itens).
5. ⬜ (Opcional) Rodada de polimento de prosa — presentation 3/4 por
   densidade; sem tocar em claims/gates.

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
