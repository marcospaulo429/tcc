"""D1/W5 — Quantifica os sub-mecanismos do screening-off nos replays do teste 3.

Para cada ponto com screening exato (C_HM == C_M) e C_H != 0 (decisão "blindada",
o caso interessante), classifica:
- mech1_reinjecao: o a′ forçado (write_file) contém ≥1 constante crítica da task
  (a informação destruída pelo summarize volta pela ação do modelo) — propriedade
  ESTRUTURAL do estimando do-operator.
- mech2_redisparo: no replay do braço M (sem flip), o harness dispara summarize_context
  em até 2 decisões de context_policy após o ponto — a intervenção só antecipa o
  que aconteceria de qualquer forma — achado EMPÍRICO.
Tasks sem dicionário de constantes (v2) só recebem mech2.

Uso: uv run python -m experiments.analise_mecanismos --tags g600 g450 g900 mt6
"""
import argparse
import json
from pathlib import Path

from environment.tasks_all import CRITICAL_CONSTANTS


def _decisions(path: str) -> list[dict]:
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    return [r for r in rows if r.get("decision_point")]


def _aprime_content(hm_decisions: list[dict]) -> str:
    for d in hm_decisions:
        if d["decision_point"] == "tool_call" and d.get("chosen_action", {}).get("forced"):
            return json.dumps(d["chosen_action"], ensure_ascii=False)
    # fallback: primeiro tool_call do replay (o a′ é a 1ª ação de modelo forçada)
    for d in hm_decisions:
        if d["decision_point"] == "tool_call":
            return json.dumps(d["chosen_action"], ensure_ascii=False)
    return ""


def _summarize_within(m_decisions: list[dict], k: int = 2) -> bool:
    cps = [d for d in m_decisions if d["decision_point"] == "context_policy"]
    return any(d["chosen_action"].get("action") == "summarize_context" for d in cps[:k])


def analyse(tags: list[str], runs_dir: Path) -> dict:
    per_point, counts = [], {"screening_total": 0, "blindados": 0, "mech1": 0,
                             "mech2": 0, "ambos": 0, "nenhum": 0, "sem_dicionario": 0}
    for tag in tags:
        for line in open(runs_dir / f"teste3_{tag}" / "cf_results.jsonl", encoding="utf-8"):
            r = json.loads(line)
            if r["C_HM"] != r["C_M"]:
                continue
            counts["screening_total"] += 1
            if r["C_H"] == 0:
                continue
            counts["blindados"] += 1
            consts = CRITICAL_CONSTANTS.get(r["task_id"])
            hm = _decisions(r["replay_trajs"]["hm"])
            m = _decisions(r["replay_trajs"]["m"])
            content = _aprime_content(hm)
            mech1 = bool(consts) and any(c in content for c in consts)
            mech2 = _summarize_within(m)
            if consts is None:
                counts["sem_dicionario"] += 1
            counts["mech1"] += mech1
            counts["mech2"] += mech2
            counts["ambos"] += mech1 and mech2
            counts["nenhum"] += (not mech1) and (not mech2) and consts is not None
            per_point.append({"tag": tag, "task_id": r["task_id"], "cp_index": r["cp_index"],
                              "C_H": r["C_H"], "I": r["I"], "mech1_reinjecao": mech1,
                              "mech2_redisparo": mech2, "tem_dicionario": consts is not None})
    return {"counts": counts, "points": per_point}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=["g600", "g450", "g900", "mt6"])
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", default="runs/analise_mecanismos.json")
    args = ap.parse_args()
    report = analyse(args.tags, Path(args.runs_dir))
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    for p in report["points"]:
        print(p)


if __name__ == "__main__":
    main()
