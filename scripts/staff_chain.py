"""Chaining test: are the Staff's triads a genealogy?

A genealogy chains: the offspring of one entry returns as the parent of a
later one, and a parent is often repeated over consecutive entries. The
1886 creation chant does both. Fischer's reading of the Santiago Staff as
triads X.76 Y Z predicts the same for the Staff.

For every text cut at sign 76 (Staff, Gv, Ta) and for the chant:
  chain      share of segments whose last unit reappears as the first unit
             of a later segment (any later one, and the very next one)
  parent     share of consecutive segment pairs with the same first unit
  slots      how much the first, middle and last slots share vocabulary
Each share is compared with a null that shuffles the order of the segments
(NULL_TRIALS times), which keeps every segment intact and destroys only
their sequence, so any chaining that survives is due to order.

Only segments of exactly three units are used for the slot analysis; the
chain and parent measures use all segments, taking first and last units.
Head signs are compared, so ligature differences do not break a match, and
the 76 attachment on the first unit is ignored.

Outputs (out/): staff_chain.md, staff_triads.csv, staff_chain.csv
"""
import collections, csv, json, pathlib, random, re

NULL_TRIALS = 500
random.seed(11)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
STROKES = {"001", "002", "003", "004", "005"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


sides = collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    sides[lid[:2]].extend(corpus[lid])


def segments76(seq):
    units = [clean(u) for u in seq if head(u) not in ("000", "999") and not head(u).startswith("(")]
    idx = [i for i, u in enumerate(units) if "076" in u.split(".")[1:] or u.split(".")[0] == "076"]
    segs = []
    for a, b in zip(idx, idx[1:]):
        seg = [u.split(".")[0] for u in units[a:b]]
        segs.append(seg)
    return segs


def measures(segs):
    """chain-any, chain-next, parent-repeat shares over a list of segments (lists of tokens)."""
    firsts = [s[0] for s in segs]
    lasts = [s[-1] for s in segs]
    n = len(segs)
    later_first = collections.Counter()
    chain_any = 0
    for i in range(n - 1, -1, -1):
        # does lasts[i] appear among firsts[i+1:]?
        if later_first[lasts[i]] > 0:
            chain_any += 1
        later_first[firsts[i]] += 1
    chain_next = sum(1 for i in range(n - 1) if lasts[i] == firsts[i + 1])
    parent = sum(1 for i in range(n - 1) if firsts[i] == firsts[i + 1])
    return chain_any / n, chain_next / max(1, n - 1), parent / max(1, n - 1)


def with_null(segs):
    obs = measures(segs)
    nulls = []
    order = list(segs)
    for _ in range(NULL_TRIALS):
        random.shuffle(order)
        nulls.append(measures(order))
    mean = [sum(x[k] for x in nulls) / NULL_TRIALS for k in range(3)]
    # one-sided p: share of nulls at or above the observation
    p = [sum(1 for x in nulls if x[k] >= obs[k]) / NULL_TRIALS for k in range(3)]
    return obs, mean, p


def slot_overlap(triads):
    A, B, C = (set(t[k] for t in triads) for k in range(3))
    j = lambda x, y: len(x & y) / len(x | y) if x | y else 0
    strokes = [sum(1 for t in triads if t[k] in STROKES) / len(triads) for k in range(3)]
    return j(A, B), j(A, C), j(B, C), strokes, (len(A), len(B), len(C))


# ---------------------------------------------------------------- chant
chant = []
for r in csv.DictReader(open(out / "chant_entries.csv", encoding="utf-8")):
    chant.append([r["A"], r["B"], r["C"]])

# ---------------------------------------------------------------- texts
results = {}
triad_rows = []
for name, segs in (("chant", chant), ("Staff", segments76(sides["Ia"])), ("Gv", segments76(sides["Gv"])), ("Ta", segments76(sides["Ta"]))):
    obs, null, p = with_null(segs)
    triads = [s for s in segs if len(s) == 3]
    ov = slot_overlap(triads) if len(triads) >= 5 else None
    results[name] = {"n": len(segs), "triads": len(triads), "obs": obs, "null": null, "p": p, "overlap": ov}
    if name == "Staff":
        for i, s in enumerate(segs):
            triad_rows.append([i + 1, len(s), " ".join(s)])

with open(out / "staff_triads.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["segment", "length", "head_signs"])
    w.writerows(triad_rows)
with open(out / "staff_chain.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["text", "segments", "measure", "observed", "null_mean", "p"])
    for name, r in results.items():
        for k, m in enumerate(("last reappears as a later first", "last equals next first", "consecutive same first")):
            w.writerow([name, r["n"], m, f"{r['obs'][k]:.4f}", f"{r['null'][k]:.4f}", f"{r['p'][k]:.3f}"])

md = ["# Chaining test on the sign-76 segments\n",
      f"Each share is compared with the mean over {NULL_TRIALS} shuffles of segment order; p is the share of shuffles "
      "scoring at least the observed value. Head signs are matched, ligatures ignored.\n",
      "| text | segments | last reappears as a later first | null | p | last equals next first | null | p | consecutive same first | null | p |",
      "|---|---|---|---|---|---|---|---|---|---|---|"]
for name, r in results.items():
    o, nl, p = r["obs"], r["null"], r["p"]
    md.append(f"| {name} | {r['n']} | {o[0]:.0%} | {nl[0]:.0%} | {p[0]:.2f} | {o[1]:.1%} | {nl[1]:.1%} | {p[1]:.2f} | "
              f"{o[2]:.1%} | {nl[2]:.1%} | {p[2]:.2f} |")
md.append("\n## Slot vocabularies in the three-unit segments\n")
md.append("| text | triads | distinct first / middle / last | overlap first-middle | first-last | middle-last | strokes in first / middle / last |")
md.append("|---|---|---|---|---|---|---|")
for name, r in results.items():
    if r["overlap"]:
        j1, j2, j3, st, sizes = r["overlap"]
        md.append(f"| {name} | {r['triads']} | {sizes[0]} / {sizes[1]} / {sizes[2]} | {j1:.2f} | {j2:.2f} | {j3:.2f} | "
                  f"{st[0]:.0%} / {st[1]:.0%} / {st[2]:.0%} |")
# most common Staff triads
staff_tri = collections.Counter(" ".join(s) for s in segments76(sides["Ia"]) if len(s) == 3)
md.append("\n## Most repeated three-unit segments on the Staff\n")
md.append("| segment (head signs) | count |\n|---|---|")
for s, n in staff_tri.most_common(12):
    md.append(f"| {s} | {n} |")
(out / "staff_chain.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
