"""Generate a printable PDF worksheet of balance-both-sides equations."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 12
# Inclusive range for the missing number
ANSWER_MIN = 2
ANSWER_MAX = 15
# Inclusive range for other operands
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 30
# Inclusive upper bound for the shared side value
TOTAL_MAX = 100
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 400
# Retries when searching for a matching right-hand expression
RIGHT_ATTEMPTS = 80
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.7cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Balance Both Sides"
INSTRUCTIONS = (
    "Find the missing number that makes both sides equal."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "balance"
# Binary operators used when building a matching right-hand side
OPS = ("+", "-", "*", "/")
# Layout identifiers: which pair is evaluated first
LAYOUT_LEFT = "left"
LAYOUT_RIGHT = "right"
# LaTeX placeholder drawn where the missing number belongs
BLANK_LATEX = r"[~~~~~]"


def is_additive(op):
    """True for + and - (lower precedence than \\times/\\div)."""
    return op in ("+", "-")


def is_multiplicative(op):
    """True for * and / (higher precedence than +/-)."""
    return op in ("*", "/")


def in_value_range(n):
    """True when n is a positive integer within the operand range."""
    return isinstance(n, int) and NUMBER_VALUE_MIN <= n <= NUMBER_VALUE_MAX


def in_total_range(n):
    """True when n is a positive shared side-value within TOTAL_MAX."""
    return isinstance(n, int) and n >= 1 and n <= TOTAL_MAX


def apply_op(left, op, right):
    """
    Evaluate left op right for positive-integer arithmetic.
    Raises ValueError when the result would not be a positive whole number.
    """
    if op == "+":
        return left + right
    if op == "-":
        if left <= right:
            raise ValueError("non-positive subtraction")
        return left - right
    if op == "*":
        # Skip ×1; it does not change the other operand
        if left == 1 or right == 1:
            raise ValueError("trivial multiplication")
        return left * right
    # Exact integer division only; skip ÷1 (same as the other operand)
    if right == 0 or right == 1 or left % right != 0:
        raise ValueError("non-exact or trivial division")
    return left // right


def latex_op(op):
    """Map a Python operator symbol to its LaTeX counterpart."""
    return {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[op]


def needs_parens(layout, op1, op2):
    """Wrap the first-step pair when order of operations would change it."""
    if layout == LAYOUT_LEFT:
        return is_additive(op1) and is_multiplicative(op2)
    if is_additive(op2) and is_multiplicative(op1):
        return False
    return True


def render_two_step(layout, op1, op2, x, y, z, wrap):
    """Build a two-step LaTeX body (no $). x/y/z may already be blank strings."""
    inner = f"{x} {latex_op(op1)} {y}"
    outer_op = latex_op(op2)
    if layout == LAYOUT_LEFT:
        if wrap:
            return rf"\left( {inner} \right) {outer_op} {z}"
        return f"{inner} {outer_op} {z}"
    if wrap:
        return rf"{z} {outer_op} \left( {inner} \right)"
    return f"{z} {outer_op} {inner}"


def try_left_from_answer(n):
    """
    Build a left-hand expression that contains n in one slot.
    Returns (latex, total, filled_latex) or None.
    filled_latex is the same expression with n visible (for duplicate checks).
    """
    kind = random.choice(
        (
            "a_mul_n_add",
            "a_mul_n_sub",
            "n_mul_a_add",
            "n_mul_a_sub",
            "n_add_a_mul_b",
            "a_mul_b_add_n",
            "a_mul_b_sub_n",
            "paren_n_add_times",
        )
    )
    a = random.randint(2, 9)
    b = random.randint(1, 12)

    if kind == "a_mul_n_add":
        total = a * n + b
        left = rf"{a} \times {BLANK_LATEX} + {b}"
        filled = rf"{a} \times {n} + {b}"
    elif kind == "a_mul_n_sub":
        b = random.randint(1, min(12, a * n - 1))
        total = a * n - b
        left = rf"{a} \times {BLANK_LATEX} - {b}"
        filled = rf"{a} \times {n} - {b}"
    elif kind == "n_mul_a_add":
        total = n * a + b
        left = rf"{BLANK_LATEX} \times {a} + {b}"
        filled = rf"{n} \times {a} + {b}"
    elif kind == "n_mul_a_sub":
        b = random.randint(1, min(12, n * a - 1))
        total = n * a - b
        left = rf"{BLANK_LATEX} \times {a} - {b}"
        filled = rf"{n} \times {a} - {b}"
    elif kind == "n_add_a_mul_b":
        a = random.randint(2, 8)
        b = random.randint(2, 8)
        total = n + a * b
        left = rf"{BLANK_LATEX} + {a} \times {b}"
        filled = rf"{n} + {a} \times {b}"
    elif kind == "a_mul_b_add_n":
        a = random.randint(2, 8)
        b = random.randint(2, 8)
        total = a * b + n
        left = rf"{a} \times {b} + {BLANK_LATEX}"
        filled = rf"{a} \times {b} + {n}"
    elif kind == "a_mul_b_sub_n":
        a = random.randint(3, 9)
        b = random.randint(3, 9)
        total = a * b - n
        if total < 1:
            return None
        left = rf"{a} \times {b} - {BLANK_LATEX}"
        filled = rf"{a} \times {b} - {n}"
    else:
        # (n + a) × b
        a = random.randint(1, 8)
        b = random.randint(2, 6)
        total = (n + a) * b
        left = rf"({BLANK_LATEX} + {a}) \times {b}"
        filled = rf"({n} + {a}) \times {b}"

    if not in_total_range(total):
        return None
    return left, total, filled


def one_step_equals(total):
    """Return LaTeX for a one-step expression equal to total, or None."""
    candidates = []
    # a + b
    a = random.randint(1, total - 1)
    candidates.append(f"{a} + {total - a}")
    # a - b
    b = random.randint(1, 20)
    left = total + b
    if in_value_range(left):
        candidates.append(f"{left} - {b}")
    # factors for multiplication
    for f in range(2, 13):
        if total % f == 0:
            other = total // f
            if 2 <= other <= NUMBER_VALUE_MAX:
                candidates.append(rf"{f} \times {other}")
    # a ÷ b
    b = random.randint(2, 8)
    left = total * b
    if left <= TOTAL_MAX:
        candidates.append(rf"{left} \div {b}")
    if not candidates:
        return None
    return random.choice(candidates)


def two_step_equals(total, forbidden):
    """
    Search for a two-step expression equal to total whose latex is not forbidden.
    Returns latex or None.
    """
    for _ in range(RIGHT_ATTEMPTS):
        layout = random.choice([LAYOUT_LEFT, LAYOUT_RIGHT])
        op1 = random.choice(OPS)
        op2 = random.choice(OPS)
        x = random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)
        y = random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)
        try:
            mid = apply_op(x, op1, y)
        except ValueError:
            continue
        if not (1 <= mid <= TOTAL_MAX):
            continue
        z = random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)
        try:
            result = apply_op(mid, op2, z) if layout == LAYOUT_LEFT else apply_op(z, op2, mid)
        except ValueError:
            continue
        if result != total:
            continue
        wrap = needs_parens(layout, op1, op2)
        latex = render_two_step(layout, op1, op2, x, y, z, wrap)
        if latex == forbidden:
            continue
        return latex
    return None


def try_build_balance():
    """Build one balance equation with a single blank on the left."""
    n = random.randint(ANSWER_MIN, ANSWER_MAX)
    left_built = try_left_from_answer(n)
    if left_built is None:
        return None
    left, total, filled = left_built
    # Prefer a two-step right-hand side; fall back to one-step
    right = None
    if random.random() < 0.55:
        right = two_step_equals(total, filled)
    if right is None:
        right = one_step_equals(total)
    if right is None or right == filled:
        return None
    return {
        "left": left,
        "right": right,
        "answer": n,
        "total": total,
    }


def fallback_exercise():
    """Deterministic teaching example: 3 × [ ] + 2 = 5 × 4 − 6."""
    return {
        "left": rf"3 \times {BLANK_LATEX} + 2",
        "right": r"5 \times 4 - 6",
        "answer": 4,
        "total": 14,
    }


def generate_one_exercise():
    """Build one balance-both-sides exercise."""
    for _ in range(GENERATION_ATTEMPTS):
        built = try_build_balance()
        if built is not None:
            return built
    return fallback_exercise()


def expression_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return f"{exercise['left']}={exercise['right']}"


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique balance exercises."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = expression_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format the two-sided equation with a blank on the left."""
    return rf"${exercise['left']} = {exercise['right']}$"


def format_answer(exercise):
    """Format the missing integer."""
    return rf"\textbf{{{exercise['answer']}}}"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    plain = (
        f"{exercise['left']} = {exercise['right']}"
        .replace(BLANK_LATEX, "[ ]")
        .replace(r"\left( ", "(")
        .replace(r" \right)", ")")
        .replace(r"\times", "x")
        .replace(r"\div", "/")
    )
    return f"{plain}  -> {exercise['answer']}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    for i, ex in enumerate(exercises, 1):
        print(f"{i}. {preview_line(ex)}")

    items = format_enumerate_items(format_question(ex) for ex in exercises)

    answers_section = ""
    if GENERATE_ANSWERS:
        answers_section = build_answers_section(
            [format_answer(ex) for ex in exercises],
            column_count=COLUMN_COUNT,
            itemsep=ITEMSEP,
        )

    latex_content = render_worksheet(
        title=TITLE,
        instructions=INSTRUCTIONS,
        column_count=COLUMN_COUNT,
        itemsep=ITEMSEP,
        items=items,
        answers_section=answers_section,
    )
    write_and_compile(latex_content, OUTPUT_PREFIX)


if __name__ == "__main__":
    main()
