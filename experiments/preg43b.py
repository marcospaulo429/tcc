"""Adendo 43b — escritas no RAMO Ha (replay gravado), não no episódio original.

Para cada ponto pivotal (C_H != 0) do pool headline (V1 folga + ext4b) e do 8B
com H_w >= 1 no episódio original, lê a trajetória do replay Ha (replay_traj),
localiza a ação original forçada em j (última decisão model com forced=True) e
conta write_file / tool_calls no sufixo AO VIVO. Também reporta o estrato
H_w = 0. Descritivo; zero rollouts. Saída: runs/preg43/adendo_43b.json.
"""
import json
from pathlib import Path

from experiments.common import load_rows
from experiments.preg43 import _h_write_env, _trajs_v1
from trajectories.schema import load_trajectory

V1_FOLGA = ("g450", "g600", "g900")
EXT4B = ("mbpp_g600", "mbpp_mt6", "he_g600", "he_mt6")
Q8 = ("q8_g600", "q8_mt4", "q8_mt6")


def _suffix_ha(path: str) -> dict:
    t = load_trajectory(path)
    forced = [i for i, d in enumerate(t.decisions)
              if d.decision_type == "model" and d.chosen_action.get("forced")]
    assert forced, path
    k = forced[-1]
    suf = [d for d in t.decisions[k + 1:] if d.decision_type == "model"]
    acts = [d.chosen_action.get("action") for d in suf]
    return {"Hw_Ha": sum(a == "write_file" for a in acts),
            "T_Ha": sum(a != "finish" for a in acts), "acoes_Ha": acts}


def _pontos(rows: list[dict], cache: dict) -> list[dict]:
    out = []
    for r in rows:
        cfg = r["cfg"]
        cache.setdefault(cfg, _trajs_v1(cfg))
        traj = cache[cfg][r["trajectory_id"]]
        hw, _ = _h_write_env(traj, r["index"])
        p = {"cfg": cfg, "task_id": r["task_id"], "cp_index": r["cp_index"],
             "nde0": r["C_Ha"] == 0, "H_w": hw, **_suffix_ha(r["replay_traj"])}
        out.append(p)
    return out


def _resumo(pontos: list[dict]) -> dict:
    def _k(sel):
        return {"n": len(sel), "nde0": sum(p["nde0"] for p in sel)}
    ge1 = [p for p in pontos if p["H_w"] >= 1]
    eq0 = [p for p in pontos if p["H_w"] == 0]
    return {
        "Hw_ge1": {**_k(ge1),
                   "HwHa_ge1": _k([p for p in ge1 if p["Hw_Ha"] >= 1]),
                   "HwHa_0": _k([p for p in ge1 if p["Hw_Ha"] == 0]),
                   "mediadores_com_HwHa_ge1": sum(p["nde0"] and p["Hw_Ha"] >= 1 for p in ge1),
                   "T_Ha_mediana": sorted(p["T_Ha"] for p in ge1)[len(ge1) // 2] if ge1 else None},
        "Hw_0": {**_k(eq0),
                 "HwHa_ge1": _k([p for p in eq0 if p["Hw_Ha"] >= 1])},
    }


def main():
    v1 = [r for r in load_rows(Path("runs/preg40/v1_rows.jsonl"))
          if r["C_H"] != 0 and r["cfg"] in V1_FOLGA]
    r42 = load_rows(Path("runs/preg42/rows.jsonl"))
    ext = [r for r in r42 if r["cfg"] in EXT4B and r["pivotal"] and r["screened"]]
    q8 = [r for r in r42 if r["cfg"] in Q8 and r["pivotal"]]
    cache: dict = {}
    pop = {"v1_folga": _pontos(v1, cache), "ext4b": _pontos(ext, cache),
           "q8": _pontos(q8, cache)}
    pop["pool_headline"] = pop["v1_folga"] + pop["ext4b"]
    assert len(pop["v1_folga"]) == 37 and len(pop["ext4b"]) == 49 and len(pop["q8"]) == 74
    report = {"adendo": "43b", "populacoes": {k: _resumo(v) for k, v in pop.items()},
              "pontos_Hw_ge1": {k: [p for p in v if p["H_w"] >= 1] for k, v in pop.items()
                                if k != "pool_headline"}}
    Path("runs/preg43/adendo_43b.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report["populacoes"], indent=2))


if __name__ == "__main__":
    main()
