"""Generate a printable PDF worksheet of smart-calculation reorder exercises."""

import random

from pdf_pipeline import (
    build_answers_section,
    format_enumerate_items,
    render_worksheet,
    write_and_compile,
)

# Total number of exercises to generate
EXERCISE_COUNT = 20
# Inclusive range for each operand (two-digit, matching the teaching examples)
NUMBER_VALUE_MIN = 11
NUMBER_VALUE_MAX = 89
# Inclusive chain length (count of numbers in the expression)
LENGTH_MIN = 3
LENGTH_MAX = 4
# Pair sums whose ones digits make 10 (two two-digit addends cannot make 20)
PAIR_TARGETS = (30, 40, 50, 60, 70, 80, 90, 100)
# Round intermediates used as the first smart subtraction
ROUND_INTERMEDIATES = (20, 30, 40, 50, 60, 70)
# Ones-digit pairs that sum to 10 (carry into the tens place)
ONES_COMPLEMENTS = (
    (1, 9),
    (2, 8),
    (3, 7),
    (4, 6),
    (5, 5),
    (6, 4),
    (7, 3),
    (8, 2),
    (9, 1),
)
# How many times to retry building one valid exercise
GENERATION_ATTEMPTS = 400
# Shuffle retries so intended friendly pairs are not adjacent
SHUFFLE_ATTEMPTS = 80
# Vertical spacing between enumerate items in the LaTeX PDF
ITEMSEP = "0.6cm"
# Number of columns in the exercise layout
COLUMN_COUNT = 2
# When True, append a new page with the answer key
GENERATE_ANSWERS = False
# Worksheet title and instructions injected into the LaTeX template
TITLE = "Smart Calculation"
INSTRUCTIONS = (
    r"""Look for a smarter order: pair numbers whose ones digits make 10 """
)
# Output file name prefix (timestamp yyyyMMddHHmmss is appended)
OUTPUT_PREFIX = "smart_calc"
# Operators used for one-operator chains
OP_ADD = "+"
OP_SUB = "-"
# LaTeX placeholder drawn where the missing result belongs
BLANK_LATEX = r"[~~~~~]"


def in_value_range(n):
    """True when n is a two-digit operand in range and not a multiple of 10."""
    return (
        isinstance(n, int)
        and NUMBER_VALUE_MIN <= n <= NUMBER_VALUE_MAX
        and n % 10 != 0
    )


def ones_make_ten(a, b):
    """True when the ones digits of a and b sum to 10 (a tens-friendly pair)."""
    return (a % 10) + (b % 10) == 10


def try_make_pair(target):
    """
    Build two distinct in-range addends whose ones digits sum to 10
    and whose total equals target. Returns (a, b) or None.
    """
    # Ones sum to 10, so the tens digits plus the carry must make target / 10
    tens_sum = target // 10 - 1
    o1, o2 = random.choice(ONES_COMPLEMENTS)
    candidates = []
    for t1 in range(1, 9):
        t2 = tens_sum - t1
        if not 1 <= t2 <= 8:
            continue
        a = 10 * t1 + o1
        b = 10 * t2 + o2
        if in_value_range(a) and in_value_range(b) and a != b:
            candidates.append((a, b))
    if not candidates:
        return None
    a, b = random.choice(candidates)
    if random.random() < 0.5:
        return b, a
    return a, b


def random_leftover(used):
    """Draw one leftover addend not in used and not a multiple of 10."""
    for _ in range(GENERATION_ATTEMPTS):
        n = random.randint(NUMBER_VALUE_MIN, NUMBER_VALUE_MAX)
        if in_value_range(n) and n not in used:
            return n
    return None


def adjacent_ones_complements(numbers):
    """True when any neighboring pair has ones digits that sum to 10."""
    return any(ones_make_ten(numbers[i], numbers[i + 1]) for i in range(len(numbers) - 1))


def intended_pair_adjacent(numbers, pairs):
    """True when any intended complementary pair sits next to each other."""
    intended = {frozenset(pair) for pair in pairs}
    for i in range(len(numbers) - 1):
        if frozenset((numbers[i], numbers[i + 1])) in intended:
            return True
    return False


def shuffle_addends(parts, leftovers):
    """
    Interleave pair members and leftovers so no ones-complement pair is adjacent.
    `parts` is a list of (a, b) tuples. Returns a list of numbers or None.
    """
    values = [n for pair in parts for n in pair] + list(leftovers)
    for _ in range(SHUFFLE_ATTEMPTS):
        random.shuffle(values)
        if intended_pair_adjacent(values, parts):
            continue
        if adjacent_ones_complements(values):
            continue
        return list(values)
    return None


def addition_strategy_latex(pairs, leftovers, answer):
    """LaTeX body (no $) showing grouped pairs, then tens, then the result."""
    group_tex = " + ".join(rf"({a} + {b})" for a, b in pairs)
    pair_sums = [a + b for a, b in pairs]
    leftover_tex = "".join(f" + {n}" for n in leftovers)
    tens_tex = " + ".join(str(s) for s in pair_sums)
    leftover_tens = "".join(f" + {n}" for n in leftovers)
    return (
        rf"{group_tex}{leftover_tex} = {tens_tex}{leftover_tens} =$ \textbf{{{answer}}}"
    )


def try_build_addition(length):
    """
    Build an all-plus chain of `length` numbers with 1–2 tens-friendly pairs.
    Returns an exercise dict or None.
    """
    pair_count = 1 if length == 3 else 2
    leftover_count = length - 2 * pair_count
    used = set()
    pairs = []
    for _ in range(pair_count):
        pair = None
        for _attempt in range(GENERATION_ATTEMPTS):
            target = random.choice(PAIR_TARGETS)
            built = try_make_pair(target)
            if built is None:
                continue
            a, b = built
            if a in used or b in used:
                continue
            pair = (a, b)
            break
        if pair is None:
            return None
        pairs.append(pair)
        used.update(pair)

    leftovers = []
    for _ in range(leftover_count):
        n = random_leftover(used)
        if n is None:
            return None
        leftovers.append(n)
        used.add(n)

    numbers = shuffle_addends(pairs, leftovers)
    if numbers is None:
        return None

    answer = sum(numbers)
    strategy = addition_strategy_latex(pairs, leftovers, answer)
    return {
        "op": OP_ADD,
        "numbers": numbers,
        "answer": answer,
        "strategy_latex": strategy,
        "pairs": pairs,
        "leftovers": leftovers,
    }


def subtraction_strategy_latex(start, smart_first, pair, leftover, answer):
    """
    LaTeX body (no $): round first subtract, then combine a tens-pair,
    then subtract any leftover from the new ten.
    """
    tail = [smart_first]
    if pair:
        tail.extend(pair)
    if leftover is not None:
        tail.append(leftover)
    chain = [start] + tail
    parts = [" - ".join(str(n) for n in chain)]

    round_mid = start - smart_first
    rest_after_first = tail[1:]
    if rest_after_first:
        parts.append(" - ".join([str(round_mid)] + [str(n) for n in rest_after_first]))

    # Remaining subtractands that make a ten are combined in one step
    if pair:
        pair_sum = pair[0] + pair[1]
        after_pair = round_mid - pair_sum
        if leftover is not None:
            parts.append(f"{round_mid} - {pair_sum} - {leftover}")
            parts.append(f"{after_pair} - {leftover}")
        else:
            parts.append(f"{round_mid} - {pair_sum}")

    joined = " = ".join(parts)
    return rf"{joined} =$ \textbf{{{answer}}}"


def shuffle_subtractands(smart_first, pair, leftover):
    """
    Order subtracted terms so s* is not first and the tens-pair is not adjacent.
    Returns the shuffled tail or None.
    """
    values = [smart_first]
    if pair:
        values.extend(pair)
    if leftover is not None:
        values.append(leftover)
    pair_list = [pair] if pair else []

    for _ in range(SHUFFLE_ATTEMPTS):
        random.shuffle(values)
        if values[0] == smart_first:
            continue
        if pair_list and intended_pair_adjacent(values, pair_list):
            continue
        if pair_list and adjacent_ones_complements(values):
            continue
        return list(values)
    return None


def try_build_subtraction(length):
    """
    Build an all-minus chain that stays tens-friendly at every step:
    first subtract to a ten, then remaining terms form a ones-complement
    pair (length 4) or one leftover subtracted from that ten (length 3).
    Returns an exercise dict or None.
    """
    # Length 3: s* + leftover. Length 4: s* + pair.
    need_pair = length >= 4
    need_leftover = length != 4

    # Pair sums start at 30; a leftover still needs room under the first ten
    min_mid = 20
    if need_pair:
        min_mid = 40
    if need_pair and need_leftover:
        min_mid = 50
    round_choices = [m for m in ROUND_INTERMEDIATES if m >= min_mid]
    if not round_choices:
        return None
    round_mid = random.choice(round_choices)

    # start = round_mid + s*, both two-digit and not multiples of 10
    s_hi = NUMBER_VALUE_MAX - round_mid
    if s_hi < NUMBER_VALUE_MIN:
        return None
    smart_first = None
    start = None
    for _ in range(GENERATION_ATTEMPTS):
        candidate = random.randint(NUMBER_VALUE_MIN, s_hi)
        if not in_value_range(candidate):
            continue
        built_start = round_mid + candidate
        if not in_value_range(built_start):
            continue
        smart_first = candidate
        start = built_start
        break
    if smart_first is None:
        return None

    used = {start, smart_first}
    pair = None
    leftover = None

    if need_pair:
        max_pair = round_mid - 1
        if need_leftover:
            # Leave room for a two-digit leftover and a positive result
            max_pair = round_mid - NUMBER_VALUE_MIN - 1
        pair_targets = [t for t in PAIR_TARGETS if t <= max_pair]
        if not pair_targets:
            return None
        pair = None
        for _ in range(GENERATION_ATTEMPTS):
            built = try_make_pair(random.choice(pair_targets))
            if built is None:
                continue
            a, b = built
            if a in used or b in used:
                continue
            # Only s* should turn start into a ten
            if (start - a) % 10 == 0 or (start - b) % 10 == 0:
                continue
            pair = (a, b)
            break
        if pair is None:
            return None
        used.update(pair)

    if need_leftover:
        remaining = round_mid - (sum(pair) if pair else 0)
        hi = min(NUMBER_VALUE_MAX, remaining - 1)
        if hi < NUMBER_VALUE_MIN:
            return None
        leftover = None
        for _ in range(GENERATION_ATTEMPTS):
            n = random.randint(NUMBER_VALUE_MIN, hi)
            if not in_value_range(n) or n in used:
                continue
            if (start - n) % 10 == 0:
                continue
            leftover = n
            break
        if leftover is None:
            return None

    presented_tail = shuffle_subtractands(smart_first, pair, leftover)
    if presented_tail is None:
        return None

    numbers = [start] + presented_tail
    answer = start - sum(presented_tail)
    if answer < 1:
        return None
    strategy = subtraction_strategy_latex(
        start, smart_first, pair, leftover, answer
    )
    return {
        "op": OP_SUB,
        "numbers": numbers,
        "answer": answer,
        "strategy_latex": strategy,
        "smart_first": smart_first,
        "pair": pair,
        "leftover": leftover,
    }


def fallback_exercise():
    """Deterministic examples matching the teaching cases."""
    if random.random() < 0.5:
        numbers = [37, 28, 13, 32]
        pairs = [(37, 13), (28, 32)]
        leftovers = []
        answer = 110
        return {
            "op": OP_ADD,
            "numbers": numbers,
            "answer": answer,
            "strategy_latex": addition_strategy_latex(pairs, leftovers, answer),
            "pairs": pairs,
            "leftovers": leftovers,
        }
    numbers = [53, 18, 33]
    answer = 2
    return {
        "op": OP_SUB,
        "numbers": numbers,
        "answer": answer,
        "strategy_latex": subtraction_strategy_latex(53, 33, None, 18, answer),
        "smart_first": 33,
        "pair": None,
        "leftover": 18,
    }


def generate_one_exercise():
    """Build one all-plus or all-minus smart-calculation exercise."""
    # Pick the operator first so worksheets stay close to half-and-half
    op = random.choice((OP_ADD, OP_SUB))
    builder = try_build_addition if op == OP_ADD else try_build_subtraction
    for _ in range(GENERATION_ATTEMPTS):
        length = random.randint(LENGTH_MIN, LENGTH_MAX)
        built = builder(length)
        if built is not None:
            return built
    other = try_build_subtraction if op == OP_ADD else try_build_addition
    for _ in range(GENERATION_ATTEMPTS):
        length = random.randint(LENGTH_MIN, LENGTH_MAX)
        built = other(length)
        if built is not None:
            return built
    return fallback_exercise()


def expression_key(exercise):
    """Stable string used to reject duplicate worksheet items."""
    op = f" {exercise['op']} "
    return op.join(str(n) for n in exercise["numbers"])


def generate_exercises(count=EXERCISE_COUNT):
    """Return `count` unique smart-calculation exercises."""
    exercises = []
    seen = set()
    while len(exercises) < count:
        exercise = generate_one_exercise()
        key = expression_key(exercise)
        if key in seen:
            continue
        seen.add(key)
        exercises.append(exercise)
    return exercises


def format_question(exercise):
    """Format one chain as a LaTeX enumerate item body with a result blank."""
    op = f" {exercise['op']} "
    body = op.join(str(n) for n in exercise["numbers"])
    return f"${body} = {BLANK_LATEX}$"


def format_answer(exercise):
    """Format the regrouped strategy and bold numeric result."""
    return f"${exercise['strategy_latex']}"


def preview_line(exercise):
    """Human-readable one-line preview for the terminal."""
    return f"{expression_key(exercise)}  -> {exercise['answer']}"


def main():
    """Generate exercises, render the worksheet, and compile the PDF."""
    exercises = generate_exercises()

    for i, ex in enumerate(exercises, 1):
        print(f"{i}. {preview_line(ex)}")

    items = format_enumerate_items(format_question(ex) for ex in exercises)

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
