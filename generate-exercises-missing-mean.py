"""Generate a printable PDF worksheet of missing-number mean exercises."""

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
NUMBERS_PER_EXERCISE_MIN = 4
NUMBERS_PER_EXERCISE_MAX = 6
# Inclusive range for each number value (including the missing answer)
NUMBER_VALUE_MIN = 1
NUMBER_VALUE_MAX = 20
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.8cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Missing Number for Mean"
INSTRUCTIONS = (
    "Find the missing number so the average (mean) of each list equals the given mean. "
    "All answers are whole integers."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "missing_mean"


def generate_one_exercise():
    """Build one list with a blank slot and a whole-integer target mean.

    Returns a dict with numbers (blank as None), blank_index, mean, and answer.
    """
    while True:
        # Pick length of this number set within the configured range
        length = random.randint(NUMBERS_PER_EXERCISE_MIN, NUMBERS_PER_EXERCISE_MAX)
        # Draw random integers within the configured value range
        nums = [
            random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX) for _ in range(length)
        ]
        # Keep only sets whose mean is a whole integer
        if sum(nums) % length != 0:
            continue

        # Hide one random value; student recovers it from the given mean
        blank_index = random.randrange(length)
        answer = nums[blank_index]
        mean = sum(nums) // length
        # Question list shows None where the blank will be rendered
        numbers = [None if i == blank_index else n for i, n in enumerate(nums)]
        return {
            "numbers": numbers,
            "blank_index": blank_index,
            "mean": mean,
            "answer": answer,
        }


def generate_exercises():
    """Return EXERCISE_COUNT missing-number mean exercises."""
    return [generate_one_exercise() for _ in range(EXERCISE_COUNT)]


def format_question(exercise):
    """Format one mean + blanked list as a LaTeX enumerate item body."""
    # Escape underscores for LaTeX (\_\_ renders as __)
    parts = [r"\_\_" if n is None else str(n) for n in exercise["numbers"]]
    joined = ", ".join(parts)
    mean = exercise["mean"]
    return rf"Mean: {mean}. \\[0.2cm] \textbf{{ {joined} }}"


def format_answer(exercise):
    """Format the missing integer as a LaTeX enumerate item body."""
    return rf"\textbf{{{exercise['answer']}}}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, ex in enumerate(exercises, 1):
        parts = ["__" if n is None else str(n) for n in ex["numbers"]]
        print(f"{i}. mean={ex['mean']}  {', '.join(parts)}  -> {ex['answer']}")

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
