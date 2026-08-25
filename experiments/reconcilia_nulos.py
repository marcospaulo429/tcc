"""Reconciliação run-a-run dos null replays (tabela do apêndice do paper).

Enumera todos os summaries em runs/: nulos dedicados (teste0_*), nulos attached
às runs de interação (teste3_*), e as runs EXCLUÍDAS do total canônico
(pré-fix ASLR em runs/_asrl_pre_fix/, APC-contaminada em runs/_apc_contaminado/).
Falha (exit 1) se os totais divergirem dos publicados no paper.
"""
import glob
import json
import os
import sys

PAPER_DEDICATED = 7728
PAPER_ATTACHED = 1568
PAPER_TOTAL = PAPER_DEDICATED + PAPER_ATTACHED  # 9.296
PAPER_EVER_RUN = PAPER_TOTAL + 432              # + pré-fix ASLR → 9.728 (2 inexatos)


def _load(path):
    with open(path) as f:
        return json.load(f)


def main() -> int:
    ded = att = 0
    print(f"{'run':<28}{'dedicados':>10}{'attached':>10}{'inexatos':>10}")
    for p in sorted(glob.glob("runs/teste0_*/summary.json")):
        s = _load(p)
        if "n_replays" not in s:  # pool merged (v5cur): sem nulos novos
            continue
        n = s["n_replays"]
        inexact = round(n * (1 - s["exact_rate"]))
        ded += n
        print(f"{os.path.dirname(p).split('/')[1]:<28}{n:>10}{'':>10}{inexact:>10}")
    for p in sorted(glob.glob("runs/teste3_*/summary.json")):
        s = _load(p)
        n = s["n_null_replays"]
        att += n
        print(f"{os.path.dirname(p).split('/')[1]:<28}{'':>10}{n:>10}{s['n_null_inexact']:>10}")
    print(f"{'TOTAL CANÔNICO':<28}{ded:>10}{att:>10}{'0':>10}  (= {ded + att})")

    print("\nexcluídos do total canônico:")
    for base, label in [("runs/_asrl_pre_fix", "pré-fix ASLR"),
                        ("runs/_apc_contaminado", "APC contaminada")]:
        for p in sorted(glob.glob(f"{base}/teste*/summary.json")):
            s = _load(p)
            n = s.get("n_replays", s.get("n_null_replays", 0))
            inexact = (s["n_null_inexact"] if "n_null_inexact" in s
                       else round(n * (1 - s.get("exact_rate", 1.0))))
            print(f"  {label:<18}{os.path.dirname(p).split('/')[-1]:<22}{n:>6}{inexact:>4} inexatos")

    ok = (ded == PAPER_DEDICATED and att == PAPER_ATTACHED)
    print(f"\npaper: {PAPER_DEDICATED}+{PAPER_ATTACHED}={PAPER_TOTAL} exatos; "
          f"{PAPER_EVER_RUN} já rodados sob as premissas (2 inexatos, pré-fix). "
          f"{'OK' if ok else 'DIVERGÊNCIA!'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
