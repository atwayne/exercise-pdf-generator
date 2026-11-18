"""Generate a printable PDF worksheet of comparison-with-blank exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 12
# Inclusive range for simple operands
NUMBER_VALUE_MIN = 2
NUMBER_VALUE_MAX = 20
# Inclusive range for the whole-number answer
ANSWER_MIN = 2
ANSWER_MAX = 20
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 400
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.7cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Comparison Blank"
INSTRUCTIONS = (
    "Write the smallest or largest whole number that makes each comparison true."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "comparison_blank"
# Goal words printed on the question
GOAL_SMALLEST = "smallest"
GOAL_LARGEST = "largest"
# Comparison operators
CMP_LT = "<"
CMP_GT = ">"
# LaTeX placeholder drawn where the missing number belongs
BLANK_LATEX = r"[~~~~~]"


def latex_op(op):
    """Map a Python operator symbol to its LaTeX counterpart."""
    return {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[op]


def in_answer_range(n):
    """True when n is a whole-number answer in the allowed window."""
    return isinstance(n, int) and ANSWER_MIN <= n <= ANSWER_MAX


def random_value(lo=NUMBER_VALUE_MIN, hi=NUMBER_VALUE_MAX):
    """Draw an integer in an inclusive range."""
    return random.randint(lo, hi)


def try_one_step_value():
    """
    Build a small one-step expression used as the known side of a comparison.
    Returns (latex_body, value) or None.
    """
    op = random.choice(("+", "-", "*"))
    a = random_value(2, 12)
    b = random_value(2, 12)
    if op == "+":
        value = a + b
    elif op == "-":
        if a <= b:
            return None
        value = a - b
    else:
        value = a * b
    # Keep the known side small enough that the blank stays in range
    if not (6 <= value <= 80):
        return None
    return f"{a} {latex_op(op)} {b}", value


def try_mul_blank():
    """a × [ ] ? bound — smallest or largest n."""
    a = random_value(2, 12)
    bound = random_value(10, 70)
    cmp_op = random.choice((CMP_LT, CMP_GT))
    if cmp_op == CMP_GT:
        # Smallest n with a*n > bound
        n = bound // a + 1
        goal = GOAL_SMALLEST
    else:
        # Largest n with a*n < bound
        n = (bound - 1) // a
        goal = GOAL_LARGEST
    if not in_answer_range(n):
        return None
    # Skip cases where 1 would already work, or the bound is a multiple that
    # makes the jump feel empty (e.g. 5 × n > 4 → n = 1)
    if goal == GOAL_SMALLEST and a * (n - 1) >= bound:
        return None
    if goal == GOAL_LARGEST and (n < ANSWER_MIN or a * (n + 1) < bound):
        return None
    latex = rf"{a} \times {BLANK_LATEX} {cmp_op} {bound}"
    return {
        "latex": latex,
        "goal": goal,
        "answer": n,
        "cmp_op": cmp_op,
    }


def try_blank_add():
    """[ ] + a ? bound — smallest or largest n."""
    a = random_value(3, 18)
    bound = random_value(10, 50)
    cmp_op = random.choice((CMP_LT, CMP_GT))
    if cmp_op == CMP_GT:
        n = bound - a + 1
        goal = GOAL_SMALLEST
    else:
        n = bound - a - 1
        goal = GOAL_LARGEST
    if not in_answer_range(n):
        return None
    latex = rf"{BLANK_LATEX} + {a} {cmp_op} {bound}"
    return {
        "latex": latex,
        "goal": goal,
        "answer": n,
        "cmp_op": cmp_op,
    }


def try_blank_sub():
    """[ ] − a ? bound — smallest or largest n."""
    a = random_value(2, 15)
    bound = random_value(4, 30)
    cmp_op = random.choice((CMP_LT, CMP_GT))
    if cmp_op == CMP_GT:
        n = bound + a + 1
        goal = GOAL_SMALLEST
    else:
        n = bound + a - 1
        goal = GOAL_LARGEST
    if not in_answer_range(n):
        return None
    latex = rf"{BLANK_LATEX} - {a} {cmp_op} {bound}"
    return {
        "latex": latex,
        "goal": goal,
        "answer": n,
        "cmp_op": cmp_op,
    }


def try_blank_add_expr():
    """[ ] + a ? one-step expression (e.g. [ ] + 18 < 3 × 12)."""
    built = try_one_step_value()
    if built is None:
        return None
    expr_tex, bound = built
    a = random_value(4, 18)
    cmp_op = random.choice((CMP_LT, CMP_GT))
    if cmp_op == CMP_GT:
        n = bound - a + 1
        goal = GOAL_SMALLEST
    else:
        n = bound - a - 1
        goal = GOAL_LARGEST
    if not in_answer_range(n):
        return None
    latex = rf"{BLANK_LATEX} + {a} {cmp_op} {expr_tex}"
    return {
        "latex": latex,
        "goal": goal,
        "answer": n,
        "cmp_op": cmp_op,
    }


def try_mul_blank_expr():
    """a × [ ] ? one-step expression (e.g. 7 × [ ] > 5 × 8)."""
    built = try_one_step_value()
    if built is None:
        return None
    expr_tex, bound = built
    a = random_value(2, 12)
    cmp_op = random.choice((CMP_LT, CMP_GT))
    if cmp_op == CMP_GT:
        n = bound // a + 1
        goal = GOAL_SMALLEST
    else:
        n = (bound - 1) // a
        goal = GOAL_LARGEST
    if not in_answer_range(n):
        return None
    latex = rf"{a} \times {BLANK_LATEX} {cmp_op} {expr_tex}"
    return {
        "latex": latex,
        "goal": goal,
        "answer": n,
        "cmp_op": cmp_op,
    }


# Pattern builders mixed so expression-vs-number questions both appear
BUILDERS = (
    try_mul_blank,
    try_mul_blank,
    try_blank_add,
    try_blank_sub,
    try_blank_add_expr,
    try_mul_blank_expr,
)


def fallback_exercise():
    """Deterministic example: smallest n with 7 × n > 40 is 6."""
    return {
        "latex": rf"7 \times {BLANK_LATEX} > 40",
        "goal": GOAL_SMALLEST,
        "answer": 6,
        "cmp_op": CMP_GT,
    }


def generate_one_exercise():
    """Build one comparison-blank exercise."""
    for _ in range(GENERATION_ATTEMPTS):
        built = random.choice(BUILDERS)()
        if built is not None:
            return built
    return fallback_exercise()


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique comparison-blank exercises."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = exercise["latex"]
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format the comparison and the smallest/largest prompt on one line."""
    goal = exercise["goal"]
    return rf"${exercise['latex']}$ \quad ({goal})"


def format_answer(exercise):
    """Format the whole-number answer."""
    return rf"\textbf{{{exercise['answer']}}}"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    plain = (
        exercise["latex"]
        .replace(BLANK_LATEX, "[ ]")
        .replace(r"\times", "x")
        .replace(r"\div", "/")
    )
    return f"{plain}  ({exercise['goal']})  -> {exercise['answer']}"


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
