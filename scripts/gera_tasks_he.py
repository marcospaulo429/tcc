"""Gera environment/tasks_he.py a partir do HumanEval+ (EvalPlus) — pré-registro 25 (D7).

Determinístico (seed 20260821). Rodar com:
    uv run --with evalplus python scripts/gera_tasks_he.py

Pipeline IDÊNTICO ao de scripts/gera_tasks_mbpp.py (pré-reg 16), com as únicas
diferenças impostas pelo formato do dataset, declaradas no pré-registro:
  - a solução canônica completa é prompt + canonical_solution (no HumanEval o
    canonical_solution é só o corpo da função);
  - a descrição vem da docstring da função de entrada (via ast), com as linhas
    de doctest (">>>"/saídas) removidas — os exemplos mostrados ao agente vêm
    dos asserts escolhidos, como no MBPP+;
  - task_id = "he_" + número.
"""

import ast
import random
import signal
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from environment.sandbox import Sandbox  # noqa: E402
from scripts.gera_tasks_mbpp import (  # noqa: E402
    MAX_ASSERTS, MIN_ASSERTS, _alarm_handler, _extract_signature, _MAX_REPR,
    _roundtrips, _timed_call, SEED,
)

POOL_SIZE = 60


def _description(canonical_full: str, entry: str) -> list[str]:
    """Linhas da docstring da função de entrada, sem doctests."""
    try:
        tree = ast.parse(canonical_full)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == entry:
            doc = ast.get_docstring(node) or ""
            lines, skip_next = [], False
            for line in doc.splitlines():
                s = line.strip()
                if s.startswith(">>>"):
                    skip_next = True
                    continue
                if skip_next:  # linha de saída do doctest
                    skip_next = False
                    continue
                if s:
                    lines.append(s)
            return lines
    return []


def _build_task(raw: dict) -> tuple[dict | None, str]:
    entry = raw["entry_point"]
    canonical = raw["prompt"] + raw["canonical_solution"]
    task_id = "he_" + raw["task_id"].split("/")[-1]

    signature = _extract_signature(canonical, entry)
    if signature is None:
        return None, "sem_assinatura"

    namespace: dict = {}
    try:
        exec(canonical, namespace)  # noqa: S102 — dataset confiável, offline
        fn = namespace[entry]
    except Exception:
        return None, "canonica_nao_executa"

    def usable(inputs: list) -> list[tuple[str, str]]:
        out, seen = [], set()
        for args in inputs:
            args = list(args)
            args_repr = ", ".join(repr(a) for a in args)
            if args_repr in seen or len(args_repr) > _MAX_REPR:
                continue
            if not all(_roundtrips(a) for a in args):
                continue
            try:
                result = _timed_call(fn, args)
            except Exception:
                continue
            if not _roundtrips(result):
                continue
            seen.add(args_repr)
            out.append((args_repr, repr(result)))
        return out

    base = usable(raw["base_input"])
    rng = random.Random(f"{SEED}:{task_id}")
    plus_pool = list(raw["plus_input"])
    rng.shuffle(plus_pool)
    n_target = rng.randint(MIN_ASSERTS, MAX_ASSERTS)
    chosen = base[:n_target]
    base_reprs = {a for a, _ in chosen}
    for args_repr, exp_repr in usable(plus_pool[: 4 * MAX_ASSERTS]):
        if len(chosen) >= n_target:
            break
        if args_repr not in base_reprs:
            chosen.append((args_repr, exp_repr))
    if len(chosen) < MIN_ASSERTS:
        return None, "menos_de_6_asserts"

    test_lines = [f"from solution import {entry}", "", ""]
    for i, (args_repr, exp_repr) in enumerate(chosen, 1):
        test_lines += [
            f"def test_{i:02d}():",
            f"    assert {entry}({args_repr}) == {exp_repr}",
            "",
            "",
        ]
    test_code = "\n".join(test_lines[:-1])

    desc = _description(canonical, entry)
    if not desc:
        return None, "sem_docstring"
    doc = desc[0].rstrip(".") + "."
    starter_code = f'{signature}\n    """{doc}"""\n    raise NotImplementedError\n'

    sig_display = signature[len("def "):-1]
    examples = "\n".join(f"  {entry}({a}) -> {e}" for a, e in chosen[:2])
    prompt = (
        f"Implement the function `{sig_display}` in the file solution.py.\n"
        + "\n".join(desc) + "\n\n"
        + "Examples:\n" + examples + "\n"
    )

    task = {
        "task_id": task_id,
        "prompt": prompt,
        "starter_code": starter_code,
        "test_code": test_code,
    }
    return task, ""


def _validate(task: dict, canonical: str) -> bool:
    sandbox = Sandbox()
    try:
        sandbox.write_file("solution.py", canonical)
        n_tests = task["test_code"].count("def test_")
        result = sandbox.run_tests(task["test_code"], timeout=float(n_tests) + 10.0)
        return result["success"] and result["total"] == n_tests
    finally:
        sandbox.cleanup()


def main() -> None:
    from evalplus.data import get_human_eval_plus

    raw_tasks = get_human_eval_plus()
    signal.signal(signal.SIGALRM, _alarm_handler)

    survivors: list[tuple[dict, str]] = []
    discarded = {"sem_assinatura": 0, "canonica_nao_executa": 0,
                 "menos_de_6_asserts": 0, "sem_docstring": 0,
                 "validacao_falhou": 0}
    for key in sorted(raw_tasks):
        raw = raw_tasks[key]
        task, reason = _build_task(raw)
        if task is None:
            discarded[reason] += 1
            continue
        canonical = raw["prompt"] + raw["canonical_solution"]
        if not _validate(task, canonical):
            discarded["validacao_falhou"] += 1
            continue
        survivors.append((task, canonical))

    survivors.sort(key=lambda pair: pair[0]["task_id"])
    if len(survivors) > POOL_SIZE:
        selected = random.Random(SEED).sample(survivors, POOL_SIZE)
        selected.sort(key=lambda pair: pair[0]["task_id"])
    else:
        selected = survivors
        print(f"AVISO: só {len(survivors)} sobreviventes (<{POOL_SIZE}); usando todas.")

    ids = [t["task_id"] for t, _ in selected]
    sample_ids = sorted(random.Random(SEED).sample(sorted(ids), 5))
    canonical_sample = {
        t["task_id"]: sol for t, sol in selected if t["task_id"] in sample_ids
    }

    header = (
        f'"""Pool CONGELADO de {len(selected)} tasks derivadas do HumanEval+ '
        f"(EvalPlus) — pré-registro 25 (D7).\n\n"
        f"GERADO por scripts/gera_tasks_he.py (seed {SEED}) em {date.today()}. "
        f"NÃO EDITAR À MÃO.\n"
        f"HumanEval+ processadas: {len(raw_tasks)} | descartadas: {discarded} | "
        f"sobreviventes: {len(survivors)} | selecionadas: {len(selected)}.\n"
        f'"""\n'
    )
    lines = [header, "TASKS: list[dict] = ["]
    for task, _ in selected:
        lines.append("    {")
        for k in ("task_id", "prompt", "starter_code", "test_code"):
            lines.append(f"        {k!r}: {task[k]!r},")
        lines.append("    },")
    lines.append("]")
    lines.append("")
    lines.append('STRATA: dict[str, str] = {t["task_id"]: "HE" for t in TASKS}')
    lines.append("")
    lines.append("# soluções canônicas da amostra de validação dos testes (não usadas pelo agente)")
    lines.append("_CANONICAL_SAMPLE: dict[str, str] = {")
    for tid in sample_ids:
        lines.append(f"    {tid!r}: {canonical_sample[tid]!r},")
    lines.append("}")
    lines.append("")
    lines.append('__all__ = ["TASKS", "STRATA"]')
    lines.append("")
    lines.append("")
    lines.append("def get_task(task_id: str) -> dict:")
    lines.append("    for t in TASKS:")
    lines.append('        if t["task_id"] == task_id:')
    lines.append("            return t")
    lines.append("    raise KeyError(task_id)")
    lines.append("")

    out = REPO / "environment" / "tasks_he.py"
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"HumanEval+ processadas: {len(raw_tasks)}")
    print(f"Descartadas: {discarded}")
    print(f"Sobreviventes: {len(survivors)} | selecionadas: {len(selected)}")
    print(f"Escrito: {out}")


if __name__ == "__main__":
    main()
