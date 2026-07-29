import os
import random
import subprocess
from datetime import datetime
from pathlib import Path
from string import Template

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
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Calculating Averages"
INSTRUCTIONS = (
    "Find the average (mean) for each set of numbers. "
    "All answers evaluate to a whole integer."
)
# Shared LaTeX worksheet template (stdlib string.Template placeholders)
TEMPLATE_FILE = Path(__file__).resolve().parent / "templates" / "worksheet.tex"
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "average_exercises"

# Build base name with current timestamp, e.g. average_exercises_20260729143055
OUTPUT_BASE = f"{OUTPUT_PREFIX}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
# Derived output paths for LaTeX and PDF
TEX_FILE = f"{OUTPUT_BASE}.tex"
PDF_FILE = f"{OUTPUT_BASE}.pdf"

# Generate exercises until we have EXERCISE_COUNT valid sets
exercises = []
while len(exercises) < EXERCISE_COUNT:
    # Pick length of this number set within the configured range
    L = random.randint(NUMBERS_PER_EXERCISE_MIN, NUMBERS_PER_EXERCISE_MAX)
    # Draw random integers within the configured value range
    nums = [random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX) for _ in range(L)]
    # Keep only sets whose mean is a whole integer
    if sum(nums) % L == 0:
        exercises.append(nums)

# Display the exercises in the output for the user to see
for i, ex in enumerate(exercises, 1):
    print(f"{i}. {ex}")

# Build one enumerate item per exercise for the template
items = "\n".join(
    rf"    \item Find the average of: \\[0.2cm] \textbf{{ {', '.join(map(str, ex))} }}"
    for ex in exercises
)

# Fill the shared LaTeX worksheet template with exercise-specific values
latex_content = Template(TEMPLATE_FILE.read_text(encoding="utf-8")).substitute(
    title=TITLE,
    instructions=INSTRUCTIONS,
    column_count=COLUMN_COUNT,
    itemsep=ITEMSEP,
    items=items,
)

# Write the generated LaTeX source file
with open(TEX_FILE, "w", encoding="utf-8") as f:
    f.write(latex_content)

# Compile the LaTeX source to PDF
result = subprocess.run(["pdflatex", TEX_FILE], capture_output=True, text=True)

# Report success or failure based on whether the PDF was produced
if os.path.exists(PDF_FILE):
    # Remove intermediate LaTeX artifacts; keep only the PDF
    for ext in (".tex", ".log", ".aux"):
        artifact = f"{OUTPUT_BASE}{ext}"
        if os.path.exists(artifact):
            os.remove(artifact)
    print(f"\nPDF generated successfully: {PDF_FILE}")
else:
    print("Failed to generate PDF. Output:\n", result.stdout, "\nErrors:\n", result.stderr)
