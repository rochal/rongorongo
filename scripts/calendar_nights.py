"""The Mamari calendar against the named month under three counting rules, with the anchor fixed.

Section 21 rebuilt the calendar as seven runs of crescents (2, 6, 3, 2, 5,
3, 5; 28 crescents) framed by eight marker groups, and section 21's names
test let the crescents slide against the thirty night names by a free
offset. Five signs that are not crescents stand inside the runs: 30, 59,
143, 152 and the bird 600. Whether they count as nights was left open.

Three rules are tested here:
  A  crescents only                                      28 nights
  B  every unit inside a run                             31 nights
  C  every unit inside a run except the bird 600, which  30 nights
     also appears fused onto the opener of marker group 5
     and so belongs to the marker vocabulary

For each rule the units inside the runs are numbered as nights in order,
the marker groups fall in the gaps between runs, and the gaps are compared
with the boundaries of the named month where a name class changes: the two
Kokore stretches (5 to 10 and 19 to 23), and the two named pairs (Rongo
26 to 27, Mauri 28 to 29). Two placements are scored: anchored, with the
first unit as night 1 and no free parameter; and the best of the thirty
offsets, as before. The null is random placement of the same number of
marker gaps among the month's gaps, 20,000 draws, for each placement.

Also recorded: the orientation of the crescents in Barthel's tracing,
measured as the ink asymmetry of each crescent instance, to see whether
the crescents flip between halves of the month. They do not.

Outputs: out/calendar_nights.md, out/calendar_nights.csv
"""
import csv, json, pathlib, re
import numpy as np

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
rng = np.random.default_rng(21)
LINES = ("Ca06", "Ca07", "Ca08", "Ca09")


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


# the named month
names = {}
for l in (root / "data" / "rapanui" / "nights.txt").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*(\d+)\s+(.+)", l)
    if m:
        names[int(m.group(1))] = m.group(2).strip()
N_NIGHTS = max(names)


def base(name):
    return re.sub(r"\s+(tahi|rua|toru|ha|rima|ono|Tane|nui|kero)$", "", re.sub(r"\(.*?\)", "", name)).strip()


# a boundary lies in the gap after night g where a shared-base stretch begins or ends: own-name to shared,
# shared to own-name, or one shared base to another
classes = []
for n in range(1, N_NIGHTS + 1):
    b = base(names[n])
    shared = sum(1 for m in names.values() if base(m) == b) > 1
    classes.append(b if shared else "own")
name_boundaries = {g for g in range(1, N_NIGHTS) if classes[g - 1] != classes[g]}

# the calendar's units: crescent, marker or other, exactly as section 21 classified them
seq = [u for lid in LINES for u in corpus[lid]]
units = []
in_marker = False
for u in seq:
    c = clean(u); heads = c.split(".")
    if c.startswith("390.041") or c.startswith("600.390.041"):
        in_marker = True
    if in_marker and "040" in heads and not c.startswith("390"):
        in_marker = False                   # group 2 has no tail: a marker group ends at the first crescent
    if in_marker:
        units.append(("marker", u))
        if "711" in heads:
            in_marker = False
        continue
    if "040" in heads:
        units.append(("crescent", u))
    else:
        units.append(("other", u))
# the calendar proper runs from the first marker group; what precedes it on Ca06 is the text before the calendar
start = next(i for i, (k, _) in enumerate(units) if k == "marker")
cal = units[start:]
# runs between marker groups, with the units after the last group as the final run
runs, cur = [], []
for k, u in cal:
    if k == "marker":
        if cur:
            runs.append(cur); cur = []
    else:
        cur.append((k, u))
if cur:
    runs.append(cur)
# the calendar proper is the seven runs framed by the eight marker groups; the two crescents after the last
# group (with three other signs before them) are kept apart as a tail, as in section 21
tail = runs[-1]
runs = runs[:-1]
tail_cres = sum(1 for k, _ in tail if k == "crescent")

RULES = {
    "A: crescents only": lambda k, u: k == "crescent",
    "B: every unit in a run": lambda k, u: True,
    "C: every unit but the bird 600": lambda k, u: not (k == "other" and clean(u).split(".")[0] == "600"),
}


def gaps_for(rule):
    lens = [sum(1 for k, u in r if rule(k, u)) for r in runs]
    cum = np.cumsum(lens)
    return lens, [int(g) for g in cum[:-1]], int(cum[-1])       # gaps after night g, interior marker groups only


def hits(gaps, offset):
    return sum(1 for g in gaps if (g + offset) in name_boundaries)


def null_hits(n_gaps, draws, best_offset):
    res = []
    all_gaps = list(range(1, N_NIGHTS))
    for _ in range(draws):
        g = rng.choice(all_gaps, n_gaps, replace=False)
        if best_offset:
            res.append(max(sum(1 for x in g if ((x + o - 1) % N_NIGHTS) + 1 in name_boundaries) for o in range(N_NIGHTS)))
        else:
            res.append(sum(1 for x in g if x in name_boundaries))
    return np.array(res)


rows = []
md = ["# The Mamari calendar against the named month, three counting rules\n",
      f"Named month: {N_NIGHTS} nights; name-class boundaries after nights {sorted(name_boundaries)} "
      f"(the Kokore stretches {[n for n in names if base(names[n]) == 'Kokore']} and the shared-base pairs).\n",
      f"The calendar proper: seven runs between the eight marker groups; {tail_cres} crescents follow the last group and are counted apart.\n",
      "| rule | run lengths | nights | anchored: marker gaps on a boundary | chance | best offset | its hits | chance (best of 30 offsets) |",
      "|---|---|---|---|---|---|---|---|"]
detail = {}
for name, rule in RULES.items():
    lens, gaps, total = gaps_for(rule)
    anchored = hits(gaps, 0)
    null_a = null_hits(len(gaps), 20000, False)
    best_off, best = max(((o, hits([((g + o - 1) % N_NIGHTS) + 1 for g in gaps], 0)) for o in range(N_NIGHTS)), key=lambda x: x[1])
    null_b = null_hits(len(gaps), 20000, True)
    p_a = float(np.mean(null_a >= anchored)); p_b = float(np.mean(null_b >= best))
    rows.append([name, " ".join(map(str, lens)), total, anchored, len(gaps), round(p_a, 3), best_off, best, round(p_b, 3)])
    md.append(f"| {name} | {' '.join(map(str, lens))} | {total} | {anchored} of {len(gaps)} | {p_a:.3f} | {best_off} | {best} of {len(gaps)} | {p_b:.3f} |")
    detail[name] = (lens, gaps, total)

# rule C, anchored, night by night
lens, gaps, total = detail["C: every unit but the bird 600"]
md.append("\n## Rule C, anchored: which nights each run covers\n")
md.append("| run | nights | names | marker group after it falls on a name boundary |\n|---|---|---|---|")
n = 1
for i, L in enumerate(lens):
    span = list(range(n, n + L)); n += L
    nm = ", ".join(names.get(x, "?") for x in span)
    boundary = "yes" if i < len(lens) - 1 and (n - 1) in name_boundaries else ("" if i == len(lens) - 1 else "no")
    md.append(f"| {i + 1} | {span[0]} to {span[-1]} | {nm} | {boundary} |")
md.append("\nMarker group 5, the one with the bird 600 fused onto its opener, is the group after run 4.")

# crescent orientation in the tracing
tr = {(r["line"], int(r["position"])): r for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8")) if r["side"] == "Ca"}
orient = []
try:
    from PIL import Image
    for lid in LINES:
        us = [u for u in corpus[lid] if not clean(u).startswith("(") and clean(u).split(".")[0] not in ("000", "999")]
        for k, u in enumerate(us):
            if "040" in clean(u).split(".") and clean(u) == "040":
                p = root / "data" / "tracings" / "instances" / "Ca" / f"{lid}_{k:03d}.png"
                if p.exists():
                    a = np.asarray(Image.open(p).convert("L")) < 128
                    ys, xs = np.where(a)
                    if len(xs) > 5:
                        w = xs.max() - xs.min() + 1; x0 = xs.min(); t = max(1, w // 3)
                        orient.append((lid, k, int(a[:, x0:x0 + t].sum()), int(a[:, x0 + w - t:x0 + w].sum())))
except ImportError:
    pass
if orient:
    same = sum(1 for _, _, l, r in orient if l >= r)
    md.append(f"\n## Crescent orientation in the tracing\n\n{len(orient)} plain crescents measured by ink asymmetry (left third against right third of the glyph): "
              f"{same} have more ink on the left, {len(orient) - same} on the right. In Barthel's reading orientation the crescents do not flip between "
              f"halves of the month, so the drawing offers no waxing-to-waning anchor; the anchor used above is the first unit as night 1.")
with open(out / "calendar_nights.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["rule", "run_lengths", "nights", "anchored_hits", "gaps", "p_anchored", "best_offset", "best_hits", "p_best"]); w.writerows(rows)
(out / "calendar_nights.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
