#!/usr/bin/env python3
"""Exact certificate for the section computation on I_4 + 3 I_3 + 23 I_1.

Run with Python 3 (standard library only):

    python3 check_I4_3I3_semampleness.py
    python3 check_I4_3I3_semampleness.py --show-minors

The spelling of this filename agrees with the ancillary-file citation in the
manuscript.  The calculation uses exact fractions to construct eight matrices
of size 75 by 54 and check their canonical kernel vectors.  Reduction modulo
1000003 certifies a nonzero 53 by 53 minor of each matrix.  These two checks
together prove that each rational matrix has rank exactly 53.

Local construction:
  B(t) = P(t) R(t), z = x - 1, Y = y / sqrt(3),
  w = z sqrt(1 + z/3), u = Y + w, v = Y - w.
Then uv = B(t)/3, w = (u-v)/2, and Y = (u+v)/2.  The change from
y to Y is a constant change of basis over C and makes all coefficients of
the matrices rational.  Lagrange inversion gives

  z(w) = sum_{k>=1} binom(-k/2,k-1) w^k / (k * 3^(k-1)).

At t=a, write s=t-a and B(a+s)/3=s^n H(s).  On the j-th exceptional
component substitute u=s^j U, v=s^(n-j) H(s) U^(-1), where U is a formal
unit whose residue is transcendental.  Vanishing of every coefficient of
s^r U^ell for r below the required threshold is equivalent to the
corresponding divisorial valuation inequality.  Because every threshold
is at most six and w has positive valuation, powers w^k with k>=6 can
be discarded without changing any condition.

This program certifies the explicit linear-algebra and polynomial checks.
The geometric interpretation of the valuation conditions, the deformation
argument, and the deduction of non-semiampleness are proved in the paper.
No Mordell-Weil or Picard-number computation for the explicit surface is
claimed here.
"""

from argparse import ArgumentParser
from fractions import Fraction
from itertools import product
from math import comb


PRIME = 1000003
NUMERATOR_DEGREES = (18, 12, 9, 6, 3, 0)
COLUMNS = tuple(
    (basis_index, degree)
    for basis_index, bound in enumerate(NUMERATOR_DEGREES)
    for degree in range(bound + 1)
)


def polynomial_multiply(a, b):
    """Ordinary polynomials, with coefficients in increasing degree order."""
    result = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] += x * y
    return result


def polynomial_from_roots(roots_and_orders):
    result = [1]
    for root, order in roots_and_orders:
        for _ in range(order):
            result = polynomial_multiply(result, [-root, 1])
    return result


P = polynomial_from_roots(((0, 4), (1, 3), (2, 3), (3, 3)))
R = [1, 1, 0, 0, 0, 1]
B = polynomial_multiply(P, R)
Q = polynomial_from_roots(((0, 6), (1, 4), (2, 4), (3, 4)))
FOUR_PLUS_B = B.copy()
FOUR_PLUS_B[0] += 4


def translated_polynomial(coefficients, a):
    """Return the exact coefficients of f(a+s)."""
    return [
        sum(coefficients[k] * comb(k, j) * a ** (k - j)
            for k in range(j, len(coefficients)))
        for j in range(len(coefficients))
    ]


def generalized_binomial(value, order):
    result = Fraction(1)
    for i in range(order):
        result *= (value - i) / (i + 1)
    return result


def series_add(a, b):
    """Laurent polynomials in U, polynomial in s: keys are (s power,U power)."""
    result = a.copy()
    for monomial, coefficient in b.items():
        result[monomial] = result.get(monomial, 0) + coefficient
    return {monomial: value for monomial, value in result.items() if value}


def series_scale(a, scalar):
    return {key: value * scalar for key, value in a.items() if value * scalar}


def series_multiply(a, b, cutoff):
    result = {}
    for (i, j), x in a.items():
        for (k, ell), y in b.items():
            if i + k < cutoff:
                key = (i + k, j + ell)
                result[key] = result.get(key, 0) + x * y
    return {key: value for key, value in result.items() if value}


def series_power(a, exponent, cutoff):
    result = {(0, 0): Fraction(1)}
    for _ in range(exponent):
        result = series_multiply(result, a, cutoff)
    return result


def local_conditions(a, n, j, threshold):
    """Rows imposing numerator valuation >= threshold on E_j over t=a."""
    shifted_b = translated_polynomial(B, a)
    assert all(value == 0 for value in shifted_b[:n])
    assert shifted_b[n] != 0
    h = [Fraction(value, 3) for value in shifted_b[n:]]

    u = {(j, 1): Fraction(1)} if j < threshold else {}
    v = {
        (n - j + r, -1): coefficient
        for r, coefficient in enumerate(h)
        if n - j + r < threshold and coefficient
    }
    w = series_scale(series_add(u, series_scale(v, -1)), Fraction(1, 2))
    z = {}
    for k in range(1, threshold):
        coefficient = (
            generalized_binomial(Fraction(-k, 2), k - 1)
            / (k * 3 ** (k - 1))
        )
        z = series_add(z, series_scale(series_power(w, k, threshold), coefficient))

    one = {(0, 0): Fraction(1)}
    x = series_add(one, z)
    capital_y = series_scale(series_add(u, v), Fraction(1, 2))
    basis = (
        one,
        x,
        capital_y,
        series_power(x, 2, threshold),
        series_multiply(x, capital_y, threshold),
        series_power(x, 3, threshold),
    )

    expanded_columns = []
    for basis_index, degree in COLUMNS:
        coefficient_polynomial = {
            (r, 0): Fraction(comb(degree, r) * a ** (degree - r))
            for r in range(min(degree, threshold - 1) + 1)
            if comb(degree, r) * a ** (degree - r)
        }
        expanded_columns.append(
            series_multiply(coefficient_polynomial, basis[basis_index], threshold)
        )

    monomials = sorted(set().union(*(set(column) for column in expanded_columns)))
    rows = [
        [Fraction(column.get(monomial, 0)) for column in expanded_columns]
        for monomial in monomials
    ]
    labels = [(a, n, j, threshold, *monomial) for monomial in monomials]
    return rows, labels


def build_matrix(epsilon):
    matrix, labels, block_sizes = [], [], []
    specifications = [(0, 4, j, threshold)
                      for j, threshold in ((1, 3), (2, 6), (3, 3))]
    specifications.extend(
        (a, 3, j, 4 if j == selected else 2)
        for a, selected in enumerate(epsilon, start=1)
        for j in (1, 2)
    )
    for specification in specifications:
        rows, row_labels = local_conditions(*specification)
        matrix.extend(rows)
        labels.extend(row_labels)
        block_sizes.append(len(rows))
    return matrix, labels, block_sizes


def reduce_fraction(value, prime):
    value = Fraction(value)
    if value.denominator % prime == 0:
        raise ValueError("A matrix denominator is divisible by the chosen prime.")
    return value.numerator * pow(value.denominator, -1, prime) % prime


def modular_rank_with_minor(matrix, prime):
    """Return rank and original row/column indices of a nonzero rank-size minor."""
    reduced = [[reduce_fraction(value, prime) for value in row] for row in matrix]
    row_indices = list(range(len(reduced)))
    selected_rows, selected_columns = [], []
    next_row = 0
    for column in range(len(reduced[0])):
        pivot = next((r for r in range(next_row, len(reduced))
                      if reduced[r][column]), None)
        if pivot is None:
            continue
        reduced[next_row], reduced[pivot] = reduced[pivot], reduced[next_row]
        row_indices[next_row], row_indices[pivot] = row_indices[pivot], row_indices[next_row]
        selected_rows.append(row_indices[next_row])
        selected_columns.append(column)
        inverse = pow(reduced[next_row][column], -1, prime)
        reduced[next_row] = [value * inverse % prime for value in reduced[next_row]]
        for r in range(next_row + 1, len(reduced)):
            multiplier = reduced[r][column]
            if multiplier:
                reduced[r] = [(value - multiplier * pivot_value) % prime
                              for value, pivot_value in zip(reduced[r], reduced[next_row])]
        next_row += 1
    return next_row, selected_rows, selected_columns


def modular_determinant(matrix, prime):
    a = [[reduce_fraction(value, prime) for value in row] for row in matrix]
    determinant = 1
    for column in range(len(a)):
        pivot = next((r for r in range(column, len(a)) if a[r][column]), None)
        if pivot is None:
            return 0
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
            determinant = -determinant
        value = a[column][column]
        determinant = determinant * value % prime
        inverse = pow(value, -1, prime)
        for r in range(column + 1, len(a)):
            multiplier = a[r][column] * inverse % prime
            if multiplier:
                a[r] = [(entry - multiplier * pivot_entry) % prime
                        for entry, pivot_entry in zip(a[r], a[column])]
    return determinant % prime


def trim_polynomial(coefficients):
    while len(coefficients) > 1 and coefficients[-1] == 0:
        coefficients.pop()
    return coefficients


def modular_polynomial_remainder(a, b, prime):
    a = a.copy()
    while len(a) >= len(b) and a != [0]:
        offset = len(a) - len(b)
        multiplier = a[-1] * pow(b[-1], -1, prime) % prime
        for j, coefficient in enumerate(b):
            a[offset + j] = (a[offset + j] - multiplier * coefficient) % prime
        trim_polynomial(a)
    return a


def modular_polynomial_gcd_degree(a, b, prime):
    # Preserve the degrees: this is needed for the characteristic-zero certificate.
    assert a[-1] % prime != 0 and b[-1] % prime != 0
    a, b = [value % prime for value in a], [value % prime for value in b]
    while b != [0]:
        a, b = b, modular_polynomial_remainder(a, b, prime)
    return len(a) - 1


def check_discriminant():
    derivative = lambda a: [i * a[i] for i in range(1, len(a))]
    checks = (
        ("R squarefree", R, derivative(R)),
        ("4+PR squarefree", FOUR_PLUS_B, derivative(FOUR_PLUS_B)),
        ("P and R coprime", P, R),
        ("P and 4+PR coprime", P, FOUR_PLUS_B),
        ("R and 4+PR coprime", R, FOUR_PLUS_B),
    )
    for description, a, b in checks:
        assert modular_polynomial_gcd_degree(a, b, PRIME) == 0, description
    print("Discriminant: all five squarefreeness/coprimality certificates PASS.")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--show-minors", action="store_true",
                        help="print 1-based row and column indices for each certified minor")
    args = parser.parse_args()

    assert len(COLUMNS) == 54 and len(Q) == 19
    canonical_vector = [Fraction(Q[degree]) if basis_index == 0 else Fraction(0)
                        for basis_index, degree in COLUMNS]
    assert any(canonical_vector)

    check_discriminant()
    print("Matrices use exact fractions; modular prime =", PRIME)
    for epsilon in product((1, 2), repeat=3):
        matrix, labels, block_sizes = build_matrix(epsilon)
        assert len(matrix) == len(labels) == 75
        assert all(len(row) == 54 for row in matrix)
        assert block_sizes[:3] == [6, 18, 6]
        assert all(sum(block_sizes[k:k + 2]) == 15 for k in (3, 5, 7))
        assert all(sum(value * coefficient for value, coefficient
                       in zip(row, canonical_vector)) == 0 for row in matrix)

        rank, minor_rows, minor_columns = modular_rank_with_minor(matrix, PRIME)
        assert rank == 53
        minor = [[matrix[r][c] for c in minor_columns] for r in minor_rows]
        determinant = modular_determinant(minor, PRIME)
        assert determinant != 0
        print(f"epsilon={epsilon}: 75x54, exact canonical kernel PASS, "
              f"rank mod p = {rank}, minor determinant mod p = {determinant}")
        if args.show_minors:
            print("  minor rows (1-based):", [r + 1 for r in minor_rows])
            print("  minor columns (1-based):", [c + 1 for c in minor_columns])
    print("All eight rational matrices have rank exactly 53 and kernel dimension one.")


if __name__ == "__main__":
    main()
