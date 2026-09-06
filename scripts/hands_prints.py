"""Stroke weight on the prints: a first physical measurement per side, and a same-object test.

The shape descriptor used for the hands test cannot see stroke weight (its
positive control shows that), so here the glyphs cut from the prints by
register.py are measured directly:

  stroke     mean stroke width of an instance, as twice the mean distance
             from the skeleton to the nearest background pixel (scikit-image
             skeletonize and scipy's distance transform), divided by the
             instance's height so that the print's resolution cancels
  density    ink area over bounding-box area
  per side   median and interquartile range of the stroke ratio over the
             locally matched instances, for sides whose glyphs are at least
             MIN_HEIGHT pixels tall on the print
  test       the two sides of one object (Br and Bv, Er and Ev, ...) share a
             carver, a photographer and a retoucher; sides of different
             objects need not. If the same-object pairs are closer in median
             stroke ratio than random pairs of sides, the measurement carries
             a per-object signature, and a permutation test says how often
             chance does as well. What the signature is, carver's tool or
             retoucher's brush, the prints cannot say.

Outputs: out/hands_prints.csv (per side), out/hands_prints_instances.csv, out/hands_prints.md
"""
import collections, csv, itertools, pathlib
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize

MIN_HEIGHT = 30
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
idir = root / "data" / "photos" / "instances"
rows = [r for r in csv.DictReader(open(out / "photo_instances.csv", encoding="utf-8")) if float(r["local_score"]) >= 0.2 and int(r["print_ink_width"]) > 0]

inst = []
for r in rows:
    p = idir / r["side"] / f"{r['line']}_{int(r['position']):03d}.png"
    if not p.exists():
        continue
    a = np.asarray(Image.open(p).convert("L")) < 128
    ys, xs = np.where(a)
    if len(ys) < 20:
        continue
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape
    sk = skeletonize(a)
    if sk.sum() < 5:
        continue
    dist = ndimage.distance_transform_edt(a)
    stroke = 2 * float(dist[sk].mean())
    inst.append([r["side"], r["line"], int(r["position"]), r["head"], h, w, round(stroke, 2), round(stroke / h, 4), round(float(a.mean()), 3)])
with open(out / "hands_prints_instances.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh); wr.writerow(["side", "line", "position", "head", "height", "width", "stroke_px", "stroke_ratio", "density"]); wr.writerows(inst)

by_side = collections.defaultdict(list)
for i in inst:
    by_side[i[0]].append(i)
side_rows = []
for s, lst in sorted(by_side.items()):
    hs = np.array([i[4] for i in lst]); ratios = np.array([i[7] for i in lst]); dens = np.array([i[8] for i in lst])
    side_rows.append([s, len(lst), int(np.median(hs)), round(float(np.median(ratios)), 4), round(float(np.percentile(ratios, 75) - np.percentile(ratios, 25)), 4),
                      round(float(np.median(dens)), 3), "measured" if np.median(hs) >= MIN_HEIGHT and len(lst) >= 20 else "too small"])
with open(out / "hands_prints.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh); wr.writerow(["side", "instances", "median_height_px", "stroke_ratio", "stroke_ratio_iqr", "density", "status"]); wr.writerows(side_rows)

# same-object test
med = {r[0]: r[3] for r in side_rows if r[6] == "measured"}
objects = collections.defaultdict(list)
for s in med:
    objects[s[0]].append(s)
same = [(a, b) for lst in objects.values() for a, b in itertools.combinations(lst, 2)]
sides = sorted(med)
all_pairs = list(itertools.combinations(sides, 2))
obs = float(np.mean([abs(med[a] - med[b]) for a, b in same])) if same else float("nan")
rng = np.random.default_rng(7)
null = []
for _ in range(5000):
    perm = dict(zip(sides, rng.permutation([med[s] for s in sides])))
    null.append(np.mean([abs(perm[a] - perm[b]) for a, b in same]))
p = float(np.mean(np.array(null) <= obs)) if same else float("nan")
others = float(np.mean([abs(med[a] - med[b]) for a, b in all_pairs if (a, b) not in same]))

md = ["# Stroke weight on the prints\n",
      f"{len(inst)} locally matched instances on {len(by_side)} sides; {len(med)} sides with glyphs at least {MIN_HEIGHT} px tall on the print and 20 instances.\n",
      "| side | instances | glyph height, px | stroke width over height | IQR | ink density | |", "|---|---|---|---|---|---|---|"]
for r in sorted(side_rows, key=lambda r: -r[3]):
    md.append("| " + " | ".join(str(v) for v in r) + " |")
md.append("\n## Are the two sides of one object alike?\n")
md.append(f"{len(same)} same-object pairs among the measured sides: " + ", ".join(f"{a}-{b}" for a, b in same) + ".")
md.append(f"Mean difference in stroke ratio, same-object pairs: {obs:.4f}; other pairs: {others:.4f}. "
          f"Permutation test, 5000 relabellings: same-object pairs this close or closer in {p:.3f} of them.\n")
(out / "hands_prints.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
