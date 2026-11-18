"""Generate worksheets of two-digit x two-digit multiplication broken into steps."""

import argparse
import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 6
# Inclusive range for each two-digit factor
FACTOR_MIN = 11
FACTOR_MAX = 99
# "1x" teens: on junior, this is always the expanded (split) factor
TEEN_MIN = 11
TEEN_MAX = 19
# Non-teen range used as the kept factor on junior
NON_TEEN_MIN = 20
NON_TEEN_MAX = 99


class LevelSpec:
    """Difficulty rules: product cap and whether exactly one teen is required."""

    def __init__(self, product_cap, require_exactly_one_teen):
        # Inclusive upper bound on kept * split, or None for no cap
        self.product_cap = product_cap
        # When True, split is a teen and kept is a non-teen
        self.require_exactly_one_teen = require_exactly_one_teen


# Named levels used by CLI and generate_exercises
LEVELS = {
    "junior": LevelSpec(product_cap=500, require_exactly_one_teen=True),
    "easy": LevelSpec(product_cap=500, require_exactly_one_teen=False),
    "medium": LevelSpec(product_cap=1000, require_exactly_one_teen=False),
    "difficult": LevelSpec(product_cap=None, require_exactly_one_teen=False),
}
# Default difficulty for standalone and combined-worksheet calls
DIFFICULTY = "junior"
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 500
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.0cm"
# One column so the multi-line step stack stays readable
COLUMN_COUNT = 1
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Two-Digit Multiplication Steps"
INSTRUCTIONS = (
    r"""Fill in each blank to complete the steps."""
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "digit_mul_steps"
# LaTeX placeholder drawn where the missing number belongs
# Twice as wide as the usual [~~~~~] so multi-digit answers fit
BLANK_LATEX = r"[~~~~~~~~~~]"
# Line break between scaffold steps
STEP_GAP = r"\\[0.15cm]"
# Deterministic fallback that satisfies junior (54 x 13 = 702 is too large;
# use 24 x 15 = 360 which keeps a non-teen and expands the teen)
FALLBACK_KEPT = 24
FALLBACK_SPLIT = 15


def get_level(name):
    """Return the LevelSpec for a difficulty name, or raise ValueError."""
    if name not in LEVELS:
        raise ValueError(f"Unknown difficulty: {name}")
    return LEVELS[name]


def is_teen(n):
    """True when n is in the 1x teen range (11-19)."""
    return TEEN_MIN <= n <= TEEN_MAX


def product_ok(kept, split, spec):
    """True when kept * split is within the level's product cap (if any)."""
    product = kept * split
    if spec.product_cap is not None and product > spec.product_cap:
        return False
    return True


def format_slot(value):
    """Render a filled number or the blank placeholder."""
    return BLANK_LATEX if value is None else str(value)


def compute_parts(kept, split):
    """
    Derive all intermediate values for kept x split with split expanded.

    Returns a dict of named parts used by question and answer formatting.
    """
    tens = split // 10
    ones = split % 10
    tens_part = tens * 10
    partial_tens = kept * tens
    partial_ones = kept * ones
    shifted = partial_tens * 10
    result = kept * split
    return {
        "kept": kept,
        "split": split,
        "tens": tens,
        "ones": ones,
        "tens_part": tens_part,
        "partial_tens": partial_tens,
        "partial_ones": partial_ones,
        "shifted": shifted,
        "result": result,
    }


def _split_has_ones(n):
    """True when n is not a multiple of 10 (ones part of the split is meaningful)."""
    return n % 10 != 0


def try_sample_factors(level):
    """
    Sample (kept, split) under the level's teen and product rules.

    Returns (kept, split) or None when the attempt is invalid.
    """
    spec = get_level(level)

    if spec.require_exactly_one_teen:
        # Junior: keep the non-teen; always expand the 1x (teen) factor
        kept = random.randint(NON_TEEN_MIN, NON_TEEN_MAX)
        split = random.randint(TEEN_MIN, TEEN_MAX)
        if is_teen(kept) or not is_teen(split):
            return None
    else:
        # Easy / medium / difficult: any two factors; randomly assign roles
        left = random.randint(FACTOR_MIN, FACTOR_MAX)
        right = random.randint(FACTOR_MIN, FACTOR_MAX)
        if random.choice((True, False)):
            kept, split = left, right
        else:
            kept, split = right, left

    if not _split_has_ones(split):
        return None
    if not product_ok(kept, split, spec):
        return None
    return kept, split


def generate_one_exercise(level=None):
    """
    Build one stepped two-digit multiplication exercise.

    Returns a dict with filled parts, answer, and level.
    """
    if level is None:
        level = DIFFICULTY

    for _ in range(GENERATION_ATTEMPTS):
        sampled = try_sample_factors(level)
        if sampled is None:
            continue
        kept, split = sampled
        parts = compute_parts(kept, split)
        return {
            **parts,
            "level": level,
            "answer": parts["result"],
        }

    # Deterministic fallback that fits junior (and easy product cap)
    parts = compute_parts(FALLBACK_KEPT, FALLBACK_SPLIT)
    return {
        **parts,
        "level": level,
        "answer": parts["result"],
    }


def exercise_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    return f"{exercise['kept']}x{exercise['split']}"


def generate_exercises(count=EXERCISE_COUNT, level=None):
    """Return `count` unique digit-mul-steps exercises for the given difficulty."""
    if level is None:
        level = DIFFICULTY
    # Validate level name early
    get_level(level)
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise(level=level)
        key = exercise_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def render_question_lines(exercise, blanked=True):
    """
    Build the multi-line LaTeX math bodies for one exercise.

    When blanked is True, hide the slots students must fill; otherwise show all values.
    When split's tens part is already 10, skip peeling 10 into 1 x 10.
    """
    kept = exercise["kept"]
    split = exercise["split"]
    ones = exercise["ones"]
    # Tens digit is 1 => tens_part is 10; no need to rewrite as 1 x 10
    skip_tens_peel = exercise["tens"] == 1

    # Question blanks: tens_part, ones, tens_part again, kept on distribute line,
    # tens digit, partial_tens, partial_ones, shifted, partial_ones again, result
    if blanked:
        tens_part = None
        ones_slot = None
        tens_part_2 = None
        kept_dist = None
        tens = None
        partial_tens = None
        partial_ones = None
        shifted = None
        partial_ones_2 = None
        result = None
    else:
        tens_part = exercise["tens_part"]
        ones_slot = ones
        tens_part_2 = exercise["tens_part"]
        kept_dist = kept
        tens = exercise["tens"]
        partial_tens = exercise["partial_tens"]
        partial_ones = exercise["partial_ones"]
        shifted = exercise["shifted"]
        partial_ones_2 = exercise["partial_ones"]
        result = exercise["result"]

    lines = [
        rf"{kept} \times {split}",
        (
            rf"= {kept} \times \left( {format_slot(tens_part)} + "
            rf"{format_slot(ones_slot)} \right)"
        ),
        (
            rf"= {kept} \times {format_slot(tens_part_2)} + "
            rf"{format_slot(kept_dist)} \times {ones}"
        ),
    ]
    # Only peel tens_part into (tens digit) x 10 when that digit is not already 1
    if not skip_tens_peel:
        lines.append(
            rf"= {kept} \times {format_slot(tens)} \times 10 + "
            rf"{kept} \times {ones}"
        )
        lines.append(
            rf"= {format_slot(partial_tens)} \times 10 + "
            rf"{format_slot(partial_ones)}"
        )
    lines.extend(
        [
            (
                rf"= {format_slot(shifted)} + "
                rf"{format_slot(partial_ones_2)}"
            ),
            rf"= {format_slot(result)}",
        ]
    )
    return lines


def format_question(exercise):
    """Format one blanked multi-line scaffold as a LaTeX enumerate item body."""
    lines = render_question_lines(exercise, blanked=True)
    # Join with small vertical gaps between step lines
    joined = STEP_GAP.join(f"${line}$" for line in lines)
    return joined


def format_answer(exercise):
    """Format the final product as a LaTeX enumerate item body."""
    return rf"\textbf{{{exercise['answer']}}}"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    kept = exercise["kept"]
    split = exercise["split"]
    peel_note = " (skip 1x10)" if exercise["tens"] == 1 else ""
    teen_note = " [teen split]" if is_teen(split) and not is_teen(kept) else ""
    return (
        f"{kept} x {split} = {kept} x ({exercise['tens_part']} + {exercise['ones']}) "
        f"= ... = {exercise['result']}{peel_note}{teen_note}"
    )


def parse_args(argv=None):
    """Parse standalone CLI flags (difficulty level)."""
    parser = argparse.ArgumentParser(
        description="Generate two-digit stepped multiplication worksheets."
    )
    parser.add_argument(
        "--level",
        choices=list(LEVELS.keys()),
        default=DIFFICULTY,
        help="Difficulty level (default: junior).",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Generate exercises, render the worksheet, and compile the PDF."""
    args = parse_args(argv)
    level = args.level
    spec = get_level(level)
    exercises = generate_exercises(level=level)

    # Show the problems in the terminal for a quick preview
    cap_text = spec.product_cap if spec.product_cap is not None else "none"
    teen_text = "exactly one teen" if spec.require_exactly_one_teen else "any factors"
    print(f"Difficulty: {level} (product cap={cap_text}, {teen_text})")
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
