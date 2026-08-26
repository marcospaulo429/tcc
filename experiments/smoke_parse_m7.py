"""Smoke de parse do pré-reg 35: 3 episódios com o modelo servido, sem análise
de screening. Passa se a taxa de parse de ações do modelo for >=80%.
Parse falho aparece como decisão harness/retry; parse ok como model/tool_call
não-forçado. taxa = ok / (ok + retries)."""
import importlib
import sys
import tempfile
from pathlib import Path

from agent.harness import Harness
from agent.llm import LLMClient
from agent.loop import Episode
from experiments.common import load_trajectories
from trajectories.recorder import Recorder


def main() -> None:
    tasks = importlib.import_module("environment.tasks_all").TASKS[:3]
    llm = LLMClient()
    with tempfile.TemporaryDirectory() as td:
        for task in tasks:
            ep = Episode(task, llm, Harness(summarize_threshold_tokens=600,
                                            max_turns=6), Recorder(Path(td)))
            try:
                r = ep.run()
                print(f"smoke ep {task['task_id']}: reward={r['reward']:.2f}")
            finally:
                ep.sandbox.cleanup()
        ok = fail = 0
        for traj in load_trajectories(Path(td)):
            for d in traj.decisions:
                if d.decision_point == "tool_call" and not d.chosen_action.get("forced"):
                    ok += 1
                elif d.decision_point == "retry":
                    fail += 1
    taxa = ok / (ok + fail) if (ok + fail) else 0.0
    print(f"smoke: {ok} parses ok, {fail} retries -> taxa {taxa:.2f}")
    sys.exit(0 if taxa >= 0.80 else 1)


if __name__ == "__main__":
    main()
