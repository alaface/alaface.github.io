# Catalogue audit

This audit covers all **26** entries of the explicit plane catalogue.

## What was compared with the LaTeX sources

For every entry, the web record was checked against the corresponding source entry for:

1. coefficient field / parameter curve and the displayed cubic;
2. the complete ordered cluster \(p_1,\ldots,p_9\);
3. infinitely-near chart/tangent data, or the explicit statement that all nine centers are proper;
4. middle group and extension/orbit data;
5. the number of degree-one components;
6. the unique canonical class matrix used by the catalogue.

The index-five cyclic Tate normal form is deliberately **not** imported as a second catalogue matrix: the source itself says that the nine-proper-point model is the preferred plane catalogue entry.

The web records also expand auxiliary equations that are defined globally in the LaTeX source (for example `Psi_cyc` and the `Phi` equations) so that every web entry is self-contained.

## Uniform-schema checks

Every one of the 26 records has exactly the same fields and the same display order:

1. field, parameters, and cubic;
2. ordered cluster;
3. infinitely-near data;
4. normal class, extension, and verification;
5. exactly one class matrix for the prime \((-2)\)-curves.

All records contain nine labeled centers. No parsed record contains leftover LaTeX table markup, a second component/class matrix, an “as above” cross-reference, or an incomplete trailing clause.

## Independent lattice checks

For every class-matrix row
\[
D=(d,e_1,\ldots,e_9)
\]
the validator checks

- exactly 10 coefficients;
- \(D^2=d^2-\sum e_i^2=-2\);
- \(D\cdot K_X=-3d-\sum e_i=0\);
- no repeated matrix rows.

For the matrix as a whole it checks

- the affine ADE decomposition reconstructed from intersections;
- the primitive positive relation in every connected affine component equals \(-mK_X\);
- the number of degree-one rows equals the stated line count;
- Smith normal form of \(K_X^\perp/\langle D_i\rangle\) equals the stated middle group;
- the class \([-K_X]\) has exact order equal to the stated Halphen index \(m\).

All **26/26** entries pass these checks.

## Entry-by-entry status

| Surface | Index | Components | Lines | Middle group | Status |
|---|---:|---:|---:|---|---|
| `$D_{8,\mathrm{sp}}^{(2)}` | 2 | 9 | 4 | `$(\mathbb Z/2)^2` | PASS |
| `$D_{8,\mathrm{cyc}}^{(2)}` | 2 | 9 | 4 | `$\mathbb Z/4` | PASS |
| `$(E_7+A_1)_{\mathrm{sp}}^{(2)}` | 2 | 10 | 4 | `$(\mathbb Z/2)^2` | PASS |
| `$(E_7+A_1)_{\mathrm{cyc}}^{(2)}` | 2 | 10 | 4 | `$\mathbb Z/4` | PASS |
| `$(D_6+2A_1)_{\mathrm{pair}}^{(2)}` | 2 | 11 | 2 | `$\mathbb Z/2\oplus\mathbb Z/4` | PASS |
| `$(D_6+2A_1)_{\mathrm{fixed}}^{(2)}` | 2 | 11 | 7 | `$\mathbb Z/2\oplus\mathbb Z/4` | PASS |
| `$(2D_4)^{(2)}` | 2 | 10 | 8 | `$\mathbb Z/2\oplus\mathbb Z/4` | PASS |
| `$A_{8,\mathrm{ns}}^{(3)}` | 3 | 9 | 9 | `$\mathbb Z/9` | PASS |
| `$A_{8,\mathrm{sp}}^{(3)}` | 3 | 9 | 7 | `$(\mathbb Z/3)^2` | PASS |
| `$(E_6+A_2)_{\mathrm{ns}}^{(3)}` | 3 | 10 | 8 | `$\mathbb Z/9` | PASS |
| `$(E_6+A_2)_{\mathrm{sp}}^{(3)}` | 3 | 10 | 8 | `$(\mathbb Z/3)^2` | PASS |
| `$(4A_2)_{\mathrm{ns}}^{(3)}` | 3 | 12 | 8 | `$\mathbb Z/3\oplus\mathbb Z/9` | PASS |
| `$(A_7+A_1)_{\mathrm{sp}}^{(4)}` | 4 | 10 | 7 | `$(\mathbb Z/4)^2` | PASS |
| `$(A_7+A_1)_{\mathrm{mid}}^{(4)}` | 4 | 10 | 8 | `$\mathbb Z/2\oplus\mathbb Z/8` | PASS |
| `$(A_7+A_1)_{\mathrm{cyc}}^{(4)}` | 4 | 10 | 7 | `$\mathbb Z/16` | PASS |
| `$(D_5+A_3)_{\mathrm{sp}}^{(4)}` | 4 | 10 | 7 | `$(\mathbb Z/4)^2` | PASS |
| `$(D_5+A_3)_{\mathrm{mid}}^{(4)}` | 4 | 10 | 8 | `$\mathbb Z/2\oplus\mathbb Z/8` | PASS |
| `$(D_5+A_3)_{\mathrm{cyc}}^{(4)}` | 4 | 10 | 7 | `$\mathbb Z/16` | PASS |
| `$(A_5+A_2+A_1)_{\mathrm{sp}}^{(6)}` | 6 | 11 | 8 | `$(\mathbb Z/6)^2` | PASS |
| `$(A_5+A_2+A_1)_{\xi=3}^{(6)}` | 6 | 11 | 7 | `$\mathbb Z/3\oplus\mathbb Z/12` | PASS |
| `$(A_5+A_2+A_1)_{\xi=2}^{(6)}` | 6 | 11 | 8 | `$\mathbb Z/2\oplus\mathbb Z/18` | PASS |
| `$(A_5+A_2+A_1)_{\mathrm{cyc}}^{(6)}` | 6 | 11 | 7 | `$\mathbb Z/36` | PASS |
| `$(2A_3+2A_1)_{\mathrm{other}\,2}^{(4)}` | 4 | 12 | 7 | `$\mathbb Z/4\oplus\mathbb Z/8` | PASS |
| `$(2A_3+2A_1)_{\mathrm{ord}\,4}^{(4)}` | 4 | 12 | 7 | `$\mathbb Z/2\oplus\mathbb Z/16` | PASS |
| `$(2A_4)_{\mathrm{sp}}^{(5)}` | 5 | 10 | 8 | `$(\mathbb Z/5)^2` | PASS |
| `$(2A_4)_{\mathrm{cyc}}^{(5)}` | 5 | 10 | 7 | `$\mathbb Z/25` | PASS |

## Scope of the audit

This establishes source fidelity of the web catalogue and gives independent lattice-level consistency checks. The LaTeX source and the companion Magma repository contain additional exact certificates for smoothness, marked-point incidence, recursive jets, exact torsion/group-law statements, fat-point linear systems, and geometric irreducibility. Those Magma programs cannot be executed in this environment, so this audit does **not** claim to be an independent rerun of those Magma certificates.
