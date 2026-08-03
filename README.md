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

## Usage

Run a script from the project directory. Each run prints the generated problems, compiles a PDF, and removes intermediate `.tex` / `.log` / `.aux` files on success.

```bash
python generate-exercises-average-numbers.py
python generate-exercises-missing-mean.py
python generate-exercises-rational-operation.py
python generate-exercises-linear-system.py
python generate-exercises-target-sum.py
```

Output PDFs are named with a timestamp, for example:

- `average_exercises_20260729143055.pdf`
- `missing_mean_20260804070000.pdf`
- `rational_operations_20260729143055.pdf`
- `linear_systems_20260729143055.pdf`
- `target_sum_20260802113000.pdf`

## Customization

At the top of each script you can adjust constants such as:

- number of exercises
- value ranges
- spacing and column layout
- output file name prefix

Then run the script again to generate a new worksheet.
