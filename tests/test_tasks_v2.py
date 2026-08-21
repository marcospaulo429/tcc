"""Testes de referência para environment/tasks_v2.py.

Para cada task v2: a solução de referência (possivelmente multi-arquivo) deve
dar reward 1.0; o starter_code puro deve dar reward 0.0. Testes estruturais
garantem que o enunciado é longo (>600 chars) e que as constantes críticas
ficam APÓS os primeiros 240 chars (região preservada pelo summarize).
"""

import pytest

from environment.sandbox import Sandbox
from environment.tasks import TASKS as TASKS_V1
from environment.tasks_v2 import TASKS, get_task

# solução de referência por task: {relpath: conteúdo}
REFERENCE_SOLUTIONS: dict[str, dict[str, str]] = {
    "invoice_pricing": {
        "pricing.py": '''
def line_total(qty: int, unit_price: float) -> float:
    return round(qty * unit_price, 2)
''',
        "solution.py": '''
from pricing import line_total


def invoice_total(items, vip):
    subtotal = sum(line_total(q, p) for q, p in items)
    if subtotal > 250.00:
        subtotal *= 0.9265
    if subtotal < 180.50:
        subtotal += 12.90
    if vip:
        subtotal *= 0.88
    return round(subtotal, 2)
''',
    },
    "log_formatter": {
        "solution.py": '''
def format_logs(lines):
    valid = {"DEBUG", "INFO", "WARN", "CRIT"}
    out = []
    for line in lines:
        parts = line.split("|")
        if len(parts) != 3:
            out.append("ERR_07")
            continue
        level, code, msg = parts
        if level not in valid:
            out.append("ERR_04")
            continue
        s = f"[{level}] #{code} :: {msg}"
        if level == "CRIT":
            s = "!! " + s
        out.append(s)
    return out
''',
    },
    "inventory_restock": {
        "models.py": '''
def make_item(name: str, category: str, qty: int) -> dict:
    return {"name": name, "category": category, "qty": qty}
''',
        "solution.py": '''
def restock_report(items):
    low = [i for i in items if i["qty"] < 17]
    low.sort(key=lambda i: i["name"])
    low.sort(key=lambda i: i["category"], reverse=True)
    return [f"{i['category']}/{i['name']}:{i['qty'] * 3 + 5}" for i in low]
''',
    },
    "rate_limiter_bucket": {
        "solution.py": '''
def simulate(gaps):
    tokens = 23
    out = []
    for gap in gaps:
        tokens = min(23, tokens + 4 * gap)
        if tokens >= 5:
            tokens -= 5
            out.append(True)
        else:
            out.append(False)
    return out
''',
    },
    "grade_curve": {
        "solution.py": '''
def assign_grades(scores):
    out = []
    for score in scores:
        s = min(100.0, round(score + 3.2, 2))
        if s >= 91.5:
            out.append("A")
        elif s >= 77.25:
            out.append("B")
        elif s >= 62.0:
            out.append("C")
        elif s >= 48.75:
            out.append("D")
        else:
            out.append("F")
    return out
''',
    },
    "config_renderer": {
        "validators.py": '''
def is_valid_key(key: str) -> bool:
    if not key or key.startswith("_"):
        return False
    return all(ch == "_" or ("a" <= ch <= "z") for ch in key)
''',
        "solution.py": '''
from validators import is_valid_key


def render_config(pairs):
    lines = []
    for key, value in pairs:
        if is_valid_key(key):
            lines.append(f"CFG> {key} := {value}")
        else:
            lines.append("E_KEY_9")
    return "\\n".join(lines)
''',
    },
    "shift_cipher": {
        "solution.py": '''
def encode(s: str) -> str:
    out = []
    for ch in s:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + 11) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + 19) % 26 + 65))
        elif "0" <= ch <= "9":
            out.append(chr((ord(ch) - 48 + 6) % 10 + 48))
        else:
            out.append(ch)
    return "".join(out)
''',
    },
    "loyalty_points": {
        "solution.py": '''
def compute_points(amount, tier):
    mult = {"gold": 1.75, "silver": 1.2}.get(tier, 1.0)
    points = int(amount * 4.5 * mult)
    if amount > 320:
        points += 250
    return points
''',
    },
    "csv_normalizer": {
        "solution.py": '''
def normalize(rows):
    out = []
    for row in rows:
        fields = [f.strip() for f in row.split(";")]
        fields = [f if f else "N/A" for f in fields]
        while len(fields) < 3:
            fields.append("N/A")
        fields[0] = fields[0].upper()
        out.append(";".join(fields))
    return out
''',
    },
    "api_router": {
        "handlers.py": '''
def not_found() -> str:
    return "RT_404_X"
''',
        "solution.py": '''
from handlers import not_found

_ROUTES = {
    "/api/v3/users": "users_handler",
    "/api/v3/items": "items_handler",
    "/api/v3/health": "OK_200",
}


def route(path: str) -> str:
    return _ROUTES.get(path, not_found())
''',
    },
}

# literais críticos por task: devem estar no prompt, mas NUNCA nos primeiros
# 240 chars (região que sobrevive ao truncamento do summarize).
CRITICAL_LITERALS: dict[str, list[str]] = {
    "invoice_pricing": ["7.35", "250.00", "180.50", "12.90", "0.88"],
    "log_formatter": ["ERR_07", "ERR_04", "'!! '", "' :: '"],
    "inventory_restock": ["17", "qty * 3 + 5", "'category/name:restock'"],
    "rate_limiter_bucket": ["capacity 23", "add 4 tokens", "costs exactly 5 tokens"],
    "grade_curve": ["3.2", "91.5", "77.25", "62.0", "48.75"],
    "config_renderer": ["'CFG> '", "' := '", "E_KEY_9"],
    "shift_cipher": ["by 11 positions", "by 19 positions", "by 6 positions"],
    "loyalty_points": ["4.5", "1.75", "1.2", "250", "320"],
    "csv_normalizer": ["'N/A'", "';'", "fewer than 3 fields"],
    "api_router": ["'/api/v3'", "RT_404_X", "OK_200", "users_handler", "items_handler"],
}

TASK_IDS = [t["task_id"] for t in TASKS]


@pytest.fixture
def sandbox():
    sb = Sandbox()
    yield sb
    sb.cleanup()


class TestTasksV2Schema:
    def test_has_exactly_ten_tasks(self):
        assert len(TASKS) == 10

    def test_task_ids_unique(self):
        assert len(set(TASK_IDS)) == 10

    def test_task_ids_disjoint_from_v1(self):
        v1_ids = {t["task_id"] for t in TASKS_V1}
        assert not v1_ids & set(TASK_IDS)

    def test_all_fields_present_and_nonempty(self):
        for task in TASKS:
            for field in ("task_id", "prompt", "test_code", "starter_code"):
                assert isinstance(task[field], str) and task[field].strip(), (
                    f"{task.get('task_id')}: campo {field} vazio ou ausente"
                )

    def test_starter_code_raises_not_implemented(self):
        for task in TASKS:
            assert "raise NotImplementedError" in task["starter_code"]

    def test_get_task_returns_task(self):
        task = get_task("invoice_pricing")
        assert task["task_id"] == "invoice_pricing"

    def test_get_task_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_task("nao_existe")


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_prompt_long_enough(task_id):
    assert len(get_task(task_id)["prompt"]) > 600


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_critical_literals_after_first_240_chars(task_id):
    prompt = get_task(task_id)["prompt"]
    head = prompt[:240]
    for literal in CRITICAL_LITERALS[task_id]:
        assert literal in prompt, f"{task_id}: literal {literal!r} ausente do prompt"
        assert literal not in head, (
            f"{task_id}: literal crítico {literal!r} nos primeiros 240 chars"
        )


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_gets_full_reward(task_id, sandbox):
    task = get_task(task_id)
    for relpath, content in REFERENCE_SOLUTIONS[task_id].items():
        sandbox.write_file(relpath, content)
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 1.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is True
    assert result["failed"] == 0 and result["errors"] == 0
    assert result["total"] == result["passed"] >= 6
    assert result["timed_out"] is False


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_starter_code_gets_zero_reward(task_id, sandbox):
    task = get_task(task_id)
    sandbox.write_file("solution.py", task["starter_code"])
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 0.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is False
    assert result["passed"] == 0


@pytest.mark.parametrize(
    "task_id",
    [tid for tid in TASK_IDS if len(REFERENCE_SOLUTIONS[tid]) > 1],
)
def test_multifile_partial_reward_without_helper_file(task_id, sandbox):
    """Só solution.py de referência (sem o arquivo auxiliar): reward parcial,
    não colapso de coleta — imports dentro das funções de teste garantem isso."""
    task = get_task(task_id)
    files = REFERENCE_SOLUTIONS[task_id]
    helper_free = {k: v for k, v in files.items() if k == "solution.py"}
    # solution.py de referência importa o helper; sem ele todo teste falha
    # individualmente, mas o total de testes coletados não pode zerar.
    for relpath, content in helper_free.items():
        sandbox.write_file(relpath, content)
    result = sandbox.run_tests(task["test_code"])
    assert result["total"] >= 6, f"{task_id}: coleta colapsou:\n{result['output']}"
    assert result["reward"] < 1.0
