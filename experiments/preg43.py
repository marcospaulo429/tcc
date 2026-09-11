"""Pré-registro 43 — estratificação por horizonte: mediação proximal medida vs.
implicada pela Cor. behav.

ZERO GPU/LLM: releitura de runs/preg40/{v1,v2}_rows.jsonl, runs/preg42/rows.jsonl
e das trajetórias originais (runs/teste0_*/baseline, census V2).
Saída: runs/preg43/report.json.

Variáveis por ponto (trajetória ORIGINAL, decisões tool_call com index > j):
  H     = nº total de tool_calls após j (igual a preg41._h_apos);
  H_w   = nº daquelas com chosen_action["action"] == "write_file";
  H_env = nº daquelas com action != "finish".
Estrato "implicado" := H_w == 0; "informativo" := H_w >= 1.

Teste de permutação em nível de task (perm_stat = "diff_medias_H_task_mediana"):
o rótulo de task é any(NDE != 0) entre seus pontos; H_task é a MEDIANA de H dos
pontos da task; a estatística observada é mean(H_task | rótulo=1) −
mean(H_task | rótulo=0); a permutação embaralha os rótulos entre as tasks
(cada task é a unidade, pontos da mesma task movem juntos), 20.000 permutações,
random.Random(43); p unilateral (greater) = (1 + #{stat_perm >= stat_obs}) /
(20.000 + 1). Repetido com H_w no lugar de H.

Uso: .venv/bin/python -m experiments.preg43
"""
import json
import random
import statistics
from collections import Counter
from pathlib import Path

from experiments.common import load_rows
from experiments.preg41 import (_h_apos, _r, _trajs_v1, _trajs_v2_base,
                                horizonte_stats)

OUT = Path("runs/preg43")
V1_FOLGA = ("g450", "g600", "g900")
V1_PRESSAO = ("mt4", "mt6", "mt8")
CELLS_EXT4B = ("mbpp_g600", "mbpp_mt6", "he_g600", "he_mt6")
CELLS_Q8 = ("q8_g600", "q8_mt4", "q8_mt6")
N_PERMS = 20_000
SEED = 43
PERM_STAT = ("diff_medias_H_task_mediana: rotulo_task=any(NDE!=0); "
             "H_task=mediana(H dos pontos); stat=mean(H_task|1)-mean(H_task|0); "
             "permuta rotulos entre tasks (cluster), 20000 perms, seed 43, "
             "p=(1+#{>=obs})/(N+1)")


def _counts_h(pontos: list[dict], key: str, incluir: bool | None = None) -> int:
    return sum(1 for p in pontos if incluir is None or p["nde0"] is incluir)


def _dist(vals: list[int]) -> dict:
    return {str(k): v for k, v in sorted(Counter(vals).items())}


def _h_write_env(traj, idx: int) -> tuple[int, int]:
    """(H_w, H_env) das tool_calls após idx na trajetória original."""
    hw = henv = 0
    for d in traj.decisions:
        if d.decision_point != "tool_call" or d.index <= idx:
            continue
        act = d.chosen_action.get("action")
        if act == "write_file":
            hw += 1
        if act != "finish":
            henv += 1
    return hw, henv


def _ponto(r: dict, traj, j: int) -> dict:
    hw, henv = _h_write_env(traj, j)
    return {"task_id": r["task_id"], "cfg": r["cfg"],
            "cp_index": r.get("cp_index", r.get("index")),
            "C_H": r["C_H"], "C_Ha": r["C_Ha"],
            "nde0": r["C_Ha"] == 0,
            "H": _h_apos(traj, j), "H_w": hw, "H_env": henv}


def _taxa(k: int, n: int):
    return _r(k / n) if n else None


def estratos(pontos: list[dict]) -> dict:
    n = len(pontos)
    nde0 = [p for p in pontos if p["nde0"]]
    hw0 = [p for p in pontos if p["H_w"] == 0]
    violacoes = [{"task_id": p["task_id"], "cfg": p["cfg"],
                  "cp_index": p["cp_index"], "C_Ha": p["C_Ha"]}
                 for p in hw0 if not p["nde0"]]

    def _endpoint(pred) -> dict:
        estrato = [p for p in pontos if pred(p)]
        k = sum(p["nde0"] for p in estrato)
        return {"k": k, "n": len(estrato), "taxa": _taxa(k, len(estrato))}

    return {
        "n": n, "n_nde0": len(nde0),
        "dist_H": _dist([p["H"] for p in pontos]),
        "dist_H_w": _dist([p["H_w"] for p in pontos]),
        "frac_Hw0": _taxa(len(hw0), n),
        "frac_nde0_implicado_Hw0":
            _taxa(sum(p["H_w"] == 0 for p in nde0), len(nde0)),
        "checagem_implicacao": {
            "taxa_nde0_em_Hw0": _taxa(sum(p["nde0"] for p in hw0), len(hw0)),
            "n_Hw0": len(hw0), "violacoes": violacoes},
        "endpoint_Hw_ge1": _endpoint(lambda p: p["H_w"] >= 1),
        "sens_Henv_ge1": _endpoint(lambda p: p["H_env"] >= 1),
        "sens_H_ge2": _endpoint(lambda p: p["H"] >= 2),
    }


def perm_task_level(pontos: list[dict], hkey: str) -> dict:
    """p por permutação cluster em nível de task; ver PERM_STAT no docstring."""
    por_task: dict[str, list[dict]] = {}
    for p in pontos:
        por_task.setdefault(p["task_id"], []).append(p)
    tasks = sorted(por_task)
    h_task = [statistics.median([p[hkey] for p in por_task[t]]) for t in tasks]
    rotulos = [any(not p["nde0"] for p in por_task[t]) for t in tasks]

    def _stat(rots) -> float | None:
        g1 = [h for h, z in zip(h_task, rots) if z]
        g0 = [h for h, z in zip(h_task, rots) if not z]
        if not g1 or not g0:
            return None
        return statistics.mean(g1) - statistics.mean(g0)

    obs = _stat(rotulos)
    base = {"n_tasks": len(tasks),
            "n_tasks_nde_nao0": sum(rotulos),
            "stat_obs": _r(obs) if obs is not None else None}
    if obs is None:
        return {**base, "p_perm": None}
    rng = random.Random(SEED)
    rots = list(rotulos)
    ge = 0
    for _ in range(N_PERMS):
        rng.shuffle(rots)
        s = _stat(rots)
        if s is not None and s >= obs:
            ge += 1
    return {**base, "p_perm": _r((1 + ge) / (N_PERMS + 1), 6)}


def holm(ps: dict[str, float | None]) -> dict[str, float | None]:
    """Holm step-down sobre os p não nulos; None permanece None."""
    validos = sorted((p, k) for k, p in ps.items() if p is not None)
    m = len(validos)
    adj, cummax = {}, 0.0
    for i, (p, k) in enumerate(validos):
        cummax = max(cummax, (m - i) * p)
        adj[k] = _r(min(1.0, cummax), 6)
    return {k: adj.get(k) for k in ps}


def _mw_familia(populacoes: dict[str, list[dict]], hkey: str) -> dict:
    res = {}
    for nome, pontos in populacoes.items():
        pares = [(p["nde0"], p[hkey]) for p in pontos]
        res[nome] = {"analitico": horizonte_stats(pares),
                     "permutacao": perm_task_level(pontos, hkey)}
    adj_a = holm({n: res[n]["analitico"]["p_unilateral"] for n in res})
    adj_p = holm({n: res[n]["permutacao"]["p_perm"] for n in res})
    for nome in res:
        res[nome]["analitico"]["p_holm"] = adj_a[nome]
        res[nome]["permutacao"]["p_holm"] = adj_p[nome]
    return res


def desfecho(taxa: float | None) -> str | None:
    if taxa is None:
        return None
    return "h1" if taxa >= 0.75 else ("h2" if taxa >= 0.50 else "h3")


def main():
    p_v1 = Path("runs/preg40/v1_rows.jsonl")
    p_v2 = Path("runs/preg40/v2_rows.jsonl")
    p_42 = Path("runs/preg42/rows.jsonl")
    v1 = load_rows(p_v1)
    v2_all = load_rows(p_v2)
    v2 = [r for r in v2_all if r.get("C_Ha") is not None and not r.get("error")]
    r42 = load_rows(p_42)
    meta_rows = {str(p_v1): len(v1), str(p_v2): len(v2_all), str(p_42): len(r42)}

    sem_traj = []
    trajs_v1_cache: dict[str, dict] = {}

    def _pontos_v1like(rows: list[dict]) -> list[dict]:
        pontos = []
        for r in rows:
            cfg = r["cfg"]
            if cfg not in trajs_v1_cache:
                trajs_v1_cache[cfg] = _trajs_v1(cfg)
            traj = trajs_v1_cache[cfg].get(r.get("trajectory_id"))
            if traj is None:
                sem_traj.append({"cfg": cfg, "task_id": r["task_id"],
                                 "trajectory_id": r.get("trajectory_id")})
                continue
            pontos.append(_ponto(r, traj, r["index"]))
        return pontos

    trajs_v2 = _trajs_v2_base()

    def _pontos_v2(rows: list[dict]) -> list[dict]:
        pontos = []
        for r in rows:
            traj = trajs_v2.get((r["cfg"], r["task_id"]))
            if traj is None:
                sem_traj.append({"cfg": r["cfg"], "task_id": r["task_id"]})
                continue
            pontos.append(_ponto(r, traj, r["j"]))
        return pontos

    # populações (só pivotais; ext4b também screened, q8 com e sem screening)
    piv_v1 = [r for r in v1 if r["C_H"] != 0]
    pop = {
        "v1_folga": _pontos_v1like([r for r in piv_v1 if r["cfg"] in V1_FOLGA]),
        "v1_pressao": _pontos_v1like(
            [r for r in piv_v1 if r["cfg"] in V1_PRESSAO]),
        "ext4b": _pontos_v1like(
            [r for r in r42 if r["cfg"] in CELLS_EXT4B
             and r["pivotal"] and r["screened"]]),
        "q8": _pontos_v1like(
            [r for r in r42 if r["cfg"] in CELLS_Q8 and r["pivotal"]]),
        "v2_context": _pontos_v2(
            [r for r in v2 if r["tipo"] == "context_policy" and r["C_H"] != 0]),
        "v2_observation": _pontos_v2(
            [r for r in v2 if r["tipo"] == "observation_policy"
             and r["C_H"] != 0]),
    }
    # descritivo apenas: termination tem caminho direto por construção
    term_desc = _pontos_v2(
        [r for r in v2 if r["tipo"] == "termination" and r["C_H"] != 0])
    # v2_total (família MW) = context + observation + test_schedule (38 pts);
    # termination excluída — pré-registro 43
    v2_total = pop["v2_context"] + pop["v2_observation"] + _pontos_v2(
        [r for r in v2 if r["tipo"] == "test_schedule" and r["C_H"] != 0])

    def _nde0(nome):
        return sum(p["nde0"] for p in pop[nome])

    assert len(pop["v1_folga"]) == 37 and _nde0("v1_folga") == 36, \
        (len(pop["v1_folga"]), _nde0("v1_folga"))
    assert len(pop["ext4b"]) == 49 and _nde0("ext4b") == 48, \
        (len(pop["ext4b"]), _nde0("ext4b"))
    assert len(pop["v2_context"]) == 23 and _nde0("v2_context") == 13, \
        (len(pop["v2_context"]), _nde0("v2_context"))
    assert len(pop["v2_observation"]) == 12 and _nde0("v2_observation") == 4, \
        (len(pop["v2_observation"]), _nde0("v2_observation"))
    assert len(pop["q8"]) == 74 and _nde0("q8") == 51, \
        (len(pop["q8"]), _nde0("q8"))

    pool = pop["v1_folga"] + pop["ext4b"]
    estr = {nome: estratos(pontos) for nome, pontos in pop.items()}
    estr_pool = estratos(pool)
    estr_pool["desfecho"] = desfecho(estr_pool["endpoint_Hw_ge1"]["taxa"])

    familia = {"v1_folga": pop["v1_folga"], "v1_pressao": pop["v1_pressao"],
               "v2_total": v2_total, "v2_context": pop["v2_context"],
               "v2_observation": pop["v2_observation"], "ext4b": pop["ext4b"]}

    # adendo 43a (descritivo): NDE=0 por valor exato de H_w; mediana em H_w>=1
    def _por_hw(pontos: list[dict]) -> dict:
        bins = {"0": lambda h: h == 0, "1": lambda h: h == 1,
                "2": lambda h: h == 2, ">=3": lambda h: h >= 3}
        out = {}
        for b, f in bins.items():
            sel = [p for p in pontos if f(p["H_w"])]
            out[b] = {"k": sum(p["nde0"] for p in sel), "n": len(sel),
                      "taxa": _taxa(sum(p["nde0"] for p in sel), len(sel))}
        ge1 = sorted(p["H_w"] for p in pontos if p["H_w"] >= 1)
        out["mediana_Hw_em_ge1"] = statistics.median(ge1) if ge1 else None
        out["n_ge1"] = len(ge1)
        # decisões únicas (task, cp_index): medeia se todos os seus pontos medeiam
        for nome, f in (("ge1", lambda h: h >= 1), ("eq1", lambda h: h == 1)):
            dec: dict[tuple, list[bool]] = {}
            for p in pontos:
                if f(p["H_w"]):
                    dec.setdefault((p["task_id"], p["cp_index"]), []).append(p["nde0"])
            out[f"decisoes_unicas_{nome}"] = {
                "k": sum(all(v) for v in dec.values()), "n": len(dec),
                "tasks": len({t for t, _ in dec})}
        return out

    por_hw = {nome: _por_hw(pontos) for nome, pontos in pop.items()}
    por_hw["pool_headline"] = _por_hw(pool)
    # desagregados citados na Tab. 2 do paper (por benchmark; 8B por blindagem)
    por_hw["ext4b_mbpp"] = _por_hw([p for p in pop["ext4b"] if p["cfg"].startswith("mbpp")])
    por_hw["ext4b_he"] = _por_hw([p for p in pop["ext4b"] if p["cfg"].startswith("he")])
    q8_scr = {(r["cfg"], r["task_id"], r["cp_index"]): r["screened"]
              for r in r42 if r["cfg"] in CELLS_Q8}
    por_hw["q8_screened"] = _por_hw(
        [p for p in pop["q8"] if q8_scr[(p["cfg"], p["task_id"], p["cp_index"])]])
    por_hw["q8_nonscreened"] = _por_hw(
        [p for p in pop["q8"] if not q8_scr[(p["cfg"], p["task_id"], p["cp_index"])]])

    # n efetivo e IC Clopper–Pearson do endpoint H_w >= 1 (pool headline)
    def _cp_ci(k: int, n: int) -> list[float]:
        from scipy.stats import beta
        lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
        hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
        return [_r(lo), _r(hi)]

    inf = [p for p in pool if p["H_w"] >= 1]
    dec: dict[tuple, list[bool]] = {}
    tsk: dict[str, list[bool]] = {}
    for p in inf:
        dec.setdefault((p["task_id"], p["cp_index"]), []).append(p["nde0"])
        tsk.setdefault(p["task_id"], []).append(p["nde0"])
    k_pts, n_pts = sum(p["nde0"] for p in inf), len(inf)
    k_dec, n_dec = sum(all(v) for v in dec.values()), len(dec)
    k_tsk, n_tsk = sum(all(v) for v in tsk.values()), len(tsk)
    n_efetivo = {"pontos": {"k": k_pts, "n": n_pts, "ci95_cp": _cp_ci(k_pts, n_pts)},
                 "decisoes_unicas": {"k": k_dec, "n": n_dec, "ci95_cp": _cp_ci(k_dec, n_dec)},
                 "tasks_unicas": {"k": k_tsk, "n": n_tsk}}

    report = {
        "meta": {
            "pre_registro": 43,
            "rows_lidas": meta_rows,
            "n_pontos_sem_trajetoria": len(sem_traj),
            "pontos_sem_trajetoria": sem_traj,
            "perm_stat": PERM_STAT,
            "nota_v2_total": ("v2_total = context+observation+test_schedule "
                              f"({len(v2_total)} pontos); termination "
                              f"({len(term_desc)} pts) excluída da família — "
                              "caminho direto por construção"),
        },
        "populacoes": estr,
        "pool_headline_v1folga_ext4b": estr_pool,
        "v2_termination_descritivo": estratos(term_desc),
        "testes_horizonte": {"H": _mw_familia(familia, "H"),
                             "H_w": _mw_familia(familia, "H_w")},
        "adendo_43a_por_Hw": por_hw,
        "n_efetivo_Hw_ge1_headline": n_efetivo,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return report


if __name__ == "__main__":
    main()
