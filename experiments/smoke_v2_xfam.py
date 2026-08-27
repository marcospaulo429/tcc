"""Smoke do pré-reg 38: 3 episódios V2 (protocolo texto plano) com o modelo
servido, sem análise de screening. Forma idêntica ao smoke do 35: passa se a
taxa de parse de ações do modelo for >=80%. Parse falho aparece como decisão
harness/retry; parse ok como model/tool_call não-forçado.
Tasks declaradas no pré-registro: swe_agendador_v1, swe_cache_v1,
swe_config_merge_v1; config v2_folga (HarnessV2 default)."""
import sys
import tempfile
from pathlib import Path

from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from agent.loop_v2 import EpisodeV2
from environment.tasks_swe import TASKS
from experiments.common import load_trajectories
from trajectories.recorder import Recorder

SMOKE_TASKS = ("swe_agendador_v1", "swe_cache_v1", "swe_config_merge_v1")


def main() -> None:
    tasks = [t for t in TASKS if t["task_id"] in SMOKE_TASKS]
    assert len(tasks) == 3
    llm = LLMClient()
    with tempfile.TemporaryDirectory() as td:
        for task in tasks:
            ep = EpisodeV2(task, llm, HarnessV2(), Recorder(Path(td)))
            try:
                r = ep.run()
                print(f"smoke ep {task['task_id']}: reward={r['reward']:.2f}",
                      flush=True)
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
