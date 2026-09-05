"""Is the odd-line narrowing of section 25 in the text or in the tracing?

For each side with enough aligned lines, odd-numbered and even-numbered
lines are compared on: units per line, line length in pixels of the
tracing, mean glyph width in pixels, the width slope along the line, and
the width of the first and last fifth of the line. Since Barthel drew
alternate lines rotated into reading orientation, a difference that tracks
parity on every side would point at the tracing process; one confined to
particular texts would belong to those texts.

A permutation test asks how often a random assignment of the side's lines
to two groups of the same sizes produces an odd-minus-even slope difference
as large as the observed one.

Outputs (out/): parity_check.csv, parity_check.md
"""
import collections, csv, pathlib, random
import numpy as np

random.seed(4)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
rows = [r for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8")) if r["line_quality"] == "reliable"]
by_line = collections.defaultdict(list)
for r in rows:
    by_line[(r["side"], r["line"])].append(r)

line_stats = []
for (side, lid), lst in by_line.items():
    lst.sort(key=lambda r: int(r["position"]))
    w = np.array([int(r["width"]) for r in lst], float)
    if len(lst) < 8:
        continue
    pos = np.linspace(0, 1, len(lst))
    rel = w / np.median(w)
    slope = np.polyfit(pos, rel, 1)[0]
    x0 = min(int(r["x0"]) for r in lst); x1 = max(int(r["x1"]) for r in lst)
    line_stats.append({"side": side, "line": lid, "parity": "odd" if int(lid[2:]) % 2 else "even", "units": len(lst),
                       "pixels": x1 - x0, "mean_width": float(w.mean()), "slope": float(slope),
                       "first_fifth": float(rel[pos < 0.2].mean()), "last_fifth": float(rel[pos > 0.8].mean())})

with open(out / "parity_check.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(line_stats[0].keys()))
    wr.writeheader()
    for r in line_stats:
        wr.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})

md = ["# Odd against even lines\n",
      "Per side, means over aligned lines of at least eight units. Slope = change in relative glyph width from the start of a line to its end. "
      "p = share of random regroupings of the side's lines giving an odd-minus-even slope difference at least as large in magnitude.\n",
      "| side | odd lines | even lines | units, odd / even | pixels, odd / even | mean width px, odd / even | slope, odd / even | difference | p |",
      "|---|---|---|---|---|---|---|---|---|"]
summary = []
for side in sorted({r["side"] for r in line_stats}):
    odd = [r for r in line_stats if r["side"] == side and r["parity"] == "odd"]
    even = [r for r in line_stats if r["side"] == side and r["parity"] == "even"]
    if len(odd) < 2 or len(even) < 2:
        continue
    m = lambda lst, k: float(np.mean([r[k] for r in lst]))
    diff = m(odd, "slope") - m(even, "slope")
    allr = odd + even
    slopes = [r["slope"] for r in allr]
    n_odd = len(odd)
    hits = 0
    for _ in range(4000):
        random.shuffle(slopes)
        d = np.mean(slopes[:n_odd]) - np.mean(slopes[n_odd:])
        if abs(d) >= abs(diff):
            hits += 1
    p = hits / 4000
    summary.append((side, len(odd), len(even), diff, p))
    md.append(f"| {side} | {len(odd)} | {len(even)} | {m(odd, 'units'):.0f} / {m(even, 'units'):.0f} | {m(odd, 'pixels'):.0f} / {m(even, 'pixels'):.0f} | "
              f"{m(odd, 'mean_width'):.1f} / {m(even, 'mean_width'):.1f} | {m(odd, 'slope'):+.2f} / {m(even, 'slope'):+.2f} | {diff:+.2f} | {p:.2f} |")
neg = sum(1 for s in summary if s[3] < 0)
md.append(f"\nSides where odd lines narrow more than even: {neg} of {len(summary)}. Sides with p below 0.05: "
          + (", ".join(f"{s[0]} ({s[3]:+.2f})" for s in summary if s[4] < 0.05) or "none") + ".")
(out / "parity_check.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
