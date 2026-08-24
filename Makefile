# Reprodução das estatísticas publicadas a partir dos artefatos em runs/.
# Cada script FALHA (exit != 0) se qualquer número divergir do publicado.
# Requer os artefatos brutos (runs/) no lugar; nenhum alvo usa GPU.

PY := .venv/bin/python

.PHONY: reproduce test
reproduce:
	$(PY) experiments/reconcilia_nulos.py
	$(PY) experiments/estatisticas_pivotais.py
	$(PY) experiments/margem_calibracao.py
	$(PY) experiments/analise_selecao.py
	@echo "REPRODUCE: todas as estatísticas reconciliadas"

test:
	.venv/bin/pytest tests/ -q
