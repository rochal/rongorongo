"""Cut Barthel's tracings into lines and glyph instances, aligned to the transliteration.

For every side with a tracing in data/tracings/:
  lines      horizontal ink bands, top to bottom, matched to the CEIPP line
             ids in order (Barthel drew line 1 at the top; a side whose band
             count differs from its line count is reported and skipped)
  glyphs     within a line, connected components of ink; components that
             overlap in their horizontal extent are merged (stacked or fused
             parts of one compound); the result is a left-to-right sequence
             of blobs
  alignment  the blobs of a line are aligned to its transliterated units by
             count: when the counts agree the alignment is one to one; when
             they differ, the narrowest gaps between neighbouring blobs are
             merged (too many blobs) or the widest blobs are split at their
             thinnest column (too few) until they agree. Lines where this
             needs more than MAX_ADJUST changes are marked unreliable.

Outputs
  data/tracings/instances/<side>/<line>_<k>.png   one image per instance
  out/glyph_instances.csv   side, line, position, unit, head sign, box,
                            width, height, ink, reliability of the line
  out/tracings.md           per-side report of line and blob counts
"""
import collections, csv, json, pathlib, re
import numpy as np
from PIL import Image
from scipy import ndimage

MAX_ADJUST = 0.25          # share of units a line may need adjusting before it is marked unreliable
MIN_WIDTH = 5              # a split may not leave a piece narrower than this, in tracing pixels
SLIVER_GAP = 3             # a component narrower than MIN_WIDTH joins its neighbour across a gap up to this
root = pathlib.Path(__file__).resolve().parent.parent
tdir = root / "data" / "tracings"
idir = tdir / "instances"
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def bands(a):
    ink = (a < 128).sum(axis=1)
    thr = max(2, ink.max() * 0.04)
    res, inb = [], False
    for y, v in enumerate(ink):
        if v > thr and not inb:
            start, inb = y, True
        elif v <= thr and inb:
            if y - start > 6:
                res.append((start, y))
            inb = False
    if inb:
        res.append((start, len(ink)))
    return res


def blobs(line_img):
    """left-to-right boxes of ink blobs, horizontally overlapping components merged"""
    a = line_img < 128
    lab, n = ndimage.label(a, structure=np.ones((3, 3)))
    boxes = []
    for sl in ndimage.find_objects(lab):
        ys, xs = sl
        if (a[sl].sum()) < 4:
            continue
        boxes.append([xs.start, xs.stop, ys.start, ys.stop])
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] < merged[-1][1] - 1:          # horizontal overlap with the previous blob
            m = merged[-1]
            m[1] = max(m[1], b[1]); m[2] = min(m[2], b[2]); m[3] = max(m[3], b[3])
        else:
            merged.append(b)
    # Barthel draws a plain stroke as two parallel lines; where their ends are open they label as two
    # components a pixel or two apart. A component narrower than a stroke is joined to the neighbour
    # across the smaller gap, if that gap is at most SLIVER_GAP
    changed = True
    while changed and len(merged) > 1:
        changed = False
        for i, b in enumerate(merged):
            if b[1] - b[0] >= MIN_WIDTH:
                continue
            left = (b[0] - merged[i - 1][1]) if i > 0 else 10 ** 6
            right = (merged[i + 1][0] - b[1]) if i + 1 < len(merged) else 10 ** 6
            j = i - 1 if left <= right else i + 1
            if min(left, right) <= SLIVER_GAP:
                m = merged[j]
                m[0] = min(m[0], b[0]); m[1] = max(m[1], b[1]); m[2] = min(m[2], b[2]); m[3] = max(m[3], b[3])
                del merged[i]; changed = True
                break
    return merged


def align(boxes, n_units, a):
    """merge or split blobs until their number equals the unit count; returns boxes and number of changes"""
    boxes = [list(b) for b in boxes]
    changes = 0
    while len(boxes) > n_units and len(boxes) > 1:
        gaps = [boxes[i + 1][0] - boxes[i][1] for i in range(len(boxes) - 1)]
        i = int(np.argmin(gaps))
        b1, b2 = boxes[i], boxes[i + 1]
        boxes[i:i + 2] = [[b1[0], b2[1], min(b1[2], b2[2]), max(b1[3], b2[3])]]
        changes += 1
    tried = set()
    while len(boxes) < n_units:
        # split the widest box that can still be split into two pieces of at least MIN_WIDTH, at its emptiest
        # column; never at the edge, which is what produced two-pixel slivers of a single stroke
        order = sorted(range(len(boxes)), key=lambda i: -(boxes[i][1] - boxes[i][0]))
        i = next((i for i in order if boxes[i][1] - boxes[i][0] >= 2 * MIN_WIDTH + 1 and tuple(boxes[i]) not in tried), None)
        if i is None:
            break
        b = boxes[i]
        col = (a[b[2]:b[3], b[0]:b[1]] < 128).sum(axis=0)
        inner = col[MIN_WIDTH:-MIN_WIDTH]
        cut = int(np.argmin(inner)) + MIN_WIDTH + b[0]
        tried.add(tuple(b))
        boxes[i:i + 1] = [[b[0], cut, b[2], b[3]], [cut, b[1], b[2], b[3]]]
        changes += 1
    return boxes, changes


hand = {}
for hf in (root / "data" / "boxes" / "tracing").glob("*.json"):
    hj = json.load(open(hf, encoding="utf-8"))
    hand[hj["side"]] = {}
    for b in hj["boxes"]:
        hand[hj["side"]].setdefault(b["line"], []).append(b)
    for lid in hand[hj["side"]]:
        hand[hj["side"]][lid].sort(key=lambda b: b["position"])

rows = []
report = []
for f in sorted(tdir.glob("*.*")):
    if f.suffix.lower() not in (".png", ".jpg") or f.stem.startswith("_"):
        continue
    side = f.stem
    key = "Ia" if side == "I" else side
    lids = sorted((k for k in corpus if k.startswith(key)), key=lambda k: int(k[2:]))
    img = np.array(Image.open(f).convert("L"))
    bs = bands(img)
    if len(bs) != len(lids):
        report.append((side, len(bs), len(lids), "skipped: band count differs from line count"))
        continue
    (idir / side).mkdir(parents=True, exist_ok=True)
    good = total = 0
    for lid, (y0, y1) in zip(lids, bs):
        units = [u for u in corpus[lid] if not head(u).startswith("(") and head(u) not in ("000", "999")]
        line = img[y0:y1]
        bx = blobs(line)
        bx, changes = align(bx, len(units), line)
        reliable = changes <= MAX_ADJUST * max(1, len(units)) and len(bx) == len(units)
        source = "auto"
        # hand-drawn boxes on the tracing (box_editor.py --source tracing) replace the automatic ones on a
        # line whose box count matches its unit count
        if lid in hand.get(side, {}) and len(hand[side][lid]) == len(units):
            bx = [[b["x0"], b["x1"], b["y0"] - y0, b["y1"] - y0] for b in hand[side][lid]]
            reliable, source = True, "manual"
        total += 1
        good += reliable
        for k, (u, b) in enumerate(zip(units, bx)):
            x0, x1, yy0, yy1 = b
            yy0, yy1 = max(0, yy0), min(line.shape[0], yy1)
            crop = line[yy0:yy1, x0:x1]
            Image.fromarray(crop).save(idir / side / f"{lid}_{k:03d}.png")
            rows.append([side, lid, k, u, head(u), x0, x1, y0 + yy0, y0 + yy1, x1 - x0, yy1 - yy0,
                         int((crop < 128).sum()), "reliable" if reliable else "unreliable", source])
    report.append((side, len(bs), len(lids), f"{good}/{total} lines aligned within tolerance"))

with open(out / "glyph_instances.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side", "line", "position", "unit", "head", "x0", "x1", "y0", "y1", "width", "height", "ink", "line_quality", "source"])
    w.writerows(rows)

n_rel = sum(1 for r in rows if r[12] == "reliable")
md = ["# Glyph instances cut from Barthel's tracings\n",
      f"{len(rows)} instances from {len([r for r in report if 'aligned' in r[3]])} sides; {n_rel} on lines aligned within tolerance.\n",
      "| side | ink bands | transliterated lines | result |\n|---|---|---|---|"]
for side, nb, nl, res in report:
    md.append(f"| {side} | {nb} | {nl} | {res} |")
(out / "tracings.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
