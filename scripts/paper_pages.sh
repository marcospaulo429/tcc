#!/bin/bash
# Compila o paper e imprime a fronteira p9/p10 (uso: scripts/paper_pages.sh)
cd "$(dirname "$0")/.." || exit 1
(cd paper && XDG_CACHE_HOME=/raid/user_marcospaulo/.cache ~/.local/bin/tectonic main.tex 2>&1 | grep -iE "^error|undefined|multiply" | head)
UV_CACHE_DIR=/raid/user_marcospaulo/.cache/uv ~/.local/bin/uvx --from pymupdf python - <<'EOF'
import fitz
d = fitz.open('paper/main.pdf'); print('pages', len(d))
for i in range(7, 12):
    t = d[i].get_text()
    for k in ['Conclusion', 'Reproducibility Statement', 'References', 'Master Claim']:
        if k in t: print(f'{k} -> p{i+1}')
t = d[9].get_text(); j = t.find('Reproducibility'); k = t.find('References')
print('chars on p10 before Reproducibility:', j if j >= 0 else 0, '| before References:', k)
print('p9 tail:', d[8].get_text().strip()[-160:].replace('\n', ' '))
EOF
