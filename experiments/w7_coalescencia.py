"""W7 — Verificação de coalescência de trace (review 7, W-2).

Pergunta: em quantos dos pontos blindados (screened & C_H != 0) a hipótese do
Lema 1 — existe k >= t com estado (messages, workspace) idêntico nos ramos
B_M = do(a') e B_HM = do(h', a') — de fato ocorre nos traces gravados?

Também mede a versão comportamental (sufixos de (ação, observação) idênticos
até a terminação), que é consequência necessária da coalescência estrita e
suficiente para igualdade de R quando as observações finais coincidem.

Saída: experiments/results/2026-08-23_w7_coalescencia.json
Custo: 0 rollouts (análise offline de JSONLs existentes).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ["teste3_g450", "teste3_g600", "teste3_g900", "teste3_mt6"]
OUT = ROOT / "experiments" / "results" / "2026-08-23_w7_coalescencia.json"

HEX_ADDR = re.compile(r"0x[0-9a-fA-F]+")
SANDBOX_DIR = re.compile(r"sandbox_[A-Za-z0-9]+")


def norm(obj) -> str:
    """Serializa normalizando identificadores não-semânticos que vazam em
    outputs de teste: endereços de memória (ASLR) e nomes de diretório
    temporário do sandbox."""
    s = json.dumps(obj, sort_keys=True)
    return SANDBOX_DIR.sub("sandbox_X", HEX_ADDR.sub("0xADDR", s))


def load_model_steps(trace_path: str):
    """Extrai a sequência de decisões do modelo de um trace de replay."""
    steps = []
    final_reward = None
    for line in open(ROOT / trace_path):
        d = json.loads(line)
        if d.get("kind") == "trajectory":
            final_reward = d.get("final_reward")
        elif d.get("kind") == "decision" and d.get("decision_type") == "model":
            sb = d["state_before"]
            steps.append(
                {
                    "turn": sb.get("turn"),
                    "state": norm(
                        {"messages": sb.get("messages"), "workspace": sb.get("workspace")}
                    ),
                    "behavior": norm(
                        {"action": d.get("chosen_action"), "obs": d.get("observation")}
                    ),
                }
            )
    return steps, final_reward


def analyze_point(rec):
    """Compara os ramos m e hm de um ponto de interação."""
    m_steps, m_r = load_model_steps(rec["replay_trajs"]["m"])
    hm_steps, hm_r = load_model_steps(rec["replay_trajs"]["hm"])

    m_by_turn = {s["turn"]: s for s in m_steps}
    hm_by_turn = {s["turn"]: s for s in hm_steps}
    common = sorted(set(m_by_turn) & set(hm_by_turn))
    t0 = rec["turn"]

    # Coalescência estrita: primeiro turno k >= t0 com estado idêntico.
    strict_k = None
    for k in common:
        if k >= t0 and m_by_turn[k]["state"] == hm_by_turn[k]["state"]:
            strict_k = k
            break

    # Coalescência comportamental: menor k tal que os dois ramos têm o mesmo
    # conjunto de turnos >= k e (ação, observação) idênticos em todos eles.
    m_turns = sorted(m_by_turn)
    hm_turns = sorted(hm_by_turn)
    behav_k = None
    for k in sorted(set(m_turns) | set(hm_turns)):
        if k < t0:
            continue
        mt = [t for t in m_turns if t >= k]
        ht = [t for t in hm_turns if t >= k]
        if mt and mt == ht and all(
            m_by_turn[t]["behavior"] == hm_by_turn[t]["behavior"] for t in mt
        ):
            behav_k = k
            break

    # Sanidade: se coalescência estrita em k, sufixos devem ser idênticos
    # (determinismo). Uma violação falsificaria a premissa.
    suffix_ok = None
    if strict_k is not None:
        mt = [t for t in m_turns if t >= strict_k]
        ht = [t for t in hm_turns if t >= strict_k]
        suffix_ok = mt == ht and all(
            m_by_turn[t]["state"] == hm_by_turn[t]["state"]
            and m_by_turn[t]["behavior"] == hm_by_turn[t]["behavior"]
            for t in mt
        )

    return {
        "task_id": rec["task_id"],
        "cp_index": rec["cp_index"],
        "turn": t0,
        "C_H": rec["C_H"],
        "saturated": rec["saturated"],
        "r_m": m_r,
        "r_hm": hm_r,
        "strict_coalescence_turn": strict_k,
        "strict_depth": None if strict_k is None else strict_k - t0,
        "behavioral_coalescence_turn": behav_k,
        "behavioral_depth": None if behav_k is None else behav_k - t0,
        "suffix_deterministic_ok": suffix_ok,
        "len_m": len(m_steps),
        "len_hm": len(hm_steps),
    }


def main():
    screened, shielded = [], []
    for cfg in CONFIGS:
        for line in open(ROOT / "runs" / cfg / "cf_results.jsonl"):
            rec = json.loads(line)
            rec["_config"] = cfg
            if rec["C_HM"] == rec["C_M"]:
                screened.append(rec)
                if rec["C_H"] != 0:
                    shielded.append(rec)

    print(f"screened: {len(screened)}  shielded: {len(shielded)}")
    assert len(screened) == 75 and len(shielded) == 52, "contagens divergem do paper"

    results = {"shielded": [], "screened_unshielded": []}
    for rec in shielded:
        r = analyze_point(rec)
        r["config"] = rec["_config"]
        results["shielded"].append(r)
    for rec in screened:
        if rec["C_H"] == 0:
            r = analyze_point(rec)
            r["config"] = rec["_config"]
            results["screened_unshielded"].append(r)

    def summarize(pts):
        strict = [p for p in pts if p["strict_coalescence_turn"] is not None]
        behav = [p for p in pts if p["behavioral_coalescence_turn"] is not None]
        depths = sorted(p["strict_depth"] for p in strict)
        bdepths = sorted(p["behavioral_depth"] for p in behav)
        bad_suffix = [p for p in strict if p["suffix_deterministic_ok"] is False]
        return {
            "n": len(pts),
            "strict_coalescence": len(strict),
            "behavioral_coalescence": len(behav),
            "strict_depth_median": depths[len(depths) // 2] if depths else None,
            "strict_depths": depths,
            "behavioral_depth_median": bdepths[len(bdepths) // 2] if bdepths else None,
            "behavioral_depths": bdepths,
            "suffix_determinism_violations": len(bad_suffix),
            "no_coalescence_points": [
                {k: p[k] for k in ("task_id", "cp_index", "config", "r_m", "r_hm", "saturated")}
                for p in pts
                if p["behavioral_coalescence_turn"] is None
            ],
        }

    summary = {
        "shielded": summarize(results["shielded"]),
        "screened_unshielded": summarize(results["screened_unshielded"]),
    }
    out = {"summary": summary, "points": results}
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"escrito em {OUT}")


if __name__ == "__main__":
    main()
