"""Generate a printable PDF worksheet of two-truths-and-a-lie arithmetic sets."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 8
# How many claims appear in each set (two true, one false)
CLAIM_COUNT = 3
# Inclusive range for operands
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 30
# Inclusive upper bound for the intermediate (first-step) value
MID_MAX = 80
# Inclusive upper bound for claim results
RESULT_MAX = 100
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 300
# Chance an individual claim uses two operations
TWO_STEP_PROBABILITY = 0.55
# Offsets used to make a false printed result look plausible
FALSE_DELTAS = (1, 2, 3, 4, 5, -1, -2, -3, -4)
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.32cm"
# Two sets per row; each set is four short lines
COLUMN_COUNT = 2
# Answers are a letter plus the corrected result
ANSWER_COLUMN_COUNT = 2
ANSWER_ITEMSEP = "0.4cm"
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Two Truths and a Lie"
INSTRUCTIONS = "Write the letter of the lie."
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "two_truths"
# Binary operators used in generated expressions
OPS = ("+", "-", "*", "/")
# Layout identifiers: which pair is evaluated first
LAYOUT_LEFT = "left"
LAYOUT_RIGHT = "right"
# Labels printed beside the three claims
LETTERS = ("A", "B", "C")
# LaTeX placeholder for the lie's letter
BLANK_LATEX = "[~~~]"


def is_additive(op):
    """True for + and - (lower precedence than \\times/\\div)."""
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


def random_value():
    """Draw one operand from the configured value range."""
    return random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)


def render_one_step(a, op, b, printed_result):
    """Build the LaTeX math body for a one-step claim (no surrounding $)."""
    return f"{a} {latex_op(op)} {b} = {printed_result}"


def render_two_step(layout, op1, op2, x, y, z, printed_result, wrap):
    """Build the LaTeX math body for a two-step claim (no surrounding $)."""
    inner = f"{x} {latex_op(op1)} {y}"
    outer_op = latex_op(op2)
    if layout == LAYOUT_LEFT:
        body = rf"\left( {inner} \right) {outer_op} {z}" if wrap else f"{inner} {outer_op} {z}"
    else:
        body = rf"{z} {outer_op} \left( {inner} \right)" if wrap else f"{z} {outer_op} {inner}"
    return f"{body} = {printed_result}"


def pick_false_result(true_result):
    """Pick a nearby wrong result that still looks like a worksheet answer."""
    deltas = list(FALSE_DELTAS)
    random.shuffle(deltas)
    for delta in deltas:
        candidate = true_result + delta
        if in_result_range(candidate) and candidate != true_result:
            return candidate
    return None


def try_build_one_step():
    """Return a one-step expression dict, or None."""
    a, b = random_value(), random_value()
    op = random.choice(OPS)
    try:
        result = apply_op(a, op, b)
    except ValueError:
        return None
    if not in_result_range(result):
        return None
    return {"kind": "one", "a": a, "op": op, "b": b, "true_result": result}


def try_build_two_step():
    """Return a two-step expression dict, or None."""
    layout = random.choice([LAYOUT_LEFT, LAYOUT_RIGHT])
    op1 = random.choice(OPS)
    op2 = random.choice(OPS)
    x, y = random_value(), random_value()
    try:
        mid = apply_op(x, op1, y)
    except ValueError:
        return None
    if not in_mid_range(mid):
        return None
    z = random_value()
    try:
        if layout == LAYOUT_LEFT:
            result = apply_op(mid, op2, z)
        else:
            result = apply_op(z, op2, mid)
    except ValueError:
        return None
    if not in_result_range(result):
        return None
    if not (in_value_range(x) and in_value_range(y) and in_value_range(z)):
        return None
    wrap = needs_parens(layout, op1, op2)
    return {
        "kind": "two",
        "layout": layout,
        "op1": op1,
        "op2": op2,
        "x": x,
        "y": y,
        "z": z,
        "true_result": result,
        "needs_parens": wrap,
    }


def claim_latex(built, printed_result):
    """Render a built one-step or two-step claim with the printed result."""
    if built["kind"] == "one":
        return render_one_step(built["a"], built["op"], built["b"], printed_result)
    return render_two_step(
        built["layout"],
        built["op1"],
        built["op2"],
        built["x"],
        built["y"],
        built["z"],
        printed_result,
        built["needs_parens"],
    )


def try_make_claim(is_lie):
    """Build one true or false claim dict, or None."""
    builder = try_build_two_step if random.random() < TWO_STEP_PROBABILITY else try_build_one_step
    built = builder()
    if built is None:
        return None
    true_result = built["true_result"]
    if is_lie:
        printed = pick_false_result(true_result)
        if printed is None:
            return None
    else:
        printed = true_result
    return {
        "latex": claim_latex(built, printed),
        "is_lie": is_lie,
        "true_result": true_result,
        "printed_result": printed,
    }


def generate_one_exercise():
    """
    Build one two-truths-and-a-lie set.

    Returns a dict with claims (lettered) and lie_letter.
    """
    for _ in range(GENERATION_ATTEMPTS):
        lie_index = random.randrange(CLAIM_COUNT)
        claims = []
        seen = set()
        ok = True
        for i in range(CLAIM_COUNT):
            claim = None
            for _attempt in range(GENERATION_ATTEMPTS):
                candidate = try_make_claim(is_lie=(i == lie_index))
                if candidate is None:
                    continue
                if candidate["latex"] in seen:
                    continue
                claim = candidate
                break
            if claim is None:
                ok = False
                break
            seen.add(claim["latex"])
            claims.append(claim)
        if not ok:
            continue
        labeled = []
        lie_letter = None
        for letter, claim in zip(LETTERS, claims):
            labeled.append(
                {
                    "letter": letter,
                    "latex": claim["latex"],
                    "is_lie": claim["is_lie"],
                    "true_result": claim["true_result"],
                }
            )
            if claim["is_lie"]:
                lie_letter = letter
        return {"claims": labeled, "lie_letter": lie_letter}

    # Deterministic fallback matching the teaching example
    return {
        "claims": [
            {
                "letter": "A",
                "latex": r"6 \times 8 = 48",
                "is_lie": False,
                "true_result": 48,
            },
            {
                "letter": "B",
                "latex": r"50 - 17 = 33",
                "is_lie": False,
                "true_result": 33,
            },
            {
                "letter": "C",
                "latex": r"9 \times 5 + 4 = 50",
                "is_lie": True,
                "true_result": 49,
            },
        ],
        "lie_letter": "C",
    }


def set_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return "|".join(claim["latex"] for claim in exercise["claims"])


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique two-truths-and-a-lie sets."""
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
    """Format three labeled claims and a blank for the lie's letter."""
    lines = []
    for claim in exercise["claims"]:
        lines.append(rf"{claim['letter']}.\ ${claim['latex']}$")
    body = r"\\[0.08cm] ".join(lines)
    return rf"{body}\\[0.12cm] The lie is: {BLANK_LATEX}"


def format_answer(exercise):
    """Format the lie's letter and the corrected result."""
    lie = next(c for c in exercise["claims"] if c["is_lie"])
    return rf"{exercise['lie_letter']} (${lie['true_result']}$)"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    parts = []
    for claim in exercise["claims"]:
        plain = (
            claim["latex"]
            .replace(r"\left( ", "(")
            .replace(r" \right)", ")")
            .replace(r"\times", "x")
            .replace(r"\div", "/")
        )
        mark = "LIE" if claim["is_lie"] else "ok"
        parts.append(f"{claim['letter']}:{plain}[{mark}]")
    return "  ".join(parts) + f"  -> {exercise['lie_letter']}"


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
