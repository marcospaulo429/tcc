"""Smoke do pré-reg 38: 3 episódios V2 (protocolo texto plano) com o modelo
servido, sem análise de screening. Forma idêntica ao smoke do 35: passa se a
taxa de parse de ações do modelo for >=80%. Parse falho aparece como decisão
harness/retry; parse ok como model/tool_call não-forçado.
Tasks declaradas no pré-registro: swe_agendador_v1, swe_cache_v1,
swe_config_merge_v1; config v2_folga (HarnessV2 default).
Adendo 38a: episódio abortado por estouro de contexto (400 no serving de 8k,
propriedade do stack — a célula Qwen tem o mesmo 400 em 3/60 tasks do base 29)
entra na contagem com as decisões até o abort; métrica inalterada."""
import sys
import tempfile
from pathlib import Path

import openai

from agent.harness_v2 import HarnessV2
from agent.llm import LLMClient
from agent.loop_v2 import EpisodeV2
from environment.tasks_swe import TASKS
from experiments.common import load_trajectories
from trajectories.recorder import Recorder

SMOKE_TASKS = ("swe_agendador_v1", "swe_cache_v1", "swe_config_merge_v1")


def _conta(decisions) -> tuple[int, int]:
    ok = fail = 0
    for d in decisions:
        if d.decision_point == "tool_call" and not d.chosen_action.get("forced"):
            ok += 1
        elif d.decision_point == "retry":
            fail += 1
    return ok, fail


def main() -> None:
    tasks = [t for t in TASKS if t["task_id"] in SMOKE_TASKS]
    assert len(tasks) == 3
    llm = LLMClient()
    ok = fail = 0
    with tempfile.TemporaryDirectory() as td:
        for task in tasks:
            rec = Recorder(Path(td))
            ep = EpisodeV2(task, llm, HarnessV2(), rec)
            try:
                r = ep.run()  # sucesso: finish() salva; contado do arquivo abaixo
                print(f"smoke ep {task['task_id']}: reward={r['reward']:.2f}",
                      flush=True)
            except openai.BadRequestError:
                print(f"smoke ep {task['task_id']}: truncado (context overflow "
                      "no serving de 8k) — decisões até o abort contam", flush=True)
            finally:
                if rec.trajectory is not None:  # episódio truncado (sem finish)
                    o, f = _conta(rec.trajectory.decisions)
                    ok, fail = ok + o, fail + f
                ep.sandbox.cleanup()
        for traj in load_trajectories(Path(td)):  # episódios completos (salvos)
            o, f = _conta(traj.decisions)
            ok, fail = ok + o, fail + f
    taxa = ok / (ok + fail) if (ok + fail) else 0.0
    print(f"smoke: {ok} parses ok, {fail} retries -> taxa {taxa:.2f}")
    sys.exit(0 if taxa >= 0.80 else 1)


if __name__ == "__main__":
    main()
