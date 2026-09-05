"""The Santiago Staff's carved dividers: what do they group?

The Staff carries vertical strokes, coded 999 in the CEIPP file, that cut
its text into stretches. Section 14 found a median stretch of nine units,
about three sign-76 triads. This script asks what the stretches are:

  length      stretch length in units and in 76-segments, against a null
              that keeps the number of dividers and places them at random
  alignment   share of stretches that begin with a 76-bearing unit and end
              just before one, i.e. whether dividers sit on triad boundaries
  openers     the signs that begin and end stretches, with enrichment
              against their overall frequency on the Staff
  cohesion    whether consecutive triads inside a stretch share a first
              unit more often than consecutive triads across a divider
  repeats     stretches whose sign sequence recurs

Outputs (out/): staff_dividers.md, staff_stretches.csv
"""
import collections, csv, json, pathlib, random, re

random.seed(5)
TRIALS = 500
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


seq = []
for lid in sorted((k for k in corpus if k.startswith("Ia")), key=lambda k: int(k[2:])):
    seq.extend(clean(u) for u in corpus[lid])
seq = [u for u in seq if not u.startswith("000") and not u.startswith("(")]
is_div = [u == "999" for u in seq]
has76 = [("076" in u.split(".")[1:] or u.split(".")[0] == "076") for u in seq]
heads = [u.split(".")[0] for u in seq]
n_units = sum(1 for d in is_div if not d)
n_div = sum(is_div)


def stretches(is_div):
    """Lists of unit indices between consecutive dividers (partial ends dropped)."""
    cuts = [i for i, d in enumerate(is_div) if d]
    return [list(range(a + 1, b)) for a, b in zip(cuts, cuts[1:]) if b - a > 1]


def describe(is_div):
    S = stretches(is_div)
    lens = [len(s) for s in S]
    tri = [sum(1 for i in s if has76[i]) for s in S]
    begin76 = sum(1 for s in S if has76[s[0]]) / len(S)
    # a divider sits at a triad boundary when the unit after it carries 76
    # (a new triad starts) and the unit before it does not (the old triad had ended)
    mean = sum(lens) / len(lens)
    cv = (sum((l - mean) ** 2 for l in lens) / len(lens)) ** 0.5 / mean
    return S, lens, tri, begin76, cv


S, lens, tri, begin76, cv = describe(is_div)

# null: same number of dividers at random positions among the units
null_begin, null_cv, null_tri3 = [], [], []
for _ in range(TRIALS):
    flags = [True] * n_div + [False] * n_units
    random.shuffle(flags)
    # rebuild a sequence where dividers are placed among the non-divider units
    units_only = [i for i, d in enumerate(is_div) if not d]
    fake = []
    k = 0
    for f in flags:
        if f:
            fake.append(True)
        else:
            fake.append(False)
    # map fake positions back onto real units to look up has76
    fake_has76 = []
    j = 0
    for f in fake:
        if f:
            fake_has76.append(None)
        else:
            fake_has76.append(has76[units_only[j]]); j += 1
    cuts = [i for i, f in enumerate(fake) if f]
    FS = [list(range(a + 1, b)) for a, b in zip(cuts, cuts[1:]) if b - a > 1]
    if not FS:
        continue
    null_begin.append(sum(1 for s in FS if fake_has76[s[0]]) / len(FS))
    fl = [len(s) for s in FS]
    m = sum(fl) / len(fl)
    null_cv.append((sum((l - m) ** 2 for l in fl) / len(fl)) ** 0.5 / m)
    ft = [sum(1 for i in s if fake_has76[i]) for s in FS]
    null_tri3.append(sum(1 for t in ft if t == 3) / len(ft))
null_begin_m = sum(null_begin) / len(null_begin)
null_cv_m = sum(null_cv) / len(null_cv)
null_tri3_m = sum(null_tri3) / len(null_tri3)
p_begin = sum(1 for x in null_begin if x >= begin76) / len(null_begin)
p_cv = sum(1 for x in null_cv if x <= cv) / len(null_cv)
tri3 = sum(1 for t in tri if t == 3) / len(tri)
p_tri3 = sum(1 for x in null_tri3 if x >= tri3) / len(null_tri3)

# openers and closers
bg = collections.Counter(heads[i] for i, d in enumerate(is_div) if not d)
first = collections.Counter(heads[s[0]] for s in S)
last = collections.Counter(heads[s[-1]] for s in S)


def enriched(c, n):
    rows = []
    for sign, k in c.most_common(8):
        exp = n * bg[sign] / n_units
        rows.append((sign, k, k / exp if exp else 0))
    return rows


# cohesion: consecutive 76-segments inside a stretch vs across a divider
def segs76(idx):
    starts = [i for i in idx if has76[i]]
    return [heads[i] for i in starts]


inside_same = inside_n = across_same = across_n = 0
prev_last_first = None
for s in S:
    firsts = segs76(s)
    for a, b in zip(firsts, firsts[1:]):
        inside_n += 1
        inside_same += a == b
    if prev_last_first is not None and firsts:
        across_n += 1
        across_same += prev_last_first == firsts[0]
    prev_last_first = firsts[-1] if firsts else prev_last_first

# repeated stretches
content = collections.Counter(tuple(heads[i] for i in s) for s in S)
repeats = [(k, v) for k, v in content.items() if v > 1]

with open(out / "staff_stretches.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["stretch", "units", "triads_76", "starts_with_76", "first_sign", "last_sign", "head_signs"])
    for k, s in enumerate(S, 1):
        w.writerow([k, len(s), sum(1 for i in s if has76[i]), has76[s[0]], heads[s[0]], heads[s[-1]], " ".join(heads[i] for i in s)])

md = ["# The Staff's carved dividers\n",
      f"{n_units} legible units, {n_div} dividers, {len(S)} complete stretches between them. "
      f"Nulls place the same number of dividers at random among the units, {TRIALS} times.\n",
      "## Stretch length\n",
      f"Units per stretch: mean {sum(lens) / len(lens):.1f}, median {sorted(lens)[len(lens) // 2]}, "
      f"min {min(lens)}, max {max(lens)}. Coefficient of variation {cv:.2f} against {null_cv_m:.2f} for random dividers "
      f"(p that random is as regular: {p_cv:.2f}).\n",
      "| 76-segments per stretch | stretches | share |\n|---|---|---|"]
tc = collections.Counter(tri)
for k in sorted(tc):
    md.append(f"| {k} | {tc[k]} | {tc[k] / len(tri):.0%} |")
md.append(f"\nExactly three 76-segments: {tri3:.0%} observed against {null_tri3_m:.0%} under random dividers (p {p_tri3:.2f}).\n")
md.append("## Alignment with the triads\n")
md.append(f"Stretches that begin with a 76-bearing unit: {begin76:.0%}, against {null_begin_m:.0%} for random dividers (p {p_begin:.2f}). "
          f"Overall {sum(has76) / n_units:.0%} of units carry 76.\n")
md.append("## Opening and closing signs\n")
md.append("| position | sign | stretches | enrichment over its Staff frequency |\n|---|---|---|---|")
for sign, k, e in enriched(first, len(S)):
    md.append(f"| first | {sign} | {k} | {e:.1f} |")
for sign, k, e in enriched(last, len(S)):
    md.append(f"| last | {sign} | {k} | {e:.1f} |")
md.append("\n## Cohesion of triads inside a stretch\n")
md.append(f"Consecutive 76-segments sharing a first sign: inside a stretch {inside_same}/{inside_n} = {inside_same / max(1, inside_n):.1%}; "
          f"across a divider {across_same}/{across_n} = {across_same / max(1, across_n):.1%}.\n")
md.append("## Repeated stretches\n")
md.append(f"{len(repeats)} stretch sequences occur more than once." + ("" if not repeats else " " + "; ".join(f"{' '.join(k)} x{v}" for k, v in repeats[:5])))
(out / "staff_dividers.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
