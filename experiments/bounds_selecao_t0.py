"""T0.1 — Bounds de identificação parcial (Manski) para a seleção por a'.

Pós-hoc declarado (2026-08-26). Pergunta: os vereditos do paper sobrevivem
à imputação adversarial dos pontos excluídos por falta de a'?

Dois alvos:
- V1 slack (57/57 medidos screened; 129 candidatos excluídos): bound inferior
  de pior caso e break-even da leitura "screening domina".
- Gate V2 (limiar 0.20): as quatro contabilidades × dois extremos de imputação.
"""
import json
from pathlib import Path

OUT = Path("experiments/results/2026-08-26_bounds_selecao.json")

# V1 slack: candidatos e medidos por config (fonte: 2026-08-24_analise_selecao.json)
V1 = {"g450": (64, 17), "g600": (61, 21), "g900": (61, 19)}

# V2 (fonte: paper tab:gate + census_rows): 114 pivotais, 48 medidos, 66 excluídos
V2 = {
    "pivotal": 114, "medidos_com_duais": 48, "medidos_sem_duais": 38,
    "nonscreened_com_duais": 24, "nonscreened_sem_duais": 15,
    "excluidos": 66, "limiar": 0.20,
}


def main() -> None:
    n_cand = sum(n for n, _ in V1.values())
    n_med = sum(m for _, m in V1.values())
    n_exc = n_cand - n_med
    # screened observados no slack V1: 57/57
    s_obs = n_med
    lo = s_obs / n_cand          # pior caso: todo excluído é non-screened
    hi = (s_obs + n_exc) / n_cand
    # break-even da leitura "maioria dos candidatos screened"
    faltam = max(0, -(-n_cand // 2) - s_obs)  # ceil(n/2) - observados
    v1 = {
        "candidatos": n_cand, "medidos": n_med, "excluidos": n_exc,
        "screened_medidos": s_obs,
        "fracao_screened_bounds": [round(lo, 3), round(hi, 3)],
        "break_even_maioria": {
            "excluidos_screened_necessarios": faltam,
            "fracao_dos_excluidos": round(faltam / n_exc, 3),
        },
        "leitura": ("pior caso 0.31; 'maioria screened' exige que apenas "
                    f"{faltam}/{n_exc} = {faltam/n_exc:.0%} dos excluidos "
                    "screenem; sob a leitura do estimando (excluidos = modelo "
                    "quase-deterministico, correcao vacua), a populacao e "
                    "definida pelo estimando e o bound nao se aplica"),
    }

    v2 = {}
    for duais, ns, med in (("com_duais", V2["nonscreened_com_duais"], V2["medidos_com_duais"]),
                           ("sem_duais", V2["nonscreened_sem_duais"], V2["medidos_sem_duais"])):
        pior = ns / V2["pivotal"]                      # excluídos todos screened
        melhor = (ns + V2["excluidos"]) / V2["pivotal"]  # excluídos todos non-screened
        v2[duais] = {
            "medidos": f"{ns}/{med} = {ns/med:.2f}",
            "todos_pivotais_pior_caso": round(pior, 3),
            "todos_pivotais_melhor_caso": round(melhor, 3),
            "gate_pior_caso": "abre" if pior >= V2["limiar"] else "fecha",
            "gate_melhor_caso": "abre" if melhor >= V2["limiar"] else "fecha",
            "identificado": pior >= V2["limiar"] or melhor < V2["limiar"],
        }
    v2["leitura"] = ("com duais o gate abre ate no pior caso adversarial "
                     "(0.211 >= 0.20) — a selecao por a' nao pode ter fabricado "
                     "a abertura; sem duais os extremos cruzam o limiar "
                     "(0.132 vs 0.711) — indeterminado sob imputacao, como a "
                     "tabela do paper ja reporta ao fechar nessa contabilidade")

    res = {"data": "2026-08-26", "status": "pos-hoc declarado", "V1_slack": v1,
           "V2_gate": v2}
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
