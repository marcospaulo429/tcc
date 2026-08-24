"""Anatomia descritiva dos 6 pontos de quebra raw do D5 (4B no pool curado).

Review 13 residual 4: a anatomia existente (anatomia_v4b) cobre as 6 quebras
do 8B; as do 4B só tinham assinatura de créditos. Mesmo método/formato:
0 rollouts novos, só leitura de traços já gravados (runs/teste3_q4cur_*).

Para cada ponto (task_id, cp_index, regime):
  (a) constantes críticas destruídas (ou restauradas, se o flip é
      summarize→keep) pelo braço H: contexto da baseline vs contexto visto
      pela 1ª decisão de modelo do replay H;
  (b) tipo e conteúdo do a′ (contém constantes?);
  (c) rewards dos 4 braços + primeira divergência de cada replay vs baseline;
  (d) rótulo de padrão derivado dos números, comparado com os 2 padrões do 8B
      ("resgate parcial por a′ com constantes → conjunto intermediário" vs
       "a′ benéfico anulado → conjunto volta ao original");
  (e) h_turnstile_fsm cp10 (recorrente NÃO-idêntico: I=+0.77 folga vs +0.31
      pressão): de onde vem a diferença de magnitude;
  (f) h_hotel_folio cp7 (idêntico entre regimes): identidade numérica dos 4
      braços + comparação com o cp0 do 8B na mesma task.

Uso: uv run python -m experiments.anatomia_d5
"""
from __future__ import annotations

import json
from pathlib import Path

from environment import tasks_v4
from experiments.common import load_rows, load_trajectories

REGIMES = {"q4cur_g600": "slack", "q4cur_mt6": "pressure"}
# (task_id, cp_index) -> tags onde é quebra raw (2026-08-24_d5_simetrico.json)
POINTS = [
    ("h_turnstile_fsm", 10, ["q4cur_g600", "q4cur_mt6"]),
    ("h_telco_roaming", 10, ["q4cur_g600"]),
    ("h_telco_roaming", 13, ["q4cur_g600"]),
    ("h_hotel_folio", 7, ["q4cur_g600", "q4cur_mt6"]),
]
OUT = Path("experiments/results/2026-08-24_anatomia_d5.json")
ANAT_8B = Path("experiments/results/2026-08-24_anatomia_v4b.json")

CONSTS = tasks_v4.CRITICAL_CONSTANTS

# Padrões nomeados na anatomia do 8B (para o item d)
PATTERN_8B_1 = ("resgate parcial por a′ com constantes → conjunto "
                "intermediário")
PATTERN_8B_2 = "a′ benéfico anulado → conjunto volta ao original"


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
    """Primeira decisão em que (decision_point, chosen_action) difere."""
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
    return {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v)
            for k, v in action.items()}


def arm_anatomy(traj, start_index: int, replay_path: str,
                consts: list[str]) -> dict:
    hdr, decs = load_replay(replay_path)
    suffix = [d for d in traj.decisions if d.index >= start_index]
    div = first_divergence(suffix, decs)
    div_free = first_divergence(suffix, decs, skip_forced=True)
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


def classify_vs_8b(label: str, consts_in_a_prime: list[str],
                   r_orig: float, r_m: float, r_hm: float,
                   tol=1e-9) -> str:
    """Mapeia o ponto nos 2 padrões nomeados do 8B, ou declara outro."""
    if ("conjunto intermediário" in label and consts_in_a_prime
            and "a′ sozinho destrutivo" not in label):
        return f"padrão 8B #1 ({PATTERN_8B_1})"
    if r_m - r_orig > tol and abs(r_hm - r_orig) <= tol:
        return f"padrão 8B #2 ({PATTERN_8B_2})"
    return "fora dos 2 padrões do 8B (ver d_label)"


def analyze_point(task_id: str, cp_index: int, tag: str) -> dict:
    consts = CONSTS[task_id]
    cf = next(r for r in load_rows(Path(f"runs/teste3_{tag}/cf_results.jsonl"))
              if r["task_id"] == task_id and r["cp_index"] == cp_index)
    sample = next(s for s in load_rows(Path(f"runs/teste3_{tag}/samples.jsonl"))
                  if s["task_id"] == task_id and s["cp_index"] == cp_index)
    traj = next(t for t in load_trajectories(Path(f"runs/teste0_{tag}/baseline"))
                if t.trajectory_id == cf["trajectory_id"])
    tc = next(d for d in traj.decisions if d.index == cf["index"])

    ctx_base = consts_present(
        text_of_messages(tc.state_before["messages"]), consts)
    arms = {arm: arm_anatomy(
        traj, cp_index if arm in ("h", "hm") else cf["index"],
        cf["replay_trajs"][arm], consts) for arm in ("h", "m", "hm")}
    ctx_h = arms["h"]["consts_in_ctx_first_model_decision"]

    # direção do flip decide a semântica do delta de constantes no braço H
    to_summarize = cf["direction"].endswith("summarize_context")
    if to_summarize:
        consts_delta = {"consts_destroyed": [c for c in ctx_base
                                             if c not in ctx_h]}
    else:  # summarize→keep: o flip RESTAURA o que a baseline destruiu
        consts_delta = {"consts_restored": [c for c in ctx_h
                                            if c not in ctx_base]}

    alt = sample["sample"]["action"]
    alt_text = json.dumps(alt, ensure_ascii=False)
    a_orig = sample["original_action"]
    consts_a_prime = consts_present(alt_text, consts)

    label = label_point(cf["r_orig"], cf["r_cf_h"], cf["r_cf_m"],
                        cf["r_cf_hm"])
    return {
        "task_id": task_id, "cp_index": cp_index, "tag": tag,
        "regime": REGIMES[tag], "trajectory_id": cf["trajectory_id"],
        "direction": cf["direction"], "turn": cf["turn"],
        "tc_index": cf["index"],
        "rewards": {"orig": cf["r_orig"], "h": cf["r_cf_h"],
                    "m": cf["r_cf_m"], "hm": cf["r_cf_hm"]},
        "credits": {k: cf[k] for k in ("C_H", "C_M", "C_HM", "I")},
        "saturated": cf["saturated"],
        "a_consts_flip_h": {
            "flip_to_summarize": to_summarize,
            "consts_in_ctx_baseline_tc": ctx_base,
            "consts_in_ctx_pos_flip_h": ctx_h,
            **consts_delta,
            "n_total": len(consts),
        },
        "b_a_prime": {
            "action_type": alt["action"],
            "original_action_type": a_orig["action"],
            "same_path": alt.get("path") == a_orig.get("path"),
            "consts_in_a_prime": consts_a_prime,
            "consts_in_a_orig": consts_present(
                json.dumps(a_orig, ensure_ascii=False), consts),
            "a_prime_chars": len(alt_text),
        },
        "c_arms": arms,
        "d_label": label,
        "d_padrao_vs_8b": classify_vs_8b(
            label, consts_a_prime, cf["r_orig"], cf["r_cf_m"], cf["r_cf_hm"]),
    }


def compare_regimes(pts: list[dict]) -> dict:
    a, b = pts
    keys_eq = {
        "rewards_identicos": a["rewards"] == b["rewards"],
        "labels_identicos": a["d_label"] == b["d_label"],
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
        na = a["c_arms"][arm]["n_decisions_replay_suffix"]
        nb = b["c_arms"][arm]["n_decisions_replay_suffix"]
        if na != nb:
            diffs[f"n_decisoes_{arm}"] = {a["tag"]: na, b["tag"]: nb}
    return {"iguais": keys_eq, "diferencas": diffs}


def deep_dive_turnstile(pts: list[dict]) -> dict:
    """(e) De onde vem I=+0.77 (folga) vs +0.31 (pressão)?"""
    g, m = pts  # g600, mt6
    per_arm = {}
    for arm in ("orig", "h", "m", "hm"):
        rg, rm = g["rewards"][arm], m["rewards"][arm]
        per_arm[arm] = {"g600": rg, "mt6": rm, "delta_mt6_menos_g600": rm - rg}
    changing = [a for a, v in per_arm.items()
                if abs(v["delta_mt6_menos_g600"]) > 1e-9]
    suffix_len = {t["tag"]: {arm: t["c_arms"][arm]["n_decisions_replay_suffix"]
                             for arm in ("h", "m", "hm")} for t in pts}
    baseline_suffix_len = {
        t["tag"]: t["c_arms"]["h"]["n_decisions_baseline_suffix"]
        for t in pts}
    return {
        "pergunta": "diferença de magnitude de I entre regimes vem de qual "
                    "braço/mecanismo?",
        "trajetorias_baseline_distintas":
            g["trajectory_id"] != m["trajectory_id"],
        "rewards_por_braco": per_arm,
        "bracos_que_mudam": changing,
        "I": {"g600": g["credits"]["I"], "mt6": m["credits"]["I"]},
        "decomposicao": {
            "C_H": {"g600": g["credits"]["C_H"], "mt6": m["credits"]["C_H"]},
            "C_M": {"g600": g["credits"]["C_M"], "mt6": m["credits"]["C_M"]},
            "C_HM": {"g600": g["credits"]["C_HM"],
                     "mt6": m["credits"]["C_HM"]},
        },
        "comprimento_sufixo_baseline": baseline_suffix_len,
        "comprimento_sufixo_replays": suffix_len,
        "divergencia_livre_por_braco": {
            t["tag"]: {arm: t["c_arms"][arm]["first_free_divergence"]
                       for arm in ("h", "m", "hm")} for t in pts},
    }


def deep_dive_hotel(pts: list[dict]) -> dict:
    """(f) identidade numérica entre regimes + comparação com 8B cp0."""
    g, m = pts
    identity = {
        "rewards_4_bracos_identicos": g["rewards"] == m["rewards"],
        "rewards": g["rewards"],
        "creditos_identicos": g["credits"] == m["credits"],
        "mesma_trajetoria_baseline": g["trajectory_id"] == m["trajectory_id"],
        "trajectory_ids": {g["tag"]: g["trajectory_id"],
                           m["tag"]: m["trajectory_id"]},
    }
    comp_8b = None
    if ANAT_8B.exists():
        d8 = json.load(open(ANAT_8B))
        p8 = next((p for p in d8["points"]
                   if p["task_id"] == "h_hotel_folio"
                   and p["tag"] == "v5cur_g600"), None)
        if p8:
            comp_8b = {
                "nota": "mesma task, pontos DIFERENTES: 8B quebra no cp0 "
                        "(turno 0), 4B no cp7 (turno 2)",
                "8b_cp0": {k: p8[k] for k in
                           ("cp_index", "turn", "direction", "rewards",
                            "credits", "d_label")},
                "8b_consts_destroyed":
                    p8["a_summarize_destroyed"]["consts_destroyed"],
                "8b_a_prime": {k: p8["b_a_prime"][k] for k in
                               ("action_type", "consts_in_a_prime")},
                "4b_cp7": {k: g[k] for k in
                           ("cp_index", "turn", "direction", "rewards",
                            "credits", "d_label")},
                "4b_consts_delta": g["a_consts_flip_h"],
                "4b_a_prime": {k: g["b_a_prime"][k] for k in
                               ("action_type", "consts_in_a_prime")},
            }
    return {"identidade_entre_regimes": identity,
            "comparacao_8b_cp0_vs_4b_cp7": comp_8b}


def main():
    results = []
    for task_id, cp_index, tags in POINTS:
        for tag in tags:
            results.append(analyze_point(task_id, cp_index, tag))

    def pick(task_id, cp_index):
        return [r for r in results
                if r["task_id"] == task_id and r["cp_index"] == cp_index]

    recurrent = {
        "h_turnstile_fsm_cp10": compare_regimes(pick("h_turnstile_fsm", 10)),
        "h_hotel_folio_cp7": compare_regimes(pick("h_hotel_folio", 7)),
    }
    e_turnstile = deep_dive_turnstile(pick("h_turnstile_fsm", 10))
    f_hotel = deep_dive_hotel(pick("h_hotel_folio", 7))

    limitations = [
        "Detecção de constantes é por substring textual no contexto/ação; "
        "não captura valores recomputados pelo modelo a partir do enunciado "
        "resumido nem constantes reescritas em outra forma.",
        "Análise descritiva post-hoc de n=6 pontos; nenhum teste estatístico, "
        "nenhuma inferência causal além dos rewards já medidos no Teste 3 "
        "(q4cur_*).",
        "Dois pontos têm flip summarize→keep (direção inversa à anatomia do "
        "8B, que era toda keep→summarize): neles o braço H RESTAURA contexto "
        "em vez de destruir, e o campo (a) reporta consts_restored.",
        "Os rótulos de padrão vs 8B são heurísticos (classify_vs_8b) sobre "
        "igualdades exatas de reward; padrões novos são declarados como "
        "'fora dos 2 padrões do 8B'.",
        "A comparação hotel 4B cp7 vs 8B cp0 usa pontos de intervenção "
        "diferentes (turnos 2 vs 0) e baselines de modelos diferentes; é "
        "mecânica descritiva, não contraste pareado.",
    ]

    out = {"date": "2026-08-24",
           "motivo": "review 13 residual 4 — anatomia das 6 quebras raw do "
                     "D5 (4B no pool curado, q4cur_*)",
           "n_rollouts_novos": 0,
           "points": results,
           "recorrentes_entre_regimes": recurrent,
           "e_turnstile_cp10_diferenca_I": e_turnstile,
           "f_hotel_cp7": f_hotel,
           "limitations": limitations}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"== Anatomia D5 — 6 quebras raw q4cur (gravado em {OUT}) ==\n")
    for r in results:
        rw = r["rewards"]
        a = r["a_consts_flip_h"]
        delta_key = ("consts_destroyed" if a["flip_to_summarize"]
                     else "consts_restored")
        print(f"{r['task_id']} cp{r['cp_index']} [{r['tag']}] "
              f"turno={r['turn']} dir={r['direction']}")
        print(f"  rewards: orig={rw['orig']:.3f} H={rw['h']:.3f} "
              f"M={rw['m']:.3f} HM={rw['hm']:.3f}  I={r['credits']['I']:+.3f}"
              f"  sat={r['saturated']}")
        print(f"  (a) flip H {delta_key}: {a[delta_key]} "
              f"(ctx_base={len(a['consts_in_ctx_baseline_tc'])}, "
              f"ctx_pos_flip={len(a['consts_in_ctx_pos_flip_h'])}, "
              f"total={a['n_total']})")
        print(f"  (b) a′: {r['b_a_prime']['original_action_type']}→"
              f"{r['b_a_prime']['action_type']} "
              f"consts_em_a′={r['b_a_prime']['consts_in_a_prime']}")
        for arm in ("h", "m", "hm"):
            c = r["c_arms"][arm]
            fd, ff = c["first_divergence"], c["first_free_divergence"]
            print(f"  (c) {arm.upper():2s}: r={c['reward']:.3f} "
                  f"diverge@+{fd['offset']} ({fd['decision_point']}); "
                  f"livre @+{ff['offset']} ({ff['decision_point']}) "
                  f"n_dec={c['n_decisions_replay_suffix']} "
                  f"(baseline_sufixo={c['n_decisions_baseline_suffix']})")
        print(f"  (d) {r['d_label']}")
        print(f"      vs 8B: {r['d_padrao_vs_8b']}\n")

    print("== (e) turnstile cp10: diferença de I entre regimes ==")
    print(json.dumps(e_turnstile, ensure_ascii=False, indent=1))
    print("\n== (f) hotel cp7: identidade + 4B vs 8B ==")
    print(json.dumps(f_hotel, ensure_ascii=False, indent=1))
    print("\n== Limitações ==")
    for l in limitations:
        print(f"- {l}")


if __name__ == "__main__":
    main()
