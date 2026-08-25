"""Gera e congela o pool mini-SWE (pré-registro 28, piloto V2).

Valida cada task das famílias em scripts/miniswe/familia_*.py:
  - canônica passa 100%; estado inicial com reward em (0,1) — variância obrigatória;
  - determinismo: 3 execuções com output sanitizado byte-idêntico;
  - suite < 10s; 4–6 arquivos de repo (fora test_app.py), 150–300 linhas totais;
  - test_app.py presente e idêntico a test_code (visível ao modelo, nunca executado).
Tasks reprovadas são descartadas e reportadas; congela com >=16 sobreviventes.

Uso: uv run python scripts/gera_tasks_swe.py [--out environment/tasks_swe.py]
"""
import argparse
import importlib
import json
import pprint
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from environment.sandbox import Sandbox  # noqa: E402

FAMILIA_MODULES = (
    "scripts.miniswe.familia_config_merge",
    "scripts.miniswe.familia_text_pipeline",
    "scripts.miniswe.familia_ledger",
    "scripts.miniswe.familia_graphlib",
    "scripts.miniswe.familia_statemachine",
)
REQUIRED_KEYS = {"task_id", "family", "prompt", "repo_files", "canonical_files",
                 "test_code", "bug_file"}
MIN_POOL = 16


def _run(files: dict[str, str], test_code: str) -> tuple[dict, float]:
    sb = Sandbox()
    try:
        for rel, content in files.items():
            sb.write_file(rel, content)
        t0 = time.monotonic()
        res = sb.run_tests(test_code)
        return res, time.monotonic() - t0
    finally:
        sb.cleanup()


def valida_task(task: dict) -> list[str]:
    """Retorna lista de motivos de reprovação (vazia = aprovada)."""
    erros = []
    faltam = REQUIRED_KEYS - set(task)
    if faltam:
        return [f"chaves faltando: {sorted(faltam)}"]
    repo = task["repo_files"]
    if repo.get("test_app.py") != task["test_code"]:
        erros.append("test_app.py ausente ou != test_code")
    if task["bug_file"] not in repo or task["bug_file"] not in task["canonical_files"]:
        erros.append("bug_file fora de repo_files/canonical_files")
    src = {k: v for k, v in repo.items() if k != "test_app.py"}
    if not 4 <= len(src) <= 6:
        erros.append(f"{len(src)} arquivos de repo (exigido 4-6)")
    n_linhas = sum(v.count("\n") for v in src.values())
    if not 150 <= n_linhas <= 300:
        erros.append(f"{n_linhas} linhas de repo (exigido 150-300)")
    if erros:
        return erros

    canon = {**repo, **task["canonical_files"]}
    res_c, dur_c = _run(canon, task["test_code"])
    if not res_c["success"]:
        erros.append(f"canônica não passa ({res_c['passed']}/{res_c['total']})")
    if res_c["total"] < 6 or res_c["total"] > 12:
        erros.append(f"{res_c['total']} testes (exigido 6-12)")

    outs, durs = [], []
    for _ in range(3):
        res_i, dur_i = _run(repo, task["test_code"])
        outs.append(res_i["output"])
        durs.append(dur_i)
    if not 0.0 < res_i["reward"] < 1.0:
        erros.append(f"reward inicial {res_i['reward']:.3f} fora de (0,1)")
    if len(set(outs)) != 1:
        erros.append("output inicial não-determinístico em 3 execuções")
    if max(durs + [dur_c]) >= 10.0:
        erros.append(f"suite lenta ({max(durs + [dur_c]):.1f}s >= 10s)")
    return erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment/tasks_swe.py")
    args = ap.parse_args()

    aprovadas, reprovadas = [], {}
    for mod_name in FAMILIA_MODULES:
        mod = importlib.import_module(mod_name)
        for task in mod.TASKS:
            erros = valida_task(task)
            if erros:
                reprovadas[task.get("task_id", "?")] = erros
            else:
                aprovadas.append(task)

    print(f"aprovadas: {len(aprovadas)} | reprovadas: {len(reprovadas)}")
    for tid, erros in reprovadas.items():
        print(f"  REPROVADA {tid}: {erros}")
    if len(aprovadas) < MIN_POOL:
        print(f"ABORTA: {len(aprovadas)} < {MIN_POOL} sobreviventes — recalibrar geração")
        sys.exit(1)

    aprovadas.sort(key=lambda t: t["task_id"])
    header = (f'"""Pool CONGELADO mini-SWE (piloto V2, pré-registro 28).\n\n'
              f'GERADO por scripts/gera_tasks_swe.py em 2026-08-25. NÃO EDITAR À MÃO.\n'
              f'Aprovadas: {len(aprovadas)} | reprovadas: {len(reprovadas)} '
              f'({json.dumps(sorted(reprovadas))}).\n"""\n\n')
    body = "TASKS: list[dict] = " + pprint.pformat(aprovadas, width=100, sort_dicts=True)
    footer = ('\n\nSTRATA: dict[str, str] = {t["task_id"]: t["family"] for t in TASKS}\n\n'
              '__all__ = ["TASKS", "STRATA"]\n\n\n'
              'def get_task(task_id: str) -> dict:\n'
              '    for t in TASKS:\n'
              '        if t["task_id"] == task_id:\n'
              '            return t\n'
              '    raise KeyError(task_id)\n')
    Path(args.out).write_text(header + body + footer, encoding="utf-8")
    print(f"congelado em {args.out}")


if __name__ == "__main__":
    main()
