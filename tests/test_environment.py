"""Tests for environment/tasks.py and environment/sandbox.py."""

import pytest

from environment.sandbox import Sandbox
from environment.tasks import TASKS, get_task

REFERENCE_SOLUTIONS: dict[str, str] = {
    "rle_encode": '''
def rle_encode(s: str) -> str:
    if not s:
        return ""
    out = []
    prev, count = s[0], 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            out.append(prev + str(count))
            prev, count = ch, 1
    out.append(prev + str(count))
    return "".join(out)
''',
    "merge_intervals": '''
def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
    "balanced_brackets": '''
def is_balanced(s: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        else:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
''',
    "int_to_roman": '''
def int_to_roman(n: int) -> str:
    values = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = []
    for value, symbol in values:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)
''',
    "spiral_order": '''
def spiral_order(matrix):
    if not matrix or not matrix[0]:
        return []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    out = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            out.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):
            out.append(matrix[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                out.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                out.append(matrix[r][left])
            left += 1
    return out
''',
    "group_anagrams": '''
def group_anagrams(words):
    groups = {}
    for word in words:
        groups.setdefault("".join(sorted(word)), []).append(word)
    return sorted(sorted(group) for group in groups.values())
''',
    "sum_two_largest_primes": '''
def _is_prime(k: int) -> bool:
    if k < 2:
        return False
    i = 2
    while i * i <= k:
        if k % i == 0:
            return False
        i += 1
    return True


def sum_two_largest_primes(n: int) -> int:
    primes = []
    for k in range(n - 1, 1, -1):
        if _is_prime(k):
            primes.append(k)
            if len(primes) == 2:
                return primes[0] + primes[1]
    return 0
''',
    "validate_ipv4": '''
def is_valid_ipv4(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        if len(part) > 1 and part[0] == "0":
            return False
        if int(part) > 255:
            return False
    return True
''',
    "longest_common_prefix": '''
def longest_common_prefix(strs):
    if not strs:
        return ""
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
''',
    "eval_plus_minus": '''
def evaluate(expr: str) -> int:
    result, sign, num = 0, 1, 0
    stack = []
    for ch in expr:
        if ch.isdigit():
            num = num * 10 + int(ch)
        elif ch == "+":
            result += sign * num
            num, sign = 0, 1
        elif ch == "-":
            result += sign * num
            num, sign = 0, -1
        elif ch == "(":
            stack.append((result, sign))
            result, sign, num = 0, 1, 0
        elif ch == ")":
            result += sign * num
            num, sign = 0, 1
            prev_result, prev_sign = stack.pop()
            result = prev_result + prev_sign * result
    return result + sign * num
''',
}

TASK_IDS = [t["task_id"] for t in TASKS]


@pytest.fixture
def sandbox():
    sb = Sandbox()
    yield sb
    sb.cleanup()


class TestTasksSchema:
    def test_has_exactly_ten_tasks(self):
        assert len(TASKS) == 10

    def test_task_ids_unique(self):
        assert len(set(TASK_IDS)) == 10

    def test_all_fields_present_and_nonempty(self):
        for task in TASKS:
            for field in ("task_id", "prompt", "test_code", "starter_code"):
                assert isinstance(task[field], str) and task[field].strip(), (
                    f"{task.get('task_id')}: campo {field} vazio ou ausente"
                )

    def test_test_code_imports_from_solution(self):
        for task in TASKS:
            assert "from solution import" in task["test_code"]

    def test_starter_code_raises_not_implemented(self):
        for task in TASKS:
            assert "raise NotImplementedError" in task["starter_code"]

    def test_get_task_returns_task(self):
        task = get_task("rle_encode")
        assert task["task_id"] == "rle_encode"

    def test_get_task_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_task("nao_existe")


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_gets_full_reward(task_id, sandbox):
    task = get_task(task_id)
    sandbox.write_file("solution.py", REFERENCE_SOLUTIONS[task_id])
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 1.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is True
    assert result["failed"] == 0 and result["errors"] == 0
    assert result["total"] == result["passed"] >= 5
    assert result["timed_out"] is False


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_starter_code_gets_zero_reward(task_id, sandbox):
    task = get_task(task_id)
    sandbox.write_file("solution.py", task["starter_code"])
    result = sandbox.run_tests(task["test_code"])
    assert result["reward"] == 0.0, f"{task_id}:\n{result['output']}"
    assert result["success"] is False
    assert result["passed"] == 0


class TestSandboxFiles:
    def test_write_read_list(self, sandbox):
        sandbox.write_file("a.py", "x = 1\n")
        sandbox.write_file("pkg/b.py", "y = 2\n")
        assert sandbox.read_file("a.py") == "x = 1\n"
        assert sandbox.read_file("pkg/b.py") == "y = 2\n"
        assert sandbox.list_files() == ["a.py", "pkg/b.py"]

    def test_snapshot_restore_round_trip(self, sandbox):
        sandbox.write_file("keep.py", "original\n")
        sandbox.write_file("modify.py", "before\n")
        sandbox.write_file("delete_me.py", "gone after restore? no: restored\n")
        snap = sandbox.snapshot()

        sandbox.write_file("modify.py", "after\n")
        sandbox.write_file("extra.py", "should be removed\n")
        (sandbox.dir / "delete_me.py").unlink()

        sandbox.restore(snap)
        assert sandbox.snapshot() == snap
        assert sandbox.list_files() == sorted(snap)
        assert sandbox.read_file("modify.py") == "before\n"

    def test_run_tests_does_not_pollute_snapshot(self, sandbox):
        task = get_task("rle_encode")
        sandbox.write_file("solution.py", REFERENCE_SOLUTIONS["rle_encode"])
        before = sandbox.snapshot()
        sandbox.run_tests(task["test_code"])
        assert "test_solution.py" not in sandbox.list_files()
        assert sandbox.snapshot() == before

    def test_run_tests_reward_zero_on_collect_error(self, sandbox):
        sandbox.write_file("solution.py", "this is not valid python(\n")
        result = sandbox.run_tests(get_task("rle_encode")["test_code"])
        assert result["reward"] == 0.0
        assert result["success"] is False
