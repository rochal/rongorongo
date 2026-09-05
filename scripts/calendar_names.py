"""The Mamari calendar against the named nights of the Rapa Nui month.

Section 21 rebuilt the calendar from the transliteration: 28 crescents in
seven runs (2, 6, 3, 2, 5, 3, 5) separated by eight marker groups. Metraux
(1940, p. 50) prints the thirty night names of the Rapa Nui month, taken
from Thomson's informant and from later lists. Their structure is uneven:
most nights have a name of their own, but two stretches are counted with
one base name and an ordinal, six Kokore nights (5 to 10) and five Kokore
nights (19 to 23), and two pairs share a base (Rongo 26 to 27, Mauri 28 to
29).

The comparison asks two things without assuming any sign's value:
  runs      do the calendar's crescent runs have the lengths of the named
            stretches? The two longest runs are 6 and 5, in that order; the
            two Kokore stretches are 6 and 5, in that order. A permutation
            test gives how often a random division of the crescents into
            seven runs shows a 6 before a 5.
  markers   if crescents are nights in order, do the marker groups fall
            where the name class changes (a Kokore stretch begins or ends,
            or a named pair begins)? Every offset of the crescents against
            the month is tried, and the count is compared with random marker
            placement.

The night names are read from data/rapanui/nights.txt (one per line,
number and name), parsed from the OCR of the page scan.

Outputs (out/): calendar_names.md
"""
import collections, csv, pathlib, random, re

random.seed(9)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
names = {}
for l in (root / "data" / "rapanui" / "nights.txt").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*(\d+)\s+(.+)", l)
    if m:
        names[int(m.group(1))] = m.group(2).strip()
N = max(names)
ORDINALS = {"tahi", "rua", "toru", "ha", "rima", "ono", "hitu", "varu", "iva"}


def base(name):
    w = re.sub(r"\(.*?\)", "", name).lower().split()
    w = [x for x in w if x not in ORDINALS]
    return w[0] if w else name.lower()


bases = [base(names[i]) for i in range(1, N + 1)]
# stretches of consecutive nights sharing a base name
stretches = []
i = 0
while i < N:
    j = i
    while j + 1 < N and bases[j + 1] == bases[i]:
        j += 1
    stretches.append((i + 1, j + 1, bases[i], j - i + 1))
    i = j + 1
multi = [s for s in stretches if s[3] > 1]
# class boundaries: a gap (between night k and k+1) where a multi-night stretch starts or ends
boundaries = set()
for a, b, _, n in multi:
    if a > 1:
        boundaries.add(a - 1)      # gap before the stretch
    if b < N:
        boundaries.add(b)          # gap after it

# the calendar
rows = list(csv.DictReader(open(out / "calendar_sequence.csv", encoding="utf-8")))
seq = [r for r in rows if r["run"] or r["marker_group"]]
runs = []
cur = 0
for r in seq:
    if r["class"] == "crescent":
        cur += 1
    elif r["class"] == "marker" and r["marker_group"]:
        if cur:
            runs.append(cur); cur = 0
if cur:
    runs.append(cur)
# crescents inside the calendar proper plus the two after the last marker
after = sum(1 for r in rows if r["class"] == "crescent" and not r["run"] and int(r["index"]) > max(int(r["index"]) for r in rows if r["marker_group"]))
total = sum(runs)

# permutation test: a 6 before a 5 among seven runs summing to the total
def random_runs(total, k):
    cuts = sorted(random.sample(range(1, total), k - 1))
    return [b - a for a, b in zip([0] + cuts, cuts + [total])]


trials = 20000
hit = 0
for _ in range(trials):
    r = random_runs(total, len(runs))
    if 6 in r and 5 in r and r.index(6) < r.index(5):
        hit += 1
p_runs = hit / trials

# marker alignment: crescent c (1-based) is night c + offset; a marker group after
# crescent c falls in the gap (c + offset)
marker_gaps = []
c = 0
for r in seq:
    if r["class"] == "crescent":
        c += 1
    elif r["class"] == "marker" and r["marker_group"]:
        if 0 < c < total:
            marker_gaps.append(c)
results = []
for off in range(0, N - total + 1):
    hits = sum(1 for g in marker_gaps if (g + off) in boundaries)
    results.append((off, hits))
best_off, best_hits = max(results, key=lambda x: x[1])
# null: the same number of markers at random gaps
null_hits = []
gaps = list(range(1, total))
for _ in range(trials):
    mg = random.sample(gaps, len(marker_gaps))
    null_hits.append(max(sum(1 for g in mg if (g + off) in boundaries) for off in range(0, N - total + 1)))
p_markers = sum(1 for h in null_hits if h >= best_hits) / trials

md = ["# The Mamari calendar against the named nights\n",
      f"Night names from Metraux 1940, page 50: {N} nights. Stretches sharing a base name: "
      + ", ".join(f"{b} nights {a} to {e} ({n})" for a, e, b, n in multi) + ".\n",
      f"Calendar from section 21: {len(runs)} crescent runs of {', '.join(map(str, runs))}, sum {total}, plus {after} after the last marker group; "
      f"marker groups after crescents {', '.join(map(str, marker_gaps))}.\n",
      "## The two longest runs\n",
      f"The calendar's two longest runs are 6 and 5 crescents, in that order. The month's two Kokore stretches are 6 and 5 nights, "
      f"in that order. Among {trials} random divisions of {total} crescents into {len(runs)} runs, a run of exactly 6 followed later by "
      f"a run of exactly 5 occurred in {p_runs:.1%}.\n",
      "## Marker groups at name-class boundaries\n",
      f"Boundaries of the month, gaps where a shared-name stretch begins or ends: after nights {', '.join(map(str, sorted(boundaries)))}. "
      f"With crescents taken as nights in order and every offset tried, the best offset is {best_off}, placing {best_hits} of "
      f"{len(marker_gaps)} interior marker groups on a boundary. Random marker placement, best offset likewise chosen, reaches at least "
      f"{best_hits} in {p_markers:.1%} of trials.\n",
      "| offset | marker groups on a boundary |\n|---|---|"]
for off, h in results:
    md.append(f"| {off} | {h} |")
md.append("\n## The nights, for reference\n")
md.append("| night | name |\n|---|---|")
for i in range(1, N + 1):
    md.append(f"| {i} | {names[i]} |")
(out / "calendar_names.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:12]))
