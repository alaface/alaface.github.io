#!/usr/bin/env python3
import gzip, json, re, sys
from collections import Counter
from functools import reduce
from math import gcd
from pathlib import Path

import sympy as sp
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_form
from sympy.polys.domains import ZZ

ROOT_SIGNATURES = {
    "A1": (2,(1,1)), "A2": (3,(1,1,1)), "A3": (4,(1,1,1,1)),
    "A4": (5,(1,1,1,1,1)), "A5": (6,(1,1,1,1,1,1)),
    "A7": (8,(1,1,1,1,1,1,1,1)), "A8": (9,(1,1,1,1,1,1,1,1,1)),
    "D4": (5,(1,1,1,1,2)), "D5": (6,(1,1,1,1,2,2)),
    "D6": (7,(1,1,1,1,2,2,2)), "D8": (9,(1,1,1,1,2,2,2,2,2)),
    "E6": (7,(1,1,1,2,2,2,3)), "E7": (8,(1,1,2,2,2,3,3,4)),
}
EXPECTED = {
    "D_8":["D8"], "E_7+A_1":["A1","E7"], "D_6+2A_1":["A1","A1","D6"],
    "2D_4":["D4","D4"], "A_8":["A8"], "E_6+A_2":["A2","E6"],
    "4A_2":["A2"]*4, "A_7+A_1":["A1","A7"], "D_5+A_3":["A3","D5"],
    "A_5+A_2+A_1":["A1","A2","A5"], "2A_3+2A_1":["A1","A1","A3","A3"],
    "2A_4":["A4","A4"],
}
FORBIDDEN_TEXT = (
    "component matrix", "affine-component matrix", "Class matrix &", "smallmatrix",
    "longtable", "multicolumn", "addlinespace", "as above",
)


def ip(v,w): return v[0]*w[0]-sum(a*b for a,b in zip(v[1:],w[1:]))
def dk(v): return -3*v[0]-sum(v[1:])

def components(m):
    unseen=set(range(len(m))); out=[]
    while unseen:
        seed=unseen.pop(); comp={seed}; stack=[seed]
        while stack:
            i=stack.pop()
            for j in list(unseen):
                if ip(m[i],m[j])>0:
                    unseen.remove(j); comp.add(j); stack.append(j)
        out.append(sorted(comp))
    return out

def primitive_kernel(comp,m):
    Q=sp.Matrix([[ip(m[i],m[j]) for j in comp] for i in comp])
    ns=Q.nullspace(); assert len(ns)==1
    v=ns[0]; L=1
    for x in v: L=sp.ilcm(L,sp.denom(x))
    a=[int(x*L) for x in v]
    if sum(x>0 for x in a)<sum(x<0 for x in a): a=[-x for x in a]
    g=reduce(gcd,[abs(x) for x in a if x])
    return [x//g for x in a]

def classify(comp,m):
    sig=(len(comp),tuple(sorted(primitive_kernel(comp,m))))
    return next((name for name,s in ROOT_SIGNATURES.items() if sig==s), "?")

def quotient_invariants(m):
    A=sp.Matrix([row[:9] for row in m])
    assert A.rank()==9
    D=smith_normal_form(A.T,domain=ZZ)
    return [abs(int(D[i,i])) for i in range(min(D.rows,D.cols)) if abs(int(D[i,i]))>1]

def parse_middle(tex):
    tex=tex.replace(" ","")
    m=re.fullmatch(r"\(\\mathbbZ/(\d+)\)\^2",tex)
    if m: return [int(m.group(1))]*2
    m=re.fullmatch(r"\\mathbbZ/(\d+)\\oplus\\mathbbZ/(\d+)",tex)
    if m: return [int(m.group(1)),int(m.group(2))]
    m=re.fullmatch(r"\\mathbbZ/(\d+)",tex)
    if m: return [int(m.group(1))]
    t=tex.replace(r"\mathbbZ",r"\mathbb Z")
    m=re.fullmatch(r"\(\\mathbbZ/(\d+)\)\^2",t)
    if m: return [int(m.group(1))]*2
    raise AssertionError(f"Cannot parse middle group: {tex}")

def in_row_lattice(m,v9):
    A=sp.Matrix([row[:9] for row in m])
    H=hermite_normal_form(A.T)
    x=H.inv()*sp.Matrix(v9)
    return all(val.q==1 for val in x)

def order_minus_K(m, max_order=100):
    v=[3]+[-1]*8
    for n in range(1,max_order+1):
        if in_row_lattice(m,[n*x for x in v]): return n
    return None

def point_indices(txt):
    out=set(map(int,re.findall(r"p_\{?(\d)\}?",txt)))
    for a,b in re.findall(r"p_\{?(\d)\}?\s*=\\cdots=\s*p_\{?(\d)\}?",txt):
        out.update(range(int(a),int(b)+1))
    return out

def balanced(txt,op,cl): return txt.count(op)==txt.count(cl)

def main(path):
    raw=gzip.open(path,"rt").read() if str(path).endswith(".gz") else Path(path).read_text()
    data=json.loads(raw)
    assert data["catalogue_count"]==26
    ss=data["surfaces"]; assert len(ss)==26
    keyset=set(ss[0]); ids=set(); names=set()
    required_text=("field_cubic","cluster","infinitely_near","normal_extension_verification")
    for s in ss:
        assert set(s)==keyset, s["id"]
        assert s["id"] not in ids; ids.add(s["id"])
        assert s["name_tex"] not in names; names.add(s["name_tex"])
        assert s["name_math"]==r"\("+s["name_tex"]+r"\)"
        assert all(s[k].strip() for k in required_text)
        assert point_indices(s["cluster"])==set(range(1,10)), s["id"]
        alltext="\n".join(s[k] for k in required_text)
        assert not any(f.lower() in alltext.lower() for f in FORBIDDEN_TEXT), s["id"]
        assert balanced(alltext,r"\(",r"\)"), s["id"]
        assert balanced(alltext,r"\[",r"\]"), s["id"]
        assert alltext.count("{")==alltext.count("}"), s["id"]
        assert not s["normal_extension_verification"].rstrip().endswith(","), s["id"]
        assert s["source_refs"] and all(r["file"] and len(r["lines"])==2 for r in s["source_refs"])

        m=s["class_matrix"]
        assert s["component_count"]==len(m)
        assert all(len(r)==10 for r in m)
        assert len({tuple(r) for r in m})==len(m)
        assert all(ip(r,r)==-2 for r in m)
        assert all(dk(r)==0 for r in m)
        profile=Counter(r[0] for r in m)
        assert s["line_count"]==profile[1]
        expected_profile=", ".join(f"{k}×{v}" for k,v in sorted(profile.items()))
        assert expected_profile==s["degree_profile"], (s["id"],expected_profile,s["degree_profile"])

        cc=sorted(classify(c,m) for c in components(m))
        assert cc==sorted(EXPECTED[s["root_tex"]]), (s["id"],cc)
        target=[3*s["index"]]+[-s["index"]]*9
        for c in components(m):
            w=primitive_kernel(c,m)
            total=[sum(w[k]*m[c[k]][j] for k in range(len(c))) for j in range(10)]
            assert total==target, (s["id"],total,target)

        assert quotient_invariants(m)==parse_middle(s["middle_tex"]), (s["id"],quotient_invariants(m),s["middle_tex"])
        assert order_minus_K(m)==s["index"], (s["id"],order_minus_K(m),s["index"])

    print("PASS: 26/26 entries; uniform schema, text sanity, ADE, fiber, middle-group, and index checks")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "data/catalogue.gz")
