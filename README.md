# Exercise PDF Generator

A collection of Python scripts that generate printable PDF worksheets for students. Each script produces one kind of exercise: it builds randomized problems, writes a LaTeX document, and compiles it to PDF with `pdflatex`.

## Requirements

- **Python 3** (standard library only; no extra packages)
- **`pdflatex`** (from a TeX distribution such as [TeX Live](https://www.tug.org/texlive/), [MiKTeX](https://miktex.org/), or [MacTeX](https://www.tug.org/mactex/))

Confirm both are available:

```bash
python --version
pdflatex --version
```

## Scripts

| Script | Exercise type |
|--------|----------------|
| `generate-exercises-average-numbers.py` | Calculating averages (mean) of integer sets; answers are whole numbers |
| `generate-exercises-missing-mean.py` | Find the missing number in a list so the average equals a given mean |
| `generate-exercises-rational-operation.py` | Rational-number mixed operations (integers and fractions, with order of operations) |
| `generate-exercises-linear-system.py` | Systems of two linear equations in $x$ and $y$ (unique solution; rational coeffs/answers) |
| `generate-exercises-target-sum.py` | Circle numbers in a list that add up to a target (0–2 unused distractors) |
| `generate-exercises-two-step-blank.py` | Two-step arithmetic with one missing number (any of the three slots) |
| `generate-exercises-three-step-result.py` | Three-step arithmetic (four numbers); student finds the result |
| `generate-exercises.py` | Combined worksheet: pick a template or custom counts; groups by type |

## Usage

Run a script from the project directory. Each run prints the generated problems, compiles a PDF, and removes intermediate `.tex` / `.log` / `.aux` files on success.

```bash
python generate-exercises-average-numbers.py
python generate-exercises-missing-mean.py
python generate-exercises-rational-operation.py
python generate-exercises-linear-system.py
python generate-exercises-target-sum.py
python generate-exercises-two-step-blank.py
python generate-exercises-three-step-result.py
```

### Combined worksheet

`generate-exercises.py` builds one PDF with multiple exercise types in numbered sections. Question numbering restarts at 1 inside each section; section numbers stay continuous (1, 2, 3, …). A grouped answer key is always included. The PDF title and output filename prefix come from the selected template (`title` / `output_prefix`); custom selections use `Custom` / `custom`. There is no top-level worksheet description.

Edit templates in [`exercise_templates.py`](exercise_templates.py) — add or change entries in `TEMPLATES` without touching the main script.

**Interactive (default):** choose a predefined template, or **custom** to enter a count for each type (`0` or Enter skips).

```bash
python generate-exercises.py
```

**Flags:**

```bash
# Pre-select a template (skips the menu)
python generate-exercises.py --template means
python generate-exercises.py -t mixed

# List template ids and counts
python generate-exercises.py --list-templates
```

| Template id | PDF title / filename prefix | Contents |
|-------------|-----------------------------|----------|
| `means` | Means / `means` | average 10, missing-mean 5 |
| `arithmetic` | Arithmetic / `arithmetic` | two-step 10, three-step 10 |
| `rationals` | Rationals / `rationals` | rational 12, linear 6 |
| `targets` | Targets / `targets` | target-sum 18 |
| `mixed` | Mixed / `mixed` | 4 of each type (linear 3) |

Output PDFs are named with a timestamp, for example:

- `average_exercises_20260729143055.pdf`
- `missing_mean_20260804070000.pdf`
- `rational_operations_20260729143055.pdf`
- `linear_systems_20260729143055.pdf`
- `target_sum_20260802113000.pdf`
- `two_step_blank_20260804074500.pdf`
- `three_step_result_20260811000000.pdf`
- `means_20260812100000.pdf`
- `mixed_20260812100000.pdf`
- `custom_20260812100000.pdf`

## Customization

At the top of each script you can adjust constants such as:

- number of exercises
- value ranges
- spacing and column layout
- output file name prefix

Then run the script again to generate a new worksheet.
