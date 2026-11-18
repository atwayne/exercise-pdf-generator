"""Generate a printable PDF worksheet of odd-one-out expression sets."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 8
# How many expressions appear in each set (three match, one does not)
SET_SIZE = 4
# Inclusive range for operands
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 40
# Inclusive window for the shared value
TARGET_MIN = 12
TARGET_MAX = 48
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 400
# Retries when searching for expressions equal to a target
EXPR_ATTEMPTS = 80
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.32cm"
# Two 2x2 grids per row
COLUMN_COUNT = 2
# Answers are a letter plus two values
ANSWER_COLUMN_COUNT = 2
ANSWER_ITEMSEP = "0.4cm"
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Odd One Out"
INSTRUCTIONS = "Circle the expression with a different value."
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "odd_one_out"
# Binary operators
OPS = ("+", "-", "*", "/")
# Layout identifiers: which pair is evaluated first
LAYOUT_LEFT = "left"
LAYOUT_RIGHT = "right"
# Labels printed beside the four expressions
LETTERS = ("A", "B", "C", "D")
# Nearby offsets used to build the odd expression's value
ODD_DELTAS = (1, 2, 3, 4, -1, -2, -3)


def is_additive(op):
    """True for + and - (lower precedence than \\times/\\div)."""
    return op in ("+", "-")


def is_multiplicative(op):
    """True for * and / (higher precedence than +/-)."""
    return op in ("*", "/")


def in_value_range(n):
    """True when n is a positive integer within the operand range."""
    return isinstance(n, int) and NUMBER_VALUE_MIN <= n <= NUMBER_VALUE_MAX


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
    """Build a two-step LaTeX body (no $)."""
    inner = f"{x} {latex_op(op1)} {y}"
    outer_op = latex_op(op2)
    if layout == LAYOUT_LEFT:
        if wrap:
            return rf"\left( {inner} \right) {outer_op} {z}"
        return f"{inner} {outer_op} {z}"
    if wrap:
        return rf"{z} {outer_op} \left( {inner} \right)"
    return f"{z} {outer_op} {inner}"


def one_step_for(target):
    """Return (latex, value) for a one-step expression equal to target, or None."""
    candidates = []
    if target >= 2:
        a = random.randint(1, target - 1)
        candidates.append((f"{a} + {target - a}", target))
    b = random.randint(1, 20)
    left = target + b
    if in_value_range(left):
        candidates.append((f"{left} - {b}", target))
    for f in range(2, 13):
        if target % f == 0:
            other = target // f
            if 2 <= other <= NUMBER_VALUE_MAX and f != target:
                candidates.append((rf"{f} \times {other}", target))
    b = random.randint(2, 8)
    left = target * b
    if left <= NUMBER_VALUE_MAX * 2:
        candidates.append((rf"{left} \div {b}", target))
    if not candidates:
        return None
    return random.choice(candidates)


def two_step_for(target):
    """Return (latex, value) for a two-step expression equal to target, or None."""
    for _ in range(EXPR_ATTEMPTS):
        layout = random.choice([LAYOUT_LEFT, LAYOUT_RIGHT])
        op1 = random.choice(OPS)
        op2 = random.choice(OPS)
        x = random.randint(NUMBER_VALUE_MIN, min(NUMBER_VALUE_MAX, 30))
        y = random.randint(NUMBER_VALUE_MIN, min(NUMBER_VALUE_MAX, 30))
        try:
            mid = apply_op(x, op1, y)
        except ValueError:
            continue
        if not (1 <= mid <= 80):
            continue
        z = random.randint(NUMBER_VALUE_MIN, min(NUMBER_VALUE_MAX, 30))
        try:
            result = apply_op(mid, op2, z) if layout == LAYOUT_LEFT else apply_op(z, op2, mid)
        except ValueError:
            continue
        if result != target:
            continue
        wrap = needs_parens(layout, op1, op2)
        latex = render_two_step(layout, op1, op2, x, y, z, wrap)
        return latex, result
    return None


def expression_for(target):
    """Pick a one-step or two-step expression equal to target, or None."""
    if random.random() < 0.55:
        built = one_step_for(target)
        if built is not None:
            return built
    built = two_step_for(target)
    if built is not None:
        return built
    return one_step_for(target)


def collect_expressions(target, count, forbidden_latex):
    """Collect `count` distinct expressions equal to target."""
    found = []
    seen = set(forbidden_latex)
    for _ in range(EXPR_ATTEMPTS * 2):
        built = expression_for(target)
        if built is None:
            continue
        latex, value = built
        if latex in seen or value != target:
            continue
        seen.add(latex)
        found.append(latex)
        if len(found) == count:
            return found
    return None


def generate_one_exercise():
    """
    Build one set of four expressions: three share a value, one does not.

    Returns a dict with items (letter, latex, value), odd_letter, target.
    """
    for _ in range(GENERATION_ATTEMPTS):
        target = random.randint(TARGET_MIN, TARGET_MAX)
        delta = random.choice(ODD_DELTAS)
        odd_value = target + delta
        if odd_value < 2 or odd_value == target:
            continue
        matching = collect_expressions(target, SET_SIZE - 1, set())
        if matching is None:
            continue
        odd_built = expression_for(odd_value)
        if odd_built is None:
            continue
        odd_latex, _ = odd_built
        if odd_latex in matching:
            continue
        items = [(latex, target, False) for latex in matching]
        items.append((odd_latex, odd_value, True))
        random.shuffle(items)
        labeled = []
        odd_letter = None
        for letter, (latex, value, is_odd) in zip(LETTERS, items):
            labeled.append({"letter": letter, "latex": latex, "value": value})
            if is_odd:
                odd_letter = letter
        return {
            "items": labeled,
            "odd_letter": odd_letter,
            "target": target,
            "odd_value": odd_value,
        }

    # Deterministic fallback matching the teaching example
    return {
        "items": [
            {"letter": "A", "latex": r"3 \times 8", "value": 24},
            {"letter": "B", "latex": r"20 + 4", "value": 24},
            {"letter": "C", "latex": r"30 - 7", "value": 23},
            {"letter": "D", "latex": r"6 \times 4", "value": 24},
        ],
        "odd_letter": "C",
        "target": 24,
        "odd_value": 23,
    }


def set_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return "|".join(item["latex"] for item in exercise["items"])


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique odd-one-out sets."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = set_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format four labeled expressions in a 2x2 grid with B and D aligned.

    A and C are boxed to the same width so B and D start at the same x.
    """
    items = exercise["items"]
    # Half the item width so B lines up over D inside a two-column layout
    col_width = r"0.48\linewidth"
    rows = []
    for left, right in ((items[0], items[1]), (items[2], items[3])):
        left_cell = (
            rf"\makebox[{col_width}][l]{{{left['letter']}.\ ${left['latex']}$}}"
        )
        right_cell = rf"{right['letter']}.\ ${right['latex']}$"
        rows.append(left_cell + right_cell)
    return r"\\[0.2cm]".join(rows)


def format_answer(exercise):
    """Format the odd letter only (answer key is lookup, not working)."""
    return str(exercise["odd_letter"])


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    parts = []
    for item in exercise["items"]:
        plain = (
            item["latex"]
            .replace(r"\left( ", "(")
            .replace(r" \right)", ")")
            .replace(r"\times", "x")
            .replace(r"\div", "/")
        )
        mark = "*" if item["letter"] == exercise["odd_letter"] else ""
        parts.append(f"{item['letter']}{mark}:{plain}")
    return "  ".join(parts) + f"  -> {exercise['odd_letter']}"


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
