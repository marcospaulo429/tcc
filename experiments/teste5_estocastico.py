"""Teste 5 — Célula estocástica: executa a receita do "stochastic protocol" do paper.

PRÉ-REGISTRO (23): em 5 pontos do mt6 (3 quebras publicadas + 2 screened
selecionados pela regra declarada: maior |C_H| entre pivotais screened,
desempate por task_id), replay estocástico a temperature 0.8 com n=12
réplicas por braço (seeds 6001–6012), braços null / M (a′ do census) / HM
(fila [flip, a′]):
- (i) null spread: sd de R no braço nulo por ponto (medição, sem limiar);
- (ii) screening estocástico: D = mean(R_M) − mean(R_HM) = C_HM − C_M;
  CI95 bootstrap (10k, seed 20260824) sobre as réplicas;
- outcomes declarados: s1 = CI(D) cobre 0 nos 2/2 screened E exclui 0 em
  ≥2/3 quebras; s2 = exatamente uma das duas condições; s3 = nenhuma.

Réplicas idempotentes por (task_id, cp_index, arm, seed).
"""
import argparse
import json
import random
from pathlib import Path

from agent.llm import LLMClient
from trajectories.replay import replay_from

from .common import append_row, done_keys, load_rows, load_trajectories

BOOT_SEED = 20260824
SEEDS = list(range(6001, 6013))
# (task_id, cp_index) dos 5 pontos pré-registrados
BREAK_POINTS = [("l_log_parser", 7), ("l_vending_machine", 10), ("api_router", 0)]
SCREENED_POINTS = [("c_temp_label", 0), ("csv_normalizer", 0)]
FLIP = {"keep_context": "summarize_context", "summarize_context": "keep_context"}


def sanitize(action: dict) -> dict:
    return {k: v for k, v in action.items() if k != "forced"}


def load_point_specs(census_dir: Path) -> list[dict]:
    cf = {(r["task_id"], r["cp_index"]): r
          for r in load_rows(census_dir / "cf_results.jsonl")}
    samples = {(r["task_id"], r["cp_index"]): r
               for r in load_rows(census_dir / "samples.jsonl")}
    specs = []
    for kind, pts in (("break", BREAK_POINTS), ("screened", SCREENED_POINTS)):
        for key in pts:
            r, s = cf[key], samples[key]
            assert s["sample"]["found"]
            specs.append({"kind": kind, "task_id": key[0], "cp_index": key[1],
                          "index": r["index"], "direction": r["direction"],
                          "a_prime": s["sample"]["action"],
                          "original_action": sanitize(s["original_action"]),
                          "r_orig": r["r_orig"],
                          "det": {"C_M": r["C_M"], "C_HM": r["C_HM"]}})
    return specs


def run_replicates(baseline_dir: Path, out: Path, specs: list[dict]):
    results = out / "results.jsonl"
    done = done_keys(load_rows(results), ("task_id", "cp_index", "arm", "seed"))
    trajs = {t.task_id: t for t in load_trajectories(baseline_dir)}
    for spec in specs:
        traj = trajs[spec["task_id"]]
        cp = next(d for d in traj.decisions if d.index == spec["cp_index"])
        cp_orig = sanitize(cp.chosen_action)
        cp_flip = {"action": FLIP[cp_orig["action"]]}
        arms = {
            "null": (spec["cp_index"], [{"point": "context_policy", "action": cp_orig},
                                        {"point": "tool_call", "action": spec["original_action"]}]),
            "m": (spec["cp_index"], [{"point": "context_policy", "action": cp_orig},
                                     {"point": "tool_call", "action": spec["a_prime"]}]),
            "hm": (spec["cp_index"], [{"point": "context_policy", "action": cp_flip},
                                      {"point": "tool_call", "action": spec["a_prime"]}]),
        }
        for arm, (start, queue) in arms.items():
            for seed in SEEDS:
                if (spec["task_id"], spec["cp_index"], arm, seed) in done:
                    continue
                llm = LLMClient(temperature=0.8, seed=seed, max_tokens=1200)
                r = replay_from(traj, start, llm, out / "replays",
                                override_actions=queue)
                append_row(results, {
                    "task_id": spec["task_id"], "cp_index": spec["cp_index"],
                    "kind": spec["kind"], "arm": arm, "seed": seed,
                    "r_orig": spec["r_orig"], "reward": r["reward"],
                    "final_timed_out": r["final_timed_out"],
                    "replay_traj": r["trajectory_path"]})
                print(f"[t5] {spec['task_id']} cp={spec['cp_index']} {arm} "
                      f"seed={seed} R={r['reward']:.3f}", flush=True)


def _boot_ci(a: list[float], b: list[float], rng: random.Random,
             n_boot: int = 10_000) -> list[float]:
    diffs = sorted(
        sum(rng.choices(a, k=len(a))) / len(a) - sum(rng.choices(b, k=len(b))) / len(b)
        for _ in range(n_boot))
    return [diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot)]]


def summarize(out: Path, specs: list[dict]) -> dict:
    rows = [r for r in load_rows(out / "results.jsonl")
            if not r.get("final_timed_out")]
    rng = random.Random(BOOT_SEED)
    per_point, s1_screen, s1_break = {}, [], []
    for spec in specs:
        key = (spec["task_id"], spec["cp_index"])
        arm = {a: [r["reward"] for r in rows
                   if (r["task_id"], r["cp_index"], r["arm"]) == (*key, a)]
               for a in ("null", "m", "hm")}
        mean = {a: sum(v) / len(v) for a, v in arm.items() if v}
        var = sum((x - mean["null"]) ** 2 for x in arm["null"]) / max(len(arm["null"]) - 1, 1)
        d_ci = _boot_ci(arm["m"], arm["hm"], rng)
        covers0 = d_ci[0] <= 0 <= d_ci[1]
        per_point["/".join(map(str, key))] = {
            "kind": spec["kind"], "n": {a: len(v) for a, v in arm.items()},
            "null_sd": round(var ** 0.5, 4),
            "mean_null": round(mean["null"], 4), "mean_m": round(mean["m"], 4),
            "mean_hm": round(mean["hm"], 4),
            "C_M_stoch": round(mean["null"] - mean["m"], 4),
            "C_HM_stoch": round(mean["null"] - mean["hm"], 4),
            "D_mean": round(mean["m"] - mean["hm"], 4),
            "D_ci95": [round(x, 4) for x in d_ci],
            "det": spec["det"], "screening_survives": covers0,
        }
        (s1_screen if spec["kind"] == "screened" else s1_break).append(
            covers0 if spec["kind"] == "screened" else not covers0)
    cond_screen = all(s1_screen) and len(s1_screen) == 2
    cond_break = sum(s1_break) >= 2
    outcome = "s1" if (cond_screen and cond_break) else \
              "s2" if (cond_screen or cond_break) else "s3"
    summary = {"pre_registro": 23, "per_point": per_point,
               "cond_screened_2de2": cond_screen,
               "cond_breaks_2de3": cond_break, "outcome": outcome}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="runs/teste0_mt6/baseline")
    ap.add_argument("--census", default="runs/teste3_mt6")
    ap.add_argument("--out", default="runs/teste5_estocastico")
    args = ap.parse_args()
    out = Path(args.out)
    specs = load_point_specs(Path(args.census))
    run_replicates(Path(args.baseline), out, specs)
    print(json.dumps(summarize(out, specs), indent=1, ensure_ascii=False))
