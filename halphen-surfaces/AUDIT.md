# Catalogue audit — 19 September 2026

All **26 records**, including **268 component classes**, were checked against the supplied LaTeX catalogue and independently audited. No incorrect cubic, marked point, tangent vector, or component-matrix entry was found. The mathematical checks below passed; their scope differs between families.

## Source fidelity and conventions

Every ordered cluster and component matrix agrees with the cited source, including row order. The fields, cubics, parameter equations and tangent formulas also agree, apart from corrected punctuation and TeX typos. The supplementary cyclic index-five Tate presentation is not counted as a second catalogue entry.

The source's recursive chart convention is restored in the webpage. Its provenance is `catalogue_index23.tex`, lines 10–26: translate the proper center to the origin; for a tangent \([\alpha:\beta]\), use

\[
(u_j,v_j)=
\begin{cases}
(u_{j+1},u_{j+1}(\beta/\alpha+v_{j+1})),&\alpha\ne0,\\
(u_{j+1}v_{j+1},u_{j+1}),&\alpha=0.
\end{cases}
\]

Here \(p\prec q\) means that \(q\) lies above \(p\). Numerical subscripts label the points and need not give their blow-up order. All **32 exceptional rows** agree with the displayed chain directions.

## Independent lattice checks: 26/26 passed

Exact integer and rational arithmetic verified:

- ten coefficients per row, square \(-2\), and orthogonality to \(K_X\);
- nonnegative intersections between distinct rows and the full weighted affine ADE graphs;
- all **60 connected configurations**, whose primitive positive relations give exactly \(-mK_X\);
- rank nine in \(K_X^\perp\), Smith invariants equal to the displayed middle groups, and exact order \(m\) of \([-K_X]\);
- component counts, degree profiles and numbers of line components.

Smith invariants were also independently cross-checked with Magma. These lattice checks alone do not prove geometric effectivity or irreducibility.

## Geometric certificates rerun

Magma was available for this audit. Every execution below completed successfully, with the expected success output and no failed assertion or runtime error. Script paths identify the supplied verification package; they are not claims that those files are publicly downloadable.

| Families | Executed certificates | Scope |
|---|---|---|
| Seven index-two entries | `index23/verify_index2_models.m`; `index23/identify_d6_ii_orbit.m` | Generic smoothness, incidence, recursive jets, normal order, unique geometrically integral positive-degree components; the seven-line D6+2A1 model's fixed extension orbit is separately checked. |
| Five index-three entries | `index23/verify_index3_models.m` | Generic checks for the A8 and E6+A2 families. For 4A2: generic incidence/lattice, characteristic-zero arithmetic specialization, and all twelve geometrically integral components modulo 31. |
| Additional 4A2 checks | `index23/check_4a2_generic_order.m`, `check_4a2_constants.m`, `check_4a2_pairing.m`, `check_4a2_t1_components.m` | Generic normal order three; constant field; characteristic-zero Weil pairing and all twelve nullities at the degree-six point with t=1. |
| Three index-four Weierstrass families | `index46/verify_weierstrass_families.m`, loading `index4_uniform/verify_index4.m` | Generic group relations, smoothness, normal order and row restrictions; unique integral components at the stated characteristic-zero specializations. |
| Nine incidence-normalized index-four/six families | `index46/verify_printed_formulas.py`, using `verify_incidence_formulas.py` | Direct checks of the printed formulas at the finite-field specializations listed below: incidence, smoothness, distinct points, normal order, group/extension data, lattice, unique sections and absolute irreducibility. |
| Parameter curves | `index46/verify_parameter_curves.py` | Exact irreducibility, absolute-irreducibility and constant-field calculations, including the quadratic and cubic covers. |
| Split index five | `index5/index5_split_verify.m` | Generic point/group identities and normal order; parameter factor; Weil pairing and all ten unique absolutely irreducible sections modulo 31. |
| Cyclic index five | `index5/index5_cyclic_division.m`; additional `verify_cyclic5_specializations.m` | Generic incidence surface and division-locus calculation. Independent checks at the printed degree-twelve characteristic-zero point: point identities, orders 25 and 5, and all row restrictions; all ten unique absolutely irreducible sections modulo 17. |

### Nine finite-field formula checks

| Catalogue ID | Verified specialization |
|---|---|
| `a7-a1-cyc-4` | F11, (s,u)=(4,7) |
| `d5-a3-sp-4` | F13, (a,s)=(6,2) |
| `d5-a3-cyc-4` | F11, (t,eta)=(2,8) |
| `a5-a2-a1-sp-6` | F109, (omega,s,t)=(45,3,44) |
| `a5-a2-a1-xi3-6` | F31, (a,t)=(0,13) |
| `a5-a2-a1-xi2-6` | F29, (s,t)=(2,4) |
| `a5-a2-a1-cyc-6` | F29, (t,u)=(2,7) |
| `2a3-2a1-other2-4` | F29, (s,t)=(2,9) |
| `2a3-2a1-ord4-4` | F23, (s,u)=(2,5) |

**Scope:** these nine computations certify the stated specializations. Their success alone does not independently establish the generic characteristic-zero torsion, row restrictions, or effectivity. The corresponding generic assertions remain those of the source catalogue. Geometric integrality is asserted on the indicated nonempty open loci, not at every parameter value yielding a smooth cubic and distinct points.

## Available public material

The [catalogue data](https://github.com/alaface/alaface.github.io/blob/main/halphen-surfaces/data/catalogue.gz) and [web-catalogue validator](https://github.com/alaface/alaface.github.io/blob/main/halphen-surfaces/validate_catalogue.py) are publicly available. Article filenames and line ranges in the records identify the source passages used in this audit; they are bibliographic locators, not download links. This update does not publish the source manuscript or its nonpublic certificate package.
