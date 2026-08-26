"""Distribuição de a′ nos pontos do census V2 (pré-reg 36).

PRÉ-REGISTRO (DIARIO-EXPERIMENTAL.md, 2026-08-26, commit 8f0a6fe ANTES de rodar):
- 5 schedules novos e disjuntos (S3–S7) nos 48 pontos medidos do census,
  mesma temperatura por ponto, mesmo sampler (sample_alternative_v2).
- Pool de análise por ponto: census + A1/A2 (pré-reg 30A) + S3–S7 (≤8 draws).
- Draw válido := encontrado e braços M/HM sem erro; idêntico ao a′ do census
  herda o veredito do census sem replay novo. Duais (29a) herdados.
- Primário: U = fração dos pontos com ≥2 draws válidos e veredito UNÂNIME.
  d1 U≥0.80 / d2 [0.60,0.80) / d3 <0.60.
- Secundários: headline (desfecho + gate medidos sem duais 0.20) por schedule
  novo e sob voto majoritário; nº de a′ distintos por ponto; flips por tipo.

Uso (sequencial, servidor 8321 com APC off):
  uv run python -m experiments.v2_dist_aprime            # coleta S3–S7
  uv run python -m experiments.v2_dist_aprime --relatorio
"""
import argparse
import json
from pathlib import Path

from agent.llm import LLMClient
from experiments.census_v2 import _canon, _trajs_base, avalia_desfecho, gate_f4f5
from experiments.common import append_row, done_keys, load_rows
from experiments.v2_controles import (OUT as OUT_30A, _a_prime_census, _bracos,
                                      _dual, _screening, _validos)
from interventions.model_v2 import _canonical, sample_alternative_v2

OUT = Path("runs/v2_dist_aprime")
SCHEDULES = {
    "S3": tuple(range(7001, 7009)),
    "S4": tuple(range(8001, 8009)),
    "S5": tuple(range(9001, 9009)),
    "S6": tuple(range(10001, 10009)),
    "S7": tuple(range(11001, 11009)),
}


def coleta():
    trajs, scr = _trajs_base(), _screening()
    llm = LLMClient()
    rows_path = OUT / "rows.jsonl"
    feitos = done_keys(load_rows(rows_path),
                       ("schedule", "cfg", "task_id", "index"))
    for r in sorted(_validos(), key=lambda r: (r["cfg"], r["task_id"], r["index"])):
        chave = (r["cfg"], r["task_id"], r["index"])
        traj, scr_row = trajs[(r["cfg"], r["task_id"])], scr[chave]
        dual = _dual(r, scr)
        a_orig = None
        for nome, seeds in SCHEDULES.items():
            if (nome, *chave) in feitos:
                continue
            base = {"schedule": nome, "cfg": r["cfg"], "task_id": r["task_id"],
                    "index": r["index"], "tipo": r["tipo"], "j": r["j"],
                    "dual": dual, "temp": r.get("a_prime_temp", 0.8),
                    "screened_census": r["screened_exato"]}
            print(f"[36:{nome}] {r['cfg']} {r['task_id']} idx{r['index']} "
                  f"({r['tipo']})", flush=True)
            if a_orig is None:
                a_orig = _a_prime_census(llm, traj, r)
                if a_orig is None:
                    append_row(rows_path, {**base, "status": "a_prime_orig_irreproduzivel"})
                    continue
            dj = traj.decisions[r["j"]]
            amostra = sample_alternative_v2(
                llm, dj.state_before["messages"], _canon(dj.chosen_action),
                temperature=base["temp"], seeds=seeds)
            if not amostra["found"]:
                append_row(rows_path, {**base, "status": "sem_a_prime_re"})
                continue
            a_canon = _canonical(amostra["action"])
            if a_canon == _canonical(a_orig):
                # herda o veredito do census (replay determinístico)
                append_row(rows_path, {**base, "status": "identico",
                                       "seed": amostra["seed"],
                                       "a_canon": a_canon,
                                       "screened_re": r["screened_exato"]})
                continue
            b = _bracos(llm, traj, r, scr_row, amostra["action"], dual,
                        OUT / "trajs")
            if b["error"]:
                append_row(rows_path, {**base, "status": "erro_replay",
                                       "seed": amostra["seed"], "error": b["error"]})
                continue
            append_row(rows_path, {
                **base, "status": "informativo", "seed": amostra["seed"],
                "a_canon": a_canon, "R_M": b["R_M"], "R_HM": b["R_HM"],
                "screened_re": b["R_HM"] == b["R_M"]})
    relatorio()


def _draws_por_ponto() -> dict:
    """Pool de draws válidos por ponto: census + A1/A2 (30A) + S3–S7."""
    pontos = {}
    for r in _validos():
        chave = (r["cfg"], r["task_id"], r["index"])
        pontos[chave] = {"tipo": r["tipo"], "screened_census": r["screened_exato"],
                         "verdicts": [bool(r["screened_exato"])],
                         "a_canons": {"census"}}
    rows_30a = [x for x in load_rows(OUT_30A / "a_rows.jsonl")
                if x["status"] in ("informativo", "identico")]
    rows_36 = [x for x in load_rows(OUT / "rows.jsonl")
               if x["status"] in ("informativo", "identico")]
    for x in rows_30a + rows_36:
        chave = (x["cfg"], x["task_id"], x["index"])
        if chave not in pontos:
            continue
        p = pontos[chave]
        if x["status"] == "identico":
            p["verdicts"].append(bool(x["screened_census"]))
            p["a_canons"].add("census")
        else:
            p["verdicts"].append(bool(x["screened_re"]))
            p["a_canons"].add(x.get("a_canon") or f"anon:{x['schedule']}")
    return pontos


def relatorio():
    validos, scr = _validos(), _screening()
    pontos = _draws_por_ponto()
    eleg = {k: p for k, p in pontos.items() if len(p["verdicts"]) >= 2}
    unanime = {k: p for k, p in eleg.items() if len(set(p["verdicts"])) == 1}
    U = round(len(unanime) / len(eleg), 4) if eleg else None
    desfecho = (None if U is None else
                "d1_robusto" if U >= 0.80 else
                "d2_sensivel" if U >= 0.60 else "d3_dependente")
    flips_tipo = {}
    for k, p in eleg.items():
        t = flips_tipo.setdefault(p["tipo"], {"n": 0, "flip": 0})
        t["n"] += 1
        t["flip"] += len(set(p["verdicts"])) > 1
    # voto majoritário por ponto (empate mantém census) → headline
    maioria = {}
    for k, p in pontos.items():
        v = p["verdicts"]
        maioria[k] = (sum(v) > len(v) / 2 if sum(v) != len(v) / 2
                      else bool(p["screened_census"]))
    por_tipo, nao_scr_sd, n_sd = {}, 0, 0
    for r in validos:
        chave = (r["cfg"], r["task_id"], r["index"])
        s = maioria[chave]
        t = por_tipo.setdefault(r["tipo"], {"n": 0, "scr": 0})
        t["n"] += 1
        t["scr"] += bool(s)
        if not _dual(r, scr):
            n_sd += 1
            nao_scr_sd += not s
    taxas = {t: {"n": v["n"], "taxa": round(v["scr"] / v["n"], 4)}
             for t, v in por_tipo.items()}
    frac = round(nao_scr_sd / n_sd, 4) if n_sd else None
    # headline por schedule novo
    rows_36 = load_rows(OUT / "rows.jsonl")
    por_schedule = {}
    for nome in SCHEDULES:
        subs = {(x["cfg"], x["task_id"], x["index"]): x["screened_re"]
                for x in rows_36 if x["schedule"] == nome
                and x["status"] in ("informativo", "identico")}
        pt, nsd, ns = {}, 0, 0
        for r in validos:
            chave = (r["cfg"], r["task_id"], r["index"])
            s = subs.get(chave, r["screened_exato"])
            t = pt.setdefault(r["tipo"], {"n": 0, "scr": 0})
            t["n"] += 1
            t["scr"] += bool(s)
            if not _dual(r, scr):
                ns += 1
                nsd += not s
        tx = {t: {"n": v["n"], "taxa": round(v["scr"] / v["n"], 4)}
              for t, v in pt.items()}
        fr = round(nsd / ns, 4) if ns else None
        por_schedule[nome] = {"n_substituidos": len(subs),
                              "desfecho": avalia_desfecho(tx),
                              "gate_sem_duais": {"frac": fr, "abre": gate_f4f5(fr)}}
    n_draws = sorted(len(p["verdicts"]) for p in pontos.values())
    n_dist = sorted(len(p["a_canons"]) for p in pontos.values())
    resumo = {
        "n_pontos": len(pontos),
        "n_elegiveis_2draws": len(eleg),
        "U_unanimidade": U,
        "desfecho_primario": desfecho,
        "flips_por_tipo": flips_tipo,
        "draws_validos_por_ponto": {"min": n_draws[0], "mediana": n_draws[len(n_draws)//2],
                                    "max": n_draws[-1]} if n_draws else None,
        "a_distintos_por_ponto": {"min": n_dist[0], "mediana": n_dist[len(n_dist)//2],
                                  "max": n_dist[-1]} if n_dist else None,
        "headline_voto_majoritario": {
            "taxas_por_tipo": taxas, "desfecho": avalia_desfecho(taxas),
            "gate_medidos_sem_duais": {"frac": frac, "abre": gate_f4f5(frac)}},
        "headline_por_schedule_novo": por_schedule,
        "status_counts": {s: sum(1 for x in rows_36 if x["status"] == s)
                          for s in ("informativo", "identico", "sem_a_prime_re",
                                    "erro_replay", "a_prime_orig_irreproduzivel")},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(resumo, indent=2,
                                                 ensure_ascii=False))
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--relatorio", action="store_true")
    args = ap.parse_args()
    relatorio() if args.relatorio else coleta()
