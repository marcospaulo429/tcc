"""C1 — treino REINFORCE da política de context_policy em 3 braços dose-matched.

Contabilidade de orçamento: TODA chamada LLM conta (episódios + replays de crédito +
amostragem de a′). O llm passado deve expor `call_count` (o CLI embrulha o LLMClient
em CountingLLM; os FakeLLMs dos testes contam sozinhos).

Contabilidade de tokens do crédito (pré-registrado): R_eff de um replay a partir do
índice i usa prompt_tokens = Σ costs das decisões ORIGINAIS [0:i] (prefixo pago de
fato) + Σ costs das decisões do replay-traj. Assim C_*_eff compara trajetórias
completas sob a mesma pressão de custo.

Replays de crédito SEMPRE com a política em modo greedy (estimando pré-registrado:
crédito sob continuação greedy) e mesmo harness config. `trajectories.replay.
replay_from` reconstrói um Harness fixo do config e não aceita harness custom, então
_replay_with_policy espelha sua mecânica (mesmo resume/forced_actions do Episode)
injetando a política — desvio documentado, sem alterar módulos existentes.

Split determinístico: tasks do módulo ordenadas por task_id; 20 primeiras = treino,
10 restantes = held-out.
"""
import argparse
import importlib
import json
import random
from pathlib import Path

from agent.harness import Harness
from agent.loop import Episode
from environment.registry import resolve_task
from environment.sandbox import Sandbox
from interventions.model import sample_alternative
from trajectories.recorder import Recorder
from trajectories.schema import Trajectory, load_trajectory

from .policy import N_FEATURES, LogisticContextPolicy


class CountingLLM:
    """Proxy que conta toda chamada chat() — base da contabilidade de orçamento."""

    def __init__(self, llm):
        self._llm = llm
        self.call_count = 0

    def config(self) -> dict:
        return self._llm.config()

    def chat(self, messages, **kw) -> dict:
        self.call_count += 1
        return self._llm.chat(messages, **kw)


def _ensure_counting(llm):
    return llm if hasattr(llm, "call_count") else CountingLLM(llm)


class PolicyEpisode(Episode):
    """Episode que injeta turn/tests_passed_frac/n_writes na política via
    set_turn_state() antes de cada decisão de context_policy, sem tocar agent.loop."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._n_writes = 0
        self._tests_passed_frac = 0.0

    def _apply_model_action(self, action, messages):
        obs = super()._apply_model_action(action, messages)
        if action["action"] == "write_file":
            self._n_writes += 1
        elif action["action"] == "run_tests" and obs.get("total"):
            self._tests_passed_frac = obs["passed"] / obs["total"]
        return obs

    def _step_context_policy(self, messages, turn):
        if hasattr(self.harness, "set_turn_state"):
            self.harness.set_turn_state(turn, self._tests_passed_frac, self._n_writes)
        return super()._step_context_policy(messages, turn)


def r_eff(reward: float, prompt_tokens: int, lambda_cost: float) -> float:
    return reward - lambda_cost * (prompt_tokens / 100000.0)


def _prompt_tokens(decisions) -> int:
    return sum(d.costs.get("prompt_tokens", 0) for d in decisions)


def _append_flush(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


# -- coleta ------------------------------------------------------------------

def collect_episode(task: dict, llm, policy: LogisticContextPolicy, out_dir,
                    episode_seed: int, lambda_cost: float = 1.0) -> dict:
    llm = _ensure_counting(llm)
    policy.reseed(episode_seed)
    policy.decision_log = []
    calls0 = llm.call_count
    ep = PolicyEpisode(task, llm, policy, Recorder(out_dir))
    try:
        result = ep.run()
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
    """Espelho de trajectories.replay.replay_from com harness injetável.

    Contadores da política (n_writes, tests_passed_frac) são reconstruídos do
    prefixo original para que φ no replay reflita o histórico real.
    Retorna (result, prompt_tokens do replay-traj).
    """
    d = traj.decisions[index]
    if d.decision_point not in Episode.PHASES:
        raise NotImplementedError(f"replay a partir de '{d.decision_point}' não suportado")
    assert override_actions[0]["point"] == d.decision_point

    sandbox = Sandbox()
    sandbox.restore(d.state_before["workspace"])
    episode = PolicyEpisode(resolve_task(traj.task_id), llm, harness,
                            Recorder(out_dir), sandbox)
    for dd in traj.decisions[:index]:
        if dd.decision_point != "tool_call":
            continue
        if dd.chosen_action.get("action") == "write_file":
            episode._n_writes += 1
        elif dd.chosen_action.get("action") == "run_tests" and (dd.observation or {}).get("total"):
            episode._tests_passed_frac = dd.observation["passed"] / dd.observation["total"]
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
    finally:
        sandbox.cleanup()
    rtraj = load_trajectory(result["trajectory_path"])
    return result, _prompt_tokens(rtraj.decisions)


def _canonical_tool_action(decision) -> dict:
    return {k: v for k, v in decision.chosen_action.items() if k != "forced"}


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
    samp = sample_alternative(llm, tool.state_before["messages"], orig_tool)
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
          lambda_cost: float = 1.0, k_credit: int = 2, lr: float = 0.5) -> dict:
    if arm not in ("outcome", "ch", "chm_cm"):
        raise ValueError(f"arm desconhecido: {arm}")
    out_dir = Path(out_dir)
    llm = _ensure_counting(llm)
    theta = [0.0] * N_FEATURES
    baseline = 0.0  # média móvel de R_eff (beta=0.9), inicia em 0
    beta = 0.9
    log_path = out_dir / "train_log.jsonl"
    episode_idx = 0
    while llm.call_count < budget_calls:
        task = tasks[episode_idx % len(tasks)]
        episode_seed = seed * 100003 + episode_idx
        policy = LogisticContextPolicy(theta=theta, rng_seed=episode_seed, greedy=False)
        ep = collect_episode(task, llm, policy, out_dir / "episodes",
                             episode_seed, lambda_cost)
        grad_sum = [0.0] * N_FEATURES
        credits: list[dict] = []
        if arm == "outcome":
            adv = ep["R_eff"] - baseline
            for pt in ep["cp_points"]:
                g = policy.grad_logp(pt["phi"], pt["action"])
                grad_sum = [s + adv * gi for s, gi in zip(grad_sum, g)]
            baseline = beta * baseline + (1 - beta) * ep["R_eff"]
        else:
            traj = load_trajectory(ep["trajectory"])
            pts = ep["cp_points"]
            ep_rng = random.Random(seed * 7919 + episode_idx)  # rng derivado de seed+episódio
            sampled = ep_rng.sample(pts, min(k_credit, len(pts))) if pts else []
            greedy = LogisticContextPolicy(theta=theta, greedy=True)
            for pt in sampled:
                c = credit_for_point(traj, traj.decisions[pt["index"]], llm, greedy,
                                     arm, out_dir / "replays", lambda_cost)
                credits.append(c)
                g = policy.grad_logp(pt["phi"], pt["action"])
                grad_sum = [s + c["credit"] * gi for s, gi in zip(grad_sum, g)]
        theta = [t + lr * gi for t, gi in zip(theta, grad_sum)]
        _append_flush(log_path, {
            "episode_idx": episode_idx, "task_id": task["task_id"],
            "seed": episode_seed, "R": ep["R"], "R_eff": ep["R_eff"],
            "calls_cum": llm.call_count, "theta": theta,
            "credits": credits, "arm": arm})
        episode_idx += 1
    return {"arm": arm, "seed": seed, "lambda_cost": lambda_cost,
            "episodes": episode_idx, "theta": theta,
            "llm_calls_total": llm.call_count, "budget_calls": budget_calls,
            "log_path": str(log_path)}


def evaluate(tasks: list[dict], llm, policy_theta: list[float], seed: int, out_dir,
             lambda_cost: float = 1.0) -> dict:
    llm = _ensure_counting(llm)
    per_task = []
    for i, task in enumerate(tasks):
        policy = LogisticContextPolicy(theta=policy_theta, rng_seed=seed, greedy=True)
        ep = collect_episode(task, llm, policy, Path(out_dir) / "eval",
                             seed * 100003 + i, lambda_cost)
        per_task.append({"task_id": task["task_id"], "R": ep["R"], "R_eff": ep["R_eff"],
                         "prompt_tokens_total": ep["prompt_tokens_total"]})
    n = len(per_task) or 1
    return {"mean_R": sum(t["R"] for t in per_task) / n,
            "mean_R_eff": sum(t["R_eff"] for t in per_task) / n,
            "per_task": per_task}


def calibrate(tasks: list[dict], llm, out_dir, lambda_cost: float) -> dict:
    """3 políticas fixas → R_eff médio; valida que keep-always NÃO é ótimo sob λ."""
    llm = _ensure_counting(llm)
    out_dir = Path(out_dir)
    fixed = {"keep_always": Harness(summarize_threshold_tokens=10**9),
             "summarize_always": Harness(summarize_threshold_tokens=-1),
             "thr600": Harness(summarize_threshold_tokens=600)}
    report: dict = {"lambda_cost": lambda_cost, "policies": {}}
    for name, harness in fixed.items():
        per_task = []
        for task in tasks:
            episode = Episode(task, llm, harness, Recorder(out_dir / "calibrate" / name))
            try:
                result = episode.run()
            finally:
                episode.sandbox.cleanup()
            traj = load_trajectory(result["trajectory_path"])
            tokens = _prompt_tokens(traj.decisions)
            per_task.append({"task_id": task["task_id"], "R": result["reward"],
                             "R_eff": r_eff(result["reward"], tokens, lambda_cost),
                             "prompt_tokens_total": tokens})
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

def load_task_split(module_name: str) -> tuple[list[dict], list[dict]]:
    """Determinístico: ordena por task_id; 20 primeiras = treino, resto = held-out."""
    mod = importlib.import_module(module_name)
    tasks = sorted(mod.TASKS, key=lambda t: t["task_id"])
    return tasks[:20], tasks[20:]


def main() -> None:
    ap = argparse.ArgumentParser(description="C1: treino REINFORCE da context_policy")
    ap.add_argument("--arm", required=True,
                    choices=["outcome", "ch", "chm_cm", "calibrate"])
    ap.add_argument("--tasks-module", default="environment.tasks_all")
    ap.add_argument("--budget-calls", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lambda-cost", type=float, default=1.0)
    args = ap.parse_args()

    from agent.llm import LLMClient  # lazy: testes nunca importam o cliente de rede
    llm = CountingLLM(LLMClient())
    train_tasks, heldout_tasks = load_task_split(args.tasks_module)
    out = Path(args.out)

    if args.arm == "calibrate":
        report = calibrate(train_tasks, llm, out, args.lambda_cost)
        print(json.dumps({k: v for k, v in report.items() if k != "policies"}
                         | {k: p["mean_R_eff"] for k, p in report["policies"].items()},
                         indent=2))
        return

    summary = train(train_tasks, llm, args.arm, args.budget_calls, args.seed, out,
                    lambda_cost=args.lambda_cost)
    heldout = evaluate(heldout_tasks, llm, summary["theta"], args.seed, out,
                       lambda_cost=args.lambda_cost)
    summary["heldout"] = heldout
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"arm": summary["arm"], "episodes": summary["episodes"],
                      "llm_calls_total": summary["llm_calls_total"],
                      "theta": summary["theta"],
                      "heldout_mean_R": heldout["mean_R"],
                      "heldout_mean_R_eff": heldout["mean_R_eff"]}, indent=2))


if __name__ == "__main__":
    main()
