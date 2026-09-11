"""Pré-registro 41 — análise agregada NDE/TE, mediação, horizonte e diagnóstico C1.

ZERO GPU/LLM: só leitura de artefatos em runs/. Saída: runs/preg41/report.json.

Uso: .venv/bin/python -m experiments.preg41
"""
import json
import math
import statistics
from pathlib import Path

from experiments.common import load_rows, load_trajectories

OUT = Path("runs/preg41")
V1_CONFIGS = ("g450", "g600", "g900", "mt4", "mt6", "mt8")
V1_FOLGA = ("g450", "g600", "g900")
V1_PRESSAO = ("mt4", "mt6", "mt8")
TESTE6_CFGS = ("g450", "g600", "g900", "mt6")
CELLS_EXT = ("mbpp_g600", "mbpp_mt6", "he_g600", "he_mt6",
             "q8_g600", "q8_mt4", "q8_mt6")
ARMS = ("outcome", "ch", "chm_cm")
SEEDS = (1, 2, 3)
EPS = 1e-9


def _r(x, nd=4):
    return round(x, nd) if isinstance(x, float) else x


def _quartis(vals: list[float]) -> dict:
    if not vals:
        return {"mediana": None, "q1": None, "q3": None, "max": None, "n": 0}
    vs = sorted(vals)
    if len(vs) >= 2:
        q = statistics.quantiles(vs, n=4, method="inclusive")
        q1, q3 = q[0], q[2]
    else:
        q1 = q3 = vs[0]
    return {"mediana": _r(statistics.median(vs)), "q1": _r(q1), "q3": _r(q3),
            "max": _r(max(vs)), "n": len(vs)}


# -- (a) tabela 2x2 ------------------------------------------------------------
def tabela_2x2(rows: list[dict], key_fn) -> dict:
    """pivotal := C_H != 0; nde_zero := exact_ha == True (C_Ha == 0)."""
    piv0 = piv1 = np0 = np1 = 0
    abs_te = []
    for r in rows:
        piv = r["C_H"] != 0
        nde0 = bool(r["exact_ha"])
        if piv and nde0:
            piv0 += 1
            abs_te.append(abs(r["C_H"]))
        elif piv:
            piv1 += 1
        elif nde0:
            np0 += 1
        else:
            np1 += 1
    den = piv0 + piv1
    m = piv0 / den if den else None
    # n efetivo dos PIVOTAIS: a mesma decisão medida em g450/g600/g900 conta uma vez
    piv_rows = [r for r in rows if r["C_H"] != 0]
    por_par: dict = {}
    for r in piv_rows:
        por_par.setdefault(key_fn(r), []).append(bool(r["exact_ha"]))
    pares_piv = len(por_par)
    pares_piv_nde0 = sum(all(v) for v in por_par.values())
    return {"piv_nde0": piv0, "piv_nde_nao0": piv1,
            "npiv_nde0": np0, "npiv_nde_nao0": np1,
            "m": _r(m) if m is not None else None,
            "abs_TE_piv_nde0": _quartis(abs_te),
            "pares_unicos": len({key_fn(r) for r in rows}),
            "tasks_unicas": len({r["task_id"] for r in rows}),
            "piv_pares_unicos": pares_piv,
            "piv_tasks_unicas": len({r["task_id"] for r in piv_rows}),
            "piv_pares_nde0": pares_piv_nde0,
            "m_por_par": _r(pares_piv_nde0 / pares_piv) if pares_piv else None}


def desfecho_m(m: float | None) -> str | None:
    if m is None:
        return None
    return "m1" if m >= 0.90 else ("m2" if m >= 0.60 else "m3")


def _key_v1(r):
    return (r["task_id"], r["cp_index"])


def _key_v2(r):
    return (r["task_id"], r["index"])


# -- (b) consistência de mediação ---------------------------------------------
def consistencia(rows: list[dict]) -> dict:
    """R_H = r_orig - C_H; consistente := r_cf_hm == R_H (abs diff < 1e-9)."""
    rows = [r for r in rows
            if r.get("found") is True and r.get("r_cf_hm") is not None]

    def _ok(r):
        return abs(r["r_cf_hm"] - (r["r_orig"] - r["C_H"])) < EPS

    def _stats(rs):
        n = len(rs)
        nc = sum(_ok(r) for r in rs)
        return {"n": n, "n_consistente": nc,
                "k": _r(nc / n) if n else None}

    total = _stats(rows)
    k = total["k"]
    desf = None if k is None else \
        ("k1" if k >= 0.75 else "k2" if k >= 0.50 else "k3")
    disc = []
    for r in rows:
        if _ok(r):
            continue
        rh = r["r_orig"] - r["C_H"]
        disc.append({"config": r["config"], "regime": r["regime"],
                     "task_id": r["task_id"], "cp_index": r["cp_index"],
                     "r_orig": r["r_orig"], "R_H": _r(rh),
                     "r_cf_hm": r["r_cf_hm"], "delta": _r(r["r_cf_hm"] - rh),
                     "C_H": r["C_H"], "C_M": r.get("C_M"),
                     "C_HM": r.get("C_HM")})
    return {"total": total,
            "por_regime": {reg: _stats([r for r in rows if r["regime"] == reg])
                           for reg in sorted({r["regime"] for r in rows})},
            "por_config": {c: _stats([r for r in rows if r["config"] == c])
                           for c in sorted({r["config"] for r in rows})},
            "desfecho": desf,
            "discordancias": disc}


# -- (c) Mann-Whitney ----------------------------------------------------------
def mann_whitney(x: list[float], y: list[float]) -> dict:
    """U de x e p unilateral para H1: x > y. Usa scipy se disponível."""
    if not x or not y:
        return {"U": None, "p": None}
    try:
        from scipy.stats import mannwhitneyu
        res = mannwhitneyu(x, y, alternative="greater")
        p = float(res.pvalue)
        if not math.isnan(p):
            return {"U": float(res.statistic), "p": p}
    except Exception:
        pass
    # aproximação normal com correção de empates e de continuidade
    n1, n2 = len(x), len(y)
    comb = sorted((v, i < n1) for i, v in enumerate(list(x) + list(y)))
    ranks, ties = {}, []
    i = 0
    r1 = 0.0
    while i < len(comb):
        j = i
        while j < len(comb) and comb[j][0] == comb[i][0]:
            j += 1
        t = j - i
        ties.append(t)
        rank = (i + 1 + j) / 2.0
        r1 += rank * sum(1 for k in range(i, j) if comb[k][1])
        i = j
    u1 = r1 - n1 * (n1 + 1) / 2.0
    n = n1 + n2
    mu = n1 * n2 / 2.0
    tie_corr = sum(t ** 3 - t for t in ties)
    var = n1 * n2 / 12.0 * ((n + 1) - tie_corr / (n * (n - 1)))
    if var <= 0:
        return {"U": u1, "p": None}
    z = (u1 - mu - 0.5) / math.sqrt(var)
    p = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    return {"U": u1, "p": p}


def horizonte_stats(pares: list[tuple[bool, int]]) -> dict:
    """pares: (nde_zero, H); só entradas com H válido."""
    h0 = [h for z, h in pares if z and h is not None]
    h1 = [h for z, h in pares if not z and h is not None]

    def _mm(vs):
        if not vs:
            return {"mediana": None, "media": None}
        return {"mediana": _r(statistics.median(vs)),
                "media": _r(statistics.mean(vs))}

    mw = mann_whitney(h1, h0)
    return {"n_nde0": len(h0), "n_nde_nao0": len(h1),
            "H_nde0": _mm(h0), "H_nde_nao0": _mm(h1),
            "mann_whitney_U": mw["U"],
            "p_unilateral": _r(mw["p"], 6) if mw["p"] is not None else None}


def _h_apos(traj, idx: int) -> int:
    return sum(1 for d in traj.decisions
               if d.decision_point == "tool_call" and d.index > idx)


def _trajs_v1(cfg: str) -> dict:
    return {t.trajectory_id: t
            for t in load_trajectories(Path(f"runs/teste0_{cfg}/baseline"))}


def _trajs_v2_base() -> dict:
    from experiments.census_v2 import _trajs_base
    return _trajs_base()


# -- (d) fatorial V2 por tipo --------------------------------------------------
def v2_fatorial(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0, "frac_I_fact_zero": None, "frac_nde_zero": None,
                "frac_TE_diff_NDE": None, "frac_screened": None}
    return {"n": n,
            "frac_I_fact_zero": _r(sum(r["I_fact"] == 0.0 for r in rows) / n),
            "frac_nde_zero": _r(sum(bool(r["exact_ha"]) for r in rows) / n),
            "frac_TE_diff_NDE": _r(sum(r["C_H"] != r["C_Ha"] for r in rows) / n),
            "frac_screened": _r(sum(r["C_HM"] == r["C_M"] for r in rows) / n)}


# -- (e) diagnóstico preg31/C1 -------------------------------------------------
def _grad_stats(rows: list[dict]) -> dict:
    gn = [r["grad_norm"] for r in rows]
    if not gn:
        return {"mediana": None, "media": None, "frac_zero": None}
    return {"mediana": _r(statistics.median(gn)), "media": _r(statistics.mean(gn)),
            "frac_zero": _r(sum(g == 0.0 for g in gn) / len(gn))}


def diagnostico_arm(rows: list[dict]) -> dict:
    """Braços com crédito (ch, chm_cm)."""
    n = len(rows)
    creds = [c for r in rows for c in r.get("credits", [])]
    abs_c = [abs(c["credit"]) for c in creds]
    nz = [c for c in creds if abs(c["credit"]) >= 1e-12]
    sem_nz = sum(1 for r in rows
                 if not any(abs(c["credit"]) >= 1e-12
                            for c in r.get("credits", [])))
    return {"n_episodios": n,
            "creditos_por_episodio": _r(len(creds) / n) if n else None,
            "frac_creditos_zero":
                _r((len(creds) - len(nz)) / len(creds)) if creds else None,
            "abs_credit": {"mediana": _r(statistics.median(abs_c)),
                           "media": _r(statistics.mean(abs_c)),
                           "max": _r(max(abs_c))} if abs_c else
                          {"mediana": None, "media": None, "max": None},
            "llm_calls_por_credito":
                _r(statistics.mean([c["llm_calls"] for c in creds]))
                if creds else None,
            "frac_episodios_sem_credito_nao_nulo": _r(sem_nz / n) if n else None,
            "grad_norm": _grad_stats(rows)}


def diagnostico_outcome(rows: list[dict]) -> dict:
    n = len(rows)
    reff = [r["R_eff"] for r in rows]
    return {"n_episodios": n,
            "grad_norm": _grad_stats(rows),
            "R_eff": {"media": _r(statistics.mean(reff)) if reff else None,
                      "desvio": _r(statistics.stdev(reff))
                      if len(reff) >= 2 else None}}


def _cp_counts(ep_dir: Path) -> list[int] | None:
    """Nº de decisões context_policy (cp_points) por episódio gravado."""
    if not ep_dir.is_dir():
        return None
    counts = []
    for p in sorted(ep_dir.glob("*.jsonl")):
        n = 0
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("kind") == "decision" and \
                        obj.get("decision_point") == "context_policy":
                    n += 1
        counts.append(n)
    return counts or None


def _diag_entry(arm: str, rows: list[dict], cp_counts: list[int] | None) -> dict:
    entry = diagnostico_outcome(rows) if arm == "outcome" else diagnostico_arm(rows)
    cp_mean = _r(statistics.mean(cp_counts)) if cp_counts else None
    entry["n_cp_points_por_episodio"] = cp_mean
    if arm == "outcome":
        entry["densidade"] = 1.0
    else:
        cpe = entry["creditos_por_episodio"]
        entry["densidade"] = _r(cpe / cp_mean) \
            if cpe is not None and cp_mean else None
    return entry


def diagnostico_preg31() -> tuple[dict, list[str]]:
    fontes = []
    por_arm_seed, agregado = {}, {}
    for arm in ARMS:
        pool_rows, pool_cp = [], []
        for seed in SEEDS:
            d = Path(f"runs/c1d_{arm}_s{seed}")
            log = d / "train_log.jsonl"
            if not log.exists():
                continue
            fontes.append(str(log))
            rows = load_rows(log)
            cp = _cp_counts(d / "episodes")
            por_arm_seed[f"{arm}_s{seed}"] = _diag_entry(arm, rows, cp)
            pool_rows += rows
            if cp:
                pool_cp += cp
        if pool_rows:
            agregado[arm] = _diag_entry(arm, pool_rows, pool_cp or None)
    return {"por_arm_seed": por_arm_seed, "agregado": agregado}, fontes


# -- (f) n efetivo -------------------------------------------------------------
def _n_efetivo(rows: list[dict], key_fn) -> dict:
    return {"n_pontos": len(rows),
            "pares_unicos": len({key_fn(r) for r in rows}),
            "tasks_unicas": len({r["task_id"] for r in rows}),
            "n_pivotais": sum(1 for r in rows if r["C_H"] != 0)}


def _census_v2_por_cfg() -> tuple[dict, list[str]]:
    fontes, vistos, por_cfg = [], set(), {}
    for nome in ("census_rows.jsonl", "census_esc_rows.jsonl"):
        p = Path("runs/census_v2") / nome
        if p.exists():
            fontes.append(str(p))
        for r in load_rows(p):
            if r.get("C_H") is None:
                continue
            k = (r["cfg"], r["task_id"], r["index"])
            if k in vistos:
                continue
            vistos.add(k)
            por_cfg.setdefault(r["cfg"], []).append(r)
    return por_cfg, fontes


# -- main ----------------------------------------------------------------------
def main():
    fontes = []
    p_v1 = Path("runs/preg40/v1_rows.jsonl")
    p_v2 = Path("runs/preg40/v2_rows.jsonl")
    fontes += [str(p) for p in (p_v1, p_v2) if p.exists()]
    v1 = load_rows(p_v1)
    v2_all = load_rows(p_v2)
    v2 = [r for r in v2_all if r.get("C_Ha") is not None and not r.get("error")]
    tipos = sorted({r["tipo"] for r in v2})
    folga = [r for r in v1 if r["cfg"] in V1_FOLGA]
    pressao = [r for r in v1 if r["cfg"] in V1_PRESSAO]

    # (a)
    tab_folga = tabela_2x2(folga, _key_v1)
    tab_folga["desfecho"] = desfecho_m(tab_folga["m"])
    tab_folga["por_cfg"] = {c: tabela_2x2([r for r in folga if r["cfg"] == c],
                                          _key_v1) for c in V1_FOLGA}
    tab_pressao = tabela_2x2(pressao, _key_v1)
    tab_pressao["por_cfg"] = {c: tabela_2x2([r for r in pressao
                                             if r["cfg"] == c], _key_v1)
                              for c in V1_PRESSAO}
    tabela = {"v1_folga": tab_folga, "v1_pressao": tab_pressao,
              "v2_total": tabela_2x2(v2, _key_v2),
              "v2_por_tipo": {t: tabela_2x2([r for r in v2 if r["tipo"] == t],
                                            _key_v2) for t in tipos}}

    # (b)
    t6_rows = []
    for cfg in TESTE6_CFGS:
        p = Path(f"runs/teste6_estimando/{cfg}/results.jsonl")
        if p.exists():
            fontes.append(str(p))
            t6_rows += load_rows(p)
    consist = consistencia(t6_rows)

    # (c) horizonte
    trajs_v1_cache: dict[str, dict] = {}
    h_v1 = {}
    for r in v1:
        cfg = r["cfg"]
        if cfg not in trajs_v1_cache:
            try:
                trajs_v1_cache[cfg] = _trajs_v1(cfg)
            except Exception:
                trajs_v1_cache[cfg] = {}
        traj = trajs_v1_cache[cfg].get(r.get("trajectory_id"))
        h_v1[id(r)] = _h_apos(traj, r["index"]) if traj is not None else None
    try:
        trajs_v2 = _trajs_v2_base()
    except Exception:
        trajs_v2 = {}
    h_v2 = {}
    for r in v2:
        traj = trajs_v2.get((r["cfg"], r["task_id"]))
        h_v2[id(r)] = _h_apos(traj, r["j"]) if traj is not None else None

    def _pares(rows, hmap):
        return [(bool(r["exact_ha"]), hmap[id(r)]) for r in rows
                if hmap[id(r)] is not None]

    # sensibilidade (revisor): só pivotais — não-pivotais têm NDE=0 trivialmente
    piv_folga = [r for r in folga if r["C_H"] != 0]
    piv_pressao = [r for r in pressao if r["C_H"] != 0]
    horizonte = {
        "v1_folga": horizonte_stats(_pares(folga, h_v1)),
        "v1_pressao": horizonte_stats(_pares(pressao, h_v1)),
        "v1_folga_so_pivotais": horizonte_stats(_pares(piv_folga, h_v1)),
        "v1_pressao_so_pivotais": horizonte_stats(_pares(piv_pressao, h_v1)),
        "v2_total": horizonte_stats(_pares(v2, h_v2)),
        "v2_por_tipo": {t: horizonte_stats(
            _pares([r for r in v2 if r["tipo"] == t], h_v2)) for t in tipos},
        "anatomia_v2_nde_nao0": [
            {"cfg": r["cfg"], "task_id": r["task_id"], "index": r["index"],
             "j": r["j"], "tipo": r["tipo"], "C_Ha": r["C_Ha"], "C_H": r["C_H"],
             "C_M": r["C_M"], "C_HM": r["C_HM"], "I_fact": r["I_fact"],
             "H": h_v2[id(r)]}
            for r in v2 if not r["exact_ha"]],
        "anatomia_v1_quebras": [
            {"cfg": r["cfg"], "task_id": r["task_id"], "cp_index": r["cp_index"],
             "C_Ha": r["C_Ha"], "C_H": r["C_H"], "C_M": r["C_M"],
             "C_HM": r["C_HM"], "I_fact": r["I_fact"], "H": h_v1[id(r)]}
            for r in v1 if not r["exact_ha"]],
    }

    # (d)
    fatorial = {"total": v2_fatorial(v2)}
    for t in tipos:
        fatorial[t] = v2_fatorial([r for r in v2 if r["tipo"] == t])

    # (e)
    diag, f_diag = diagnostico_preg31()
    fontes += f_diag

    # (f)
    n_ef = {}
    for cfg in V1_CONFIGS + CELLS_EXT:
        p = Path(f"runs/teste3_{cfg}/cf_results.jsonl")
        if not p.exists():
            continue
        fontes.append(str(p))
        n_ef[cfg] = _n_efetivo(load_rows(p), _key_v1)
    v2_cfg_rows, f_census = _census_v2_por_cfg()
    fontes += f_census
    for cfg in sorted(v2_cfg_rows):
        n_ef[cfg] = _n_efetivo(v2_cfg_rows[cfg], _key_v2)

    report = {
        "meta": {"pre_registro": 41, "fontes": fontes},
        "tabela_2x2": tabela,
        "consistencia_mediacao": consist,
        "horizonte": horizonte,
        "v2_fatorial_por_tipo": fatorial,
        "diagnostico_preg31": diag,
        "n_efetivo": n_ef,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"report": str(OUT / "report.json"),
                      "n_v1": len(v1), "n_v2_validos": len(v2),
                      "n_teste6": len(t6_rows)}, ensure_ascii=False),
          flush=True)
    return report


if __name__ == "__main__":
    main()
