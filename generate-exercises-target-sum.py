"""Generate a printable PDF worksheet of target-sum circle exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 18
# How many numbers appear in each exercise (inclusive range)
LIST_SIZE_MIN = 5
LIST_SIZE_MAX = 8
# How many unused distractor numbers per exercise (inclusive range)
DISTRACTORS_MIN = 0
DISTRACTORS_MAX = 2
# Inclusive range for each number value
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 20
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.8cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = True
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Target Sum"
INSTRUCTIONS = (
    "For each exercise, circle the numbers that add up to the target. "
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "target_sum"


def random_value():
    """Draw one integer in the configured value range."""
    return random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)


def generate_one_exercise():
    """Build one list with a target and 0–2 distractors.

    Returns a dict with numbers, target, and selected_indices for the answer key.
    """
    # Pick total list length and how many numbers are unused distractors
    n = random.randint(LIST_SIZE_MIN, LIST_SIZE_MAX)
    d = random.randint(DISTRACTORS_MIN, DISTRACTORS_MAX)
    k = n - d

    # Solution-first: contributors define the target, then add distractors
    contributors = [random_value() for _ in range(k)]
    distractors = [random_value() for _ in range(d)]
    target = sum(contributors)

    # Tag each value so we can recover which indices belong to the solution after shuffle
    tagged = [(value, True) for value in contributors] + [
        (value, False) for value in distractors
    ]
    random.shuffle(tagged)

    numbers = [value for value, _ in tagged]
    selected_indices = [i for i, (_, selected) in enumerate(tagged) if selected]
    return {
        "numbers": numbers,
        "target": target,
        "selected_indices": selected_indices,
    }


def generate_exercises():
    """Return EXERCISE_COUNT target-sum exercises."""
    return [generate_one_exercise() for _ in range(EXERCISE_COUNT)]


def format_question(exercise):
    """Format one target + number list as a LaTeX enumerate item body."""
    joined = ", ".join(map(str, exercise["numbers"]))
    target = exercise["target"]
    return (
        rf"Target: {target}. "
        rf"\\[0.2cm] \textbf{{ {joined} }}"
    )


def format_answer(exercise):
    """Format the list with intended solution numbers underlined and bold."""
    parts = []
    selected = set(exercise["selected_indices"])
    for i, value in enumerate(exercise["numbers"]):
        text = str(value)
        # Mark the intended contributor subset for the answer key
        if i in selected:
            text = rf"\underline{{\textbf{{{text}}}}}"
        parts.append(text)
    joined = ", ".join(parts)
    return rf"Target: {exercise['target']}. {joined}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, ex in enumerate(exercises, 1):
        selected = {j for j in ex["selected_indices"]}
        marked = [
            f"[{n}]" if j in selected else str(n)
            for j, n in enumerate(ex["numbers"])
        ]
        print(f"{i}. target={ex['target']}  {', '.join(marked)}")

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
