"""Corpus-wide map of parallel passages.

Finds every maximal run of MIN_RUN or more consecutive units shared between
two places in the corpus, compares sides pairwise, merges neighbouring runs
into blocks, and groups the sides into families of related texts.

Matching is ligature-tolerant: only the first component of each unit counts
(380.001.003 -> 380, 522fy -> 522). Runs consisting only of strokes and
illegible signs are discarded, and a run must contain at least two distinct
non-stroke signs.

Outputs (out/):
  parallel_runs.csv      every maximal shared run: both locations, length, text
  parallel_blocks.csv    runs between the same two sides that lie within
                         GAP units of each other, merged
  parallel_matrix.csv    side x side: units covered by shared runs
  parallel_map.md        report: strongest pairs, families, longest runs,
                         and where each Keiti line has parallels
"""
import argparse, collections, csv, json, pathlib, re

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--min-run", type=int, default=5, help="minimum run length (default 5)")
ap.add_argument("--mismatch", type=int, default=0,
                help="substitutions allowed inside a run (default 0); a run must still start and end with "
                     "two matching units, so a mismatch never sits at an edge")
ap.add_argument("--family-min", type=int, default=20, help="covered units needed to link two sides")
ap.add_argument("--suffix", default="", help="suffix for output file names, e.g. _fuzzy")
ap.add_argument("--merge", default=None,
                help="CSV of head,representative pairs (from allographs.py) applied before matching")
args = ap.parse_args()

MERGE = {}
if args.merge:
    with open(args.merge, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            MERGE[row["head"]] = row["representative"]

MIN_RUN = args.min_run
MAX_MISMATCH = args.mismatch
GAP = 3
FAMILY_MIN = args.family_min
SUF = args.suffix

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
out.mkdir(exist_ok=True)
STROKES = {"000", "001", "002", "003", "004", "005", "999"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    h = clean(u).split(".")[0]
    return MERGE.get(h, h)


# sides in reading order, with a map back to line ids
sides = {}
where = {}
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    s = lid[:2]
    sides.setdefault(s, [])
    where.setdefault(s, [])
    for i, u in enumerate(corpus[lid]):
        sides[s].append(u)
        where[s].append((lid, i))
H = {s: [head(u) for u in v] for s, v in sides.items()}

# index MIN_RUN-grams
index = collections.defaultdict(list)
for s, hs in H.items():
    for i in range(len(hs) - MIN_RUN + 1):
        g = tuple(hs[i:i + MIN_RUN])
        if all(x in STROKES for x in g):
            continue
        index[g].append((s, i))

# maximal runs, extended in both directions with up to MAX_MISMATCH substitutions
def extend(sa, ia, sb, ib, n):
    """Grow [ia, ia+n) / [ib, ib+n) forward and backward. A substitution is
    accepted only if the two units after it match again, so runs always end on
    two matches. Returns (ia, ib, n, mismatches)."""
    A, B = H[sa], H[sb]
    budget = MAX_MISMATCH
    # forward
    while True:
        j = ia + n
        k = ib + n
        if j < len(A) and k < len(B) and A[j] == B[k]:
            n += 1
        elif budget and j + 2 < len(A) and k + 2 < len(B) and A[j + 1] == B[k + 1] and A[j + 2] == B[k + 2]:
            budget -= 1
            n += 3
        else:
            break
    # backward
    while True:
        j = ia - 1
        k = ib - 1
        if j >= 0 and k >= 0 and A[j] == B[k]:
            ia, ib, n = ia - 1, ib - 1, n + 1
        elif budget and j >= 2 and k >= 2 and A[j - 1] == B[k - 1] and A[j - 2] == B[k - 2]:
            budget -= 1
            ia, ib, n = ia - 3, ib - 3, n + 3
        else:
            break
    return ia, ib, n, MAX_MISMATCH - budget


runs = set()
for g, occ in index.items():
    if len(occ) < 2:
        continue
    if sum(1 for x in g if x not in STROKES) < 2:
        continue
    for a in range(len(occ)):
        for b in range(a + 1, len(occ)):
            (sa, ia), (sb, ib) = occ[a], occ[b]
            if sa == sb and abs(ia - ib) < MIN_RUN:
                continue
            ia2, ib2, n, mm = extend(sa, ia, sb, ib, MIN_RUN)
            if sa == sb and abs(ia2 - ib2) < n:
                continue                       # self-overlapping
            seg = H[sa][ia2:ia2 + n]
            if len({x for x in seg if x not in STROKES}) < 2:
                continue
            key = (sa, ia2, sb, ib2, n, mm) if (sa, ia2) <= (sb, ib2) else (sb, ib2, sa, ia2, n, mm)
            runs.add(key)
# drop runs contained in a longer run between the same two sides
runs = sorted(runs, key=lambda r: (-r[4], r))
kept = []
for r in runs:
    sa, ia, sb, ib, n, mm = r
    if any(k[0] == sa and k[2] == sb and k[1] <= ia and k[3] <= ib and
           k[1] + k[4] >= ia + n and k[3] + k[4] >= ib + n and (k[1] - ia) == (k[3] - ib) for k in kept):
        continue
    kept.append(r)
runs = [(sa, ia, sb, ib, n) for sa, ia, sb, ib, n, mm in kept]
mismatches = {(sa, ia, sb, ib, n): mm for sa, ia, sb, ib, n, mm in kept}


def loc(s, i):
    lid, k = where[s][i]
    return f"{lid}@{k}"


with open(out / f"parallel_runs{SUF}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["len", "mismatches", "side_a", "from_a", "side_b", "from_b", "text_a", "text_b"])
    for sa, ia, sb, ib, n in runs:
        w.writerow([n, mismatches[(sa, ia, sb, ib, n)], sa, loc(sa, ia), sb, loc(sb, ib),
                    "-".join(sides[sa][ia:ia + n]), "-".join(sides[sb][ib:ib + n])])

# merge runs into blocks per side pair
pair_runs = collections.defaultdict(list)
for sa, ia, sb, ib, n in runs:
    pair_runs[(sa, sb)].append((ia, ib, n))
blocks = []
for (sa, sb), lst in pair_runs.items():
    lst.sort()
    cur = None
    for ia, ib, n in lst:
        if cur and ia <= cur["end_a"] + GAP and ib <= cur["end_b"] + GAP and ib >= cur["start_b"]:
            cur["end_a"] = max(cur["end_a"], ia + n)
            cur["end_b"] = max(cur["end_b"], ib + n)
            cur["runs"] += 1
            cur["matched"] += n
        else:
            if cur:
                blocks.append(cur)
            cur = {"side_a": sa, "side_b": sb, "start_a": ia, "end_a": ia + n,
                   "start_b": ib, "end_b": ib + n, "runs": 1, "matched": n}
    if cur:
        blocks.append(cur)
blocks.sort(key=lambda b: -b["matched"])
with open(out / f"parallel_blocks{SUF}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["matched_units", "runs", "side_a", "from_a", "to_a", "side_b", "from_b", "to_b"])
    for b in blocks:
        w.writerow([b["matched"], b["runs"], b["side_a"], loc(b["side_a"], b["start_a"]),
                    loc(b["side_a"], b["end_a"] - 1), b["side_b"], loc(b["side_b"], b["start_b"]),
                    loc(b["side_b"], b["end_b"] - 1)])

# side x side matrix: units covered by shared runs (union of intervals)
cover = collections.defaultdict(set)
for sa, ia, sb, ib, n in runs:
    cover[(sa, sb)].update(range(ia, ia + n))
    cover[(sb, sa)].update(range(ib, ib + n))
names = sorted(sides)
with open(out / f"parallel_matrix{SUF}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side"] + names)
    for a in names:
        w.writerow([a] + [len(cover.get((a, b), ())) if a != b else "" for b in names])

# families by union-find on strong links
weight = {}
for (a, b), cov in cover.items():
    if a < b:
        weight[(a, b)] = min(len(cov), len(cover.get((b, a), ())))
parent = {s: s for s in names}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for (a, b), wgt in weight.items():
    if wgt >= FAMILY_MIN:
        parent[find(a)] = find(b)
fam = collections.defaultdict(list)
for s in names:
    fam[find(s)].append(s)
families = sorted((v for v in fam.values() if len(v) > 1), key=lambda v: -len(v))

# report
md = ["# Parallel passages across the corpus\n",
      f"{len(runs)} maximal shared runs of {MIN_RUN}+ units (ligature-tolerant, up to {MAX_MISMATCH} substitution"
      f"{'s' if MAX_MISMATCH != 1 else ''} per run), merged into {len(blocks)} blocks. "
      f"Families link sides sharing at least {FAMILY_MIN} covered units.\n"]

md.append("## Families\n")
for f in families:
    size = {s: len(H[s]) for s in f}
    md.append("- **" + ", ".join(f) + "**  (" + ", ".join(f"{s} {size[s]} units" for s in f) + ")")
singles = [s for s in names if len(fam[find(s)]) == 1]
md.append("\nSides with no strong link: " + ", ".join(singles))

md.append("\n## Strongest side pairs (units covered by shared runs, smaller side of the pair)\n")
md.append("| side A | side B | covered | share of A | share of B | blocks |\n|---|---|---|---|---|---|")
nblocks = collections.Counter((b["side_a"], b["side_b"]) for b in blocks)
for (a, b), wgt in sorted(weight.items(), key=lambda kv: -kv[1])[:30]:
    ca, cb = len(cover[(a, b)]), len(cover[(b, a)])
    md.append(f"| {a} | {b} | {wgt} | {ca / len(H[a]):.0%} | {cb / len(H[b]):.0%} | {nblocks[(a, b)]} |")

md.append("\n## Longest shared runs\n")
md.append("| len | subst. | A | B | text (A) |\n|---|---|---|---|---|")
for sa, ia, sb, ib, n in runs[:25]:
    md.append(f"| {n} | {mismatches[(sa, ia, sb, ib, n)]} | {loc(sa, ia)} | {loc(sb, ib)} | {'-'.join(sides[sa][ia:ia + n])} |")

md.append("\n## Where Keiti has parallels (external only)\n")
md.append("| Keiti line | partner | len | subst. | Keiti text | partner text |\n|---|---|---|---|---|---|")
for sa, ia, sb, ib, n in runs:
    for (s, i, t, j) in ((sa, ia, sb, ib), (sb, ib, sa, ia)):
        if s.startswith("E") and not t.startswith("E"):
            md.append(f"| {loc(s, i)} | {loc(t, j)} | {n} | {mismatches[(sa, ia, sb, ib, n)]} | "
                      f"{'-'.join(sides[s][i:i + n])} | {'-'.join(sides[t][j:j + n])} |")

md.append("\n## Coverage per side: how much of each text has a parallel anywhere else\n")
md.append("| side | units | covered | share |\n|---|---|---|---|")
anycover = collections.defaultdict(set)
for (a, b), cov in cover.items():
    if a != b:
        anycover[a].update(cov)
for s in sorted(names, key=lambda s: -len(anycover[s]) / len(H[s])):
    md.append(f"| {s} | {len(H[s])} | {len(anycover[s])} | {len(anycover[s]) / len(H[s]):.0%} |")

(out / f"parallel_map{SUF}.md").write_text("\n".join(md), encoding="utf-8")
print(f"{len(runs)} runs, {len(blocks)} blocks, {len(families)} families")
for f in families:
    print("  ", " ".join(f))
