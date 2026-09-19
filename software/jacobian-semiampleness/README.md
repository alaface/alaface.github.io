# Semiampleness on Jacobian elliptic surfaces of Kodaira dimension one

Computational material for the paper by **Antonio Laface and Sichen Li**.

The [complete verification output](check_I4_3I3_semampleness-output.txt) includes the row and column indices of all eight certified minors.

The script [`check_I4_3I3_semampleness.py`](check_I4_3I3_semampleness.py) verifies the polynomial and linear-algebra calculations used in the example with singular fiber configuration `I4 + 3I3 + 23I1`. It constructs eight rational matrices of size `75 x 54`, indexed by `epsilon` in `{1, 2}^3`, and certifies that each has rank exactly `53` over the rational numbers, hence a one-dimensional kernel.

## Requirements and usage

- Python 3.8 or later.
- Python standard library only; no additional packages or computer algebra system are required.

Run the verification from the directory containing the script:

```sh
python3 check_I4_3I3_semampleness.py
```

To also print the row and column indices of the certified `53 x 53` minors:

```sh
python3 check_I4_3I3_semampleness.py --show-minors
```

The indices printed by `--show-minors` are one-based. Run Python normally, without the `-O` or `-OO` options, because the verification uses assertions.

## What is certified

The computation uses

```text
P(t) = t^4 (t-1)^3 (t-2)^3 (t-3)^3,
R(t) = t^5 + t + 1,
B(t) = P(t) R(t),
Q(t) = t^6 (t-1)^4 (t-2)^4 (t-3)^4.
```

For each of the eight choices of `epsilon`, the script translates the local valuation conditions in the paper into a matrix. Its 54 columns correspond to the basis `(1, x, Y, x^2, xY, x^3)`, with coefficient-polynomial degree bounds `(18, 12, 9, 6, 3, 0)`. Here `Y = y / sqrt(3)`, so all matrix entries are rational. The construction uses exact arithmetic through Python's `fractions.Fraction`.

The rank certificate has two parts:

1. The coefficient vector of `Q(t)` in the first basis summand is checked to be a nonzero kernel vector over the rational numbers. Thus the rank is at most `53`.
2. Reduction modulo the prime `1000003` identifies a `53 x 53` minor, whose determinant is independently computed and checked to be nonzero modulo that prime. All denominators are invertible modulo the prime, so this also proves that the rational determinant is nonzero and the rank is at least `53`.

Together these checks prove rank exactly `53` over the rational numbers. The conclusion is exact, with no floating-point or probabilistic computation.

The script also checks five polynomial conditions used in the discriminant calculation:

- `R` is squarefree.
- `4 + PR` is squarefree.
- `P` and `R` are coprime.
- `P` and `4 + PR` are coprime.
- `R` and `4 + PR` are coprime.

These checks exclude repeated roots in the two factors responsible for the simple singular fibers and exclude common roots between the indicated discriminant factors. Each condition is certified by a polynomial gcd modulo `1000003`, with preservation of the input degrees checked; this gives a certificate in characteristic zero.

## Expected output

The default command prints:

```text
Discriminant: all five squarefreeness/coprimality certificates PASS.
Matrices use exact fractions; modular prime = 1000003
epsilon=(1, 1, 1): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 619702
epsilon=(1, 1, 2): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 782495
epsilon=(1, 2, 1): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 905108
epsilon=(1, 2, 2): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 626049
epsilon=(2, 1, 1): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 905312
epsilon=(2, 1, 2): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 463356
epsilon=(2, 2, 1): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 629585
epsilon=(2, 2, 2): 75x54, exact canonical kernel PASS, rank mod p = 53, minor determinant mod p = 92576
All eight rational matrices have rank exactly 53 and kernel dimension one.
```

## Relation to the geometric argument

The script certifies the explicit polynomial and linear-algebra calculations. The geometric interpretation of the valuation conditions, the deformation argument, and the deduction of non-semiampleness are proved in the paper. The script does not compute the Mordell-Weil group or Picard number of the explicit surface.
