"""Generate a printable PDF worksheet of average (mean) exercises."""

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
TITLE = "Calculating Averages"
INSTRUCTIONS = (
    "Find the average (mean) for each set of numbers. "
    "All answers evaluate to a whole integer."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "average_exercises"


def generate_exercises():
    """Return EXERCISE_COUNT number lists whose mean is a whole integer."""
    exercises = []
    while len(exercises) < EXERCISE_COUNT:
        # Pick length of this number set within the configured range
        length = random.randint(NUMBERS_PER_EXERCISE_MIN, NUMBERS_PER_EXERCISE_MAX)
        # Draw random integers within the configured value range
        nums = [
            random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX) for _ in range(length)
        ]
        # Keep only sets whose mean is a whole integer
        if sum(nums) % length == 0:
            exercises.append(nums)
    return exercises


def format_question(nums):
    """Format one number list as a LaTeX enumerate item body."""
    joined = ", ".join(map(str, nums))
    return rf"Find the average of: \\[0.2cm] \textbf{{ {joined} }}"


def format_answer(nums):
    """Format the integer mean as a LaTeX enumerate item body."""
    return rf"\textbf{{{sum(nums) // len(nums)}}}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, ex in enumerate(exercises, 1):
        print(f"{i}. {ex}")

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
