"""Generate a printable PDF worksheet of function-machine (in/out) exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 10
# Inclusive range for machine inputs
INPUT_MIN = 2
INPUT_MAX = 12
# Inclusive bound for outputs (keep mental-math friendly)
OUTPUT_MIN = 1
OUTPUT_MAX = 100
# How many given in/out pairs before the blank
EXAMPLE_COUNT = 3
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 300
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.32cm"
# Two per row; each machine is one compact in/out line
COLUMN_COUNT = 2
# Answers are a number plus a short rule
ANSWER_COLUMN_COUNT = 2
ANSWER_ITEMSEP = "0.4cm"
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Function Machine"
INSTRUCTIONS = "Find the rule, then fill in the missing output."
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "function_machine"
# Rule kinds used by the machine
RULE_ADD = "add"
RULE_SUB = "sub"
RULE_MUL = "mul"
RULE_MUL_ADD = "mul_add"
RULE_MUL_SUB = "mul_sub"
# Weighted so multiply-then-add/sub show up often (matches two-step skill)
RULE_CHOICES = (
    RULE_ADD,
    RULE_ADD,
    RULE_SUB,
    RULE_MUL,
    RULE_MUL,
    RULE_MUL_ADD,
    RULE_MUL_ADD,
    RULE_MUL_ADD,
    RULE_MUL_SUB,
    RULE_MUL_SUB,
)
# LaTeX placeholder drawn where the missing output belongs
BLANK_LATEX = "[~~~]"


def in_output_range(n):
    """True when n is a whole number inside the output window."""
    return isinstance(n, int) and OUTPUT_MIN <= n <= OUTPUT_MAX


def apply_rule(n, kind, a, b):
    """Apply a named rule to input n. b is unused for add/sub/mul."""
    if kind == RULE_ADD:
        return n + a
    if kind == RULE_SUB:
        return n - a
    if kind == RULE_MUL:
        return n * a
    if kind == RULE_MUL_ADD:
        return n * a + b
    if kind == RULE_MUL_SUB:
        return n * a - b
    raise ValueError(f"unknown rule: {kind}")


def random_rule_params(kind):
    """Draw coefficients for a rule kind."""
    if kind == RULE_ADD:
        return random.randint(3, 15), 0
    if kind == RULE_SUB:
        return random.randint(2, 8), 0
    if kind == RULE_MUL:
        return random.randint(2, 8), 0
    if kind == RULE_MUL_ADD:
        return random.randint(2, 6), random.randint(1, 12)
    if kind == RULE_MUL_SUB:
        return random.randint(2, 6), random.randint(1, 10)
    raise ValueError(f"unknown rule: {kind}")


def rule_latex(kind, a, b):
    """Short LaTeX description of the rule (no surrounding $)."""
    if kind == RULE_ADD:
        return f"+ {a}"
    if kind == RULE_SUB:
        return f"- {a}"
    if kind == RULE_MUL:
        return rf"\times {a}"
    if kind == RULE_MUL_ADD:
        return rf"\times {a} + {b}"
    if kind == RULE_MUL_SUB:
        return rf"\times {a} - {b}"
    raise ValueError(f"unknown rule: {kind}")


def try_build_machine():
    """
    Pick a rule and four distinct inputs whose outputs all stay in range.
    Returns a dict or None.
    """
    kind = random.choice(RULE_CHOICES)
    a, b = random_rule_params(kind)
    pool = list(range(INPUT_MIN, INPUT_MAX + 1))
    random.shuffle(pool)
    picked = []
    for n in pool:
        out = apply_rule(n, kind, a, b)
        if not in_output_range(out):
            continue
        picked.append((n, out))
        if len(picked) == EXAMPLE_COUNT + 1:
            break
    if len(picked) < EXAMPLE_COUNT + 1:
        return None
    # Last pair is the question; the rest are worked examples
    examples = picked[:EXAMPLE_COUNT]
    prompt_in, prompt_out = picked[EXAMPLE_COUNT]
    return {
        "kind": kind,
        "a": a,
        "b": b,
        "examples": examples,
        "prompt_in": prompt_in,
        "answer": prompt_out,
    }


def fallback_exercise():
    """Deterministic ×3 + 2 machine matching the teaching example."""
    return {
        "kind": RULE_MUL_ADD,
        "a": 3,
        "b": 2,
        "examples": [(3, 11), (5, 17), (8, 26)],
        "prompt_in": 6,
        "answer": 20,
    }


def generate_one_exercise():
    """Build one function-machine exercise with three examples and one blank."""
    for _ in range(GENERATION_ATTEMPTS):
        built = try_build_machine()
        if built is not None:
            return built
    return fallback_exercise()


def machine_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    pairs = ",".join(f"{n}->{out}" for n, out in exercise["examples"])
    return f"{pairs}|{exercise['prompt_in']}"


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique function-machine exercises."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = machine_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format given pairs and the blank output as one compact machine."""
    example_tex = r",\ ".join(
        rf"{n} \rightarrow {out}" for n, out in exercise["examples"]
    )
    prompt = rf"{exercise['prompt_in']} \rightarrow {BLANK_LATEX}"
    return rf"${example_tex},\ {prompt}$"


def format_answer(exercise):
    """Format the missing output and the rule."""
    rule = rule_latex(exercise["kind"], exercise["a"], exercise["b"])
    return rf"{exercise['answer']} (${rule}$)"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    examples = ", ".join(f"{n}->{out}" for n, out in exercise["examples"])
    rule = rule_latex(exercise["kind"], exercise["a"], exercise["b"])
    plain_rule = rule.replace(r"\times", "x")
    return (
        f"{examples}; {exercise['prompt_in']}->?  "
        f"-> {exercise['answer']}  [{plain_rule}]"
    )


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
