# Figuras-alvo (definidas ANTES dos experimentos B/C — P11 do revisor)

| Fig | Conteúdo | Fonte de dados | Status |
|---|---|---|---|
| F1 | Piso de ruído: histograma de \|dR\| dos replays nulos, por config (3 thresholds); frações de timeout à parte | runs/teste0_g{450,600,900}/replay_results.jsonl | aguardando grid |
| F2 | Distribuição de C(H) e C(M) por direção, transição e estrato (V2/S/C/L); tasks-controle C ≈ 0 destacadas | runs/teste1_g*/cf_results.jsonl, teste2_g* | aguardando grid |
| F3 | Anatomia de I(H,M): dispersão C_HM vs C_H+C_M; regimes screening-off (I=−C_H) e sinergia (I>0, tasks S); fração saturada por config | runs/teste3_g*/cf_results.jsonl | aguardando grid (GATE 1) |
| F4 | Critic vs baselines dose-matched: precision@10 e Spearman clusterizado por task, com IC bootstrap | runs/credit_dataset.jsonl + Fase B | aguardando B |
| F5 | Curvas de treino C1 (3 braços) por ROLLOUT TOTAL (episódios+replays), 3 seeds, média±IC | Fase C1 | aguardando C |

Tabelas: T1 posicionamento vs related work; T2 yield/descartes por config (saturação, vácuo, timeout, sem-a′) — pré-registro (f).
