"""Generate a printable PDF worksheet of three-step result arithmetic exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 18
# Inclusive range for each operand
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 20
# Inclusive upper bound for intermediate values
MID_MAX = 100
# Inclusive upper bound for the final result
RESULT_MAX = 100
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 300
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.0cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Three-Step Result"
INSTRUCTIONS = (
    """Evaluate each expression. """
    r"""() first, then $\times$ and $\div$, then + and $-$. Always working left to right."""
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "three_step_result"

# Binary operators used in generated expressions
OPS = ("+", "-", "*", "/")
# Five Catalan association trees over four operands
LAYOUT_LEFT_LEFT = "left_left"
LAYOUT_LEFT_INNER = "left_inner"
LAYOUT_TWO_GROUPS = "two_groups"
LAYOUT_RIGHT_INNER = "right_inner"
LAYOUT_RIGHT_RIGHT = "right_right"
LAYOUTS = (
    LAYOUT_LEFT_LEFT,
    LAYOUT_LEFT_INNER,
    LAYOUT_TWO_GROUPS,
    LAYOUT_RIGHT_INNER,
    LAYOUT_RIGHT_RIGHT,
)
# Operator precedence for minimal parentheses (higher binds tighter)
OP_PREC = {"+": 1, "-": 1, "*": 2, "/": 2}
# LaTeX placeholder drawn where the missing result belongs
BLANK_LATEX = r"[~~~~~]"


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


def random_value():
    """Draw one operand from the configured value range."""
    return random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)


def build_tree(layout, a, b, c, d, op1, op2, op3):
    """
    Build an expression tree for the chosen association layout.
    Leaves are ints; internal nodes are (op, left, right) tuples.
    """
    if layout == LAYOUT_LEFT_LEFT:
        # ((a op1 b) op2 c) op3 d
        return (op3, (op2, (op1, a, b), c), d)
    if layout == LAYOUT_LEFT_INNER:
        # (a op1 (b op2 c)) op3 d
        return (op3, (op1, a, (op2, b, c)), d)
    if layout == LAYOUT_TWO_GROUPS:
        # (a op1 b) op2 (c op3 d)
        return (op2, (op1, a, b), (op3, c, d))
    if layout == LAYOUT_RIGHT_INNER:
        # a op1 ((b op2 c) op3 d)
        return (op1, a, (op3, (op2, b, c), d))
    if layout == LAYOUT_RIGHT_RIGHT:
        # a op1 (b op2 (c op3 d))
        return (op1, a, (op2, b, (op3, c, d)))
    raise ValueError(f"unknown layout: {layout}")


def evaluate_tree(node, intermediates):
    """
    Recursively evaluate a tree, appending each binary result to intermediates.
    Raises ValueError when apply_op rejects a step.
    """
    # Leaf operand
    if isinstance(node, int):
        return node
    op, left, right = node
    left_val = evaluate_tree(left, intermediates)
    right_val = evaluate_tree(right, intermediates)
    value = apply_op(left_val, op, right_val)
    intermediates.append(value)
    return value


def try_build_values(layout, op1, op2, op3):
    """
    Pick a, b, c, d so the layout tree yields positive integers in range.
    Returns (a, b, c, d, result) or None on failure.
    """
    a, b, c, d = random_value(), random_value(), random_value(), random_value()
    tree = build_tree(layout, a, b, c, d, op1, op2, op3)
    intermediates = []
    try:
        result = evaluate_tree(tree, intermediates)
    except ValueError:
        return None

    # Three binary steps: first two are mids, last is the final result
    if len(intermediates) != 3:
        return None
    mid1, mid2, final = intermediates
    if not (in_mid_range(mid1) and in_mid_range(mid2)):
        return None
    if final != result or not in_result_range(result):
        return None
    if not all(in_value_range(n) for n in (a, b, c, d)):
        return None
    return a, b, c, d, result


def render_node(node, parent_prec=None, is_right=False):
    """
    Render a tree with minimal parentheses for left-associative PEMDAS.
    Wrap a child when it has lower precedence, or the same precedence on the
    right (so a-(b-c) and a/(b/c) stay distinct from left-associated chains).
    """
    if isinstance(node, int):
        return str(node)

    op, left, right = node
    prec = OP_PREC[op]
    left_tex = render_node(left, parent_prec=prec, is_right=False)
    right_tex = render_node(right, parent_prec=prec, is_right=True)
    body = f"{left_tex} {latex_op(op)} {right_tex}"

    # Top-level expression never gets an outer wrap
    if parent_prec is None:
        return body
    needs_wrap = prec < parent_prec or (prec == parent_prec and is_right)
    if needs_wrap:
        return rf"\left( {body} \right)"
    return body


def render_expression(layout, op1, op2, op3, a, b, c, d):
    """Build the LaTeX math body for one exercise (no surrounding $)."""
    tree = build_tree(layout, a, b, c, d, op1, op2, op3)
    body = render_node(tree)
    return rf"{body} = {BLANK_LATEX}"


def expression_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return render_expression(
        exercise["layout"],
        exercise["op1"],
        exercise["op2"],
        exercise["op3"],
        exercise["a"],
        exercise["b"],
        exercise["c"],
        exercise["d"],
    )


def generate_one_exercise():
    """
    Build one three-step result exercise.

    Returns a dict with layout, ops, operands, and the numeric answer.
    """
    for _ in range(GENERATION_ATTEMPTS):
        layout = random.choice(LAYOUTS)
        op1 = random.choice(OPS)
        op2 = random.choice(OPS)
        op3 = random.choice(OPS)
        built = try_build_values(layout, op1, op2, op3)
        if built is None:
            continue

        a, b, c, d, result = built
        return {
            "layout": layout,
            "op1": op1,
            "op2": op2,
            "op3": op3,
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "answer": result,
        }

    # Deterministic fallback matching the plan example: (2+3)*(9-1)=40
    return {
        "layout": LAYOUT_TWO_GROUPS,
        "op1": "+",
        "op2": "*",
        "op3": "-",
        "a": 2,
        "b": 3,
        "c": 9,
        "d": 1,
        "answer": 40,
    }


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique three-step result exercises."""
    exercises = []
    seen = set()
    # Extra attempts so duplicate expressions can be replaced
    while len(exercises) < count:
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
        exercise["op3"],
        exercise["a"],
        exercise["b"],
        exercise["c"],
        exercise["d"],
    )
    return f"${latex}$"


def format_answer(exercise):
    """Format the computed result as a LaTeX enumerate item body."""
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
    return f"{plain}  -> {exercise['answer']}  [{exercise['layout']}]"


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
