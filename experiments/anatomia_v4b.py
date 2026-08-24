"""Anatomia descritiva dos 6 pontos de quebra raw do screening v5cur (review 11 W2).

0 rollouts novos: só leitura de traços já gravados.
Para cada ponto (task_id, cp_index, regime) compara baseline vs replays H/M/HM:
  (a) constantes críticas destruídas pelo summarize (contexto pré vs pós-flip);
  (b) o que era a′ (tipo, se contém constantes);
  (c) primeira divergência de cada braço vs baseline, nº de decisões, rewards;
  (d) rótulo de padrão derivado dos números;
  (e) comparação entre regimes para os pontos recorrentes.

Uso: uv run python -m experiments.anatomia_v4b
"""
from __future__ import annotations

import json
from pathlib import Path

from environment import tasks_v4, tasks_v5
from experiments.common import load_rows, load_trajectories

REGIMES = {"v5cur_g600": "slack", "v5cur_mt6": "pressure"}
# (task_id, cp_index) -> regimes onde é quebra raw de screening
POINTS = [
    ("h_hotel_folio", 0, ["v5cur_g600", "v5cur_mt6"]),
    ("x_hours_bank", 3, ["v5cur_g600", "v5cur_mt6"]),
    ("h_cargo_manifest", 0, ["v5cur_g600"]),
    ("h_sku_validator", 0, ["v5cur_mt6"]),
]
OUT = Path("experiments/results/2026-08-24_anatomia_v4b.json")

CONSTS = {**tasks_v4.CRITICAL_CONSTANTS, **tasks_v5.CRITICAL_CONSTANTS}


def consts_of(task_id: str) -> list[str]:
    return CONSTS[task_id]


def text_of_messages(messages: list[dict]) -> str:
    return "\n".join(m.get("content") or "" for m in messages)


def consts_present(text: str, consts: list[str]) -> list[str]:
    return [c for c in consts if c.strip("'\"") in text]


def sanitize(action: dict) -> dict:
    return {k: v for k, v in (action or {}).items() if k != "forced"}


def load_replay(path: str) -> tuple[dict, list[dict]]:
    lines = [json.loads(l) for l in open(path)]
    return lines[0], lines[1:]


def first_divergence(baseline_suffix: list, replay_decisions: list[dict],
                     skip_forced: bool = False) -> dict:
    """Primeira decisão em que (decision_point, chosen_action) difere.

    baseline_suffix: objetos Decision; replay_decisions: dicts do JSONL.
    Offset relativo ao ponto de partida do replay (0 = a intervenção).
    skip_forced=True ignora as próprias ações forçadas (divergência LIVRE:
    primeira escolha da política que diverge após a intervenção)."""
    n = min(len(baseline_suffix), len(replay_decisions))
    for k in range(n):
        b, r = baseline_suffix[k], replay_decisions[k]
        if skip_forced and (r["chosen_action"] or {}).get("forced"):
            continue
        if b.decision_point != r["decision_point"] or \
                sanitize(b.chosen_action) != sanitize(r["chosen_action"]):
            return {"offset": k, "decision_point": r["decision_point"],
                    "baseline_action": _brief(sanitize(b.chosen_action)),
                    "replay_action": _brief(sanitize(r["chosen_action"]))}
    if len(baseline_suffix) != len(replay_decisions):
        return {"offset": n, "decision_point": "(comprimento difere)",
                "baseline_action": None, "replay_action": None}
    return {"offset": None, "decision_point": None,
            "baseline_action": None, "replay_action": None}


def _brief(action: dict) -> dict:
    """Trunca campos longos para o JSON de saída ficar legível."""
    return {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v)
            for k, v in action.items()}


def arm_anatomy(traj, start_index: int, replay_path: str, consts: list[str]) -> dict:
    hdr, decs = load_replay(replay_path)
    suffix = [d for d in traj.decisions if d.index >= start_index]
    div = first_divergence(suffix, decs)
    div_free = first_divergence(suffix, decs, skip_forced=True)
    # contexto visto pela primeira decisão de modelo do replay (pós-intervenção)
    first_model = next((d for d in decs if d["decision_type"] == "model"), None)
    ctx_consts = consts_present(
        text_of_messages(first_model["state_before"]["messages"]), consts) \
        if first_model else []
    return {
        "replay_path": replay_path,
        "reward": hdr["final_reward"],
        "n_decisions_replay_suffix": len(decs),
        "n_decisions_baseline_suffix": len(suffix),
        "first_divergence": div,
        "first_free_divergence": div_free,
        "consts_in_ctx_first_model_decision": ctx_consts,
    }


def label_point(r_orig, r_h, r_m, r_hm, tol=1e-9) -> str:
    """Rótulo mecânico a partir dos rewards por braço."""
    dh, dm, dhm = r_h - r_orig, r_m - r_orig, r_hm - r_orig
    parts = []
    parts.append("H-flip destrutivo" if dh < -tol else
                 "H-flip benéfico" if dh > tol else "H-flip neutro")
    parts.append("a′ sozinho destrutivo" if dm < -tol else
                 "a′ sozinho benéfico" if dm > tol else "a′ sozinho neutro")
    if abs(r_hm - r_h) <= tol:
        parts.append("conjunto rastreia H")
    elif abs(r_hm - r_m) <= tol:
        parts.append("conjunto rastreia M")
    elif abs(r_hm - r_orig) <= tol:
        parts.append("conjunto volta ao original")
    else:
        parts.append("conjunto intermediário (não rastreia nenhum braço)")
    return "; ".join(parts)


def analyze_point(task_id: str, cp_index: int, tag: str) -> dict:
    consts = consts_of(task_id)
    cf = next(r for r in load_rows(Path(f"runs/teste3_{tag}/cf_results.jsonl"))
              if r["task_id"] == task_id and r["cp_index"] == cp_index)
    sample = next(s for s in load_rows(Path(f"runs/teste3_{tag}/samples.jsonl"))
                  if s["task_id"] == task_id and s["cp_index"] == cp_index)
    traj = next(t for t in load_trajectories(Path(f"runs/teste0_{tag}/baseline"))
                if t.trajectory_id == cf["trajectory_id"])
    cp = next(d for d in traj.decisions if d.index == cp_index)
    tc = next(d for d in traj.decisions if d.index == cf["index"])

    # (a) o que o summarize destruiu: constantes no contexto do tool_call da
    # baseline vs contexto pós-summarize visto pelo modelo no replay H
    ctx_base = consts_present(
        text_of_messages(tc.state_before["messages"]), consts)
    arms = {arm: arm_anatomy(
        traj, cp_index if arm in ("h", "hm") else cf["index"],
        cf["replay_trajs"][arm], consts) for arm in ("h", "m", "hm")}
    ctx_h = arms["h"]["consts_in_ctx_first_model_decision"]
    destroyed = [c for c in ctx_base if c not in ctx_h]

    # (b) a′
    alt = sample["sample"]["action"]
    alt_text = json.dumps(alt, ensure_ascii=False)
    a_orig = sample["original_action"]

    return {
        "task_id": task_id, "cp_index": cp_index, "tag": tag,
        "regime": REGIMES[tag], "trajectory_id": cf["trajectory_id"],
        "direction": cf["direction"], "turn": cf["turn"],
        "tc_index": cf["index"],
        "rewards": {"orig": cf["r_orig"], "h": cf["r_cf_h"],
                    "m": cf["r_cf_m"], "hm": cf["r_cf_hm"]},
        "credits": {k: cf[k] for k in ("C_H", "C_M", "C_HM", "I")},
        "saturated": cf["saturated"],
        "a_summarize_destroyed": {
            "consts_in_ctx_baseline_tc": ctx_base,
            "consts_in_ctx_pos_summarize_h": ctx_h,
            "consts_destroyed": destroyed,
            "n_destroyed": len(destroyed), "n_total": len(consts),
        },
        "b_a_prime": {
            "action_type": alt["action"],
            "original_action_type": a_orig["action"],
            "same_path": alt.get("path") == a_orig.get("path"),
            "consts_in_a_prime": consts_present(alt_text, consts),
            "consts_in_a_orig": consts_present(
                json.dumps(a_orig, ensure_ascii=False), consts),
            "a_prime_chars": len(alt_text),
        },
        "c_arms": arms,
        "d_label": label_point(cf["r_orig"], cf["r_cf_h"], cf["r_cf_m"],
                               cf["r_cf_hm"]),
    }


def compare_regimes(pts: list[dict]) -> dict:
    a, b = pts
    keys_eq = {
        "rewards_identicos": a["rewards"] == b["rewards"],
        "labels_identicos": a["d_label"] == b["d_label"],
        "consts_destruidas_identicas":
            a["a_summarize_destroyed"]["consts_destroyed"]
            == b["a_summarize_destroyed"]["consts_destroyed"],
        "a_prime_mesmo_tipo":
            a["b_a_prime"]["action_type"] == b["b_a_prime"]["action_type"],
        "mesma_trajetoria_baseline":
            a["trajectory_id"] == b["trajectory_id"],
    }
    diffs = {}
    for field in ("rewards", "d_label"):
        if a[field] != b[field]:
            diffs[field] = {a["tag"]: a[field], b["tag"]: b[field]}
    for arm in ("h", "m", "hm"):
        da = a["c_arms"][arm]["first_free_divergence"]["offset"]
        db = b["c_arms"][arm]["first_free_divergence"]["offset"]
        if da != db:
            diffs[f"divergencia_livre_{arm}"] = {a["tag"]: da, b["tag"]: db}
    return {"iguais": keys_eq, "diferencas": diffs}


def main():
    results, limitations = [], []
    for task_id, cp_index, tags in POINTS:
        for tag in tags:
            results.append(analyze_point(task_id, cp_index, tag))

    recurrent = {}
    for task_id, cp_index, tags in POINTS:
        if len(tags) == 2:
            pts = [r for r in results
                   if r["task_id"] == task_id and r["cp_index"] == cp_index]
            recurrent[f"{task_id}_cp{cp_index}"] = compare_regimes(pts)

    limitations.append(
        "Replays contrafactuais ESTÃO armazenados (sufixo a partir do ponto de "
        "intervenção); a anatomia usa as trajetórias completas de cada braço.")
    limitations.append(
        "Detecção de constantes é por substring textual no contexto/ação; "
        "não captura valores recomputados pelo modelo a partir do enunciado "
        "resumido nem constantes reescritas em outra forma (ex.: 0.0685 vs 6.85%).")
    limitations.append(
        "Análise descritiva post-hoc de n=6 pontos; nenhum teste estatístico, "
        "nenhuma inferência causal além dos rewards já medidos no Teste 3.")

    out = {"date": "2026-08-24", "motivo": "review 11 W2 — anatomia das 6 "
           "quebras raw de screening do pool curado", "n_rollouts_novos": 0,
           "points": results, "recorrentes_entre_regimes": recurrent,
           "limitations": limitations}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"== Anatomia v4b — 6 quebras raw v5cur (gravado em {OUT}) ==\n")
    for r in results:
        rw = r["rewards"]
        d = r["a_summarize_destroyed"]
        print(f"{r['task_id']} cp{r['cp_index']} [{r['tag']}] turno={r['turn']}")
        print(f"  rewards: orig={rw['orig']:.3f} H={rw['h']:.3f} "
              f"M={rw['m']:.3f} HM={rw['hm']:.3f}  I={r['credits']['I']:+.3f}"
              f"  sat={r['saturated']}")
        print(f"  (a) summarize destruiu {d['n_destroyed']}/{len(d['consts_in_ctx_baseline_tc'])} "
              f"consts no ctx: {d['consts_destroyed']}")
        print(f"  (b) a′: {r['b_a_prime']['original_action_type']}→"
              f"{r['b_a_prime']['action_type']} "
              f"consts_em_a′={r['b_a_prime']['consts_in_a_prime']}")
        for arm in ("h", "m", "hm"):
            a = r["c_arms"][arm]
            fd, ff = a["first_divergence"], a["first_free_divergence"]
            print(f"  (c) {arm.upper():2s}: r={a['reward']:.3f} "
                  f"diverge@+{fd['offset']} ({fd['decision_point']}); "
                  f"1ª divergência LIVRE @+{ff['offset']} "
                  f"({ff['decision_point']}) "
                  f"n_dec={a['n_decisions_replay_suffix']} "
                  f"(baseline_sufixo={a['n_decisions_baseline_suffix']})")
        print(f"  (d) {r['d_label']}\n")
    print("== Recorrentes entre regimes ==")
    for k, v in recurrent.items():
        print(f"{k}: iguais={v['iguais']}")
        if v["diferencas"]:
            print(f"  diferenças: {json.dumps(v['diferencas'], ensure_ascii=False)}")
    print("\n== Limitações ==")
    for l in limitations:
        print(f"- {l}")


if __name__ == "__main__":
    main()
