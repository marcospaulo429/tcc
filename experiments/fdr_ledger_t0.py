"""T0.3 — Correção de multiplicidade (BH e Holm) sobre todos os testes do paper.

Pós-hoc declarado (2026-08-26). Família: todos os testes de hipótese
computados no paper (não só os significativos), m=6.
"""
import json
from pathlib import Path

TESTES = [
    ("slack vs pressure, point-level hypergeometric", 0.005, "afirmado"),
    ("condicionado nao-saturado 0/12 vs 6/19", 0.037, "afirmado (descritivo)"),
    ("slack vs pressure, task-clustered sign test", 0.125, "reportado nao-sig"),
    ("monotonicidade Cochran-Armitage (pre-reg 13)", 0.38, "falha declarada"),
    ("D4b breaks<->re-injection Fisher (b2)", 0.94, "falha declarada"),
    ("D4b breaks<->re-injection Fisher (b1)", 1.0, "falha declarada"),
]
ALPHA = 0.05
OUT = Path("experiments/results/2026-08-26_fdr_ledger.json")


def main() -> None:
    m = len(TESTES)
    ordenado = sorted(TESTES, key=lambda t: t[1])
    linhas = []
    # Benjamini-Hochberg
    bh_corte = 0
    for i, (nome, p, status) in enumerate(ordenado, start=1):
        if p <= ALPHA * i / m:
            bh_corte = i
    # Holm
    for i, (nome, p, status) in enumerate(ordenado, start=1):
        holm_p = min(1.0, p * (m - i + 1))
        linhas.append({
            "teste": nome, "p": p, "status_no_paper": status,
            "bh_sobrevive": i <= bh_corte,
            "holm_p_ajustado": round(holm_p, 4),
            "holm_sobrevive": holm_p <= ALPHA and all(
                min(1.0, q * (m - j)) <= ALPHA
                for j, (_, q, _) in enumerate(ordenado[:i - 1])),
        })
    res = {
        "data": "2026-08-26", "status": "pos-hoc declarado",
        "familia": f"todos os {m} testes computados no paper", "alpha": ALPHA,
        "testes": linhas,
        "leitura": ("apenas o p=0.005 (point-level) sobrevive a BH e a Holm; "
                    "o p=0.037 nao sobrevive a nenhuma correcao — consistente "
                    "com a postura do paper de tratar padroes replicados, nao "
                    "p-values individuais, como evidencia primaria"),
    }
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
