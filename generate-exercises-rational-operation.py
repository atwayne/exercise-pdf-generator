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
PATTERN_ATTEMPTS = 80
# Shared factors used when building related denominators for ±
RELATED_DEN_FACTORS = (2, 3, 4, 5, 6)
# Cap on lcm of ± denominators so common dens stay manageable (allows 12 & 16)
RELATED_LCM_MAX = 48
# Smaller numerators for ± fractions keep intermediate sums small
ADD_NUMERATOR_MAX = 8
# Cancel factors used when building cross-cancelling ×/÷ pairs
MUL_CANCEL_FACTORS = (2, 3, 4, 5)
# Retries when constructing friendly operand pairs
FRIENDLY_ATTEMPTS = 40
# Reject final (and intermediate) values whose reduced form is too large
ANSWER_NUM_MAX = 36
ANSWER_DEN_MAX = 36
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


def _lcm(a, b):
    """Least common multiple of two positive integers."""
    return abs(a * b) // gcd(a, b)


def _lcm_many(values):
    """Least common multiple of an iterable of positive integers."""
    result = 1
    for value in values:
        result = _lcm(result, value)
    return result


def is_simple_rational(value):
    """True when a reduced Fraction stays within student-friendly bounds."""
    return (
        abs(value.numerator) <= ANSWER_NUM_MAX
        and value.denominator <= ANSWER_DEN_MAX
    )


def random_coprime_numerator(den, num_max=NUMERATOR_MAX):
    """
    Pick a numerator in range that is already coprime to den.
    Falls back to 1 if no other candidate exists in range.
    """
    candidates = [
        n
        for n in range(NUMERATOR_MIN, num_max + 1)
        if gcd(n, den) == 1
    ]
    if not candidates:
        return 1
    return random.choice(candidates)


def fraction_with_denominator(den, num_max=NUMERATOR_MAX):
    """Return a signed Fraction over den that is already in lowest terms."""
    num = random_coprime_numerator(den, num_max=num_max)
    return Fraction(random_sign() * num, den)


def random_fraction():
    """Return a non-zero already-reduced Fraction with a random denominator."""
    den = random.randint(DENOMINATOR_MIN, DENOMINATOR_MAX)
    return fraction_with_denominator(den)


def random_rational():
    """Return either a random integer or fraction (as Fraction)."""
    if random.random() < INTEGER_PROBABILITY:
        return Fraction(random_integer(), 1)
    return random_fraction()


def related_denominators(count):
    """
    Return `count` denominators that share a common factor g > 1
    and whose overall LCM is at most RELATED_LCM_MAX.
    Example: g=4 may yield [12, 16] (lcm 48).
    """
    # Prefer factors that still leave enough multiples in the den range
    viable = []
    for g in RELATED_DEN_FACTORS:
        multiples = [
            d
            for d in range(DENOMINATOR_MIN, DENOMINATOR_MAX + 1)
            if d % g == 0
        ]
        if len(multiples) >= min(count, 2):
            viable.append((g, multiples))
    if not viable:
        pool = list(range(DENOMINATOR_MIN, DENOMINATOR_MAX + 1))
        return [random.choice(pool) for _ in range(count)]

    for _ in range(FRIENDLY_ATTEMPTS):
        g, multiples = random.choice(viable)
        dens = [random.choice(multiples) for _ in range(count)]
        # Prefer at least two distinct dens when possible
        if count >= 2 and len(set(dens)) == 1 and len(multiples) > 1:
            dens[1] = random.choice([m for m in multiples if m != dens[0]])
        if _lcm_many(dens) <= RELATED_LCM_MAX:
            return dens

    # Fallback: repeated small shared den keeps LCM tiny
    g, multiples = min(viable, key=lambda item: min(item[1]))
    small = min(multiples)
    return [small] * count


def friendly_add_fractions(n):
    """
    Return n already-reduced fractions whose dens share a factor,
    with small LCM and numerators so ± intermediates stay manageable.
    """
    for _ in range(FRIENDLY_ATTEMPTS):
        dens = related_denominators(n)
        fracs = [
            fraction_with_denominator(d, num_max=ADD_NUMERATOR_MAX) for d in dens
        ]
        # Require pairwise ± of the first two to stay within bounds
        if n >= 2:
            a, b = fracs[0], fracs[1]
            if not (is_simple_rational(a + b) and is_simple_rational(a - b)):
                continue
        if n >= 3:
            a, b, c = fracs[0], fracs[1], fracs[2]
            samples = (a + b + c, a + b - c, a - b + c, a - b - c)
            if not all(is_simple_rational(sample) for sample in samples):
                continue
        return fracs

    # Last resort: identical small dens with tiny numerators
    den = 4
    return [Fraction(random_sign() * 1, den) for _ in range(n)]


def _has_cross_cancel(left, right):
    """True if left/right allow cancelling across a × (or ÷ as × reciprocal)."""
    a, b = abs(left.numerator), left.denominator
    c, d = abs(right.numerator), right.denominator
    return gcd(a, d) > 1 or gcd(c, b) > 1


def _only_shared_dens(left, right):
    """True when dens share a factor but there is no cross-cancellation."""
    b, d = left.denominator, right.denominator
    return gcd(b, d) > 1 and not _has_cross_cancel(left, right)


def friendly_mul_pair():
    """
    Build two fractions that cross-cancel under multiplication.
    Rejects pairs that only share denominator factors (e.g. 1/12 × 3/16).
    """
    for _ in range(FRIENDLY_ATTEMPTS):
        f = random.choice(MUL_CANCEL_FACTORS)
        # Attach cancel factor to left numerator and right denominator (or swap)
        if random.random() < 0.5:
            # left = (f*a')/b , right = c/(f*d')  with internal coprimality
            b = random.randint(DENOMINATOR_MIN, DENOMINATOR_MAX)
            if gcd(f, b) != 1:
                continue
            a_core_max = NUMERATOR_MAX // f
            if a_core_max < NUMERATOR_MIN:
                continue
            a_core = random.randint(NUMERATOR_MIN, a_core_max)
            if gcd(f * a_core, b) != 1:
                continue
            d_core_max = DENOMINATOR_MAX // f
            if d_core_max < 1:
                continue
            # Right den must stay in configured range after multiplying by f
            d_candidates = [
                d
                for d in range(1, d_core_max + 1)
                if DENOMINATOR_MIN <= f * d <= DENOMINATOR_MAX
            ]
            if not d_candidates:
                continue
            d_core = random.choice(d_candidates)
            c = random_coprime_numerator(f * d_core)
            left = Fraction(random_sign() * f * a_core, b)
            right = Fraction(random_sign() * c, f * d_core)
        else:
            # left = a/(f*b') , right = (f*c')/d
            d = random.randint(DENOMINATOR_MIN, DENOMINATOR_MAX)
            if gcd(f, d) != 1:
                continue
            c_core_max = NUMERATOR_MAX // f
            if c_core_max < NUMERATOR_MIN:
                continue
            c_core = random.randint(NUMERATOR_MIN, c_core_max)
            if gcd(f * c_core, d) != 1:
                continue
            b_core_max = DENOMINATOR_MAX // f
            if b_core_max < 1:
                continue
            b_candidates = [
                b
                for b in range(1, b_core_max + 1)
                if DENOMINATOR_MIN <= f * b <= DENOMINATOR_MAX
            ]
            if not b_candidates:
                continue
            b_core = random.choice(b_candidates)
            a = random_coprime_numerator(f * b_core)
            left = Fraction(random_sign() * a, f * b_core)
            right = Fraction(random_sign() * f * c_core, d)

        # Keep each side reduced and require real cross-cancel, not dens-only share
        if left.denominator == 1 or right.denominator == 1:
            continue
        if gcd(abs(left.numerator), left.denominator) != 1:
            continue
        if gcd(abs(right.numerator), right.denominator) != 1:
            continue
        if not _has_cross_cancel(left, right):
            continue
        if _only_shared_dens(left, right):
            continue
        # Product itself must stay student-sized
        if not is_simple_rational(left * right):
            continue
        return left, right

    # Fallback: force a simple cross-cancel pair within range
    left = Fraction(random_sign() * 2, 3)
    right = Fraction(random_sign() * 1, 4)
    return left, right


def friendly_div_pair():
    """
    Build a ÷ b as a × (1/b) with cross-cancellation against the reciprocal.
    Returns (dividend, divisor).
    """
    left, recip = friendly_mul_pair()
    # recip is the multiplicative partner; invert to get the divisor
    if recip.numerator == 0:
        raise ZeroDivisionError
    divisor = Fraction(recip.denominator, recip.numerator)
    return left, divisor


def partner_keeping_simple(value, mode):
    """
    Pick a rational partner so value ∘ partner stays within answer bounds.
    mode is '*', '/', '+', or '-'.
    """
    for _ in range(FRIENDLY_ATTEMPTS):
        if mode in ("+", "-") and value.denominator > 1:
            dens = related_denominators(2)
            related = [d for d in dens if gcd(d, value.denominator) > 1]
            den = random.choice(related or dens)
            partner = fraction_with_denominator(den, num_max=ADD_NUMERATOR_MAX)
        elif random.random() < 0.5:
            partner = random_fraction()
        else:
            partner = Fraction(random_integer(), 1)

        if mode == "*":
            if partner != 0 and is_simple_rational(value * partner):
                if partner.denominator == 1 or _has_cross_cancel(value, partner):
                    return partner
        elif mode == "/":
            if partner == 0:
                continue
            result = value / partner
            if is_simple_rational(result):
                if partner.denominator == 1 or _has_cross_cancel(value, 1 / partner):
                    return partner
        elif mode == "+" and is_simple_rational(value + partner):
            return partner
        elif mode == "-" and is_simple_rational(value - partner):
            return partner

    # Tiny integer fallback that usually keeps results small
    for magnitude in range(INTEGER_MIN, INTEGER_MAX + 1):
        partner = Fraction(random_sign() * magnitude, 1)
        if mode == "*" and is_simple_rational(value * partner):
            return partner
        if mode == "/" and partner != 0 and is_simple_rational(value / partner):
            return partner
        if mode == "+" and is_simple_rational(value + partner):
            return partner
        if mode == "-" and is_simple_rational(value - partner):
            return partner
    return Fraction(1, 1)


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


# --- Expression patterns: each builds its own friendly operands ---


def pat_add_mul():
    """Pattern: a ± b × c (multiplication binds first; b,c cross-cancel)."""
    b, c = friendly_mul_pair()
    product = b * c
    op = _pm()
    a = partner_keeping_simple(product, op)
    latex = (
        f"{latex_rational(a)} {latex_op(op)} {latex_rational(b)} "
        f"{latex_op('*')} {latex_rational(c)}"
    )
    return latex, apply_op(a, op, product)


def pat_paren_div():
    """Pattern: (a ± b) ÷ c with related dens inside the paren."""
    a, b = friendly_add_fractions(2)
    inner_tex, inner_val = _bin(a, _pm(), b)
    if not is_simple_rational(inner_val):
        raise ZeroDivisionError
    c = partner_keeping_simple(inner_val, "/")
    latex = f"{_paren(inner_tex)} {latex_op('/')} {latex_rational(c)}"
    return latex, apply_op(inner_val, "/", c)


def pat_mul_add():
    """Pattern: a × b ± c with cross-cancelling product pair."""
    a, b = friendly_mul_pair()
    product = a * b
    op = _pm()
    c = partner_keeping_simple(product, op)
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(product, op, c)


def pat_div_add():
    """Pattern: a ÷ b ± c with cross-cancelling division pair."""
    a, b = friendly_div_pair()
    quotient = apply_op(a, "/", b)
    if not is_simple_rational(quotient):
        raise ZeroDivisionError
    op = _pm()
    c = partner_keeping_simple(quotient, op)
    latex = (
        f"{latex_rational(a)} {latex_op('/')} {latex_rational(b)} "
        f"{latex_op(op)} {latex_rational(c)}"
    )
    return latex, apply_op(quotient, op, c)


def pat_add_chain():
    """Pattern: a ± b ± c with related denominators across the chain."""
    a, b, c = friendly_add_fractions(3)
    op1, op2 = _pm(), _pm()
    latex = (
        f"{latex_rational(a)} {latex_op(op1)} {latex_rational(b)} "
        f"{latex_op(op2)} {latex_rational(c)}"
    )
    return latex, apply_op(apply_op(a, op1, b), op2, c)


def pat_mul_div():
    """Pattern: a × b ÷ c; a,b cross-cancel, then ÷ c stays simple."""
    a, b = friendly_mul_pair()
    product = a * b
    c = partner_keeping_simple(product, "/")
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
        f"{latex_op('/')} {latex_rational(c)}"
    )
    return latex, apply_op(product, "/", c)


def pat_paren_mul():
    """Pattern: (a ± b) × c with related dens inside the paren."""
    a, b = friendly_add_fractions(2)
    inner_tex, inner_val = _bin(a, _pm(), b)
    if not is_simple_rational(inner_val):
        raise ZeroDivisionError
    c = partner_keeping_simple(inner_val, "*")
    latex = f"{_paren(inner_tex)} {latex_op('*')} {latex_rational(c)}"
    return latex, inner_val * c


def pat_mul_add_div():
    """Pattern: a × b ± c ÷ d with two friendly mul/div pairs and a simple sum."""
    for _ in range(FRIENDLY_ATTEMPTS):
        a, b = friendly_mul_pair()
        c, d = friendly_div_pair()
        op = _pm()
        left = a * b
        right = apply_op(c, "/", d)
        result = apply_op(left, op, right)
        if not is_simple_rational(result):
            continue
        latex = (
            f"{latex_rational(a)} {latex_op('*')} {latex_rational(b)} "
            f"{latex_op(op)} {latex_rational(c)} {latex_op('/')} {latex_rational(d)}"
        )
        return latex, result
    raise ZeroDivisionError


def pat_paren_mul_add():
    """Pattern: (a ± b) × c ± d with related dens and bounded trailing ops."""
    a, b = friendly_add_fractions(2)
    op1, op2 = _pm(), _pm()
    inner_tex, inner_val = _bin(a, op1, b)
    if not is_simple_rational(inner_val):
        raise ZeroDivisionError
    c = partner_keeping_simple(inner_val, "*")
    mid = inner_val * c
    d = partner_keeping_simple(mid, op2)
    latex = (
        f"{_paren(inner_tex)} {latex_op('*')} {latex_rational(c)} "
        f"{latex_op(op2)} {latex_rational(d)}"
    )
    return latex, apply_op(mid, op2, d)


def pat_div_paren():
    """Pattern: a ÷ (b ± c) with related dens inside the paren."""
    b, c = friendly_add_fractions(2)
    inner_tex, inner_val = _bin(b, _pm(), c)
    if inner_val == 0 or not is_simple_rational(inner_val):
        raise ZeroDivisionError
    # Choose dividend so the quotient stays within answer bounds
    for _ in range(FRIENDLY_ATTEMPTS):
        a = random_rational()
        result = a / inner_val
        if is_simple_rational(result):
            latex = f"{latex_rational(a)} {latex_op('/')} {_paren(inner_tex)}"
            return latex, result
    raise ZeroDivisionError


def pat_mul_paren_div():
    """Pattern: a × (b ± c) ÷ d with related dens and bounded outer ops."""
    b, c = friendly_add_fractions(2)
    inner_tex, inner_val = _bin(b, _pm(), c)
    if not is_simple_rational(inner_val):
        raise ZeroDivisionError
    a = partner_keeping_simple(inner_val, "*")
    mid = a * inner_val
    d = partner_keeping_simple(mid, "/")
    latex = (
        f"{latex_rational(a)} {latex_op('*')} {_paren(inner_tex)} "
        f"{latex_op('/')} {latex_rational(d)}"
    )
    return latex, apply_op(mid, "/", d)


def pat_paren_div_mul():
    """Pattern: (a ± b) ÷ c × d with related dens and bounded outer ops."""
    a, b = friendly_add_fractions(2)
    inner_tex, inner_val = _bin(a, _pm(), b)
    if not is_simple_rational(inner_val):
        raise ZeroDivisionError
    c = partner_keeping_simple(inner_val, "/")
    mid = apply_op(inner_val, "/", c)
    d = partner_keeping_simple(mid, "*")
    latex = (
        f"{_paren(inner_tex)} {latex_op('/')} {latex_rational(c)} "
        f"{latex_op('*')} {latex_rational(d)}"
    )
    return latex, mid * d


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
    Retries when generation hits division by zero or an oversized answer.
    """
    for _ in range(PATTERN_ATTEMPTS):
        pattern = random.choice(EXPRESSION_PATTERNS)
        try:
            latex, value = pattern()
        except ZeroDivisionError:
            continue
        # Final safety net: keep reduced answers within student-friendly bounds
        if is_simple_rational(value):
            return latex, value

    # Fallback: simple friendly product known to stay small
    a, b = friendly_mul_pair()
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
