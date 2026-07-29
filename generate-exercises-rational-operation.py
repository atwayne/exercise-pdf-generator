"""Generate a printable PDF worksheet of rational mixed-operation exercises."""

import random
from fractions import Fraction
from math import gcd

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

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
# Chance that a random rational is an integer rather than a fraction
INTEGER_PROBABILITY = 0.4
# How many times to retry a pattern before falling back to a simple product
PATTERN_ATTEMPTS = 50
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.2cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Rational Numbers: Mixed Operations"
INSTRUCTIONS = (
    "Evaluate each expression using the correct order of operations. "
    "Pay attention to integer and fraction rules, as well as negative signs. "
    "Simplify all answers."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "rational_operations"


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
    if random.random() < INTEGER_PROBABILITY:
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


def latex_answer(value):
    """Format a Fraction answer for the answer key (no extra parentheses)."""
    if value.denominator == 1:
        return str(value.numerator)
    abs_num = abs(value.numerator)
    body = rf"\frac{{{abs_num}}}{{{value.denominator}}}"
    if value.numerator < 0:
        return rf"-{body}"
    return body


def latex_op(op):
    """Map a Python operator symbol to its LaTeX counterpart."""
    return {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[op]


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


def _pm():
    """Pick addition or subtraction at random."""
    return random.choice(["+", "-"])


def _bin(left, op, right):
    """Return (latex, value) for a single binary operation."""
    latex = f"{latex_rational(left)} {latex_op(op)} {latex_rational(right)}"
    return latex, apply_op(left, op, right)


def _paren(inner_latex):
    """Wrap an expression fragment in sized parentheses."""
    return rf"\left({inner_latex}\right)"


# --- Expression patterns: each takes operands and returns (latex, value) ---


def pat_add_mul(a, b, c):
    """Pattern: a ± b × c (multiplication binds first)."""
    op = _pm()
    latex = (
        f"{latex_rational(a)} {latex_op(op)} {latex_rational(b)} "
        f"{latex_op('*')} {latex_rational(c)}"
    )
    return latex, apply_op(a, op, b * c)


def pat_paren_div(a, b, c):
    """Pattern: (a ± b) ÷ c"""
    inner_tex, inner_val = _bin(a, _pm(), b)
    latex = f"{_paren(inner_tex)} {latex_op('/')} {latex_rational(c)}"
    return latex, apply_op(inner_val, "/", c)


def pat_mul_add(a, b, c):
    """Pattern: a × b ± c"""
    op = _pm()
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(a * b, op, c)


def pat_div_add(a, b, c):
    """Pattern: a ÷ b ± c"""
    op = _pm()
    latex = (
        f"{latex_rational(a)} {latex_op('/')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(apply_op(a, "/", b), op, c)


def pat_add_chain(a, b, c):
    """Pattern: a ± b ± c"""
    op1, op2 = _pm(), _pm()
    latex = (
        f"{latex_rational(a)} {latex_op(op1)} {latex_rational(b)} "
        f"{latex_op(op2)} {latex_rational(c)}"
    )
    return latex, apply_op(apply_op(a, op1, b), op2, c)


def pat_mul_div(a, b, c):
    """Pattern: a × b ÷ c"""
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op('/')} {latex_rational(c)}"
    )
    return latex, apply_op(a * b, "/", c)


def pat_paren_mul(a, b, c):
    """Pattern: (a ± b) × c"""
    inner_tex, inner_val = _bin(a, _pm(), b)
    latex = f"{_paren(inner_tex)} {latex_op('*')} {latex_rational(c)}"
    return latex, inner_val * c


def pat_mul_add_div(a, b, c, d):
    """Pattern: a × b ± c ÷ d"""
    op = _pm()
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)} {latex_op('/')} {latex_rational(d)}"
    )
    return latex, apply_op(a * b, op, apply_op(c, "/", d))


def pat_paren_mul_add(a, b, c, d):
    """Pattern: (a ± b) × c ± d"""
    op1, op2 = _pm(), _pm()
    inner_tex, inner_val = _bin(a, op1, b)
    latex = (
        f"{_paren(inner_tex)} {latex_op('*')} {latex_rational(c)} "
        f"{latex_op(op2)} {latex_rational(d)}"
    )
    return latex, apply_op(inner_val * c, op2, d)


def pat_div_paren(a, b, c):
    """Pattern: a ÷ (b ± c)"""
    inner_tex, inner_val = _bin(b, _pm(), c)
    latex = f"{latex_rational(a)} {latex_op('/')} {_paren(inner_tex)}"
    return latex, apply_op(a, "/", inner_val)


def pat_mul_paren_div(a, b, c, d):
    """Pattern: a × (b ± c) ÷ d"""
    inner_tex, inner_val = _bin(b, _pm(), c)
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {_paren(inner_tex)} "
        f"{latex_op('/')} {latex_rational(d)}"
    )
    return latex, apply_op(a * inner_val, "/", d)


def pat_paren_div_mul(a, b, c, d):
    """Pattern: (a ± b) ÷ c × d"""
    inner_tex, inner_val = _bin(a, _pm(), b)
    latex = (
        f"{_paren(inner_tex)} {latex_op('/')} {latex_rational(c)} "
        f"{latex_op('*')} {latex_rational(d)}"
    )
    return latex, apply_op(inner_val, "/", c) * d


# Registry of expression shapes used when sampling a random problem
EXPRESSION_PATTERNS = (
    pat_add_mul,
    pat_paren_div,
    pat_mul_add,
    pat_div_add,
    pat_add_chain,
    pat_mul_div,
    pat_paren_mul,
    pat_mul_add_div,
    pat_paren_mul_add,
    pat_div_paren,
    pat_mul_paren_div,
    pat_paren_div_mul,
)


def generate_expression():
    """
    Build one random mixed-operation expression and its exact Fraction result.
    Retries with fresh operands when a pattern hits division by zero.
    """
    for _ in range(PATTERN_ATTEMPTS):
        pattern = random.choice(EXPRESSION_PATTERNS)
        # Fresh operands sized to the chosen pattern's arity
        operands = [random_rational() for _ in range(pattern.__code__.co_argcount)]
        try:
            return pattern(*operands)
        except ZeroDivisionError:
            continue

    # Fallback: simple product if every attempt divided by zero
    a, b = random_rational(), random_rational()
    return f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)}", a * b


def generate_exercises():
    """Return EXERCISE_COUNT unique (latex, value) exercise pairs."""
    exercises = []
    seen = set()
    while len(exercises) < EXERCISE_COUNT:
        latex, value = generate_expression()
        # Skip duplicates so the worksheet does not repeat the same problem
        if latex in seen:
            continue
        seen.add(latex)
        exercises.append((latex, value))
    return exercises


def format_question(latex):
    """Wrap an expression in math mode for the questions page."""
    return f"${latex}$"


def format_answer(value):
    """Wrap a Fraction answer in math mode for the answer key."""
    return f"${latex_answer(value)}$"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, (latex, value) in enumerate(exercises, 1):
        print(f"{i}. {latex}  =  {value}")

    # Build question items for the shared LaTeX template
    items = format_enumerate_items(format_question(latex) for latex, _ in exercises)

    # Optionally append a matching answer-key page
    answers_section = ""
    if GENERATE_ANSWERS:
        answers_section = build_answers_section(
            [format_answer(value) for _, value in exercises],
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
