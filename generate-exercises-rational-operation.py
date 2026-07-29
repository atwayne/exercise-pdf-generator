import os
import random
import subprocess
from datetime import datetime
from fractions import Fraction
from math import gcd
from pathlib import Path
from string import Template

# Total number of exercises to generate
EXERCISE_COUNT = 20
# Inclusive magnitude range for standalone integers
INTEGER_MIN = 1
INTEGER_MAX = 12
# Inclusive ranges for fraction numerators and denominators
NUMERATOR_MIN = 1
NUMERATOR_MAX = 15
DENOMINATOR_MIN = 2
DENOMINATOR_MAX = 16
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.2cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Rational Numbers: Mixed Operations"
INSTRUCTIONS = (
    "Evaluate each expression using the correct order of operations. "
    "Pay attention to integer and fraction rules, as well as negative signs. "
    "Simplify all answers."
)
# Shared LaTeX worksheet template (stdlib string.Template placeholders)
TEMPLATE_FILE = Path(__file__).resolve().parent / "templates" / "worksheet.tex"
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "rational_operations"

# Build base name with current timestamp, e.g. rational_operations_20260729143055
OUTPUT_BASE = f"{OUTPUT_PREFIX}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
# Derived output paths for LaTeX and PDF
TEX_FILE = f"{OUTPUT_BASE}.tex"
PDF_FILE = f"{OUTPUT_BASE}.pdf"


def random_sign():
    """Return +1 or -1 at random."""
    return random.choice([1, -1])


def random_integer():
    """Return a non-zero random integer within the configured magnitude range."""
    return random_sign() * random.randint(INTEGER_MIN, INTEGER_MAX)


def random_fraction():
    """Return a non-zero simplified Fraction with random numerator/denominator."""
    num = random.randint(NUMERATOR_MIN, NUMERATOR_MAX)
    den = random.randint(DENOMINATOR_MIN, DENOMINATOR_MAX)
    # Reduce before applying sign so LaTeX shows a simplified fraction
    g = gcd(num, den)
    return Fraction(random_sign() * (num // g), den // g)


def random_rational():
    """Return either a random integer or fraction (as Fraction)."""
    if random.random() < 0.4:
        return Fraction(random_integer(), 1)
    return random_fraction()


def latex_rational(value):
    """Format a Fraction as LaTeX, wrapping negatives in parentheses when useful."""
    # Integer values render without a fraction bar
    if value.denominator == 1:
        body = str(value.numerator)
    else:
        # Absolute fraction for clean negative placement
        abs_num = abs(value.numerator)
        body = rf"\frac{{{abs_num}}}{{{value.denominator}}}"
        if value.numerator < 0:
            body = rf"-{body}"
    # Parenthesize negatives so adjacent operators stay unambiguous
    if value < 0:
        return rf"\left({body}\right)"
    return body


def latex_op(op):
    """Map a Python operator symbol to its LaTeX counterpart."""
    return {
        "+": "+",
        "-": "-",
        "*": r"\times",
        "/": r"\div",
    }[op]


def apply_op(left, op, right):
    """Evaluate left op right using Fraction arithmetic."""
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    # Guard against division by zero before evaluating
    if right == 0:
        raise ZeroDivisionError
    return left / right


def generate_expression():
    """
    Build one random mixed-operation expression and its exact Fraction result.
    Templates mirror the style of the original fixed worksheet.
    """
    # Random operands used across templates
    a = random_rational()
    b = random_rational()
    c = random_rational()
    d = random_rational()

    # Template builders: each returns (latex_string, exact_value)
    templates = [
        # a ± b × c
        lambda: _add_mul(a, b, c),
        # (a ± b) ÷ c
        lambda: _paren_then_div(a, b, c),
        # a × b ± c
        lambda: _mul_then_add(a, b, c),
        # a ÷ b ± c
        lambda: _div_then_add(a, b, c),
        # a ± b ± c
        lambda: _add_chain(a, b, c),
        # a × b ÷ c
        lambda: _mul_div(a, b, c),
        # (a ± b) × c
        lambda: _paren_then_mul(a, b, c),
        # a × b ± c ÷ d
        lambda: _mul_add_div(a, b, c, d),
        # (a ± b) × c ± d
        lambda: _paren_mul_add(a, b, c, d),
        # a ÷ (b ± c)
        lambda: _div_paren(a, b, c),
        # a × (b ± c) ÷ d
        lambda: _mul_paren_div(a, b, c, d),
        # (a ± b) ÷ c × d
        lambda: _paren_div_mul(a, b, c, d),
    ]

    # Keep trying templates until one evaluates without division by zero
    for _ in range(50):
        try:
            latex, value = random.choice(templates)()
            return latex, value
        except ZeroDivisionError:
            continue
    # Fallback: simple product if templates keep failing
    return f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)}", a * b


def _paren_then_div(a, b, c):
    """Template: (a ± b) ÷ c"""
    op = random.choice(["+", "-"])
    inner = a + b if op == "+" else a - b
    latex = (
        rf"\left({latex_rational(a)} {latex_op(op)} {latex_rational(b)}\right) "
        rf"{latex_op('/')} {latex_rational(c)}"
    )
    return latex, apply_op(inner, "/", c)


def _mul_then_add(a, b, c):
    """Template: a × b ± c"""
    op = random.choice(["+", "-"])
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(a * b, op, c)


def _div_then_add(a, b, c):
    """Template: a ÷ b ± c"""
    op = random.choice(["+", "-"])
    latex = (
        f"{latex_rational(a)} {latex_op('/')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(apply_op(a, "/", b), op, c)


def _add_chain(a, b, c):
    """Template: a ± b ± c"""
    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])
    latex = (
        f"{latex_rational(a)} {latex_op(op1)} {latex_rational(b)} "
        f"{latex_op(op2)} {latex_rational(c)}"
    )
    mid = apply_op(a, op1, b)
    return latex, apply_op(mid, op2, c)


def _mul_div(a, b, c):
    """Template: a × b ÷ c"""
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op('/')} {latex_rational(c)}"
    )
    return latex, apply_op(a * b, "/", c)


def _paren_then_mul(a, b, c):
    """Template: (a ± b) × c"""
    op = random.choice(["+", "-"])
    inner = a + b if op == "+" else a - b
    latex = (
        rf"\left({latex_rational(a)} {latex_op(op)} {latex_rational(b)}\right) "
        rf"{latex_op('*')} {latex_rational(c)}"
    )
    return latex, inner * c


def _add_mul(a, b, c):
    """Template: a ± b × c  (multiplication binds first)"""
    op = random.choice(["+", "-"])
    latex = (
        f"{latex_rational(a)} {latex_op(op)} {latex_rational(b)} "
        f"{latex_op('*')} {latex_rational(c)}"
    )
    return latex, apply_op(a, op, b * c)


def _mul_add_div(a, b, c, d):
    """Template: a × b ± c ÷ d"""
    op = random.choice(["+", "-"])
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)} {latex_op('/')} {latex_rational(d)}"
    )
    return latex, apply_op(a * b, op, apply_op(c, "/", d))


def _paren_mul_add(a, b, c, d):
    """Template: (a ± b) × c ± d"""
    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])
    inner = a + b if op1 == "+" else a - b
    latex = (
        rf"\left({latex_rational(a)} {latex_op(op1)} {latex_rational(b)}\right) "
        rf"{latex_op('*')} {latex_rational(c)} {latex_op(op2)} {latex_rational(d)}"
    )
    return latex, apply_op(inner * c, op2, d)


def _div_paren(a, b, c):
    """Template: a ÷ (b ± c)"""
    op = random.choice(["+", "-"])
    inner = b + c if op == "+" else b - c
    latex = (
        rf"{latex_rational(a)} {latex_op('/')} "
        rf"\left({latex_rational(b)} {latex_op(op)} {latex_rational(c)}\right)"
    )
    return latex, apply_op(a, "/", inner)


def _mul_paren_div(a, b, c, d):
    """Template: a × (b ± c) ÷ d"""
    op = random.choice(["+", "-"])
    inner = b + c if op == "+" else b - c
    latex = (
        rf"{latex_rational(a)} {latex_op('*')} "
        rf"\left({latex_rational(b)} {latex_op(op)} {latex_rational(c)}\right) "
        rf"{latex_op('/')} {latex_rational(d)}"
    )
    return latex, apply_op(a * inner, "/", d)


def _paren_div_mul(a, b, c, d):
    """Template: (a ± b) ÷ c × d"""
    op = random.choice(["+", "-"])
    inner = a + b if op == "+" else a - b
    latex = (
        rf"\left({latex_rational(a)} {latex_op(op)} {latex_rational(b)}\right) "
        rf"{latex_op('/')} {latex_rational(c)} {latex_op('*')} {latex_rational(d)}"
    )
    return latex, apply_op(inner, "/", c) * d


# Generate unique random exercises until we reach EXERCISE_COUNT
exercises = []
seen = set()
while len(exercises) < EXERCISE_COUNT:
    latex, value = generate_expression()
    # Skip duplicates so the worksheet does not repeat the same problem
    if latex in seen:
        continue
    seen.add(latex)
    exercises.append(latex)

# Display the exercises in the output for the user to see
for i, ex in enumerate(exercises, 1):
    print(f"{i}. {ex}")

# Build one enumerate item per exercise for the template
items = "\n".join(rf"    \item ${ex}$" for ex in exercises)

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
