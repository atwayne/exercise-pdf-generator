# Friendly Fraction Generation Algorithm

This document explains how
[`generate-exercises-rational-operation.py`](../generate-exercises-rational-operation.py)
chooses numerators and denominators so mixed-operation worksheets stay
computationally friendly for students.

## Goal

Independent random fractions often produce awkward problems:

| Kind | Example | Why it is awkward |
|------|---------|-------------------|
| Unrelated add/sub dens | \(\frac{1}{7} + \frac{1}{11}\) | LCM is \(77\); large common denominator |
| Dens-only mul pair | \(\frac{1}{12} \times \frac{3}{16}\) | \(\gcd(12,16)=4\) does not help multiplication |
| Unreduced single fraction | \(\frac{9}{12}\) | Looks “related,” but is just \(\frac{3}{4}\) after simplifying |

Preferred examples:

- **Addition / subtraction:** \(\frac{1}{12} + \frac{3}{16}\) — dens share factor \(4\), so \(\mathrm{lcm}(12,16)=48\).
- **Multiplication:** \(\frac{8}{7} \times \frac{13}{12}\) — \(\gcd(8,12)=4\) cancels across the product.
- **Always reduced:** each printed fraction already has \(\gcd(|\text{num}|,\text{den})=1\).

The algorithm is **operation-aware**: ± pairs get related denominators; ×/÷ pairs get cross-cancellation.

## High-level flow

```text
pick expression pattern
        │
        ▼
pattern builds its own operands
        │
        ├── ± slots  → friendly_add_fractions / related_denominators
        ├── × slots  → friendly_mul_pair
        ├── ÷ slots  → friendly_div_pair  (mul pair, then invert partner)
        └── other    → random_rational (integer or unrelated fraction)
        │
        ▼
emit LaTeX + exact Fraction value
```

Patterns are **zero-argument builders**. Each pattern knows which of its
operands participate in ± versus ×/÷, and calls the matching helper.

## Design principle: already reduced

Older logic picked arbitrary `num`/`den` and then reduced with `gcd`. That
destroys intentional denominators: generating \(\frac{9}{12}\) next to a
partner with den \(16\) becomes \(\frac{3}{4}\) after reduction, and the
shared-factor relationship with \(16\) disappears.

New rule:

1. Choose the denominator first (possibly constrained by the helper).
2. Choose a numerator **already coprime** to that denominator.
3. Apply a random sign.

So the printed den is exactly the den that was planned.

### `random_coprime_numerator(den)`

Collects all \(n\) in `[NUMERATOR_MIN, NUMERATOR_MAX]` with \(\gcd(n,\text{den})=1\),
then picks one at random. Falls back to \(1\) if the candidate list is empty.

### `fraction_with_denominator(den)`

Returns \(\pm\,\frac{n}{\text{den}}\) using that coprime numerator.

## Addition / subtraction: related denominators

### Why shared dens help

For \(\frac{a}{b} \pm \frac{c}{d}\), students need a common denominator
\(\mathrm{lcm}(b,d)=\frac{bd}{\gcd(b,d)}\).

If \(\gcd(b,d)>1\), the LCM shrinks. Example:

- \(b=12\), \(d=16\), \(\gcd=4\) → \(\mathrm{lcm}=48\)
- unrelated dens like \(7\) and \(11\) → \(\mathrm{lcm}=77\)

### `related_denominators(count)`

1. For each candidate shared factor \(g \in \{2,3,4,5,6\}\), list multiples of
   \(g\) inside `[DENOMINATOR_MIN, DENOMINATOR_MAX]` (currently \(2..16\)).
2. Keep only factors that still leave enough multiples (at least
   \(\min(\text{count}, 2)\)).
3. Pick one viable \((g, \text{multiples})\) at random.
4. Sample `count` denominators from that multiple list.
5. If `count ≥ 2` and all dens came out identical, but other multiples exist,
   replace the second den so the problem is not trivially same-denominator.

Example with \(g=4\): multiples include \(4,8,12,16\). Sampling might yield
`[12, 16]`.

### `friendly_add_fractions(n)`

```text
dens = related_denominators(n)
return [fraction_with_denominator(d) for d in dens]
```

Used by patterns whose ± operands should be easy to combine, e.g.:

- `a ± b ± c` → three related dens
- `(a ± b) ÷ c` → related dens inside the parentheses

## Multiplication: cross-cancellation

### What helps vs what does not

For \(\frac{a}{b} \times \frac{c}{d}\), students cancel:

- \(\gcd(|a|, d) > 1\), and/or
- \(\gcd(|c|, b) > 1\)

Shared denominators alone (\(\gcd(b,d)>1\)) do **not** cancel across a product.
That is why \(\frac{1}{12} \times \frac{3}{16}\) is rejected even though
\(\gcd(12,16)=4\).

Helpers:

- `_has_cross_cancel(left, right)` — true if either cross-gcd is \(> 1\).
- `_only_shared_dens(left, right)` — dens share a factor **and** there is no
  cross-cancel (the “bad mul” case).

### `friendly_mul_pair()`

Retry up to `FRIENDLY_ATTEMPTS` (40) times:

1. Pick a cancel factor \(f \in \{2,3,4,5\}\).
2. Randomly choose one of two constructions:

**Construction A** — put \(f\) on the left numerator and right denominator:

\[
\text{left}=\frac{f\cdot a'}{b},\qquad
\text{right}=\frac{c}{f\cdot d'}
\]

Constraints:

- \(b\) in den range and \(\gcd(f,b)=1\) (left stays reduced after attaching \(f\)).
- \(a'\) chosen so \(f\cdot a' \le \text{NUMERATOR_MAX}\) and
  \(\gcd(f\cdot a', b)=1\).
- \(d'\) chosen so \(f\cdot d'\) stays in den range.
- \(c\) coprime to \(f\cdot d'\).

Then \(\gcd(f\cdot a',\, f\cdot d') \ge f > 1\), so left×right cross-cancels on \(f\).

**Construction B** — the symmetric case:

\[
\text{left}=\frac{a}{f\cdot b'},\qquad
\text{right}=\frac{f\cdot c'}{d}
\]

Same range / coprimality checks on the mirrored roles.

3. Quality gates before accept:

- both sides are non-integers (true fractions);
- each side is already reduced;
- `_has_cross_cancel` is true;
- `_only_shared_dens` is false.

4. If every attempt fails, fall back to a fixed easy pair such as
   \(\frac{2}{3} \times \frac{1}{4}\) (cross-cancels on \(2\)).

## Division: reuse multiplication

Division \(\frac{a}{b} \div \frac{c}{d} = \frac{a}{b} \times \frac{d}{c}\).

`friendly_div_pair()`:

1. Build `(left, recip) = friendly_mul_pair()` so `left * recip` cross-cancels.
2. Set `divisor = 1 / recip` (i.e. swap num/den of `recip`).
3. Return `(left, divisor)`.

Then `left ÷ divisor = left * recip`, so the worksheet’s ÷ still benefits from
the same cancellation structure.

## Wiring into expression patterns

| Pattern shape | Friendly bias |
|---------------|---------------|
| `a ± b ± c` | all three from `friendly_add_fractions(3)` |
| `(a ± b) ÷ c`, `(a ± b) × c`, `a ÷ (b ± c)`, … | ± pair from `friendly_add_fractions(2)` |
| `a × b ± c`, `a ± b × c`, `a × b ÷ c` | × pair from `friendly_mul_pair()` |
| `a ÷ b ± c`, `a × b ± c ÷ d` | ÷ (and ×) from `friendly_div_pair` / `friendly_mul_pair` |
| Remaining slots | `random_rational()` for variety (integer with probability `INTEGER_PROBABILITY`) |

`generate_expression()` picks a random pattern and calls it with no operands.
On `ZeroDivisionError` it retries (up to `PATTERN_ATTEMPTS`). Final fallback is
a simple friendly product from `friendly_mul_pair()`.

## Constants that steer difficulty

| Constant | Role |
|----------|------|
| `NUMERATOR_MIN` / `NUMERATOR_MAX` | numerator magnitude window |
| `DENOMINATOR_MIN` / `DENOMINATOR_MAX` | denominator window |
| `RELATED_DEN_FACTORS` | allowed shared factors for ± dens |
| `MUL_CANCEL_FACTORS` | allowed cross-cancel factors for ×/÷ |
| `INTEGER_PROBABILITY` | chance a free slot is an integer |
| `FRIENDLY_ATTEMPTS` | retries inside mul-pair construction |
| `PATTERN_ATTEMPTS` | retries when a whole pattern hits ÷0 |

Tightening ranges or factor lists makes problems smaller/easier; widening them
increases variety and hardness.

## Worked examples

### Related add pair

1. Choose \(g=4\).
2. Multiples in \(2..16\): \(4,8,12,16\).
3. Sample dens \(12\) and \(16\).
4. Numerators coprime to each den, e.g. \(1\) and \(3\).
5. Result: \(\frac{1}{12} + \frac{3}{16}\).

### Cross-cancel mul pair (construction A, \(f=4\))

1. Pick \(b=7\) with \(\gcd(4,7)=1\).
2. Pick \(a'=2\) → left numerator \(8\), \(\gcd(8,7)=1\) → \(\frac{8}{7}\).
3. Pick \(d'=3\) → right den \(12\).
4. Pick \(c=13\) coprime to \(12\) → \(\frac{13}{12}\).
5. Product \(\frac{8}{7} \times \frac{13}{12}\) cancels \(4\) between \(8\) and \(12\).

### Rejected dens-only mul

\(\frac{1}{12} \times \frac{3}{16}\):

- \(\gcd(1,16)=1\), \(\gcd(3,12)=3\) — wait, this one *does* cross-cancel on \(3\).

A true dens-only reject example:

\(\frac{1}{12} \times \frac{5}{16}\):

- \(\gcd(1,16)=1\), \(\gcd(5,12)=1\) → no cross-cancel
- \(\gcd(12,16)=4\) → dens share a factor only
- `_only_shared_dens` is true → rejected

## Result magnitude limits

Friendly pairwise dens/cross-cancel alone is not enough. A related ± pair can
still produce a large intermediate (e.g. \(\frac{14}{5}-\frac{4}{15}=\frac{38}{15}\)),
and a random trailing operand can explode the final answer
(\(931/495\), \(2473/3510\), …).

Additional guards:

| Guard | Role |
|-------|------|
| `RELATED_LCM_MAX` (48) | Reject ± den sets whose LCM is too large |
| `ADD_NUMERATOR_MAX` (8) | Smaller numerators on ± fractions |
| `is_simple_rational` | Reduced \(\|num\| \le 36\) and \(den \le 36\) |
| `partner_keeping_simple` | Pick trailing ±/×/÷ partners so the running value stays bounded |
| `generate_expression` filter | Final safety net: retry until the answer is simple |

Chained patterns such as `(a ± b) ÷ c × d` and `(a ± b) × c ± d` now choose `c`
and `d` from the intermediate value via `partner_keeping_simple`, instead of
independent `random_rational()` draws.

## Quality checklist

When reviewing generated worksheets:

1. Single fractions are reduced (no \(\frac{9}{12}\) on the page).
2. ± fraction pairs usually satisfy \(\gcd(\text{den}_1,\text{den}_2)>1\).
3. × fraction pairs usually satisfy a cross-gcd \(>1\).
4. × pairs that only share dens without cross-cancel should not appear.
5. ÷ pairs remain friendly because they are built from an inverted mul partner.
6. Final answers stay within `ANSWER_NUM_MAX` / `ANSWER_DEN_MAX` (default 36).

## Implementation map

| Concern | Functions |
|---------|-----------|
| Coprime / reduced fractions | `random_coprime_numerator`, `fraction_with_denominator`, `random_fraction` |
| Related dens for ± | `related_denominators`, `friendly_add_fractions` |
| Cross-cancel for × | `friendly_mul_pair`, `_has_cross_cancel`, `_only_shared_dens` |
| Friendly ÷ | `friendly_div_pair` |
| Bounded trailing ops | `partner_keeping_simple`, `is_simple_rational` |
| Pattern wiring | `pat_*` zero-arg builders, `EXPRESSION_PATTERNS`, `generate_expression` |
