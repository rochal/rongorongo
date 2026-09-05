"""Cut glyph instances from the white-filled prints of the tablets, and compare them with the tracings.

The prints (fetch_photos.py) show the glyphs filled white on the dark wood,
with a bright paper margin around the object. For each side:
  tablet     the object is found as the largest dark region, filled and
             eroded to keep clear of its edge; glyph ink is bright pixels
             inside it
  lines      the inked extent is divided equally by the transliteration's
             line count, each cut refined to the nearest valley of the
             smoothed row profile within a small window
  glyphs     connected components of ink per line, horizontally overlapping
             components merged, aligned to the transliterated units by count
             as in tracings.py, with the same reliability flag
  fidelity   for units on lines reliable in both the print and the tracing,
             the relative width of the print instance against the tracing
             instance, and the descriptor similarity between the two
  planning   glyph width along the line, on the print, for sides with
             enough reliable lines, to set beside section 25

Tahua's prints come in three overlapping parts and are skipped here.

Outputs
  data/photos/instances/<side>/<line>_<k>.png
  out/photo_instances.csv, out/photo_fidelity.csv, out/photos.md
"""
import collections, csv, json, pathlib, re
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

MAX_ADJUST = 0.25
root = pathlib.Path(__file__).resolve().parent.parent
pdir = root / "data" / "photos"
idir = pdir / "instances"
tdir = root / "data" / "tracings" / "instances"
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
SKIP = {"Aa_left", "Aa_center", "Aa_right", "Ab_left", "Ab_center", "Ab_right", "Hv_unretouched", "Sa_rubbing"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def tablet_ink(img):
    dark = ndimage.binary_opening(img < 90, iterations=3)
    lab, n = ndimage.label(dark)
    if n == 0:
        return None
    sizes = ndimage.sum(dark, lab, range(1, n + 1))
    big = lab == (int(np.argmax(sizes)) + 1)
    tablet = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_closing(big, iterations=15)), iterations=12)
    return (img > 150) & tablet


def line_cuts(ink, nlines):
    rows = ndimage.uniform_filter1d(ink.sum(axis=1).astype(float), 5)
    ys = np.where(rows > rows.max() * 0.08)[0]
    if len(ys) == 0:
        return None
    y_top, y_bot = int(ys.min()), int(ys.max())
    pitch = (y_bot - y_top) / nlines
    cuts = [y_top]
    for k in range(1, nlines):
        c = int(y_top + k * pitch); lo, hi = max(y_top, c - 12), min(y_bot, c + 12)
        cuts.append(lo + int(np.argmin(rows[lo:hi])))
    cuts.append(y_bot)
    return cuts


def blobs(line):
    lab, n = ndimage.label(line, structure=np.ones((3, 3)))
    boxes = []
    for sl in ndimage.find_objects(lab):
        if line[sl].sum() < 15:
            continue
        boxes.append([sl[1].start, sl[1].stop, sl[0].start, sl[0].stop])
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] < merged[-1][1] - 1:
            m = merged[-1]; m[1] = max(m[1], b[1]); m[2] = min(m[2], b[2]); m[3] = max(m[3], b[3])
        else:
            merged.append(b)
    return merged


def align(boxes, n_units, line):
    boxes = [list(b) for b in boxes]
    if not boxes:
        return [], n_units
    changes = 0
    while len(boxes) > n_units and len(boxes) > 1:
        gaps = [boxes[i + 1][0] - boxes[i][1] for i in range(len(boxes) - 1)]
        i = int(np.argmin(gaps)); b1, b2 = boxes[i], boxes[i + 1]
        boxes[i:i + 2] = [[b1[0], b2[1], min(b1[2], b2[2]), max(b1[3], b2[3])]]; changes += 1
    while len(boxes) < n_units:
        widths = [b[1] - b[0] for b in boxes]
        i = int(np.argmax(widths)); b = boxes[i]
        if b[1] - b[0] < 6:
            break
        col = line[b[2]:b[3], b[0]:b[1]].sum(axis=0)
        cut = int(np.argmin(col[2:-2])) + 2 + b[0]
        boxes[i:i + 1] = [[b[0], cut, b[2], b[3]], [cut, b[1], b[2], b[3]]]; changes += 1
    return boxes, changes


def descriptor(bits):
    ys, xs = np.where(bits)
    if len(ys) < 4:
        return None
    a = bits[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape; side = max(h, w)
    canvas = np.zeros((side, side), bool)
    canvas[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = a
    im = Image.fromarray((canvas * 255).astype("uint8")).resize((32, 32), Image.LANCZOS)
    sil = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), dtype=float); sil /= np.linalg.norm(sil) + 1e-9
    g = np.asarray(im, dtype=float); gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) + np.pi) % np.pi
    hog = []
    for cy in range(4):
        for cx in range(4):
            sl = (slice(cy * 8, (cy + 1) * 8), slice(cx * 8, (cx + 1) * 8))
            hist, _ = np.histogram(ang[sl], bins=8, range=(0, np.pi), weights=mag[sl]); hog.extend(hist)
    hog = np.array(hog); hog /= np.linalg.norm(hog) + 1e-9
    return np.concatenate([sil.ravel() * 0.5, hog * 0.5]), h / w


tr_rows = {(r["side"], r["line"], int(r["position"])): r for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8"))}

rows, report, fidelity = [], [], []
for f in sorted(pdir.glob("*.*")):
    if f.suffix.lower() not in (".jpg", ".png") or f.stem.startswith("_") or f.stem in SKIP:
        continue
    side = f.stem
    lids = sorted((k for k in corpus if k.startswith(side)), key=lambda k: int(k[2:]))
    if not lids:
        continue
    img = np.array(Image.open(f).convert("L")).astype(float)
    ink = tablet_ink(img)
    if ink is None:
        report.append((side, "no tablet found")); continue
    cuts = line_cuts(ink, len(lids))
    if cuts is None:
        report.append((side, "no ink found")); continue
    (idir / side).mkdir(parents=True, exist_ok=True)
    good = 0
    for lid, (y0, y1) in zip(lids, zip(cuts, cuts[1:])):
        units = [u for u in corpus[lid] if not head(u).startswith("(") and head(u) not in ("000", "999")]
        line = ink[y0:y1]
        if line.shape[0] < 4 or not line.any():
            continue
        bx = blobs(line)
        raw_count = len(bx)
        bx, changes = align(bx, len(units), line)
        reliable = changes <= MAX_ADJUST * max(1, len(units)) and len(bx) == len(units)
        good += reliable
        widths = [b[1] - b[0] for b in bx]
        med = np.median(widths) if widths else 1
        for k, (u, b) in enumerate(zip(units, bx)):
            x0, x1, yy0, yy1 = b
            crop = line[yy0:yy1, x0:x1]
            Image.fromarray((crop * 255).astype("uint8")).save(idir / side / f"{lid}_{k:03d}.png")
            rows.append([side, lid, k, u, head(u), x0, x1, y0 + yy0, y0 + yy1, x1 - x0, yy1 - yy0, int(crop.sum()),
                         "reliable" if reliable else "unreliable"])
            tr = tr_rows.get((side, lid, k))
            if reliable and tr and tr["line_quality"] == "reliable":
                tp = tdir / side / f"{lid}_{k:03d}.png"
                if tp.exists():
                    d1 = descriptor(crop); d2 = descriptor(np.asarray(Image.open(tp).convert("L")) < 128)
                    if d1 and d2:
                        s = float(d1[0] @ d2[0]) * np.sqrt(min(d1[1], d2[1]) / max(d1[1], d2[1]))
                        fidelity.append([side, lid, k, head(u), (x1 - x0) / med, float(tr["width"]), s])
    report.append((side, f"{good}/{len(lids)} lines aligned within tolerance; raw blobs on last line {raw_count} for {len(units)} units"))

with open(out / "photo_instances.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side", "line", "position", "unit", "head", "x0", "x1", "y0", "y1", "width", "height", "ink", "line_quality"]); w.writerows(rows)
with open(out / "photo_fidelity.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side", "line", "position", "head", "print_rel_width", "tracing_width", "similarity"]); w.writerows(fidelity)

# relative widths need the tracing's line medians too
tr_med = collections.defaultdict(list)
for (s, lid, k), r in tr_rows.items():
    tr_med[(s, lid)].append(float(r["width"]))
tr_med = {k: np.median(v) for k, v in tr_med.items()}
pairs = []
for s, lid, k, h, pw, tw, sim in fidelity:
    pairs.append((pw, tw / tr_med[(s, lid)], sim))
if pairs:
    pw = np.array([p[0] for p in pairs]); tw = np.array([p[1] for p in pairs]); sims = np.array([p[2] for p in pairs])
    corr = float(np.corrcoef(pw, tw)[0, 1])
else:
    corr, sims = float("nan"), np.array([])

# planning on the prints
plan = collections.defaultdict(list)
by_line = collections.defaultdict(list)
for r in rows:
    if r[-1] == "reliable":
        by_line[(r[0], r[1])].append(r)
for (s, lid), lst in by_line.items():
    lst.sort(key=lambda r: r[2])
    if len(lst) < 8:
        continue
    w = np.array([r[9] for r in lst], float); pos = np.linspace(0, 1, len(lst))
    plan[s].append((pos, w / np.median(w)))
plan_rows = []
for s, lst in plan.items():
    pos = np.concatenate([p for p, _ in lst]); w = np.concatenate([x for _, x in lst])
    plan_rows.append((s, len(lst), float(np.polyfit(pos, w, 1)[0])))

n_rel = sum(1 for r in rows if r[-1] == "reliable")
md = ["# Glyph instances from the white-filled prints\n",
      f"{len(rows)} instances on {len(report)} sides; {n_rel} on lines aligned within tolerance.\n",
      "| side | result |\n|---|---|"]
for s, res in report:
    md.append(f"| {s} | {res} |")
md.append(f"\n## Fidelity of the tracings to the prints\n")
md.append(f"{len(pairs)} glyphs on lines reliable in both sources. Correlation of relative glyph width, print against tracing: {corr:.2f}. "
          f"Descriptor similarity print-to-tracing of the same glyph: median {np.median(sims) if len(sims) else float('nan'):.3f} "
          f"(instances of different signs in section 25 scored about 0.21, of the same sign 0.19 to 0.31).\n")
md.append("## Glyph width along the line, on the prints\n")
md.append("| side | reliable lines | width slope |\n|---|---|---|")
for s, nl, sl in sorted(plan_rows, key=lambda r: r[2]):
    md.append(f"| {s} | {nl} | {sl:+.3f} |")
(out / "photos.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
