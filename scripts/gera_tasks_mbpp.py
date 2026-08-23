"""Gera environment/tasks_mbpp.py a partir do MBPP+ (EvalPlus) — pré-registro 16 (D3).

Determinístico (seed 20260821). Rodar com:
    uv run --with evalplus python scripts/gera_tasks_mbpp.py

Pipeline por task MBPP+:
  1. extrai assinatura da função `entry_point` da solução canônica (via ast);
  2. computa expected outputs executando a solução canônica sobre inputs
     base + plus (deepcopy dos args, timeout de 1 s por chamada via SIGALRM);
  3. mantém só asserts cujo repr round-tripa (eval(repr(x)) == x) e cabe em
     _MAX_REPR chars; escolhe deterministicamente 6-10 asserts (todos os base
     utilizáveis primeiro, plus sorteados para completar);
  4. valida: solução canônica escrita como solution.py deve passar 100% das
     funções de teste geradas no sandbox do repo (environment/sandbox.py);
  5. seleção final: 60 tasks sorteadas com seed 20260821 sobre as
     sobreviventes ordenadas por task_id.
"""

import ast
import copy
import random
import signal
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from environment.sandbox import Sandbox  # noqa: E402

SEED = 20260821
POOL_SIZE = 60
MIN_ASSERTS, MAX_ASSERTS = 6, 10
_MAX_REPR = 1500  # limite de chars por linha de assert (args + expected)
_CALL_TIMEOUT = 1.0  # s por chamada da solução canônica (pré-registro: <1 s)


class _CallTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _CallTimeout


def _timed_call(fn, args):
    signal.setitimer(signal.ITIMER_REAL, _CALL_TIMEOUT)
    try:
        return fn(*copy.deepcopy(args))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _roundtrips(value) -> bool:
    """repr(value) deve reconstruir um objeto igual (descarta floats instáveis,
    nan, objetos sem literal, etc.)."""
    try:
        r = repr(value)
        if len(r) > _MAX_REPR:
            return False
        return eval(r) == value  # noqa: S307 — dados locais, geração offline
    except Exception:
        return False


def _extract_signature(canonical: str, entry_point: str) -> str | None:
    """Linha `def entry_point(...):` reconstruída via ast (corpo descartado)."""
    try:
        tree = ast.parse(canonical)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == entry_point:
            clone = ast.FunctionDef(
                name=node.name, args=node.args, body=[ast.Pass()],
                decorator_list=[], returns=None, type_comment=None,
            )
            clone = ast.fix_missing_locations(ast.Module(body=[clone], type_ignores=[]))
            header = ast.unparse(clone).split("\n")[0]
            return header if header.endswith(":") else None
    return None


def _description(prompt: str) -> list[str]:
    """Linhas de texto do prompt MBPP (sem aspas triplas e sem os asserts)."""
    lines = []
    for line in prompt.strip().strip('"').strip().splitlines():
        line = line.strip()
        if not line or line.startswith("assert "):
            continue
        lines.append(line)
    return lines


def _build_task(raw: dict) -> tuple[dict | None, str]:
    """Retorna (task, motivo_descartada). task=None se descartada."""
    entry = raw["entry_point"]
    canonical = raw["canonical_solution"]
    task_id = "mbpp_" + raw["task_id"].split("/")[-1]

    signature = _extract_signature(canonical, entry)
    if signature is None:
        return None, "sem_assinatura"

    namespace: dict = {}
    try:
        exec(canonical, namespace)  # noqa: S102 — dataset confiável, offline
        fn = namespace[entry]
    except Exception:
        return None, "canonica_nao_executa"

    # asserts utilizáveis: (repr_args, repr_expected), base primeiro
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

    desc = _description(raw["prompt"])
    doc = (desc[0] if desc else f"MBPP+ task {task_id}.").rstrip(".") + "."
    starter_code = f'{signature}\n    """{doc}"""\n    raise NotImplementedError\n'

    sig_display = signature[len("def "):-1]
    examples = "\n".join(
        f"  {entry}({a}) -> {e}" for a, e in chosen[:2]
    )
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
    from evalplus.data import get_mbpp_plus

    raw_tasks = get_mbpp_plus()
    signal.signal(signal.SIGALRM, _alarm_handler)

    survivors: list[tuple[dict, str]] = []
    discarded = {"sem_assinatura": 0, "canonica_nao_executa": 0,
                 "menos_de_6_asserts": 0, "validacao_falhou": 0}
    for key in sorted(raw_tasks):
        raw = raw_tasks[key]
        task, reason = _build_task(raw)
        if task is None:
            discarded[reason] += 1
            continue
        if not _validate(task, raw["canonical_solution"]):
            discarded["validacao_falhou"] += 1
            continue
        survivors.append((task, raw["canonical_solution"]))

    survivors.sort(key=lambda pair: pair[0]["task_id"])
    if len(survivors) > POOL_SIZE:
        selected = random.Random(SEED).sample(survivors, POOL_SIZE)
        selected.sort(key=lambda pair: pair[0]["task_id"])
    else:
        selected = survivors
        print(f"AVISO: só {len(survivors)} sobreviventes (<{POOL_SIZE}); usando todas.")

    # amostra determinística de 5 tasks cujo canônico fica embutido p/ os testes
    ids = [t["task_id"] for t, _ in selected]
    sample_ids = sorted(random.Random(SEED).sample(sorted(ids), 5))
    canonical_sample = {
        t["task_id"]: sol for t, sol in selected if t["task_id"] in sample_ids
    }

    header = (
        f'"""Pool CONGELADO de {len(selected)} tasks derivadas do MBPP+ (EvalPlus) '
        f"— pré-registro 16 (D3).\n\n"
        f"GERADO por scripts/gera_tasks_mbpp.py (seed {SEED}) em {date.today()}. "
        f"NÃO EDITAR À MÃO.\n"
        f"MBPP+ processadas: {len(raw_tasks)} | descartadas: {discarded} | "
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
    lines.append('STRATA: dict[str, str] = {t["task_id"]: "MBPP" for t in TASKS}')
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

    out = REPO / "environment" / "tasks_mbpp.py"
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"MBPP+ processadas: {len(raw_tasks)}")
    print(f"Descartadas: {discarded}")
    print(f"Sobreviventes: {len(survivors)} | selecionadas: {len(selected)}")
    print(f"Escrito: {out}")


if __name__ == "__main__":
    main()
