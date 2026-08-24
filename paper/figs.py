"""Gera as figuras F1-F5 do paper a partir dos artefatos em experiments/results/ e runs/.

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

    x = np.arange(len(labels))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10.8, 2.4))
    cols = ([COL_SLACK] * 3 + [COL_PRESS] * 3 + ["#6a51a3"] * 2
            + ["#a63603"] * 3 + ["#e6550d"] * 2 + ["#08519c"] * 2 + ["#238b45"] * 2)
    ax.bar(x - w / 2, raw, w, color=cols, alpha=0.55, label="raw")
    ax.bar(x + w / 2, cond, w, color=cols, hatch="//", label="non-saturated only")
    for i in range(len(labels)):
        ax.text(x[i] - w / 2, raw[i] + 0.015, "%d/%d" % nn[i], ha="center", fontsize=6.5)
        ax.text(x[i] + w / 2, cond[i] + 0.015, "%d/%d" % nns[i], ha="center", fontsize=6.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("screening-off break rate")
    ax.set_ylim(0, 0.62)
    ax.axvspan(-0.5, 2.5, color=COL_SLACK, alpha=0.05)
    ax.axvspan(2.5, 5.5, color=COL_PRESS, alpha=0.05)
    ax.axvspan(7.5, 10.5, color="#a63603", alpha=0.05)
    ax.axvspan(10.5, 12.5, color="#e6550d", alpha=0.05)
    ax.axvspan(12.5, 14.5, color="#08519c", alpha=0.05)
    ax.axvspan(14.5, 16.5, color="#238b45", alpha=0.05)
    ax.text(1.0, 0.56, "budget slack (Qwen3-4B)", ha="center", fontsize=8, color=COL_SLACK)
    ax.text(4.0, 0.56, "budget pressure", ha="center", fontsize=8, color=COL_PRESS)
    ax.text(9.0, 0.56, "Qwen3-8B (raw flat)", ha="center", fontsize=8, color="#a63603")
    ax.text(11.5, 0.56, "8B curated", ha="center", fontsize=8, color="#e6550d")
    ax.text(13.5, 0.56, "4B curated", ha="center", fontsize=8, color="#08519c")
    ax.text(15.5, 0.56, "MBPP+ (4B)", ha="center", fontsize=8, color="#238b45")
    ax.legend(loc="center right", frameon=False)
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


# ------------------------------------------------ F5: treino (C1/C1b)
def fig5() -> None:
    c1b = load(RES / "2026-08-23_c1b_summary.json")["seeds"]
    arms = ["outcome", "ch", "chm_cm", "zero"]
    labels = ["outcome-only", "$C(H)$", "$C_{HM}{-}C_M$", "zero (control)"]
    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    rng = np.random.default_rng(1)
    for i, arm in enumerate(arms):
        vals = [c1b[s][arm]["heldout_R_eff"] for s in ["1", "2", "3"]]
        xs = i + rng.normal(0, 0.04, 3)
        ax.plot(xs, vals, "o", ms=6, color=COL_PRESS if arm in ("ch", "chm_cm") else COL_SLACK)
    ax.axhline(0.398, color="#1b7837", ls="--", lw=1)
    ax.text(3.45, 0.41, "thr600 (best fixed)", fontsize=7, color="#1b7837", ha="right")
    ax.axhline(0.237, color=COL_GREY, ls=":", lw=1)
    ax.text(3.45, 0.25, "keep-always", fontsize=7, color=COL_GREY, ha="right")
    ax.axhline(-0.464, color="#c0392b", ls=":", lw=1)
    ax.text(3.45, -0.45, "summarize-always (collapse)", fontsize=7, color="#c0392b", ha="right")
    ax.set_xticks(range(4))
    ax.set_xticklabels(labels)
    ax.set_ylabel("held-out $R_{\\mathrm{eff}}$")
    ax.set_ylim(-0.6, 0.55)
    ax.set_title("C1b (stable optimization): 3 seeds per arm")
    fig.tight_layout()
    fig.savefig(OUT / "f5_training.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print("figuras salvas em", OUT)
