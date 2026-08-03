"""Generate a printable PDF worksheet of two-step blank arithmetic exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 18
# Inclusive range for each operand and the missing answer
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 20
# Inclusive upper bound for the intermediate (first-step) value
MID_MAX = 100
# Inclusive upper bound for the final result
RESULT_MAX = 100
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 200
# When True, always wrap the first-step pair in parentheses.
# When False, wrap only when order of operations would change the first step.
ALWAYS_WRAP_FIRST_STEP = True
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.0cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Two-Step Blank"
INSTRUCTIONS = (
    "Find the missing number in each two-step expression, "
    "All answers are whole positive integers."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "two_step_blank"

# Binary operators used in generated expressions
OPS = ("+", "-", "*", "/")
# Layout identifiers: which pair is evaluated first
LAYOUT_LEFT = "left"
LAYOUT_RIGHT = "right"
# Blank can hide any of the three numeric slots
BLANK_SLOTS = ("x", "y", "z")
# LaTeX placeholder drawn where the missing number belongs
BLANK_LATEX = r"[~~~~~]"


def is_additive(op):
    """True for + and - (lower precedence than \times/\div)."""
    return op in ("+", "-")


def is_multiplicative(op):
    """True for * and / (higher precedence than +/-)."""
    return op in ("*", "/")


def in_value_range(n):
    """True when n is a positive integer within the operand range."""
    return isinstance(n, int) and NUMBER_VALUE_MIN <= n <= NUMBER_VALUE_MAX


def in_mid_range(n):
    """True when n is a positive intermediate within MID_MAX."""
    return isinstance(n, int) and n >= 1 and n <= MID_MAX


def in_result_range(n):
    """True when n is a positive final result within RESULT_MAX."""
    return isinstance(n, int) and n >= 1 and n <= RESULT_MAX


def apply_op(left, op, right):
    """
    Evaluate left op right for positive-integer arithmetic.
    Raises ValueError when the result would not be a positive whole number.
    """
    if op == "+":
        return left + right
    if op == "-":
        # Keep subtraction results strictly positive
        if left <= right:
            raise ValueError("non-positive subtraction")
        return left - right
    if op == "*":
        return left * right
    # Exact integer division only
    if right == 0 or left % right != 0:
        raise ValueError("non-exact division")
    return left // right


def latex_op(op):
    """Map a Python operator symbol to its LaTeX counterpart."""
    return {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[op]


def needs_parens(layout, op1, op2):
    """
    Decide whether the first-step pair must be wrapped in parentheses.
    ALWAYS_WRAP_FIRST_STEP forces wrapping; otherwise use precedence rules.
    """
    if ALWAYS_WRAP_FIRST_STEP:
        return True
    if layout == LAYOUT_LEFT:
        # Without parens, a low-precedence first step would lose to \times/\div
        return is_additive(op1) and is_multiplicative(op2)
    # Right group: omit only when outer +/− and inner \times/\div already bind first
    if is_additive(op2) and is_multiplicative(op1):
        return False
    return True


def random_value():
    """Draw one operand from the configured value range."""
    return random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)


def try_build_values(op1, op2, layout):
    """
    Pick x, y, z so both steps yield positive integers in range.
    Returns (x, y, z, mid, result) or None on failure.
    """
    x, y = random_value(), random_value()
    try:
        mid = apply_op(x, op1, y)
    except ValueError:
        return None
    if not in_mid_range(mid):
        return None

    z = random_value()
    try:
        # Left: (x op1 y) op2 z ; Right: z op2 (x op1 y)
        if layout == LAYOUT_LEFT:
            result = apply_op(mid, op2, z)
        else:
            result = apply_op(z, op2, mid)
    except ValueError:
        return None
    if not in_result_range(result):
        return None

    # Blank answer must itself lie in the operand range (all three slots do)
    if not (in_value_range(x) and in_value_range(y) and in_value_range(z)):
        return None
    return x, y, z, mid, result


def format_slot(value):
    """Render a filled number or the blank placeholder."""
    return BLANK_LATEX if value is None else str(value)


def render_expression(layout, op1, op2, x, y, z, result, wrap):
    """Build the LaTeX math body for one exercise (no surrounding $)."""
    inner = f"{format_slot(x)} {latex_op(op1)} {format_slot(y)}"
    outer_op = latex_op(op2)
    z_tex = format_slot(z)
    if layout == LAYOUT_LEFT:
        if wrap:
            body = rf"\left( {inner} \right) {outer_op} {z_tex}"
        else:
            body = f"{inner} {outer_op} {z_tex}"
    else:
        if wrap:
            body = rf"{z_tex} {outer_op} \left( {inner} \right)"
        else:
            body = f"{z_tex} {outer_op} {inner}"
    return rf"{body} = {result}"


def expression_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return render_expression(
        exercise["layout"],
        exercise["op1"],
        exercise["op2"],
        exercise["x"],
        exercise["y"],
        exercise["z"],
        exercise["result"],
        exercise["needs_parens"],
    )


def generate_one_exercise():
    """
    Build one two-step blank exercise.

    Returns a dict with layout, ops, x/y/z (blank as None), blank_slot,
    answer, mid, result, and needs_parens.
    """
    for _ in range(GENERATION_ATTEMPTS):
        layout = random.choice([LAYOUT_LEFT, LAYOUT_RIGHT])
        op1 = random.choice(OPS)
        op2 = random.choice(OPS)
        built = try_build_values(op1, op2, layout)
        if built is None:
            continue

        x, y, z, mid, result = built
        blank_slot = random.choice(BLANK_SLOTS)
        # Map slot name to the hidden answer value
        values = {"x": x, "y": y, "z": z}
        answer = values[blank_slot]
        # Question form replaces the blank slot with None
        slots = {k: (None if k == blank_slot else v) for k, v in values.items()}
        wrap = needs_parens(layout, op1, op2)

        return {
            "layout": layout,
            "op1": op1,
            "op2": op2,
            "x": slots["x"],
            "y": slots["y"],
            "z": slots["z"],
            "blank_slot": blank_slot,
            "answer": answer,
            "mid": mid,
            "result": result,
            "needs_parens": wrap,
        }

    # Deterministic fallback matching a typical worksheet example
    return {
        "layout": LAYOUT_LEFT,
        "op1": "+",
        "op2": "*",
        "x": None,
        "y": 6,
        "z": 4,
        "blank_slot": "x",
        "answer": 4,
        "mid": 10,
        "result": 40,
        "needs_parens": True,
    }


def generate_exercises():
    """Return EXERCISE_COUNT unique two-step blank exercises."""
    exercises = []
    seen = set()
    # Extra attempts so duplicate expressions can be replaced
    while len(exercises) < EXERCISE_COUNT:
        exercise = generate_one_exercise()
        key = expression_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format one blanked expression as a LaTeX enumerate item body."""
    latex = render_expression(
        exercise["layout"],
        exercise["op1"],
        exercise["op2"],
        exercise["x"],
        exercise["y"],
        exercise["z"],
        exercise["result"],
        exercise["needs_parens"],
    )
    return f"${latex}$"


def format_answer(exercise):
    """Format the missing integer as a LaTeX enumerate item body."""
    return rf"\textbf{{{exercise['answer']}}}"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    latex = expression_key(exercise)
    # Strip LaTeX noise for a clearer console dump
    plain = (
        latex.replace(r"\left( ", "(")
        .replace(r" \right)", ")")
        .replace(r"\times", "x")
        .replace(r"\div", "/")
        .replace(BLANK_LATEX, "[ ]")
    )
    return f"{plain}  -> {exercise['answer']}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, ex in enumerate(exercises, 1):
        print(f"{i}. {preview_line(ex)}")

    # Build question items for the shared LaTeX template
    items = format_enumerate_items(format_question(ex) for ex in exercises)

    # Optionally append a matching answer-key page
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
