"""Register Barthel's tracings to the white-filled prints, line by line, and cut the prints into glyphs.

The tracing of a side is not a picture of the tablet: Barthel drew every
line upright and left to right, while on the wood alternate lines are
upside down (reverse boustrophedon), the object is curved, and Barthel's
spacing is not the carver's. So no single transform maps tracing to print,
and even one line cannot be matched as a rigid strip. The registration
works from short chunks upward:

  ink         the print is reduced to an ink map by local contrast, since
              the lighting is uneven: bright marks inside the object (the
              white-filled prints) or dark marks anywhere (the rubbings and
              the prints with dark glyphs); the polarity that wins the vote
              below is kept. The object is what is not paper margin.
  scale       the print is rescaled so its glyphs are the size of the
              tracing's, from the ratio of the print's inked width to the
              tracing's line width, refined by the vote
  chunks      every run of CHUNK glyphs of a reliable tracing line, filled
              (Barthel drew outlines, the prints are solid) and blurred, is
              correlated over the whole print in both orientations, and its
              best few peaks are kept as candidates. A chunk alone is
              ambiguous: the glyph field is full of similar shapes
  vote        all candidates of all lines vote for a layout of the side:
              a first line position, a line pitch, a direction (line 1 at
              the top or the bottom) and a parity (which lines are upside
              down). The layout that collects the most candidate score wins,
              and only candidates consistent with it survive. Reverse
              boustrophedon is thus built in, and the vote is reported so
              that a side where it is weak can be doubted
  lines       within each line the surviving chunks give a linear map from
              tracing x to print x (Barthel's stretch) and a quadratic map
              of y along the line (the curvature of the wood)
  glyphs      each glyph's box, with neighbours as context, is matched again
              in a small window around its predicted place, then cut from
              the print at full resolution, turned upright, and binarised
              with the print's polarity so that it can be compared with the
              tracing instance by the same descriptor
  fidelity    width of the print instance, measured from its own ink inside
              a padded box, against the tracing instance's width, relative
              to line medians; and descriptor similarity of the two

Only lines whose tracing alignment was reliable (tracings.py) are used.
Tahua's three-part prints and the unretouched and rubbing images are skipped.

Outputs
  data/photos/instances/<side>/<line>_<k>.png     binary glyph from the print
  out/register_lines.csv     side, line, orientation, chunks placed, fit
  out/register_sides.csv     side, scale, polarity, vote strength, layout
  out/photo_instances.csv    side, line, position, unit, head, box on the
                             print (full resolution), print ink width,
                             tracing width, local score
  out/photo_fidelity.csv     per-instance width and similarity comparison
  out/register.md            per-side report
  docs/img/registration_check.png   the glyph boxes drawn on one print
  docs/img/registration_pairs.png   tracing and print of the same glyphs
"""
import argparse, collections, csv, json, pathlib, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from skimage.feature import match_template, peak_local_max
from skimage.filters import gaussian
from skimage.transform import rescale

ap = argparse.ArgumentParser()
ap.add_argument("--sides", nargs="*", help="restrict to these sides")
ap.add_argument("--check", default="Ev", help="side for the check images")
ap.add_argument("--ignore-hand", action="store_true", help="place every box automatically even where data/boxes has corrections")
ap.add_argument("--tag", default="", help="write the tables and instances under this suffix instead of the main ones, without merging")
args = ap.parse_args()

root = pathlib.Path(__file__).resolve().parent.parent
pdir = root / "data" / "photos"
tdir = root / "data" / "tracings"
idir = pdir / ("instances" + (f"_{args.tag}" if args.tag else ""))
TAG = f"_{args.tag}" if args.tag else ""
out = root / "out"
img_dir = root / "docs" / "img"
SKIP = {"Aa_left", "Aa_center", "Aa_right", "Ab_left", "Ab_center", "Ab_right", "Hv_unretouched", "Sa_rubbing"}
CHUNK, STRIDE = 6, 3
PEAKS = 12            # candidates kept per chunk and orientation
PEAK_MIN = 0.22
SIGMA = 1.5
Y_TOL = 0.3           # share of the line pitch a candidate may be off the predicted line
X_TOL = 14            # px, inlier tolerance of the x map
LOCAL_WIN = 10        # search half-window around the predicted glyph place
LOCAL_MIN = 0.2
PAD = 0.3             # padding of the box, as a share of its width, when measuring the print's own ink extent
VOTE_MIN = 0.35       # a side whose vote is weaker than this share of its candidate mass is not trusted


def load_tracing_rows():
    rows = collections.defaultdict(list)
    for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8")):
        if r["line_quality"] == "reliable":
            rows[r["side"]].append(r)
    return rows


def tracing_ink(side):
    f = next(tdir.glob(side + ".*"))
    a = np.asarray(Image.open(f).convert("L"), dtype=float) / 255
    return ndimage.binary_fill_holes(a < 0.5).astype(float)


def print_gray(side):
    f = next(p for p in pdir.glob(side + ".*") if p.suffix.lower() in (".jpg", ".png"))
    return np.asarray(Image.open(f).convert("L"), dtype=float) / 255


def object_mask(g):
    """What is not the bright paper margin touching the border."""
    paper = ndimage.binary_opening(g > 0.8, iterations=3)
    lab, n = ndimage.label(paper)
    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    border.discard(0)
    margin = np.isin(lab, list(border)) if border else np.zeros_like(g, bool)
    return ndimage.binary_erosion(ndimage.binary_fill_holes(~ndimage.binary_dilation(margin, iterations=3)), iterations=4)


def ink_maps(g, sigma_bg=10, delta=0.10):
    """Two candidate ink maps by local contrast: bright marks inside the object, dark marks anywhere."""
    bg = gaussian(g, sigma_bg, preserve_range=True)
    return {"bright": ((g - bg) > delta) & object_mask(g), "dark": (g - bg) < -delta}


def soft(a):
    return gaussian(a.astype(float), SIGMA, preserve_range=True)


def strip(ink, rows, margin=3):
    x0 = max(0, min(int(r["x0"]) for r in rows) - margin); x1 = min(ink.shape[1], max(int(r["x1"]) for r in rows) + margin)
    y0 = max(0, min(int(r["y0"]) for r in rows) - margin); y1 = min(ink.shape[0], max(int(r["y1"]) for r in rows) + margin)
    return ink[y0:y1, x0:x1], (x0, y0)


def candidates(Ms, tm, x0, x1):
    """Best peaks of a chunk template over the print, both orientations; returns (score, yc, xc, flipped) with centres."""
    t = soft(tm[:, x0:x1])
    res = []
    if t.shape[0] >= Ms.shape[0] or t.shape[1] >= Ms.shape[1]:
        return res
    for fl, tt in ((False, t), (True, t[::-1, ::-1])):
        c = match_template(Ms, tt)
        for p in peak_local_max(c, min_distance=6, threshold_abs=PEAK_MIN, num_peaks=PEAKS):
            res.append((float(c[tuple(p)]), p[0] + t.shape[0] / 2, p[1] + t.shape[1] / 2, fl))
    return res


def line_number(lid):
    return int(re.sub(r"\D", "", lid[2:]) or 0)


def descriptor(bits, N=32):
    ys, xs = np.where(bits)
    if len(ys) < 4:
        return None
    a = bits[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape; side = max(h, w)
    canvas = np.zeros((side, side), bool)
    canvas[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = a
    im = Image.fromarray((canvas * 255).astype("uint8")).resize((N, N), Image.LANCZOS)
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


def similarity(d1, d2):
    return float(d1[0] @ d2[0]) * np.sqrt(min(d1[1], d2[1]) / max(d1[1], d2[1]))


def own_ink(bits, x_in0, x_in1, strict=True):
    """Keep the ink components whose centre lies within the unpadded box, dropping specks, neighbours' fragments,
    and pieces of the adjacent lines: a component that touches the crop's top or bottom edge with its centre in the
    outer sixth of the height is an intruder from the line above or below, unless it is the largest component.

    Returns the cleaned crop and the horizontal extent of what is kept."""
    lab, n = ndimage.label(bits, structure=np.ones((3, 3)))
    if n == 0:
        return bits, 0
    sizes = ndimage.sum(bits, lab, range(1, n + 1))
    cx = ndimage.center_of_mass(bits, lab, range(1, n + 1))
    hgt = bits.shape[0]
    top_row, bot_row = set(lab[0]), set(lab[-1])
    keep = np.zeros(n + 1, bool)
    for i, (sz, (yy, xx)) in enumerate(zip(sizes, cx), 1):
        keep[i] = sz >= max(6, 0.02 * sizes.max()) and x_in0 <= xx < x_in1
        if strict and keep[i] and sz < sizes.max():
            if (i in top_row and yy < hgt / 6) or (i in bot_row and yy > 5 * hgt / 6):
                keep[i] = False
    clean = keep[lab]
    cols = np.where(clean.any(axis=0))[0]
    return clean, (int(cols.max() - cols.min() + 1) if len(cols) else 0)


def vote(cands, pitch0, height):
    """Choose first-line y, pitch, direction and parity maximising the candidate score collected across lines.

    cands: {line_number: [(score, yc, xc, flipped), ...]}. Returns (strength, y0, pitch, direction, parity, total)."""
    ks = sorted(cands)
    total = sum(max(s for s, *_ in cands[k]) for k in ks if cands[k])
    best = (0, 0, pitch0[0], 1, 0)
    # the whole plausible range of pitches, from the glyph height to three times it, so that a
    # doubled pitch (every second line) from the autocorrelation prior cannot mislead the vote
    for pitch in np.exp(np.arange(np.log(pitch0[0]), np.log(pitch0[1]), 0.025)):
        tol = Y_TOL * pitch
        for d in (1, -1):
            for parity in (0, 1):
                acc = np.zeros(height + 1)
                for k in ks:
                    want = (k % 2) == parity
                    line_acc = np.zeros(height + 1)
                    for s, yc, xc, fl in cands[k]:
                        if fl != want:
                            continue
                        y0 = yc - d * (k - 1) * pitch      # implied first-line y
                        lo, hi = int(max(0, y0 - tol)), int(min(height, y0 + tol))
                        if hi >= lo:
                            line_acc[lo:hi + 1] = np.maximum(line_acc[lo:hi + 1], s)
                    acc += line_acc
                i = int(np.argmax(acc))
                if acc[i] > best[0]:
                    best = (float(acc[i]), i, float(pitch), d, parity)
    return best + (total,)


def head_of(u):
    return re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])


def cut_box(side, lid, kk, unit, hd, want, hx0, hx1, hy0, hy1, lsc, tw, in0, in1, source):
    """Cut one box from the print, turn it upright, keep its own ink, save it and record it."""
    hx0, hx1 = max(0, hx0), min(G_full.shape[1], hx1); hy0, hy1 = max(0, hy0), min(G_full.shape[0], hy1)
    crop = full_ink_map[hy0:hy1, hx0:hx1]
    if crop.size == 0:
        return
    if want:
        crop = crop[::-1, ::-1]
        in0, in1 = crop.shape[1] - in1, crop.shape[1] - in0
    # a hand-drawn box is the glyph's own extent: keep everything in it but specks; the automatic box is
    # padded and may reach into the next line, so there the intruder rule applies
    crop, pw_ink = own_ink(crop, in0, in1, strict=(source == "auto"))
    Image.fromarray(((~crop) * 255).astype("uint8")).save(idir / side / f"{lid}_{kk:03d}.png")
    inst_rows.append([side, lid, kk, unit, hd, hx0, hx1, hy0, hy1, pw_ink, tw, round(lsc, 3), "flipped" if want else "upright", source])
    boxes_draw.append((lid, kk, hx0, hx1, hy0, hy1, lsc))
    tp = tdir / "instances" / side / f"{lid}_{kk:03d}.png"
    if tp.exists() and pw_ink and tw:
        d1 = descriptor(crop); d2 = descriptor(np.asarray(Image.open(tp).convert("L")) < 128)
        if d1 and d2:
            fid_rows.append([side, lid, kk, hd, pw_ink, tw, round(similarity(d1, d2), 4), round(lsc, 3)])


corpus_all = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
tr_rows = load_tracing_rows()
tracing_width = {(r["side"], r["line"], int(r["position"])): int(r["width"])
                 for r in csv.DictReader(open(out / "glyph_instances.csv", encoding="utf-8")) if r["line_quality"] == "reliable"}
sides = args.sides or sorted(s for s in tr_rows if any(p.stem == s for p in pdir.glob("*.*")) and s not in SKIP)
side_rows, line_rows, inst_rows, fid_rows = [], [], [], []
check = {}

for side in sides:
    T = tracing_ink(side)
    G = print_gray(side)
    by_line = collections.defaultdict(list)
    for r in tr_rows[side]:
        by_line[r["line"]].append(r)
    lids = sorted(by_line, key=line_number)
    full_maps = ink_maps(G)
    strips = {lid: strip(T, sorted(by_line[lid], key=lambda r: int(r["position"]))) for lid in lids}
    tw = np.median([strips[l][0].shape[1] for l in lids])
    best_side = None
    for pol in ("bright", "dark"):
        cols = np.where(full_maps[pol].sum(axis=0) > 3)[0]
        if len(cols) < 10:
            continue
        s0 = tw / (cols.max() - cols.min())      # scale from lengths
        for s in s0 * np.array([0.9, 0.95, 1.0, 1.05, 1.1]):
            gs = rescale(G, s, anti_aliasing=True)
            M = ink_maps(gs)[pol]
            Ms = soft(M)
            # pitch prior from the row profile's autocorrelation in the central half
            # lines cannot be closer than a glyph is tall: the vote sweeps pitches from the tracing's line height up
            hl = int(np.median([strips[l][0].shape[0] for l in lids]))
            pitch0 = (0.8 * hl, 3.0 * hl)
            cands = {}
            for lid in lids:
                tm, (ox, oy) = strips[lid]
                rows = sorted(by_line[lid], key=lambda r: int(r["position"]))
                cl = []
                for i in range(0, max(1, len(rows) - CHUNK + 1), STRIDE):
                    ch = rows[i:i + CHUNK]
                    x0 = max(0, min(int(r["x0"]) for r in ch) - ox - 3); x1 = min(tm.shape[1], max(int(r["x1"]) for r in ch) - ox + 3)
                    for sc, yc, xc, fl in candidates(Ms, tm, x0, x1):
                        cl.append((sc, yc, xc, fl, (x0 + x1) / 2))
                cands[line_number(lid)] = cl
            strength, y0, pitch, d, parity, total = vote({k: [c[:4] for c in v] for k, v in cands.items()}, pitch0, M.shape[0])
            if best_side is None or strength > best_side[0]:
                best_side = (strength, s, pol, y0, pitch, d, parity, total, cands, M, Ms)
    if best_side is None:
        side_rows.append([side, "", "", 0, 0, "", "", "", len(lids), 0, "no ink found"]); continue
    strength, s, pol, y0, pitch, d, parity, total, cands, M, Ms = best_side
    trusted = strength >= VOTE_MIN * total
    full_ink = full_maps[pol]
    G_full, full_ink_map = G, full_ink
    (idir / side).mkdir(parents=True, exist_ok=True)
    for f in (idir / side).glob("*.png"):
        f.unlink()
    placed = 0
    boxes_draw = []
    for lid in lids:
        k = line_number(lid)
        want = (k % 2) == parity                    # this line is upside down on the print
        yk = y0 + d * (k - 1) * pitch
        inl = [c for c in cands[k] if c[3] == want and abs(c[1] - yk) <= Y_TOL * pitch]
        sign = -1 if want else 1
        fit = None
        if len(inl) >= 2:                           # x map by RANSAC over pairs: print x = a + b * tracing x
            bestn = 0
            for i in range(len(inl)):
                for j in range(i + 1, len(inl)):
                    dx = inl[j][4] - inl[i][4]
                    if abs(dx) < 20:
                        continue
                    b = (inl[j][2] - inl[i][2]) / dx
                    if not (0.75 <= sign * b <= 1.3):
                        continue
                    a = inl[i][2] - b * inl[i][4]
                    ok = [c for c in inl if abs(a + b * c[4] - c[2]) <= X_TOL]
                    score = sum(c[0] for c in ok)
                    if len(ok) > bestn or (len(ok) == bestn and fit and score > fit[2]):
                        bestn = len(ok); fit = (a, b, score, ok)
        if fit is None and inl:
            c = max(inl, key=lambda c: c[0]); fit = (c[2] - sign * c[4], float(sign), c[0], [c])
        tm, (ox, oy) = strips[lid]
        rows = sorted(by_line[lid], key=lambda r: int(r["position"]))
        n_chunks = max(1, (len(rows) - CHUNK) // STRIDE + 1)
        if fit is None or not trusted:
            line_rows.append([side, lid, "flipped" if want else "upright", 0, n_chunks, "", "", "not placed"]); continue
        a, b, score, ok = fit
        xs = np.array([c[2] for c in ok]); ys = np.array([c[1] for c in ok])
        if len(ok) >= 4:                            # y along the line: the curvature of the wood
            yfit = np.polyfit(xs, ys, 2)
        elif len(ok) >= 2:
            yfit = np.polyfit(xs, ys, 1)
        else:
            yfit = np.array([float(ys[0])])
        resid = float(np.mean(np.abs(a + b * np.array([c[4] for c in ok]) - xs)))
        line_rows.append([side, lid, "flipped" if want else "upright", len(ok), n_chunks, round(abs(b), 3), round(resid, 1), "placed"])
        placed += 1
        H = tm.shape[0]
        shift = (0, 0)
        for r in rows:
            kk = int(r["position"])
            x0, x1, y0g, y1g = int(r["x0"]) - ox, int(r["x1"]) - ox, int(r["y0"]) - oy, int(r["y1"]) - oy
            pxc = a + b * (x0 + x1) / 2                 # predicted print centre x of the glyph
            pyc = float(np.polyval(yfit, pxc))          # predicted print centre y of the line there
            cx0, cx1 = max(0, x0 - 12), min(tm.shape[1], x1 + 12)
            lt = soft(tm[:, cx0:cx1])
            if want:
                lt = lt[::-1, ::-1]
            tx = int(round(a + b * (cx0 + cx1) / 2 - lt.shape[1] / 2 + shift[1])); ty = int(round(pyc - H / 2 + shift[0]))
            sy0, sx0 = max(0, ty - LOCAL_WIN), max(0, tx - LOCAL_WIN)
            win = Ms[sy0:ty + lt.shape[0] + LOCAL_WIN, sx0:tx + lt.shape[1] + LOCAL_WIN]
            lsc, dxy = -1.0, (0, 0)
            if win.shape[0] > lt.shape[0] and win.shape[1] > lt.shape[1]:
                c = match_template(win, lt)
                i = np.unravel_index(int(np.argmax(c)), c.shape)
                lsc = float(c[i]); dxy = (sy0 + i[0] - ty, sx0 + i[1] - tx)
            if lsc >= LOCAL_MIN:
                shift = (max(-LOCAL_WIN, min(LOCAL_WIN, shift[0] + dxy[0])), max(-LOCAL_WIN, min(LOCAL_WIN, shift[1] + dxy[1])))
            hw = (x1 - x0) * abs(b) / 2
            gx0, gx1 = pxc - hw + shift[1], pxc + hw + shift[1]
            top = pyc - H / 2 + shift[0]
            if want:
                gy0, gy1 = top + (H - y1g), top + (H - y0g)
            else:
                gy0, gy1 = top + y0g, top + y1g
            # clip the box to the print's own line band: the row profile of the ink around the glyph, followed
            # up and down from the line's centre until it falls to a tenth of its peak, since the print's lines
            # are packed tighter than the tracing's and a tall box would otherwise reach into the next line
            wx0, wx1 = int(max(0, pxc - 40)), int(min(M.shape[1], pxc + 40))
            prof = ndimage.uniform_filter1d(M[:, wx0:wx1].sum(axis=1).astype(float), 3)
            cy = int(min(max(0, round(pyc + shift[0])), M.shape[0] - 1))
            peak = prof[max(0, cy - H // 3): cy + H // 3 + 1].max() if H else 0
            if peak > 0:
                thr = 0.1 * peak
                bt = cy
                while bt > 0 and prof[bt - 1] > thr and cy - bt < H:
                    bt -= 1
                bb = cy
                while bb < M.shape[0] - 1 and prof[bb + 1] > thr and bb - cy < H:
                    bb += 1
                gy0, gy1 = max(gy0, bt - 1), min(gy1, bb + 2)
                if gy1 - gy0 < 4:
                    gy0, gy1 = top + (H - y1g) if want else top + y0g, top + (H - y0g) if want else top + y1g
            fx0, fx1, fy0, fy1 = [int(round(v / s)) for v in (gx0, gx1, gy0, gy1)]
            w = max(1, fx1 - fx0); pw = int(PAD * w)
            hy0, hy1 = max(0, fy0 - 2), min(G.shape[0], fy1 + 2)
            hx0, hx1 = max(0, fx0 - pw), min(G.shape[1], fx1 + pw)
            cut_box(side, lid, kk, r["unit"], r["head"], want, hx0, hx1, hy0, hy1, lsc, int(r["width"]), fx0 - hx0, fx1 - hx0, "auto")
    # hand corrections from box_editor.py replace the automatic boxes of the side
    manual = root / "data" / "boxes" / f"{side}.json"
    if manual.exists() and not args.ignore_hand:
        mj = json.load(open(manual, encoding="utf-8"))
        auto_rows_side = [x for x in inst_rows if x[0] == side]; auto_fid_side = [x for x in fid_rows if x[0] == side]
        inst_rows[:] = [x for x in inst_rows if x[0] != side]; fid_rows[:] = [x for x in fid_rows if x[0] != side]
        boxes_draw.clear()
        # a line whose box count does not match its unit count is not finished: its labels would be shifted,
        # so the automatic boxes of that line are kept and the hand boxes skipped, with a warning
        n_units = {lid: sum(1 for u in corpus_all[lid] if not head_of(u).startswith("(") and head_of(u) not in ("000", "999")) for lid in corpus_all if lid.startswith(side)}
        n_boxes = collections.Counter(b["line"] for b in mj["boxes"])
        unfinished = {lid for lid in n_boxes if n_boxes[lid] != n_units.get(lid, -1)}
        for f in (idir / side).glob("*.png"):
            if f.stem.rsplit("_", 1)[0] not in unfinished:
                f.unlink()
        if unfinished:
            print(f"{side}: hand boxes skipped on {', '.join(sorted(unfinished, key=line_number))}, box count differs from the unit count; automatic boxes kept there", flush=True)
        auto_keep = [x for x in auto_rows_side if x[1] in unfinished]
        inst_rows.extend(auto_keep); fid_rows.extend(x for x in auto_fid_side if x[1] in unfinished)
        for x in auto_keep:
            boxes_draw.append((x[1], x[2], x[5], x[6], x[7], x[8], x[11]))
        for b in mj["boxes"]:
            if b["unit"] == "?" or b["line"] in unfinished:
                continue
            want_b = mj["lines"].get(b["line"]) == "flipped"
            tw = tracing_width.get((side, b["line"], b["position"]), 0)
            cut_box(side, b["line"], b["position"], b["unit"], head_of(b["unit"]), want_b, b["x0"], b["x1"], b["y0"], b["y1"], 1.0, tw, 0, b["x1"] - b["x0"], "manual")
        n_manual = sum(1 for x in inst_rows if x[0] == side)
        print(f"{side}: {n_manual} hand-corrected boxes from {manual.name}", flush=True)
    side_rows.append([side, round(s, 3), pol, round(strength / total, 3) if total else 0, round(pitch, 1), y0, "1 at top" if d > 0 else "1 at bottom",
                      "odd lines flipped" if parity == 1 else "even lines flipped", len(lids), placed, "trusted" if trusted else "weak vote"])
    print(f"{side}: scale {s:.3f} {pol}, vote {strength / total if total else 0:.2f}, pitch {pitch:.1f}, {placed}/{len(lids)} lines placed", flush=True)
    if side == args.check:
        check = {"gray": G, "boxes": boxes_draw}

if args.sides and not args.tag:
    # a run restricted to some sides replaces only their rows in the tables, keeping every other side's
    def kept(name, conv):
        f = out / name
        if not f.exists():
            return []
        rows = [r for r in list(csv.reader(open(f, encoding="utf-8")))[1:] if r and r[0] not in args.sides]
        for r in rows:
            for i, fn in conv.items():
                r[i] = fn(r[i])
        return rows
    side_rows = sorted(kept("register_sides.csv", {8: int, 9: int}) + side_rows, key=lambda r: r[0])
    line_rows = sorted(kept("register_lines.csv", {}) + line_rows, key=lambda r: r[0])
    inst_rows = sorted(kept("photo_instances.csv", {2: int, 9: int, 10: int, 11: float}) + inst_rows, key=lambda r: r[0])
    fid_rows = sorted(kept("photo_fidelity.csv", {2: int, 4: int, 5: int, 6: float, 7: float}) + fid_rows, key=lambda r: r[0])
with open(out / f"register_sides{TAG}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["side", "scale", "polarity", "vote", "pitch", "first_line_y", "direction", "parity", "reliable_lines", "placed", "status"]); w.writerows(side_rows)
with open(out / f"register_lines{TAG}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["side", "line", "orientation", "chunks_inlier", "chunks", "stretch", "x_residual", "status"]); w.writerows(line_rows)
with open(out / f"photo_instances{TAG}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["side", "line", "position", "unit", "head", "x0", "x1", "y0", "y1", "print_ink_width", "tracing_width", "local_score", "orientation", "source"]); w.writerows(inst_rows)
with open(out / f"photo_fidelity{TAG}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["side", "line", "position", "head", "print_ink_width", "tracing_width", "similarity", "local_score"]); w.writerows(fid_rows)

if check and not args.tag:
    img_dir.mkdir(parents=True, exist_ok=True)
    G = check["gray"]
    im = Image.fromarray((G * 255).astype("uint8")).convert("RGB")
    dr = ImageDraw.Draw(im)
    for lid, kk, hx0, hx1, hy0, hy1, lsc in check["boxes"]:
        if hx1 <= hx0 or hy1 <= hy0:
            continue
        dr.rectangle([hx0, hy0, hx1, hy1], outline=(235, 104, 52) if lsc >= LOCAL_MIN else (42, 120, 214), width=2)
    w0 = min(1600, im.width)
    im.resize((w0, int(im.height * w0 / im.width)), Image.LANCZOS).save(img_dir / "registration_check.png")
    side = args.check
    lines_here = list(dict.fromkeys(b[0] for b in check["boxes"]))
    if lines_here:
        lid = lines_here[min(3, len(lines_here) - 1)]
        ks = [b[1] for b in check["boxes"] if b[0] == lid][:14]
        cell = 72
        canvas = Image.new("L", (cell * len(ks), cell * 2), 255)
        for i, kk in enumerate(ks):
            for row, p in enumerate((tdir / "instances" / side / f"{lid}_{kk:03d}.png", idir / side / f"{lid}_{kk:03d}.png")):
                if p.exists():
                    g = Image.open(p).convert("L"); g.thumbnail((cell - 8, cell - 8))
                    canvas.paste(g, (i * cell + (cell - g.width) // 2, row * cell + (cell - g.height) // 2))
        canvas.save(img_dir / "registration_pairs.png")

med_p, med_t = collections.defaultdict(list), collections.defaultdict(list)
for s_, lid, k, h, pw, tw, sim, lsc in fid_rows:
    med_p[(s_, lid)].append(pw); med_t[(s_, lid)].append(tw)
rel = [(pw / np.median(med_p[(s_, lid)]), tw / np.median(med_t[(s_, lid)]), sim, lsc) for s_, lid, k, h, pw, tw, sim, lsc in fid_rows if np.median(med_p[(s_, lid)]) > 0]
if rel:
    a = np.array(rel); corr = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]); med_sim = float(np.median(a[:, 2]))
    good = a[a[:, 3] >= LOCAL_MIN]
    corr_good = float(np.corrcoef(good[:, 0], good[:, 1])[0, 1]) if len(good) > 10 else float("nan")
else:
    corr, med_sim, corr_good, good = float("nan"), float("nan"), float("nan"), []

md = ["# Registration of the tracings to the prints\n",
      f"{sum(r[9] for r in side_rows)} of {sum(r[8] for r in side_rows)} reliable tracing lines placed on {len(side_rows)} prints; "
      f"{len(inst_rows)} glyphs cut from the prints, {sum(1 for r in inst_rows if r[11] >= LOCAL_MIN)} with a local match above {LOCAL_MIN}.\n",
      "| side | scale | polarity | vote | pitch | line 1 | flipped | reliable lines | placed | status |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in side_rows:
    md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} |")
md.append("\n## Fidelity of tracing to print\n")
md.append(f"{len(rel)} glyphs with ink in both; {len(good)} with a local match above {LOCAL_MIN}. Correlation of relative width, print ink extent against tracing width: "
          f"{corr:.2f} over all, {corr_good:.2f} over the locally matched. Descriptor similarity of the print glyph to its tracing: median {med_sim:.3f}.\n")
(out / f"register{TAG}.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:2]))
