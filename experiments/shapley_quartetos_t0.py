"""T0.2 — Decomposição de Shapley 2-player sobre os quartetos existentes.

Pós-hoc declarado (2026-08-26). Zero GPU: (R0, RH, RM, RHM) já medidos.

v(S) = R0 − R(flip S)  ⇒  v(H)=C_H, v(M)=C_M, v(HM)=C_HM.
φ_H = ½(C_H + C_HM − C_M);  φ_M = ½(C_M + C_HM − C_H);  φ_H+φ_M = C_HM.
Identidades: φ_H − C_H = ½I  e  φ_H − (C_HM−C_M) = −½I — Shapley é o ponto
médio entre o single-layer e o corrigido; em pontos screened (C_HM=C_M)
φ_H = ½C_H ≠ 0: Shapley NÃO elimina o double counting, divide-o ao meio.
"""
import json
from pathlib import Path

CONFIGS = {
    "v1_g450": "runs/teste3_g450/cf_results.jsonl",
    "v1_g600": "runs/teste3_g600/cf_results.jsonl",
    "v1_g900": "runs/teste3_g900/cf_results.jsonl",
    "v1_mt4": "runs/teste3_mt4/cf_results.jsonl",
    "v1_mt6": "runs/teste3_mt6/cf_results.jsonl",
    "v1_mt8": "runs/teste3_mt8/cf_results.jsonl",
    "v2_census": "runs/census_v2/census_rows.jsonl",
}
OUT = Path("experiments/results/2026-08-26_shapley_quartetos.json")


def rows(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def main() -> None:
    res = {"data": "2026-08-26", "status": "pos-hoc declarado", "configs": {}}
    tot_screened, tot_phih_screened = 0, []
    for name, path in CONFIGS.items():
        if not Path(path).exists():
            continue
        pts = []
        for r in rows(path):
            if r.get("C_H") is None or r.get("C_M") is None or r.get("C_HM") is None:
                continue
            ch, cm, chm = r["C_H"], r["C_M"], r["C_HM"]
            phi_h = 0.5 * (ch + chm - cm)
            corr = chm - cm
            screened = abs(chm - cm) < 1e-9
            pts.append((ch, corr, phi_h, screened))
        if not pts:
            continue
        n = len(pts)
        scr = [p for p in pts if p[3]]
        # em pontos screened com C_H≠0, as três atribuições divergem: C_H, 0, C_H/2
        scr_bill = [p for p in scr if abs(p[0]) > 1e-9]
        tot_screened += len(scr_bill)
        tot_phih_screened += [p[2] for p in scr_bill]
        res["configs"][name] = {
            "n_quartetos": n,
            "screened": len(scr),
            "screened_com_CH_nao_nulo": len(scr_bill),
            "mediana_abs": {
                "C_H": round(_med([abs(p[0]) for p in pts]), 4),
                "C_HM_menos_C_M": round(_med([abs(p[1]) for p in pts]), 4),
                "shapley_H": round(_med([abs(p[2]) for p in pts]), 4),
            },
            "nesses_pontos_media": {
                "C_H": round(_avg([p[0] for p in scr_bill]), 4) if scr_bill else None,
                "corrigido": 0.0 if scr_bill else None,
                "shapley_H": round(_avg([p[2] for p in scr_bill]), 4) if scr_bill else None,
            },
        }
    res["identidades_verificadas"] = "phi_H = (C_H + (C_HM-C_M))/2 por construcao"
    res["leitura"] = (
        f"em {tot_screened} pontos screened com C_H!=0, single-layer cobra C_H, "
        "o corrigido cobra 0, e Shapley cobra exatamente C_H/2 "
        f"(media {_avg(tot_phih_screened):.3f}): Shapley nao resolve o double "
        "counting no ponto — reparte-o entre as camadas; a escolha de "
        "atribuicao continua sendo uma escolha de estimando, e I e "
        "exatamente o diametro do leque de atribuicoes admissiveis")
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


def _med(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


if __name__ == "__main__":
    main()
