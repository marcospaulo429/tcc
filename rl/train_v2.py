"""Treino REINFORCE da context_policy no harness V2 (mini-SWE) — espelho de rl/train_c1.py.

Braços idênticos ao V1: outcome (R_eff − baseline), ch (crédito C_H por replay),
chm_cm (crédito marginal C_HM − C_M, 2 replays + amostragem de a′ via
interventions.model_v2.sample_alternative_v2), zero (controle: crédito 0, θ congelado).

Diferenças V2:
- política LogisticContextPolicyV2 (φ com tokens normalizados pelo threshold da config);
- contadores da política reconstruídos das ações do protocolo V2: write_file (só quando
  a escrita ocorre de fato, obs.ok) e testes por AMBOS os caminhos — ação run_tests do
  modelo E auto_tests do test_schedule aninhado no write_file;
- parada dual: budget_calls OU max_episodes, o que vier primeiro (summary registra
  stopped_by) — contabilidade dose-matched E episode-matched desde o nascimento.

Contabilidade de orçamento e de tokens do crédito: idênticas ao V1 (toda chamada LLM
conta; R_eff do replay = prefixo original pago + tokens do replay-traj).
"""
import argparse
import importlib
import json
import math
import random
from pathlib import Path

import openai

from agent.harness_v2 import HarnessV2
from agent.loop_v2 import EpisodeV2
from environment.registry import resolve_task
from environment.sandbox import Sandbox
from interventions.model_v2 import sample_alternative_v2
from trajectories.recorder import Recorder
from trajectories.schema import Trajectory, load_trajectory

from .policy_v2 import CENTER_V2, N_FEATURES, LogisticContextPolicyV2
from .train_c1 import (CountingLLM, _append_flush, _canonical_tool_action,  # noqa: F401
                       _ensure_counting, _prompt_tokens, load_task_split, r_eff)


class PolicyEpisodeV2(EpisodeV2):
    """EpisodeV2 que injeta turn/tests_passed_frac/n_writes na política via
    set_turn_state() antes de cada decisão de context_policy, sem tocar agent.loop_v2."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._n_writes = 0
        self._tests_passed_frac = 0.0

    def _update_counters(self, action: dict, obs: dict | None) -> None:
        """Regra única (vale ao vivo e na reconstrução de prefixo): write conta quando
        a escrita ocorreu (obs.ok); testes vêm de run_tests OU de auto_tests do write."""
        obs = obs or {}
        tests = None
        if action.get("action") == "write_file" and obs.get("ok"):
            self._n_writes += 1
            tests = obs.get("auto_tests")
        elif action.get("action") == "run_tests":
            tests = obs
        if tests and tests.get("total"):
            self._tests_passed_frac = tests["passed"] / tests["total"]

    def _apply_model_action(self, action, messages):
        obs = super()._apply_model_action(action, messages)
        self._update_counters(action, obs)
        return obs

    def _step_context_policy(self, messages, turn):
        if hasattr(self.harness, "set_turn_state"):
            self.harness.set_turn_state(turn, self._tests_passed_frac, self._n_writes)
        return super()._step_context_policy(messages, turn)


class _TokenTally:
    """Embrulha o CountingLLM só para acumular prompt_tokens pagos — quando o
    episódio morre em overflow de contexto (emenda 32a), sabemos o custo até ali."""

    def __init__(self, llm):
        self._llm = llm
        self.prompt_tokens = 0

    def config(self) -> dict:
        return self._llm.config()

    def chat(self, messages, **kw) -> dict:
        resp = self._llm.chat(messages, **kw)
        self.prompt_tokens += resp.get("prompt_tokens", 0)
        return resp


# -- coleta ------------------------------------------------------------------

def collect_episode(task: dict, llm, policy: LogisticContextPolicyV2, out_dir,
                    episode_seed: int, lambda_cost: float = 1.0) -> dict:
    llm = _ensure_counting(llm)
    policy.reseed(episode_seed)
    policy.decision_log = []
    calls0 = llm.call_count
    tally = _TokenTally(llm)
    ep = PolicyEpisodeV2(task, tally, policy, Recorder(out_dir))
    try:
        result = ep.run()
    except openai.BadRequestError:
        # emenda 32a: overflow de contexto = episódio FALHO, R=0, paga o que pagou
        return {"trajectory": None, "R": 0.0,
                "R_eff": r_eff(0.0, tally.prompt_tokens, lambda_cost),
                "llm_calls": llm.call_count - calls0,
                "prompt_tokens_total": tally.prompt_tokens,
                "cp_points": [{"index": None, **log} for log in policy.decision_log],
                "context_overflow": True}
    finally:
        ep.sandbox.cleanup()
    traj = load_trajectory(result["trajectory_path"])
    tokens = _prompt_tokens(traj.decisions)
    cp_idx = [d.index for d in traj.decisions if d.decision_point == "context_policy"]
    assert len(cp_idx) == len(policy.decision_log), \
        "decision_log da política dessincronizado das decisões cp da trajetória"
    cp_points = [{"index": i, **log} for i, log in zip(cp_idx, policy.decision_log)]
    return {"trajectory": result["trajectory_path"], "R": result["reward"],
            "R_eff": r_eff(result["reward"], tokens, lambda_cost),
            "llm_calls": llm.call_count - calls0,
            "prompt_tokens_total": tokens, "cp_points": cp_points}


# -- crédito counterfactual ---------------------------------------------------

def _replay_with_policy(traj: Trajectory, index: int, llm, harness, out_dir,
                        override_actions: list[dict]) -> tuple[dict, int]:
    """Espelho de trajectories.replay.replay_from (ramo V2) com harness injetável.

    Contadores da política (n_writes, tests_passed_frac) são reconstruídos do prefixo
    original com a MESMA regra do episódio ao vivo (_update_counters), para que φ no
    replay reflita o histórico real. Retorna (result, prompt_tokens do replay-traj).
    """
    d = traj.decisions[index]
    if d.decision_point not in EpisodeV2.PHASES:
        raise NotImplementedError(f"replay a partir de '{d.decision_point}' não suportado")
    assert override_actions[0]["point"] == d.decision_point

    sandbox = Sandbox()
    sandbox.restore(d.state_before["workspace"])
    tally = _TokenTally(llm)
    episode = PolicyEpisodeV2(resolve_task(traj.task_id), tally, harness,
                              Recorder(out_dir), sandbox)
    for dd in traj.decisions[:index]:
        if dd.decision_point == "tool_call":
            episode._update_counters(dd.chosen_action, dd.observation)
    try:
        result = episode.run(resume={
            "messages": d.state_before["messages"],
            "turn": d.state_before["turn"],
            "entry_point": d.decision_point,
            "forced_action": None,
            "forced_actions": override_actions,
            "last_action": d.state_before.get("last_action"),
            "tests_passed": d.state_before.get("tests_passed", False),
        })
    except openai.BadRequestError:
        # emenda 32a: o flip causou o estouro → consequência causal, R=0 do replay
        return {"reward": 0.0, "context_overflow": True}, tally.prompt_tokens
    finally:
        sandbox.cleanup()
    rtraj = load_trajectory(result["trajectory_path"])
    return result, _prompt_tokens(rtraj.decisions)


def credit_for_point(traj: Trajectory, cp_decision, llm, policy_greedy, arm: str,
                     out_dir, lambda_cost: float = 1.0) -> dict:
    llm = _ensure_counting(llm)
    calls0 = llm.call_count
    index = cp_decision.index
    orig = cp_decision.chosen_action["action"]
    flip = "keep_context" if orig == "summarize_context" else "summarize_context"
    r_eff_orig = r_eff(traj.final_reward, _prompt_tokens(traj.decisions), lambda_cost)

    def _replay_reff(from_index: int, overrides: list[dict]) -> float:
        res, rtok = _replay_with_policy(traj, from_index, llm, policy_greedy,
                                        out_dir, overrides)
        prefix = _prompt_tokens(traj.decisions[:from_index])
        return r_eff(res["reward"], prefix + rtok, lambda_cost)

    def _ch() -> dict:
        reff_flip = _replay_reff(index, [{"point": "context_policy",
                                          "action": {"action": flip}}])
        return {"credit": r_eff_orig - reff_flip, "index": index,
                "llm_calls": llm.call_count - calls0}

    if arm == "ch":
        return {**_ch(), "arm": "ch"}
    if arm != "chm_cm":
        raise ValueError(f"arm desconhecido: {arm}")

    # tool_call do MESMO turno = próximo tool_call após o ponto cp
    turn = cp_decision.state_before["turn"]
    tool = next((d for d in traj.decisions[index + 1:]
                 if d.decision_point == "tool_call"
                 and d.state_before["turn"] == turn), None)
    if tool is None:
        return {**_ch(), "arm": "chm_cm", "fallback": True,
                "fallback_reason": "sem tool_call no turno"}

    orig_tool = _canonical_tool_action(tool)
    samp = sample_alternative_v2(llm, tool.state_before["messages"], orig_tool)
    if not samp["found"]:
        # sem evidência de mediação → C_H; custo da amostragem já contado no llm
        return {**_ch(), "arm": "chm_cm", "fallback": True,
                "fallback_reason": "a_prime não encontrado",
                "n_tried": samp["n_tried"]}

    a_prime = samp["action"]
    reff_hm = _replay_reff(index, [
        {"point": "context_policy", "action": {"action": flip}},
        {"point": "tool_call", "action": a_prime}])
    reff_m = _replay_reff(tool.index, [{"point": "tool_call", "action": a_prime}])
    c_hm = r_eff_orig - reff_hm
    c_m = r_eff_orig - reff_m
    return {"credit": c_hm - c_m, "c_hm": c_hm, "c_m": c_m, "index": index,
            "a_prime_seed": samp["seed"], "arm": "chm_cm", "fallback": False,
            "llm_calls": llm.call_count - calls0}


# -- treino / avaliação / calibração ------------------------------------------

def train(tasks: list[dict], llm, arm: str, budget_calls: int, seed: int, out_dir,
          lambda_cost: float = 1.0, k_credit: int = 2, lr: float = 0.5,
          clip_norm: float = 0.0, center: list[float] | None = None,
          max_episodes: int | None = None,
          harness_kw: dict | None = None) -> dict:
    if arm not in ("outcome", "ch", "chm_cm", "zero"):
        raise ValueError(f"arm desconhecido: {arm}")
    out_dir = Path(out_dir)
    llm = _ensure_counting(llm)
    hkw = dict(harness_kw or {})
    theta = [0.0] * N_FEATURES
    baseline = 0.0  # média móvel de R_eff (beta=0.9), inicia em 0
    beta = 0.9
    log_path = out_dir / "train_log.jsonl"
    episode_idx = 0
    while llm.call_count < budget_calls and \
            (max_episodes is None or episode_idx < max_episodes):
        task = tasks[episode_idx % len(tasks)]
        episode_seed = seed * 100003 + episode_idx
        policy = LogisticContextPolicyV2(theta=theta, rng_seed=episode_seed,
                                         greedy=False, center=center, **hkw)
        ep = collect_episode(task, llm, policy, out_dir / "episodes",
                             episode_seed, lambda_cost)
        grad_sum = [0.0] * N_FEATURES
        credits: list[dict] = []
        if arm == "zero":
            pass  # controle: crédito 0 em todo ponto → grad_sum fica nulo, θ congelado
        elif arm == "outcome":
            adv = ep["R_eff"] - baseline
            for pt in ep["cp_points"]:
                g = policy.grad_logp(pt["phi"], pt["action"])
                grad_sum = [s + adv * gi for s, gi in zip(grad_sum, g)]
            baseline = beta * baseline + (1 - beta) * ep["R_eff"]
        elif ep.get("context_overflow"):
            sampled = []  # sem trajetória → sem replay; braços de crédito não amostram
        else:
            traj = load_trajectory(ep["trajectory"])
            pts = ep["cp_points"]
            ep_rng = random.Random(seed * 7919 + episode_idx)  # rng derivado de seed+episódio
            sampled = ep_rng.sample(pts, min(k_credit, len(pts))) if pts else []
            greedy = LogisticContextPolicyV2(theta=theta, greedy=True, center=center, **hkw)
            for pt in sampled:
                c = credit_for_point(traj, traj.decisions[pt["index"]], llm, greedy,
                                     arm, out_dir / "replays", lambda_cost)
                credits.append(c)
                g = policy.grad_logp(pt["phi"], pt["action"])
                grad_sum = [s + c["credit"] * gi for s, gi in zip(grad_sum, g)]
        gnorm = math.sqrt(sum(g * g for g in grad_sum))
        if clip_norm > 0 and gnorm > clip_norm:
            grad_sum = [g * clip_norm / gnorm for g in grad_sum]
        theta = [t + lr * gi for t, gi in zip(theta, grad_sum)]
        _append_flush(log_path, {
            "episode_idx": episode_idx, "task_id": task["task_id"],
            "seed": episode_seed, "R": ep["R"], "R_eff": ep["R_eff"],
            "calls_cum": llm.call_count, "theta": theta,
            "grad_norm": gnorm,
            "credits": credits, "arm": arm,
            "context_overflow": bool(ep.get("context_overflow", False))})
        episode_idx += 1
    stopped_by = "budget_calls" if llm.call_count >= budget_calls else "max_episodes"
    return {"arm": arm, "seed": seed, "lambda_cost": lambda_cost,
            "episodes": episode_idx, "theta": theta,
            "lr": lr, "clip_norm": clip_norm,
            "center": list(center) if center is not None else None,
            "harness_kw": hkw,
            "llm_calls_total": llm.call_count, "budget_calls": budget_calls,
            "max_episodes": max_episodes, "stopped_by": stopped_by,
            "log_path": str(log_path)}


def evaluate(tasks: list[dict], llm, policy_theta: list[float], seed: int, out_dir,
             lambda_cost: float = 1.0, center: list[float] | None = None,
             harness_kw: dict | None = None) -> dict:
    llm = _ensure_counting(llm)
    hkw = dict(harness_kw or {})
    per_task = []
    for i, task in enumerate(tasks):
        policy = LogisticContextPolicyV2(theta=policy_theta, rng_seed=seed,
                                         greedy=True, center=center, **hkw)
        ep = collect_episode(task, llm, policy, Path(out_dir) / "eval",
                             seed * 100003 + i, lambda_cost)
        per_task.append({"task_id": task["task_id"], "R": ep["R"], "R_eff": ep["R_eff"],
                         "prompt_tokens_total": ep["prompt_tokens_total"],
                         "context_overflow": bool(ep.get("context_overflow", False))})
    n = len(per_task) or 1
    return {"mean_R": sum(t["R"] for t in per_task) / n,
            "mean_R_eff": sum(t["R_eff"] for t in per_task) / n,
            "per_task": per_task}


def calibrate(tasks: list[dict], llm, out_dir, lambda_cost: float,
              harness_kw: dict | None = None) -> dict:
    """3 políticas fixas V2 → R_eff médio; valida que keep-always NÃO é ótimo sob λ.

    default usa o threshold vindo de harness_kw (config v2_folga: 4500)."""
    llm = _ensure_counting(llm)
    out_dir = Path(out_dir)
    hkw = dict(harness_kw or {})
    fixed = {"keep_always": HarnessV2(**{**hkw, "summarize_threshold_tokens": 10**9}),
             "summarize_always": HarnessV2(**{**hkw, "summarize_threshold_tokens": -1}),
             "default": HarnessV2(**hkw)}
    report: dict = {"lambda_cost": lambda_cost, "harness_kw": hkw, "policies": {}}
    for name, harness in fixed.items():
        per_task = []
        for task in tasks:
            tally = _TokenTally(llm)
            episode = EpisodeV2(task, tally, harness, Recorder(out_dir / "calibrate" / name))
            try:
                result = episode.run()
            except openai.BadRequestError:
                # emenda 32a: overflow = task falha, R=0, tokens pagos até o estouro
                per_task.append({"task_id": task["task_id"], "R": 0.0,
                                 "R_eff": r_eff(0.0, tally.prompt_tokens, lambda_cost),
                                 "prompt_tokens_total": tally.prompt_tokens,
                                 "context_overflow": True})
                continue
            finally:
                episode.sandbox.cleanup()
            traj = load_trajectory(result["trajectory_path"])
            tokens = _prompt_tokens(traj.decisions)
            per_task.append({"task_id": task["task_id"], "R": result["reward"],
                             "R_eff": r_eff(result["reward"], tokens, lambda_cost),
                             "prompt_tokens_total": tokens,
                             "context_overflow": False})
        n = len(per_task) or 1
        report["policies"][name] = {
            "mean_R": sum(t["R"] for t in per_task) / n,
            "mean_R_eff": sum(t["R_eff"] for t in per_task) / n,
            "per_task": per_task}
    means = {k: v["mean_R_eff"] for k, v in report["policies"].items()}
    report["keep_always_is_best"] = means["keep_always"] >= max(means.values())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "calibrate_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


# -- CLI -----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="V2: treino REINFORCE da context_policy (mini-SWE)")
    ap.add_argument("--arm", required=True,
                    choices=["outcome", "ch", "chm_cm", "zero", "calibrate"])
    ap.add_argument("--tasks-module", default="environment.tasks_swe")
    ap.add_argument("--pool-json", default=None,
                    help="pool verificado: json com train/heldout (formato do V1)")
    ap.add_argument("--budget-calls", type=int, default=2000)
    ap.add_argument("--max-episodes", type=int, default=None,
                    help="para no que vier primeiro (budget_calls OU max_episodes)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lambda-cost", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=0.1)
    ap.add_argument("--clip-norm", type=float, default=1.0)
    # config v2_folga (defaults de HarnessV2): 4500/25/6
    ap.add_argument("--threshold", type=int, default=4500)
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--keep-last", type=int, default=6)
    args = ap.parse_args()
    harness_kw = {"summarize_threshold_tokens": args.threshold,
                  "max_turns": args.max_turns, "keep_last": args.keep_last}

    from agent.llm import LLMClient  # lazy: testes nunca importam o cliente de rede
    llm = CountingLLM(LLMClient())
    if args.pool_json:
        pool = json.loads(Path(args.pool_json).read_text())
        by_id = {t["task_id"]: t
                 for t in importlib.import_module(args.tasks_module).TASKS}
        train_tasks = [by_id[tid] for tid in pool["train"]]
        heldout_tasks = [by_id[tid] for tid in pool["heldout"]]
    else:
        train_tasks, heldout_tasks = load_task_split(args.tasks_module)
    out = Path(args.out)

    if args.arm == "calibrate":
        report = calibrate(train_tasks, llm, out, args.lambda_cost, harness_kw)
        print(json.dumps({k: v for k, v in report.items() if k != "policies"}
                         | {k: p["mean_R_eff"] for k, p in report["policies"].items()},
                         indent=2))
        return

    summary = train(train_tasks, llm, args.arm, args.budget_calls, args.seed, out,
                    lambda_cost=args.lambda_cost, lr=args.lr,
                    clip_norm=args.clip_norm, center=CENTER_V2,
                    max_episodes=args.max_episodes, harness_kw=harness_kw)
    heldout = evaluate(heldout_tasks, llm, summary["theta"], args.seed, out,
                       lambda_cost=args.lambda_cost, center=CENTER_V2,
                       harness_kw=harness_kw)
    summary["heldout"] = heldout
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"arm": summary["arm"], "episodes": summary["episodes"],
                      "stopped_by": summary["stopped_by"],
                      "llm_calls_total": summary["llm_calls_total"],
                      "theta": summary["theta"],
                      "heldout_mean_R": heldout["mean_R"],
                      "heldout_mean_R_eff": heldout["mean_R_eff"]}, indent=2))


if __name__ == "__main__":
    main()
