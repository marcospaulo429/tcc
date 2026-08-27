"""Anatomia PÓS-HOC (exploratória, declarada no DESFECHO 39) das falhas de a′.

Para cada ponto sem_a_prime/sem_a_prime_esc do census 39, reamostra a′ no j
registrado gravando TODAS as tentativas (valid/differs/finish_reason + ação
canônica truncada) em temp 0.8 e 1.2. Só amostragem — nenhum replay, nenhuma
decisão de gate. Requer Qwen3-8B servindo.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("TCC_XFAM_OUT", "runs/preg39/census")
import experiments.census_v2 as cv

cv.OUT = Path("runs/preg39/census")
from agent.llm import LLMClient
from agent.loop_v2 import parse_action_v2
from experiments.common import append_row, load_rows
from interventions.model_v2 import _canonical

OUT = Path("runs/preg39")


def main():
    llm = LLMClient()
    assert "8B" in llm.model, f"esperava Qwen3-8B servindo, TCC_MODEL={llm.model}"
    trajs = cv._trajs_base()
    rows = load_rows(Path("runs/preg39/census/census_rows.jsonl"))
    alvo = [r for r in rows if r.get("error") == "sem_a_prime"]
    out_path = OUT / "anatomia_aprime.jsonl"
    feitos = {(r["task_id"], r["index"], r["temp"]) for r in load_rows(out_path)}
    for r in alvo:
        traj = trajs[(r["cfg"], r["task_id"])]
        j = r["j"]
        dj = traj.decisions[j]
        orig = cv._canon(dj.chosen_action)
        for temp in (0.8, 1.2):
            if (r["task_id"], r["index"], temp) in feitos:
                continue
            print(f"[anatomia] {r['task_id']} idx{r['index']} j={j} temp={temp}",
                  flush=True)
            tentativas = []
            for seed in range(2001, 2009):
                o = llm.chat(dj.state_before["messages"], temperature=temp,
                             seed=seed, max_tokens=2048)
                a = parse_action_v2(o["text"])
                fase2 = bool(a and a["action"] == "write_file" and "content" not in a)
                tentativas.append({
                    "seed": seed, "finish_reason": o.get("finish_reason"),
                    "valid": a is not None, "fase2_pendente": fase2,
                    "igual_original": bool(a and not fase2
                                           and _canonical(a) == _canonical(dj.chosen_action)),
                    "acao": (_canonical(a)[:120] if a else None),
                    "texto_bruto": o["text"][:120] if a is None else None})
            append_row(out_path, {
                "task_id": r["task_id"], "index": r["index"], "j": j,
                "tipo": r["tipo"], "temp": temp,
                "acao_original": json.dumps(orig, sort_keys=True)[:120],
                "tentativas": tentativas,
                "n_invalidas": sum(1 for t in tentativas if not t["valid"]),
                "n_iguais": sum(1 for t in tentativas if t["igual_original"]),
                "n_fase2": sum(1 for t in tentativas if t["fase2_pendente"])})
    # resumo
    rows_a = load_rows(out_path)
    tot = {"n_pontos": len({(r['task_id'], r['index']) for r in rows_a}),
           "tentativas": sum(len(r["tentativas"]) for r in rows_a),
           "invalidas": sum(r["n_invalidas"] for r in rows_a),
           "iguais_original": sum(r["n_iguais"] for r in rows_a),
           "fase2_pendentes": sum(r["n_fase2"] for r in rows_a)}
    (OUT / "anatomia_report.json").write_text(json.dumps(tot, indent=2))
    print(json.dumps(tot, indent=2))


def fase2():
    """2ª passada: resolve a fase 2 dos write_file pendentes e classifica."""
    from agent.loop_v2 import _BLOCK_RE, PEDIDO_CONTEUDO
    llm = LLMClient()
    assert "8B" in llm.model
    trajs = cv._trajs_base()
    out_path = OUT / "anatomia_fase2.jsonl"
    feitos = {(r["task_id"], r["index"], r["temp"], r["seed"])
              for r in load_rows(out_path)}
    for r in load_rows(OUT / "anatomia_aprime.jsonl"):
        traj = trajs[("v2_default", r["task_id"])]
        dj = traj.decisions[r["j"]]
        orig = _canonical(cv._canon(dj.chosen_action))
        for t in r["tentativas"]:
            if not t["fase2_pendente"]:
                continue
            chave = (r["task_id"], r["index"], r["temp"], t["seed"])
            if chave in feitos:
                continue
            path = json.loads(t["acao"])["path"]
            tmp = dj.state_before["messages"] + [
                {"role": "assistant", "content": f"WRITE {path}"},
                {"role": "user", "content": PEDIDO_CONTEUDO.format(path=path)}]
            o = llm.chat(tmp, temperature=r["temp"], seed=t["seed"],
                         max_tokens=2048)
            b = _BLOCK_RE.search(o["text"])
            acao = ({"action": "write_file", "path": path, "content": b.group(1)}
                    if b else None)
            append_row(out_path, {
                "task_id": r["task_id"], "index": r["index"], "temp": r["temp"],
                "seed": t["seed"], "sem_bloco": b is None,
                "igual_original": bool(acao and _canonical(acao) == orig),
                "finish_reason": o.get("finish_reason")})
    rows = load_rows(out_path)
    tot = {"n": len(rows),
           "sem_bloco": sum(r["sem_bloco"] for r in rows),
           "iguais_original": sum(r["igual_original"] for r in rows),
           "differs": sum(1 for r in rows
                          if not r["sem_bloco"] and not r["igual_original"])}
    (OUT / "anatomia_fase2_report.json").write_text(json.dumps(tot, indent=2))
    print(json.dumps(tot, indent=2))


if __name__ == "__main__":
    import sys
    fase2() if "--fase2" in sys.argv else main()
