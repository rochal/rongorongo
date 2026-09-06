"""What the glyph instances show: variation, hands, and line planning.

Uses out/glyph_instances.csv and the instance images from tracings.py,
restricted to lines aligned within tolerance.

  variation   for each head sign with at least MIN_INST reliable instances,
              the mean pairwise shape similarity of its instances (the same
              descriptor as sign_shapes.py: blurred silhouette plus gradient
              orientation histograms), against the similarity between
              instances of different signs, so a sign's consistency as carved
              can be ranked
  hands       for each pair of sides sharing enough signs, the mean
              similarity of same-sign instances across the two sides against
              the mean within each side. Sides carved by one hand should show
              no cross-side penalty; a heatmap of the penalty groups sides.
              The copy families (H, P, Q; G, K) are the natural test: copies
              of one text by different hands should be as far apart as any
              two sides.
  planning    within each reliable line, instance width relative to the
              line's median width against relative position along the line,
              pooled per side. A negative slope means glyphs narrow toward
              the line end, the signature of fitting text into a fixed space.

Outputs (out/): tracings_variation.csv, tracings_hands.csv,
tracings_planning.csv, tracings_analysis.md
"""
import argparse, collections, csv, itertools, math, pathlib
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("--source", choices=["tracings", "photos"], default="tracings",
                help="photos: the glyphs cut from the prints by register.py, restricted to locally matched ones; outputs are prefixed photos_")
args = ap.parse_args()

MIN_INST = 12
N = 32
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
if args.source == "tracings":
    idir = root / "data" / "tracings" / "instances"
    rows = [r for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8")) if r["line_quality"] == "reliable"]
    prefix = "tracings_"
else:
    idir = root / "data" / "photos" / "instances"
    rows = []
    for r in csv.DictReader(open(out / "photo_instances.csv", encoding="utf-8")):
        if float(r["local_score"]) >= 0.2 and int(r["print_ink_width"]) > 0:
            r["width"] = r["print_ink_width"]; r["height"] = str(int(r["y1"]) - int(r["y0"]))
            rows.append(r)
    prefix = "photos_"


def descriptor(path, thicken=0):
    im = Image.open(path).convert("L")
    a = np.asarray(im) < 128
    if thicken:
        a = ndimage.binary_dilation(a, iterations=thicken)
    ys, xs = np.where(a)
    if len(ys) < 4:
        return None
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape
    side = max(h, w)
    canvas = np.zeros((side, side), bool)
    canvas[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = a
    im = Image.fromarray((canvas * 255).astype("uint8")).resize((N, N), Image.LANCZOS)
    sil = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), dtype=float)
    sil /= np.linalg.norm(sil) + 1e-9
    g = np.asarray(im, dtype=float)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) + np.pi) % np.pi
    cells, hog = 4, []
    for cy in range(cells):
        for cx in range(cells):
            sl = (slice(cy * N // cells, (cy + 1) * N // cells), slice(cx * N // cells, (cx + 1) * N // cells))
            hist, _ = np.histogram(ang[sl], bins=8, range=(0, np.pi), weights=mag[sl])
            hog.extend(hist)
    hog = np.array(hog); hog /= np.linalg.norm(hog) + 1e-9
    return np.concatenate([sil.ravel() * 0.5, hog * 0.5]), h / w


feats = {}
for r in rows:
    p = idir / r["side"] / f"{r['line']}_{int(r['position']):03d}.png"
    d = descriptor(p)
    if d is not None:
        feats[(r["side"], r["line"], int(r["position"]))] = d
by_sign = collections.defaultdict(list)
for r in rows:
    k = (r["side"], r["line"], int(r["position"]))
    if k in feats:
        by_sign[r["head"]].append((r["side"], feats[k][0], feats[k][1]))


def sim(a, b):
    v = float(a[1] @ b[1])
    ratio = min(a[2], b[2]) / max(a[2], b[2])
    return v * math.sqrt(ratio)


# variation per sign
rng = np.random.default_rng(3)
var_rows = []
all_inst = [(s, f, asp) for s, lst in by_sign.items() for (_, f, asp) in lst]
between = []
for _ in range(4000):
    i, j = rng.integers(0, len(all_inst), 2)
    if all_inst[i][0] != all_inst[j][0]:
        between.append(sim((None, all_inst[i][1], all_inst[i][2]), (None, all_inst[j][1], all_inst[j][2])))
between_mean = float(np.mean(between))
for s, lst in by_sign.items():
    if len(lst) < MIN_INST:
        continue
    pairs = list(itertools.combinations(range(len(lst)), 2))
    if len(pairs) > 600:
        pairs = [pairs[i] for i in rng.choice(len(pairs), 600, replace=False)]
    within = [sim(lst[i], lst[j]) for i, j in pairs]
    same_side = [sim(lst[i], lst[j]) for i, j in pairs if lst[i][0] == lst[j][0]]
    cross_side = [sim(lst[i], lst[j]) for i, j in pairs if lst[i][0] != lst[j][0]]
    var_rows.append({"sign": s, "instances": len(lst), "sides": len({x[0] for x in lst}), "within": float(np.mean(within)),
                     "same_side": float(np.mean(same_side)) if same_side else float("nan"),
                     "cross_side": float(np.mean(cross_side)) if cross_side else float("nan")})
var_rows.sort(key=lambda r: -r["within"])
with open(out / (prefix + "variation.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(var_rows[0].keys()))
    w.writeheader()
    for r in var_rows:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})

# hands: cross-side penalty per side pair
sides = sorted({r["side"] for r in rows})
pen = {}
for a, b in itertools.combinations(sides, 2):
    diffs, n_signs = [], 0
    for s, lst in by_sign.items():
        A = [x for x in lst if x[0] == a]; B = [x for x in lst if x[0] == b]
        if len(A) >= 3 and len(B) >= 3:
            n_signs += 1
            within_a = np.mean([sim(x, y) for x, y in itertools.combinations(A[:12], 2)])
            within_b = np.mean([sim(x, y) for x, y in itertools.combinations(B[:12], 2)])
            cross = np.mean([sim(x, y) for x in A[:12] for y in B[:12]])
            diffs.append((within_a + within_b) / 2 - cross)
    if n_signs >= 4:
        pen[(a, b)] = (float(np.mean(diffs)), n_signs)
# positive control: could the test see a hand if there were one? Side B's instances are re-read with
# every stroke thickened by one pixel, a smaller change than two carvers' tools would make, and the
# penalty recomputed. If the control penalties stand clear of the real ones, the real near-zero is a finding.
feats_thick = {}
for r in rows:
    p = idir / r["side"] / f"{r['line']}_{int(r['position']):03d}.png"
    d = descriptor(p, thicken=1)
    if d is not None:
        feats_thick[(r["side"], r["line"], int(r["position"]))] = d
by_sign_thick = collections.defaultdict(list)
for r in rows:
    k = (r["side"], r["line"], int(r["position"]))
    if k in feats_thick:
        by_sign_thick[r["head"]].append((r["side"], feats_thick[k][0], feats_thick[k][1]))
pen_ctl = {}
for a, b in pen:
    diffs = []
    for s, lst in by_sign.items():
        A = [x for x in lst if x[0] == a]; B = [x for x in by_sign_thick[s] if x[0] == b]
        if len(A) >= 3 and len(B) >= 3:
            within_a = np.mean([sim(x, y) for x, y in itertools.combinations(A[:12], 2)])
            within_b = np.mean([sim(x, y) for x, y in itertools.combinations(B[:12], 2)])
            cross = np.mean([sim(x, y) for x in A[:12] for y in B[:12]])
            diffs.append((within_a + within_b) / 2 - cross)
    pen_ctl[(a, b)] = float(np.mean(diffs)) if diffs else float("nan")
with open(out / (prefix + "hands.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side_a", "side_b", "shared_signs", "cross_side_penalty", "control_penalty_thickened"])
    for (a, b), (d, n) in sorted(pen.items(), key=lambda kv: kv[1][0]):
        w.writerow([a, b, n, f"{d:.4f}", f"{pen_ctl[(a, b)]:.4f}"])

# planning: width against position along the line
plan = collections.defaultdict(list)
line_ids = collections.defaultdict(list)
by_line = collections.defaultdict(list)
for r in rows:
    by_line[(r["side"], r["line"])].append(r)
for (side, lid), lst in by_line.items():
    lst.sort(key=lambda r: int(r["position"]))
    widths = np.array([int(r["width"]) for r in lst], float)
    heights = np.array([int(r["height"]) for r in lst], float)
    if len(lst) < 8:
        continue
    pos = np.linspace(0, 1, len(lst))
    plan[side].append((pos, widths / np.median(widths), heights / np.median(heights)))
    line_ids[side].append(lid)
plan_rows = []
for side, lst in plan.items():
    pos = np.concatenate([p for p, _, _ in lst]); w_ = np.concatenate([w for _, w, _ in lst]); h_ = np.concatenate([h for _, _, h in lst])
    sw = np.polyfit(pos, w_, 1)[0]; sh = np.polyfit(pos, h_, 1)[0]
    first = w_[pos < 0.2].mean(); last = w_[pos > 0.8].mean()
    # the same slope with the two glyphs at each end of every line dropped, in case
    # line-edge segmentation inflates the first or last box
    inner = np.concatenate([np.r_[False, False, np.ones(len(p) - 4, bool), False, False] if len(p) > 6 else np.zeros(len(p), bool) for p, _, _ in lst])
    sw_inner = np.polyfit(pos[inner], w_[inner], 1)[0] if inner.sum() > 10 else float("nan")
    # by line parity: the tracings show every line in reading orientation, so a
    # carver squeezing toward the physical end of the tablet would give opposite
    # slopes on alternate lines, a carver squeezing toward the end of the text the same sign
    def slope_for(parity):
        sel = [(p, w) for (p, w, _), lid in zip(lst, line_ids[side]) if int(lid[2:]) % 2 == parity]
        if len(sel) < 2:
            return float("nan")
        pp = np.concatenate([p for p, _ in sel]); ww = np.concatenate([w for _, w in sel])
        return np.polyfit(pp, ww, 1)[0]
    plan_rows.append({"side": side, "lines": len(lst), "instances": len(pos), "width_slope": sw, "width_slope_inner": sw_inner,
                      "slope_odd_lines": slope_for(1), "slope_even_lines": slope_for(0),
                      "height_slope": sh, "width_first_fifth": first, "width_last_fifth": last})
with open(out / (prefix + "planning.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(plan_rows[0].keys()))
    w.writeheader()
    for r in plan_rows:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})

md = ["# The glyphs as carved\n",
      f"{len(rows)} reliable instances on {len(sides)} sides; {len(var_rows)} signs with at least {MIN_INST} instances. "
      f"Mean similarity between instances of different signs: {between_mean:.3f}.\n",
      "## Consistency of each sign as carved\n",
      "| sign | instances | sides | within-sign similarity | same side | across sides |\n|---|---|---|---|---|---|"]
for r in var_rows[:25]:
    md.append(f"| {r['sign']} | {r['instances']} | {r['sides']} | {r['within']:.3f} | {r['same_side']:.3f} | {r['cross_side']:.3f} |")
md.append("\n... least consistent:\n")
md.append("| sign | instances | sides | within-sign similarity | same side | across sides |\n|---|---|---|---|---|---|")
for r in var_rows[-8:]:
    md.append(f"| {r['sign']} | {r['instances']} | {r['sides']} | {r['within']:.3f} | {r['same_side']:.3f} | {r['cross_side']:.3f} |")
md.append("\n## Hands: cross-side penalty, sides that share at least four signs\n")
md.append("Penalty = mean over shared signs of (within-side similarity minus cross-side similarity). Near zero: the two sides draw the same sign the same way.\n")
md.append("| side A | side B | shared signs | penalty | control: B thickened 1 px |\n|---|---|---|---|---|")
for (a, b), (d, n) in sorted(pen.items(), key=lambda kv: kv[1][0]):
    md.append(f"| {a} | {b} | {n} | {d:+.3f} | {pen_ctl[(a, b)]:+.3f} |")
md.append("\n## Planning: glyph width along the line\n")
md.append("| side | lines | instances | width slope | same, line ends dropped | odd lines | even lines | height slope | width, first fifth | width, last fifth |\n|---|---|---|---|---|---|---|---|---|---|")
for r in sorted(plan_rows, key=lambda r: r["width_slope"]):
    md.append(f"| {r['side']} | {r['lines']} | {r['instances']} | {r['width_slope']:+.3f} | {r['width_slope_inner']:+.3f} | "
              f"{r['slope_odd_lines']:+.3f} | {r['slope_even_lines']:+.3f} | {r['height_slope']:+.3f} | "
              f"{r['width_first_fifth']:.2f} | {r['width_last_fifth']:.2f} |")
(out / (prefix + "analysis.md")).write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:8]))
print(f"pairs: {len(pen)}, sides with planning data: {len(plan_rows)}")
