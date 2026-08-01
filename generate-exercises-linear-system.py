"""Generate a printable PDF worksheet of 2x2 linear systems in x and y."""

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
EXERCISE_COUNT = 12
# Inclusive magnitude range for standalone integer values
INTEGER_MIN = 1
INTEGER_MAX = 10
# Inclusive ranges for fraction numerators and denominators
NUMERATOR_MIN = 1
NUMERATOR_MAX = 12
DENOMINATOR_MIN = 2
DENOMINATOR_MAX = 10
# Chance that a random rational is an integer rather than a fraction
INTEGER_PROBABILITY = 0.45
# Reject values whose reduced form is too large for students
VALUE_NUM_MAX = 24
VALUE_DEN_MAX = 16
# Retries when sampling a full system that meets all constraints
SYSTEM_ATTEMPTS = 80
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "1.4cm"
# Single column so each cases block has horizontal room
COLUMN_COUNT = 1
# When True, append a new page with the answer key
GENERATE_ANSWERS = True
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Systems of Linear Equations"
INSTRUCTIONS = (
    "Solve each system of linear equations for $(x, y)$. "
    "simplify all answers."
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "linear_systems"


def random_sign():
    """Return +1 or -1 at random."""
    return random.choice([1, -1])


def random_integer():
    """Return a non-zero random integer within the configured magnitude range."""
    return random_sign() * random.randint(INTEGER_MIN, INTEGER_MAX)


def is_simple_rational(value):
    """True when a reduced Fraction stays within student-friendly bounds."""
    return (
        abs(value.numerator) <= VALUE_NUM_MAX
        and value.denominator <= VALUE_DEN_MAX
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


def random_fraction():
    """Return a non-zero already-reduced Fraction with a random denominator."""
    den = random.randint(DENOMINATOR_MIN, DENOMINATOR_MAX)
    num = random_coprime_numerator(den)
    return Fraction(random_sign() * num, den)


def random_rational():
    """Return either a random integer or fraction (as Fraction)."""
    if random.random() < INTEGER_PROBABILITY:
        return Fraction(random_integer(), 1)
    return random_fraction()


def random_nonzero_rational():
    """Return a non-zero rational (random_rational already excludes zero)."""
    return random_rational()


def independent_rows(a1, b1, a2, b2):
    """True when the two coefficient rows are not proportional (unique solution)."""
    return a1 * b2 - a2 * b1 != 0


def latex_answer(value):
    """Format a Fraction for the answer key (no extra parentheses)."""
    if value.denominator == 1:
        return str(value.numerator)
    abs_num = abs(value.numerator)
    body = rf"\frac{{{abs_num}}}{{{value.denominator}}}"
    if value.numerator < 0:
        return rf"-{body}"
    return body


def latex_var_term(coeff, var):
    """
    Format coeff*var as a leading or standalone term (no leading +).
    Examples: x, -x, 2x, -\\frac{2}{3}y, \\frac{1}{2}x
    """
    # Unit coefficients omit the numeral for readability
    if coeff == 1:
        return var
    if coeff == -1:
        return f"-{var}"
    return f"{latex_answer(coeff)}{var}"


def latex_signed_var_term(coeff, var):
    """
    Format coeff*var with an explicit leading + or - for middle terms.
    Examples: + 2x, - y, + \\frac{1}{2}y
    """
    if coeff == 1:
        return f"+ {var}"
    if coeff == -1:
        return f"- {var}"
    if coeff > 0:
        return f"+ {latex_answer(coeff)}{var}"
    # Negative coefficient: emit minus and the absolute coefficient
    return f"- {latex_answer(-coeff)}{var}"


def latex_linear_left(a, b):
    """Format the left-hand side ax + by (omitting zero terms)."""
    # Both coefficients non-zero: full binomial
    if a != 0 and b != 0:
        return f"{latex_var_term(a, 'x')} {latex_signed_var_term(b, 'y')}"
    if a != 0:
        return latex_var_term(a, "x")
    if b != 0:
        return latex_var_term(b, "y")
    # Degenerate zero row should not reach formatting
    return "0"


def form_standard(a, b, c):
    """Standard form: ax + by = c."""
    if a == 0 and b == 0:
        return None
    return f"{latex_linear_left(a, b)} = {latex_answer(c)}"


def form_isolate_ax(a, b, c):
    """Isolate ax: ax = c - by (requires a != 0 and b != 0)."""
    if a == 0 or b == 0:
        return None
    # Right-hand side is c + (-b)y written as c - by or c + |b|y
    rhs = f"{latex_answer(c)} {latex_signed_var_term(-b, 'y')}"
    return f"{latex_var_term(a, 'x')} = {rhs}"


def form_isolate_by(a, b, c):
    """Isolate by: by = c - ax (requires a != 0 and b != 0)."""
    if a == 0 or b == 0:
        return None
    rhs = f"{latex_answer(c)} {latex_signed_var_term(-a, 'x')}"
    return f"{latex_var_term(b, 'y')} = {rhs}"


def form_solve_for_y(a, b, c):
    """Explicit solve for y: y = mx + k (requires b != 0)."""
    if b == 0:
        return None
    # y = (-a/b)x + (c/b)
    m = -a / b
    k = c / b
    if not (is_simple_rational(m) and is_simple_rational(k)):
        return None
    # Build mx + k with zero-term omission
    if m == 0:
        return f"y = {latex_answer(k)}"
    left = latex_var_term(m, "x")
    if k == 0:
        return f"y = {left}"
    if k > 0:
        return f"y = {left} + {latex_answer(k)}"
    return f"y = {left} - {latex_answer(-k)}"


def form_solve_for_x(a, b, c):
    """Explicit solve for x: x = my + k (requires a != 0)."""
    if a == 0:
        return None
    # x = (-b/a)y + (c/a)
    m = -b / a
    k = c / a
    if not (is_simple_rational(m) and is_simple_rational(k)):
        return None
    if m == 0:
        return f"x = {latex_answer(k)}"
    left = latex_var_term(m, "y")
    if k == 0:
        return f"x = {left}"
    if k > 0:
        return f"x = {left} + {latex_answer(k)}"
    return f"x = {left} - {latex_answer(-k)}"


def form_equals_zero(a, b, c):
    """Moved-constant form: ax + by - c = 0."""
    if a == 0 and b == 0:
        return None
    left = latex_linear_left(a, b)
    # Append - c or + |c| depending on the sign of c
    if c == 0:
        return f"{left} = 0"
    if c > 0:
        return f"{left} - {latex_answer(c)} = 0"
    return f"{left} + {latex_answer(-c)} = 0"


# Registry of equation presentation builders (canonical a,b,c -> latex or None)
EQUATION_FORMS = (
    form_standard,
    form_isolate_ax,
    form_isolate_by,
    form_solve_for_y,
    form_solve_for_x,
    form_equals_zero,
)


def format_equation(a, b, c):
    """Pick a random valid presentation form for one linear equation."""
    forms = list(EQUATION_FORMS)
    random.shuffle(forms)
    for form_fn in forms:
        latex = form_fn(a, b, c)
        if latex is not None:
            return latex
    # Fallback should always succeed for a non-zero row
    return form_standard(a, b, c)


def generate_one_system():
    """
    Solution-first: pick (x, y), independent rows, then c_i = a_i x + b_i y.
    Returns ((a1,b1,c1), (a2,b2,c2), x, y) or None if sampling fails.
    """
    for _ in range(SYSTEM_ATTEMPTS):
        # Target solution coordinates (may be integer or fractional)
        x = random_rational()
        y = random_rational()
        if not (is_simple_rational(x) and is_simple_rational(y)):
            continue

        # Coefficient rows; allow a zero in at most one place per row
        a1 = random_nonzero_rational()
        b1 = random_rational() if random.random() < 0.85 else Fraction(0)
        # Prefer a fully non-zero second row so forms stay interesting
        a2 = random_rational() if random.random() < 0.85 else Fraction(0)
        b2 = random_nonzero_rational()
        # Avoid accidental zero rows
        if a1 == 0 and b1 == 0:
            continue
        if a2 == 0 and b2 == 0:
            continue
        if not independent_rows(a1, b1, a2, b2):
            continue

        # Right-hand sides implied by the chosen solution
        c1 = a1 * x + b1 * y
        c2 = a2 * x + b2 * y
        values = (a1, b1, c1, a2, b2, c2)
        if not all(is_simple_rational(v) for v in values):
            continue
        return (a1, b1, c1), (a2, b2, c2), x, y
    return None


def generate_exercises():
    """Return EXERCISE_COUNT unique (eq1, eq2, x, y) systems."""
    exercises = []
    # Deduplicate by the solution pair plus coefficient fingerprint
    seen = set()
    while len(exercises) < EXERCISE_COUNT:
        system = generate_one_system()
        if system is None:
            continue
        eq1, eq2, x, y = system
        key = (eq1, eq2, x, y)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(system)
    return exercises


def format_question(system):
    """Format one system as a LaTeX enumerate item body with cases."""
    eq1, eq2, _, _ = system
    line1 = format_equation(*eq1)
    line2 = format_equation(*eq2)
    return (
        r"Solve the system: \\[0.3cm] "
        r"$\begin{cases} "
        f"{line1} \\\\ "
        f"{line2} "
        r"\end{cases}$"
    )


def format_answer(system):
    """Format the solution ordered pair as a LaTeX enumerate item body."""
    _, _, x, y = system
    return rf"$(x, y) = \left({latex_answer(x)}, {latex_answer(y)}\right)$"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    # Show the problems in the terminal for a quick preview
    for i, (eq1, eq2, x, y) in enumerate(exercises, 1):
        print(f"{i}. {eq1} / {eq2}  =>  ({x}, {y})")

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
