"""Gera as figuras F1-F7 do paper a partir dos artefatos em experiments/results/ e runs/.

Uso: uv run python paper/figs.py  (salva PDFs em paper/figures/)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "experiments" / "results"
RUNS = ROOT / "runs"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 150,
})

COL_SLACK = "#2b7bba"
COL_PRESS = "#d95f02"
COL_GREY = "#888888"


def load(p: Path) -> dict:
    return json.loads(p.read_text())


# ---------------------------------------------------------------- F1: piso
def fig1() -> None:
    configs = [
        ("base", RES / "2026-08-21_teste0_summary.json"),
        ("v2", RES / "2026-08-21_teste0_v2_summary.json"),
        ("v2b", RES / "2026-08-22_teste0_v2b_summary.json"),
        ("g450", RES / "2026-08-22_teste0_g450_summary.json"),
        ("g600", RES / "2026-08-22_teste0_g600_summary.json"),
        ("g900", RES / "2026-08-22_teste0_g900_summary.json"),
        ("mt6", RES / "2026-08-22_teste0_mt6_summary.json"),
    ]
    names, ns = [], []
    for name, p in configs:
        d = load(p)
        names.append(name)
        ns.append(d["n_replays"])
        assert d["noise_floor"] == 0.0 and d["exact_rate"] == 1.0
    # 1.7B (D2c): nulos exatos nas 2 configs (null_results.jsonl: 32+32, 0 inexatos)
    names += ["1.7B g600", "1.7B mt6"]
    ns += [32, 32]

    apc = load(RUNS / "_apc_contaminado" / "teste0_g600" / "summary.json")

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(6.0, 2.2), gridspec_kw={"width_ratios": [3, 1.4]}
    )
    colors = [COL_SLACK] * 7 + ["#6a51a3"] * 2
    ax.bar(range(len(names)), ns, color=colors)
    for i, n in enumerate(ns):
        ax.text(i, n + 8, "0/%d" % n, ha="center", fontsize=7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_ylabel("null replays")
    ax.set_ylim(0, 320)
    ax.set_title("(a) APC off: every null replay exact ($|\\Delta R|=0$)")

    ax2.bar([0, 1], [0.0, apc["noise_floor"]], color=[COL_SLACK, "#c0392b"])
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["APC off", "APC on"])
    ax2.set_ylabel("noise floor $\\max|\\Delta R|$")
    ax2.text(1, apc["noise_floor"] + 0.01, f"{apc['noise_floor']:.3f}", ha="center", fontsize=7)
    ax2.text(0, 0.01, "0.0", ha="center", fontsize=7)
    ax2.set_title("(b) prefix caching\nbreaks determinism")
    fig.tight_layout()
    fig.savefig(OUT / "f1_noise_floor.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------- F2: distribuições C_H, C_M
def fig2() -> None:
    rows = [json.loads(l) for l in (RUNS / "credit_dataset.jsonl").open()]
    strata = ["V2", "L", "S", "C"]
    fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.3), sharey=True)
    for ax, q in zip(axes, ["C_H", "C_M"]):
        data = [
            [r["value"] for r in rows if r["quantity"] == q and r["stratum"] == s]
            for s in strata
        ]
        parts = ax.violinplot(
            [d if d else [0.0] for d in data], showmedians=True, widths=0.8
        )
        for pc in parts["bodies"]:
            pc.set_facecolor(COL_SLACK if q == "C_H" else COL_PRESS)
            pc.set_alpha(0.5)
        for i, d in enumerate(data):
            x = np.random.default_rng(0).normal(i + 1, 0.06, len(d))
            ax.plot(x, d, ".", ms=2.5, color="k", alpha=0.35)
            ax.text(i + 1, 1.12, f"n={len(d)}", ha="center", fontsize=7)
        ax.axhline(0, color=COL_GREY, lw=0.6, ls=":")
        ax.set_xticks(range(1, len(strata) + 1))
        ax.set_xticklabels(strata)
        ax.set_title(f"$C(H)$" if q == "C_H" else "$C(M)$")
        ax.set_ylim(-1.25, 1.25)
    axes[0].set_ylabel("per-decision credit")
    fig.tight_layout()
    fig.savefig(OUT / "f2_credit_distributions.pdf", bbox_inches="tight")
    plt.close(fig)


# ----------------------------- F3: regime-dependence do screening-off
def fig3() -> None:
    wc = load(RES / "2026-08-23_wc_wb_analises.json")["por_config"]
    rep = {r["tag"]: r["all"] for r in load(RES / "2026-08-24_replicacao.json")}
    order = ["g450", "g600(mt12)", "g900", "mt8", "mt6", "mt4", "q17_g600", "q17_mt6"]
    labels = ["g450", "g600", "g900", "mt8", "mt6", "mt4", "1.7B\ng600", "1.7B\nmt6"]
    raw = [wc[k]["taxa_bruta"] for k in order]
    cond = [wc[k]["taxa_nonsat"] for k in order]
    nn = [(wc[k]["quebras"], wc[k]["n"]) for k in order]
    nns = [(wc[k]["quebras_nonsat"], wc[k]["n_nonsat"]) for k in order]
    extra = ["q8_g600", "q8_mt6", "q8_mt4", "v5cur_g600", "v5cur_mt6",
             "q4cur_g600", "q4cur_mt6", "mbpp_g600", "mbpp_mt6"]
    labels += ["8B\ng600", "8B\nmt6", "8B\nmt4", "8B cur\ng600", "8B cur\nmt6",
               "4B cur\ng600", "4B cur\nmt6", "MBPP+\ng600", "MBPP+\nmt6"]
    for k in extra:
        a = rep[k]
        raw.append((a["n"] - a["n_screened_exact"]) / a["n"])
        cond.append(a["n_breaks_nonsat"] / a["n_nonsat"] if a["n_nonsat"] else 0.0)
        nn.append((a["n"] - a["n_screened_exact"], a["n"]))
        nns.append((a["n_breaks_nonsat"], a["n_nonsat"]))

    cols = ([COL_SLACK] * 3 + [COL_PRESS] * 3 + ["#6a51a3"] * 2
            + ["#a63603"] * 3 + ["#e6550d"] * 2 + ["#08519c"] * 2 + ["#238b45"] * 2)
    w = 0.38
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(5.5, 3.8))
    rows = [(ax_top, slice(0, 8)), (ax_bot, slice(8, 17))]
    for ax, sl in rows:
        idx = range(*sl.indices(len(labels)))
        x = np.arange(len(list(idx)))
        r = raw[sl]
        c = cond[sl]
        ax.bar(x - w / 2, r, w, color=cols[sl], alpha=0.55, label="raw")
        ax.bar(x + w / 2, c, w, color=cols[sl], hatch="//",
               label="non-saturated only")
        for i, j in enumerate(idx):
            ax.text(x[i] - w / 2, r[i] + 0.015, "%d/%d" % nn[j], ha="center",
                    fontsize=6.5)
            ax.text(x[i] + w / 2, c[i] + 0.015, "%d/%d" % nns[j], ha="center",
                    fontsize=6.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels[sl], fontsize=6.5)
        ax.set_ylabel("break rate", fontsize=8)
        ax.set_ylim(0, 0.62)
        ax.set_xlim(-0.6, len(x) - 0.4)
    # linha de cima: 4B slack/pressure + 1.7B
    ax_top.axvspan(-0.5, 2.5, color=COL_SLACK, alpha=0.05)
    ax_top.axvspan(2.5, 5.5, color=COL_PRESS, alpha=0.05)
    ax_top.text(1.0, 0.55, "budget slack (Qwen3-4B)", ha="center", fontsize=6.5,
                color=COL_SLACK)
    ax_top.text(4.0, 0.55, "budget pressure", ha="center", fontsize=6.5,
                color=COL_PRESS)
    ax_top.text(6.5, 0.55, "1.7B", ha="center", fontsize=6.5, color="#6a51a3")
    # linha de baixo: 8B, curated, MBPP+
    ax_bot.axvspan(-0.5, 2.5, color="#a63603", alpha=0.05)
    ax_bot.axvspan(2.5, 4.5, color="#e6550d", alpha=0.05)
    ax_bot.axvspan(4.5, 6.5, color="#08519c", alpha=0.05)
    ax_bot.axvspan(6.5, 8.5, color="#238b45", alpha=0.05)
    ax_bot.text(1.0, 0.55, "Qwen3-8B (raw flat)", ha="center", fontsize=6.5,
                color="#a63603")
    ax_bot.text(3.5, 0.55, "8B curated", ha="center", fontsize=6.5, color="#e6550d")
    ax_bot.text(5.5, 0.55, "4B curated", ha="center", fontsize=6.5, color="#08519c")
    ax_bot.text(7.5, 0.55, "MBPP+ (4B)", ha="center", fontsize=6.5, color="#238b45")
    ax_top.legend(loc="center right", frameon=False, fontsize=6.5)
    fig.tight_layout()
    fig.savefig(OUT / "f3_regime_dependence.pdf", bbox_inches="tight")
    plt.close(fig)


# --------------------------------- F4: estrutura do crédito (critic)
def fig4() -> None:
    d = load(RUNS / "critic_por_estrato.json")
    strata = ["L", "V2", "S"]
    models = [
        ("gbm", "GBM critic", "#1b7837"),
        ("linear", "linear critic", "#7fbf7b"),
    ]
    bases = [
        ("position", "position heuristic", COL_GREY),
        ("context_size", "|context| heuristic", "#4d4d4d"),
    ]
    x = np.arange(len(strata))
    w = 0.2
    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    for j, (key, lab, c) in enumerate(models):
        vals = [d[s][key]["spearman_clustered"] for s in strata]
        ax.bar(x + (j - 1.5) * w, vals, w, label=lab, color=c)
    for j, (key, lab, c) in enumerate(bases):
        vals = [abs(d[s]["baselines"][key]["spearman_clustered"]) for s in strata]
        ax.bar(x + (j + 0.5) * w, vals, w, label=lab, color=c, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s} (n={d[s]['n']})" for s in strata])
    ax.set_ylabel("|Spearman| (task-clustered)")
    ax.set_ylim(0, 1.1)
    ax.legend(frameon=False, ncol=2, fontsize=6.5)
    fig.tight_layout()
    fig.savefig(OUT / "f4_credit_structure.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------ F5: treino (Act 4 / C1d)
def fig5() -> None:
    arms = ["outcome", "ch", "chm_cm", "zero"]
    labels = ["outcome-only", "$C(H)$", "$C_{HM}{-}C_M$", "zero (control)"]
    vals_by_arm = {
        arm: [load(RUNS / f"c1d_{arm}_s{s}" / "summary.json")["heldout"]["mean_R_eff"]
              for s in (1, 2, 3)]
        for arm in arms
    }
    # atratores held-out sob lambda*=5 (pré-reg 27): keep/thr600 do c1c_margem,
    # summarize-always do c1d_margem; R_eff = R - 5*tokens/1e5
    pool = load(RUNS / "c1d_margem" / "pool.json")
    held = pool["heldout"]
    lam = pool["lambda_star"]
    mr = load(RUNS / "c1c_margem" / "margem_report.json")
    summ = load(RUNS / "c1d_margem" / "summ_report.json")

    def reff_mean(entries: list[dict]) -> float:
        return sum(e["reward"] - lam * e["prompt_tokens"] / 1e5 for e in entries) / len(entries)

    thr600 = reff_mean([mr[t]["thr600"] for t in held])
    keep = reff_mean([mr[t]["keep"] for t in held])
    summ_always = reff_mean([summ[t] for t in held])
    assert abs(thr600 - 0.455) < 5e-3 and abs(keep - 0.392) < 5e-3 \
        and abs(summ_always - (-0.031)) < 5e-3, (thr600, keep, summ_always)

    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    rng = np.random.default_rng(1)
    for i, arm in enumerate(arms):
        xs = i + rng.normal(0, 0.04, 3)
        ax.plot(xs, vals_by_arm[arm], "o", ms=6,
                color=COL_PRESS if arm in ("ch", "chm_cm") else COL_SLACK)
    # controle episode-matched (pré-reg 31): outcome fatiado no N do braço ch
    em = load(RUNS / "ato4_em" / "summary.json")["cells"]
    em_vals = [em[f"ch_match_s{s}"]["mean_R_eff"] for s in (1, 2, 3)]
    xs = 0 + rng.normal(0, 0.04, 3) + 0.18
    ax.plot(xs, em_vals, "o", ms=6, mfc="none", mec=COL_SLACK, mew=1.2,
            label="episode-matched (pre-reg 31)")
    ax.axhline(thr600, color="#1b7837", ls="--", lw=1)
    ax.text(3.45, thr600 + 0.012, "thr600 (best fixed)", fontsize=7,
            color="#1b7837", ha="right")
    ax.axhline(keep, color=COL_GREY, ls=":", lw=1)
    ax.text(3.45, keep - 0.045, "keep-always", fontsize=7, color=COL_GREY, ha="right")
    ax.axhline(summ_always, color="#c0392b", ls=":", lw=1)
    ax.text(3.45, summ_always + 0.012, "summarize-always", fontsize=7,
            color="#c0392b", ha="right")
    ax.set_xticks(range(4))
    ax.set_xticklabels(labels)
    ax.set_ylabel("held-out $R_{\\mathrm{eff}}$")
    ax.set_ylim(-0.1, 0.5)
    ax.legend(frameon=False, fontsize=6.5, loc="lower left")
    ax.set_title("Act 4 (sane objective, pre-reg 27): 3 seeds per arm")
    fig.tight_layout()
    fig.savefig(OUT / "f5_training.pdf", bbox_inches="tight")
    plt.close(fig)


# --------------------------- F6: mediação TE vs NDE (scatter, pré-reg 40)
V2_TYPE_COLS = {
    "context_policy": COL_SLACK,
    "observation_policy": "#1b7837",
    "test_schedule": "#6a51a3",
    "termination": "#c0392b",
}


def _load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open()]


def fig6_mediation_scatter() -> None:
    v1 = _load_jsonl(RUNS / "preg40" / "v1_rows.jsonl")
    v2 = _load_jsonl(RUNS / "preg40" / "v2_rows.jsonl")
    slack = {"g450", "g600", "g900"}

    piv_slack = [r for r in v1 if r["cfg"] in slack and r["C_H"] != 0]
    piv_press = [r for r in v1 if r["cfg"] not in slack and r["C_H"] != 0]
    assert len(piv_slack) == 37
    assert sum(1 for r in piv_slack if r["C_Ha"] == 0) == 36
    term = [r for r in v2 if r["tipo"] == "termination"]
    assert sum(1 for r in term if r["C_H"] != 0 and r["C_Ha"] != 0) == 10

    rng = np.random.default_rng(40)

    def jit(vals: list[float]) -> np.ndarray:
        return np.asarray(vals) + rng.normal(0, 0.015, len(vals))

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(5.5, 2.15), sharey=True)
    for ax in (ax_a, ax_b):
        ax.axhline(0, color="k", lw=0.8)
        lim = [-1.15, 1.15]
        ax.plot(lim, lim, ls="--", color=COL_GREY, lw=0.8)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("TE $=C(H)$")

    for rows, col, lab in [
        ([r for r in v1 if r["cfg"] in slack], COL_SLACK, "slack (g450/600/900)"),
        ([r for r in v1 if r["cfg"] not in slack], COL_PRESS, "pressure (mt4/6/8)"),
    ]:
        ax_a.plot(jit([r["C_H"] for r in rows]), jit([r["C_Ha"] for r in rows]),
                  "o", ms=3, alpha=0.6, color=col, label=lab, mew=0)
    ext = RUNS / "preg42" / "rows.jsonl"
    if ext.exists():
        rows = _load_jsonl(ext)
        ax_a.plot(jit([r["C_H"] for r in rows]), jit([r["C_Ha"] for r in rows]),
                  "x", ms=3.5, color="#333333", label="external cells (pre-reg 42)")
    ax_a.set_ylabel("NDE $=C(H_a)$")
    ax_a.set_title("(a) V1 harness (n=122)")
    ax_a.text(0.03, 0.96, "slack pivotal: 36/37 on $y{=}0$\npressure: 39/46",
              transform=ax_a.transAxes, fontsize=6.5, va="top")
    ax_a.legend(frameon=False, fontsize=6, loc="lower right", handletextpad=0.2)

    for tipo, col in V2_TYPE_COLS.items():
        rows = [r for r in v2 if r["tipo"] == tipo]
        ax_b.plot(jit([r["C_H"] for r in rows]), jit([r["C_Ha"] for r in rows]),
                  "o", ms=3, alpha=0.65, color=col, label=tipo.replace("_", " "), mew=0)
    ax_b.set_title("(b) V2 factorial (n=48)")
    ax_b.text(0.03, 0.96, "termination: 0/10 on $y{=}0$",
              transform=ax_b.transAxes, fontsize=6.5, va="top")
    ax_b.legend(frameon=False, fontsize=6, loc="lower right", handletextpad=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "f6_mediation_scatter.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------- F7: censo de mediação (fração NDE != 0 nos pivotais)
def fig7_mediation_census() -> None:
    v1 = _load_jsonl(RUNS / "preg40" / "v1_rows.jsonl")
    v2 = _load_jsonl(RUNS / "preg40" / "v2_rows.jsonl")
    slack = {"g450", "g600", "g900"}

    def frac(rows: list[dict]) -> tuple[int, int]:
        piv = [r for r in rows if r["C_H"] != 0]
        return sum(1 for r in piv if r["C_Ha"] != 0), len(piv)

    pops = [
        ("V1 slack (g450/600/900)", frac([r for r in v1 if r["cfg"] in slack]), COL_SLACK),
        ("V1 pressure (mt4/6/8)", frac([r for r in v1 if r["cfg"] not in slack]), COL_PRESS),
    ]
    for tipo in ["context_policy", "observation_policy", "test_schedule", "termination"]:
        pops.append((f"V2 {tipo.replace('_', ' ')}",
                     frac([r for r in v2 if r["tipo"] == tipo]), V2_TYPE_COLS[tipo]))
    ext = RUNS / "preg42" / "rows.jsonl"
    if ext.exists():
        rows = _load_jsonl(ext)
        for pref in sorted({r["cfg"].split("_")[0] for r in rows}):
            pops.append((f"external {pref}",
                         frac([r for r in rows if r["cfg"].startswith(pref)]),
                         "#333333"))

    ks = [k for _, (k, _n), _ in pops]
    ns = [n for _, (_k, n), _ in pops]
    assert (ks[0], ns[0]) == (1, 37) and (ks[1], ns[1]) == (7, 46), (ks, ns)
    fracs = [k / n if n else 0.0 for k, n in zip(ks, ns)]

    fig, ax = plt.subplots(figsize=(5.5, 1.75))
    y = np.arange(len(pops))[::-1]
    ax.barh(y, fracs, color=[c for _, _, c in pops], alpha=0.8, height=0.65)
    for yi, f, k, n in zip(y, fracs, ks, ns):
        ax.text(f + 0.015, yi, f"{k}/{n}", va="center", fontsize=6.5)
    ax.axvline(0.20, color="k", ls="--", lw=0.8)
    ax.text(0.215, len(pops) - 0.72, "census gate threshold", fontsize=6.5,
            va="center", ha="left")
    ax.set_yticks(y)
    ax.set_yticklabels([name for name, _, _ in pops], fontsize=7)
    ax.set_xlabel("fraction of pivotal points with NDE $\\neq 0$ (unmediated)")
    ax.set_xlim(0, 1.12)
    fig.tight_layout()
    fig.savefig(OUT / "f7_mediation_census.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6_mediation_scatter()
    fig7_mediation_census()
    print("figuras salvas em", OUT)
