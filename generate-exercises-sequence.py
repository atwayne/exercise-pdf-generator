"""Generate a printable PDF worksheet of missing-term number sequences."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 12
# How many terms appear in each sequence (inclusive range)
LENGTH_MIN = 5
LENGTH_MAX = 6
# Inclusive bound for every printed term
TERM_MIN = 1
TERM_MAX = 90
# Arithmetic-step magnitude window
ARITH_STEP_MIN = 2
ARITH_STEP_MAX = 9
# Geometric ratios (integer multiply / exact divide)
GEO_RATIOS = (2, 3)
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 300
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.32cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Sequences"
INSTRUCTIONS = "Fill in the missing term."
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "sequence"
# Sequence kinds
KIND_ARITH = "arith"
KIND_GEO = "geo"
# LaTeX placeholder drawn where the missing term belongs
BLANK_LATEX = "[~~~]"


def in_term_range(n):
    """True when n is a whole number that can appear on the page."""
    return isinstance(n, int) and TERM_MIN <= n <= TERM_MAX


def rule_latex(kind, step):
    """Short LaTeX description of the step rule (no surrounding $)."""
    if kind == KIND_ARITH:
        if step > 0:
            return f"+ {step}"
        return f"- {abs(step)}"
    if step > 0:
        return rf"\times {step}"
    return rf"\div {abs(step)}"


def try_build_arithmetic():
    """Build an arithmetic sequence and hide one term."""
    length = random.randint(LENGTH_MIN, LENGTH_MAX)
    step = random.randint(ARITH_STEP_MIN, ARITH_STEP_MAX)
    if random.random() < 0.35:
        step = -step
    # Choose a start so every term stays in range
    if step > 0:
        last_max = TERM_MAX
        start_max = last_max - step * (length - 1)
        if start_max < TERM_MIN:
            return None
        start = random.randint(TERM_MIN, start_max)
    else:
        first_min = TERM_MIN - step * (length - 1)
        if first_min > TERM_MAX:
            return None
        start = random.randint(first_min, TERM_MAX)
    terms = [start + i * step for i in range(length)]
    if not all(in_term_range(t) for t in terms):
        return None
    return terms, KIND_ARITH, step


def try_build_geometric():
    """Build a multiply or exact-divide sequence and hide one term."""
    ratio = random.choice(GEO_RATIOS)
    # Shorter than arithmetic so ×2/×3 terms stay under TERM_MAX
    length = random.randint(4, 5)
    growing = random.random() < 0.7
    if growing:
        # start * ratio^(length-1) <= TERM_MAX
        start_max = TERM_MAX // (ratio ** (length - 1))
        if start_max < 1:
            return None
        start = random.randint(1, start_max)
        terms = [start * (ratio ** i) for i in range(length)]
        step = ratio
    else:
        # start is the large end; divide by ratio each time
        end = random.randint(1, 6)
        start = end * (ratio ** (length - 1))
        if not in_term_range(start):
            return None
        terms = [start // (ratio ** i) for i in range(length)]
        step = -ratio
    if not all(in_term_range(t) for t in terms):
        return None
    # Reject a constant sequence (should not happen with ratio >= 2)
    if len(set(terms)) == 1:
        return None
    return terms, KIND_GEO, step


def generate_one_exercise():
    """
    Build one sequence with a single blank.

    Returns a dict with terms (blank as None), blank_index, answer, kind, step.
    """
    for _ in range(GENERATION_ATTEMPTS):
        builder = try_build_arithmetic if random.random() < 0.55 else try_build_geometric
        built = builder()
        if built is None:
            continue
        terms, kind, step = built
        # Keep at least three visible terms so the rule is readable
        blank_index = random.randrange(len(terms))
        answer = terms[blank_index]
        shown = [None if i == blank_index else t for i, t in enumerate(terms)]
        return {
            "terms": shown,
            "blank_index": blank_index,
            "answer": answer,
            "kind": kind,
            "step": step,
        }

    # Deterministic fallback: 4, 11, 18, 25, 32 with last blank
    return {
        "terms": [4, 11, 18, 25, None],
        "blank_index": 4,
        "answer": 32,
        "kind": KIND_ARITH,
        "step": 7,
    }


def sequence_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    parts = ["_" if t is None else str(t) for t in exercise["terms"]]
    return ",".join(parts)


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique sequence exercises."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = sequence_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format the sequence with a blank slot as a LaTeX enumerate item body."""
    parts = [BLANK_LATEX if t is None else str(t) for t in exercise["terms"]]
    joined = r",\ ".join(parts)
    return f"${joined}$"


def format_answer(exercise):
    """Format the missing term and the step rule."""
    rule = rule_latex(exercise["kind"], exercise["step"])
    return rf"{exercise['answer']} (${rule}$)"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    parts = ["__" if t is None else str(t) for t in exercise["terms"]]
    rule = rule_latex(exercise["kind"], exercise["step"]).replace(r"\times", "x").replace(r"\div", "/")
    return f"{', '.join(parts)}  -> {exercise['answer']}  [{rule}]"


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
