"""Análise descritiva zero-GPU: composição dos pontos excluídos vs medidos do census V2.

Sem novos rollouts — só rows/trajetórias já gravadas (selection-into-measurement,
espelho V2 da análise de seleção do V1). Saída: runs/census_v2/analise_exclusao.json.
"""
import json
import statistics as st
from collections import Counter
from pathlib import Path

from experiments.census_v2 import _rows_census_mescladas, _trajs_base
from experiments.common import load_rows

scr = {(r["cfg"], r["task_id"], r["index"]): r
       for r in load_rows(Path("runs/census_v2/screening_rows.jsonl"))
       if not r["error"] and r["dR"] != 0}
rows = _rows_census_mescladas()
med = [r for r in rows if not r["error"] and r["screened_exato"] is not None]
exc = [r for r in rows if r not in med]
trajs = _trajs_base()


def feats(r):
    s = scr[(r["cfg"], r["task_id"], r["index"])]
    d = trajs[(r["cfg"], r["task_id"])].decisions[r["index"]]
    return {"tipo": r["tipo"], "cfg": r["cfg"], "absdR": abs(s["dR"]),
            "turn": d.state_before.get("turn", 0),
            "ctx": d.state_before.get("context_tokens", 0),
            "erro": r["error"]}


fm, fe = [feats(r) for r in med], [feats(r) for r in exc]
out = {}
for nome, f in (("medidos", fm), ("excluidos", fe)):
    out[nome] = {
        "n": len(f),
        "tipo": dict(Counter(x["tipo"] for x in f)),
        "cfg": dict(Counter(x["cfg"] for x in f)),
        "absdR_mediana": round(st.median(x["absdR"] for x in f), 4),
        "absdR_media": round(st.mean(x["absdR"] for x in f), 4),
        "turn_mediana": st.median(x["turn"] for x in f),
        "ctx_mediana": st.median(x["ctx"] for x in f),
    }
out["excluidos"]["erros"] = dict(Counter(x["erro"] for x in fe))
out["maiores_absdR_excluidos"] = [
    {"tipo": x["tipo"], "absdR": x["absdR"]}
    for x in sorted(fe, key=lambda x: -x["absdR"])[:5]]
Path("runs/census_v2/analise_exclusao.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False))
print(json.dumps(out, indent=2, ensure_ascii=False))
