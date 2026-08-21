"""Fixed pool of 10 pure-Python coding tasks for the agent environment."""

TASKS: list[dict] = [
    {
        "task_id": "rle_encode",
        "prompt": (
            "Implement the function `rle_encode(s: str) -> str` in the file solution.py.\n"
            "It performs run-length encoding: each maximal run of a repeated character is\n"
            "replaced by the character followed by the run length (always include the count,\n"
            "even when it is 1).\n\n"
            "Examples:\n"
            '  rle_encode("aaabcc") -> "a3b1c2"\n'
            '  rle_encode("abc")    -> "a1b1c1"\n'
            '  rle_encode("")       -> ""\n'
        ),
        "starter_code": (
            "def rle_encode(s: str) -> str:\n"
            '    """Run-length encode s, e.g. "aaabcc" -> "a3b1c2"."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import rle_encode\n"
            "\n"
            "\n"
            "def test_basic():\n"
            '    assert rle_encode("aaabcc") == "a3b1c2"\n'
            "\n"
            "\n"
            "def test_empty():\n"
            '    assert rle_encode("") == ""\n'
            "\n"
            "\n"
            "def test_single_char():\n"
            '    assert rle_encode("a") == "a1"\n'
            "\n"
            "\n"
            "def test_no_repeats():\n"
            '    assert rle_encode("abc") == "a1b1c1"\n'
            "\n"
            "\n"
            "def test_alternating_runs():\n"
            '    assert rle_encode("aabbaa") == "a2b2a2"\n'
            "\n"
            "\n"
            "def test_long_run_multidigit_count():\n"
            '    assert rle_encode("z" * 12) == "z12"\n'
        ),
    },
    {
        "task_id": "merge_intervals",
        "prompt": (
            "Implement the function `merge_intervals(intervals: list[list[int]]) -> list[list[int]]`\n"
            "in the file solution.py. Given a list of intervals [start, end] (possibly unsorted),\n"
            "merge all overlapping or touching intervals and return the result sorted by start.\n"
            "Intervals like [1,4] and [4,5] touch and must be merged into [1,5].\n\n"
            "Examples:\n"
            "  merge_intervals([[1,3],[2,6],[8,10],[15,18]]) -> [[1,6],[8,10],[15,18]]\n"
            "  merge_intervals([[1,4],[4,5]]) -> [[1,5]]\n"
            "  merge_intervals([]) -> []\n"
        ),
        "starter_code": (
            "def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:\n"
            '    """Merge overlapping/touching intervals; return sorted by start."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import merge_intervals\n"
            "\n"
            "\n"
            "def test_basic_overlap():\n"
            "    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]\n"
            "\n"
            "\n"
            "def test_touching_intervals():\n"
            "    assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]\n"
            "\n"
            "\n"
            "def test_empty():\n"
            "    assert merge_intervals([]) == []\n"
            "\n"
            "\n"
            "def test_single_interval():\n"
            "    assert merge_intervals([[5, 7]]) == [[5, 7]]\n"
            "\n"
            "\n"
            "def test_contained_intervals():\n"
            "    assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]\n"
            "\n"
            "\n"
            "def test_unsorted_input():\n"
            "    assert merge_intervals([[3, 4], [1, 2]]) == [[1, 2], [3, 4]]\n"
        ),
    },
    {
        "task_id": "balanced_brackets",
        "prompt": (
            "Implement the function `is_balanced(s: str) -> bool` in the file solution.py.\n"
            "The input contains only the characters ()[]{}. Return True if every opening\n"
            "bracket is closed by the same type in the correct order, False otherwise.\n"
            "The empty string is balanced.\n\n"
            "Examples:\n"
            '  is_balanced("()[]{}") -> True\n'
            '  is_balanced("([{}])") -> True\n'
            '  is_balanced("([)]")   -> False\n'
            '  is_balanced("(")      -> False\n'
        ),
        "starter_code": (
            "def is_balanced(s: str) -> bool:\n"
            '    """Return True if brackets ()[]{} in s are balanced."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import is_balanced\n"
            "\n"
            "\n"
            "def test_simple_pairs():\n"
            '    assert is_balanced("()[]{}") is True\n'
            "\n"
            "\n"
            "def test_nested():\n"
            '    assert is_balanced("([{}])") is True\n'
            "\n"
            "\n"
            "def test_wrong_type():\n"
            '    assert is_balanced("(]") is False\n'
            "\n"
            "\n"
            "def test_empty():\n"
            '    assert is_balanced("") is True\n'
            "\n"
            "\n"
            "def test_unclosed():\n"
            '    assert is_balanced("(((") is False\n'
            "\n"
            "\n"
            "def test_interleaved():\n"
            '    assert is_balanced("([)]") is False\n'
            "\n"
            "\n"
            "def test_closing_first():\n"
            '    assert is_balanced(")(") is False\n'
        ),
    },
    {
        "task_id": "int_to_roman",
        "prompt": (
            "Implement the function `int_to_roman(n: int) -> str` in the file solution.py.\n"
            "Convert an integer 1 <= n <= 3999 to its Roman numeral representation, using\n"
            "the standard subtractive forms (IV, IX, XL, XC, CD, CM).\n\n"
            "Examples:\n"
            "  int_to_roman(4)    -> \"IV\"\n"
            "  int_to_roman(58)   -> \"LVIII\"\n"
            "  int_to_roman(1994) -> \"MCMXCIV\"\n"
        ),
        "starter_code": (
            "def int_to_roman(n: int) -> str:\n"
            '    """Convert 1 <= n <= 3999 to a Roman numeral string."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import int_to_roman\n"
            "\n"
            "\n"
            "def test_one():\n"
            '    assert int_to_roman(1) == "I"\n'
            "\n"
            "\n"
            "def test_subtractive_four():\n"
            '    assert int_to_roman(4) == "IV"\n'
            "\n"
            "\n"
            "def test_subtractive_nine():\n"
            '    assert int_to_roman(9) == "IX"\n'
            "\n"
            "\n"
            "def test_fifty_eight():\n"
            '    assert int_to_roman(58) == "LVIII"\n'
            "\n"
            "\n"
            "def test_forty():\n"
            '    assert int_to_roman(40) == "XL"\n'
            "\n"
            "\n"
            "def test_1994():\n"
            '    assert int_to_roman(1994) == "MCMXCIV"\n'
            "\n"
            "\n"
            "def test_max_value():\n"
            '    assert int_to_roman(3999) == "MMMCMXCIX"\n'
        ),
    },
    {
        "task_id": "spiral_order",
        "prompt": (
            "Implement the function `spiral_order(matrix: list[list[int]]) -> list[int]` in the\n"
            "file solution.py. Return all elements of the matrix in clockwise spiral order,\n"
            "starting from the top-left corner. An empty matrix yields an empty list.\n\n"
            "Examples:\n"
            "  spiral_order([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,9,8,7,4,5]\n"
            "  spiral_order([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) -> [1,2,3,4,8,12,11,10,9,5,6,7]\n"
        ),
        "starter_code": (
            "def spiral_order(matrix: list[list[int]]) -> list[int]:\n"
            '    """Return matrix elements in clockwise spiral order."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import spiral_order\n"
            "\n"
            "\n"
            "def test_square_3x3():\n"
            "    assert spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]\n"
            "\n"
            "\n"
            "def test_rect_3x4():\n"
            "    m = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]\n"
            "    assert spiral_order(m) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]\n"
            "\n"
            "\n"
            "def test_empty():\n"
            "    assert spiral_order([]) == []\n"
            "\n"
            "\n"
            "def test_single_element():\n"
            "    assert spiral_order([[1]]) == [1]\n"
            "\n"
            "\n"
            "def test_single_row():\n"
            "    assert spiral_order([[1, 2, 3]]) == [1, 2, 3]\n"
            "\n"
            "\n"
            "def test_single_column():\n"
            "    assert spiral_order([[1], [2], [3]]) == [1, 2, 3]\n"
        ),
    },
    {
        "task_id": "group_anagrams",
        "prompt": (
            "Implement the function `group_anagrams(words: list[str]) -> list[list[str]]` in the\n"
            "file solution.py. Group the words that are anagrams of each other. Each group must\n"
            "be sorted alphabetically, and the groups themselves must be sorted by their first\n"
            "word, so the output is fully deterministic.\n\n"
            "Examples:\n"
            '  group_anagrams(["eat","tea","tan","ate","nat","bat"])\n'
            '    -> [["ate","eat","tea"], ["bat"], ["nat","tan"]]\n'
            "  group_anagrams([]) -> []\n"
        ),
        "starter_code": (
            "def group_anagrams(words: list[str]) -> list[list[str]]:\n"
            '    """Group anagrams; each group sorted, groups sorted by first word."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import group_anagrams\n"
            "\n"
            "\n"
            "def test_classic():\n"
            '    words = ["eat", "tea", "tan", "ate", "nat", "bat"]\n'
            '    assert group_anagrams(words) == [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]\n'
            "\n"
            "\n"
            "def test_empty_list():\n"
            "    assert group_anagrams([]) == []\n"
            "\n"
            "\n"
            "def test_empty_string():\n"
            '    assert group_anagrams([""]) == [[""]]\n'
            "\n"
            "\n"
            "def test_single_word():\n"
            '    assert group_anagrams(["a"]) == [["a"]]\n'
            "\n"
            "\n"
            "def test_all_anagrams_plus_one():\n"
            '    assert group_anagrams(["abc", "bca", "cab", "xyz"]) == [["abc", "bca", "cab"], ["xyz"]]\n'
            "\n"
            "\n"
            "def test_no_anagrams():\n"
            '    assert group_anagrams(["dog", "cat"]) == [["cat"], ["dog"]]\n'
        ),
    },
    {
        "task_id": "sum_two_largest_primes",
        "prompt": (
            "Implement the function `sum_two_largest_primes(n: int) -> int` in the file\n"
            "solution.py. Return the sum of the two largest (distinct) prime numbers strictly\n"
            "less than n. If there are fewer than two primes below n, return 0.\n\n"
            "Examples:\n"
            "  sum_two_largest_primes(10)  -> 12   # 7 + 5\n"
            "  sum_two_largest_primes(4)   -> 5    # 3 + 2\n"
            "  sum_two_largest_primes(3)   -> 0    # only 2 exists below 3\n"
        ),
        "starter_code": (
            "def sum_two_largest_primes(n: int) -> int:\n"
            '    """Sum of the two largest primes < n, or 0 if fewer than two exist."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import sum_two_largest_primes\n"
            "\n"
            "\n"
            "def test_below_ten():\n"
            "    assert sum_two_largest_primes(10) == 12\n"
            "\n"
            "\n"
            "def test_only_one_prime():\n"
            "    assert sum_two_largest_primes(3) == 0\n"
            "\n"
            "\n"
            "def test_exactly_two_primes():\n"
            "    assert sum_two_largest_primes(4) == 5\n"
            "\n"
            "\n"
            "def test_no_primes():\n"
            "    assert sum_two_largest_primes(2) == 0\n"
            "\n"
            "\n"
            "def test_below_thirty():\n"
            "    assert sum_two_largest_primes(30) == 52  # 29 + 23\n"
            "\n"
            "\n"
            "def test_below_hundred():\n"
            "    assert sum_two_largest_primes(100) == 186  # 97 + 89\n"
            "\n"
            "\n"
            "def test_bound_is_exclusive():\n"
            "    assert sum_two_largest_primes(8) == 12  # 7 + 5, 8 itself not counted\n"
        ),
    },
    {
        "task_id": "validate_ipv4",
        "prompt": (
            "Implement the function `is_valid_ipv4(s: str) -> bool` in the file solution.py.\n"
            "Return True only if s is a valid dotted-decimal IPv4 address: exactly four parts\n"
            "separated by dots, each part is a decimal number 0-255 made only of digits, and\n"
            "no part has leading zeros (\"0\" is fine, \"01\" is not).\n\n"
            "Examples:\n"
            '  is_valid_ipv4("192.168.1.1")   -> True\n'
            '  is_valid_ipv4("256.1.1.1")     -> False\n'
            '  is_valid_ipv4("01.1.1.1")      -> False\n'
        ),
        "starter_code": (
            "def is_valid_ipv4(s: str) -> bool:\n"
            '    """Return True if s is a valid dotted-decimal IPv4 address."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import is_valid_ipv4\n"
            "\n"
            "\n"
            "def test_valid_common():\n"
            '    assert is_valid_ipv4("192.168.1.1") is True\n'
            "\n"
            "\n"
            "def test_valid_extremes():\n"
            '    assert is_valid_ipv4("0.0.0.0") is True\n'
            '    assert is_valid_ipv4("255.255.255.255") is True\n'
            "\n"
            "\n"
            "def test_octet_out_of_range():\n"
            '    assert is_valid_ipv4("256.1.1.1") is False\n'
            "\n"
            "\n"
            "def test_too_few_parts():\n"
            '    assert is_valid_ipv4("1.1.1") is False\n'
            "\n"
            "\n"
            "def test_too_many_parts():\n"
            '    assert is_valid_ipv4("1.1.1.1.1") is False\n'
            "\n"
            "\n"
            "def test_leading_zero():\n"
            '    assert is_valid_ipv4("01.1.1.1") is False\n'
            "\n"
            "\n"
            "def test_non_numeric():\n"
            '    assert is_valid_ipv4("a.b.c.d") is False\n'
            "\n"
            "\n"
            "def test_empty_part():\n"
            '    assert is_valid_ipv4("1..1.1") is False\n'
        ),
    },
    {
        "task_id": "longest_common_prefix",
        "prompt": (
            "Implement the function `longest_common_prefix(strs: list[str]) -> str` in the file\n"
            "solution.py. Return the longest string that is a prefix of every string in the\n"
            "list. If the list is empty or there is no common prefix, return \"\".\n\n"
            "Examples:\n"
            '  longest_common_prefix(["flower","flow","flight"]) -> "fl"\n'
            '  longest_common_prefix(["dog","racecar","car"])    -> ""\n'
            '  longest_common_prefix([])                         -> ""\n'
        ),
        "starter_code": (
            "def longest_common_prefix(strs: list[str]) -> str:\n"
            '    """Longest common prefix of all strings, or "" if none."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import longest_common_prefix\n"
            "\n"
            "\n"
            "def test_partial_prefix():\n"
            '    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"\n'
            "\n"
            "\n"
            "def test_no_common_prefix():\n"
            '    assert longest_common_prefix(["dog", "racecar", "car"]) == ""\n'
            "\n"
            "\n"
            "def test_empty_list():\n"
            '    assert longest_common_prefix([]) == ""\n'
            "\n"
            "\n"
            "def test_single_string():\n"
            '    assert longest_common_prefix(["single"]) == "single"\n'
            "\n"
            "\n"
            "def test_identical_strings():\n"
            '    assert longest_common_prefix(["abc", "abc"]) == "abc"\n'
            "\n"
            "\n"
            "def test_prefix_is_whole_string():\n"
            '    assert longest_common_prefix(["ab", "a"]) == "a"\n'
            "\n"
            "\n"
            "def test_contains_empty_string():\n"
            '    assert longest_common_prefix(["abc", ""]) == ""\n'
        ),
    },
    {
        "task_id": "eval_plus_minus",
        "prompt": (
            "Implement the function `evaluate(expr: str) -> int` in the file solution.py.\n"
            "Evaluate an arithmetic expression containing non-negative integers, '+', '-',\n"
            "parentheses and spaces. A '-' may also appear as a unary minus before a number\n"
            "or an opening parenthesis. Do not use eval().\n\n"
            "Examples:\n"
            '  evaluate("1+1")                  -> 2\n'
            '  evaluate(" 2-1 + 2 ")            -> 3\n'
            '  evaluate("(1+(4+5+2)-3)+(6+8)")  -> 23\n'
            '  evaluate("-(2+3)")               -> -5\n'
        ),
        "starter_code": (
            "def evaluate(expr: str) -> int:\n"
            '    """Evaluate an expression with +, -, parentheses and spaces."""\n'
            "    raise NotImplementedError\n"
        ),
        "test_code": (
            "from solution import evaluate\n"
            "\n"
            "\n"
            "def test_simple_add():\n"
            '    assert evaluate("1+1") == 2\n'
            "\n"
            "\n"
            "def test_spaces_and_mixed_ops():\n"
            '    assert evaluate(" 2-1 + 2 ") == 3\n'
            "\n"
            "\n"
            "def test_nested_parentheses():\n"
            '    assert evaluate("(1+(4+5+2)-3)+(6+8)") == 23\n'
            "\n"
            "\n"
            "def test_unary_minus_paren():\n"
            '    assert evaluate("-(2+3)") == -5\n'
            "\n"
            "\n"
            "def test_subtract_paren():\n"
            '    assert evaluate("10-(4-2)") == 8\n'
            "\n"
            "\n"
            "def test_multidigit_numbers():\n"
            '    assert evaluate(" 12 + 3 - 4 ") == 11\n'
            "\n"
            "\n"
            "def test_single_number():\n"
            '    assert evaluate("42") == 42\n'
        ),
    },
]


def get_task(task_id: str) -> dict:
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise KeyError(task_id)
