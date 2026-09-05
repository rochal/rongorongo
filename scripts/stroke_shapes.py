"""A stroke-based shape descriptor for the sign drawings, and what it changes.

Sections 9, 12 and 25 stopped at the same wall: a pixel descriptor
(blurred silhouette plus gradient histograms) recovers only 22 percent of
Barthel's own variant pairs at a strict threshold, cannot rebuild rare
signs from common ones, and cannot see variation in small instances.
Thin line drawings are better compared as strokes than as ink.

Each drawing is thinned to a one-pixel skeleton (Zhang-Suen), the skeleton
is broken at junctions into branches, and the drawing is described by:
  counts     endpoints, junctions, branches, closed loops
  branches   orientation histogram weighted by length (6 bins),
             length histogram (4 bins), mean curvature (length over chord)
  layout     skeleton density on a 3x3 grid, endpoints on a 3x3 grid
  size       skeleton length relative to the canvas, aspect ratio
Similarity is the cosine of the normalised descriptor, best of direct and
mirrored, with the same aspect penalty as before. Three descriptors are
calibrated side by side on Barthel's variant pairs against random pairs:
pixel (as section 9), stroke (this), and their combination.

The best descriptor is then applied to the look-alike classes and to the
glyph instances cut from the tracings, and the allograph candidate pairs
are rescored.

Outputs (out/): stroke_shapes.md, stroke_similarity.csv, stroke_calibration.csv
"""
import collections, csv, json, pathlib, re
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage.morphology import skeletonize, remove_small_objects
from skimage.measure import label as sk_label
from skimage.feature import hog as sk_hog

N = 48
GAP = 6
root = pathlib.Path(__file__).resolve().parent.parent
sd = root / "data" / "signs"
out = root / "out"
rows = json.load(open(sd / "rows.json"))


# ---------------------------------------------------------------- drawings
def load_drawings():
    drawings = collections.defaultdict(list)
    for row, names in rows.items():
        f = next(iter(sd.glob(f"gif/{row}.*")), None)
        if f is None:
            continue
        a = np.array(Image.open(f).convert("L")) < 128
        w = a.shape[1] / 5
        for k, name in enumerate(names):
            if not name:
                continue
            cell = a[:, int(k * w):int((k + 1) * w)]
            cols = cell.sum(axis=0) > 0
            segs, inseg, last = [], False, 0
            for i, v in enumerate(cols):
                if v and not inseg:
                    start, inseg = i, True
                if v:
                    last = i
                if inseg and not v and i - last >= GAP:
                    segs.append((start, last + 1)); inseg = False
            if inseg:
                segs.append((start, last + 1))
            for s, e in segs:
                piece = cell[:, s:e]
                ys = np.where(piece.sum(axis=1) > 0)[0]
                if len(ys) == 0 or (e - s) < 4:
                    continue
                piece = piece[ys[0]:ys[-1] + 1]
                if piece.sum() >= 12:
                    drawings[name].append(piece)
    return drawings


def canvas(bits, size=N):
    h, w = bits.shape
    scale = size / max(h, w)
    im = Image.fromarray((bits * 255).astype("uint8")).resize((max(2, round(w * scale)), max(2, round(h * scale))), Image.LANCZOS)
    a = np.asarray(im) > 100
    c = np.zeros((size, size), bool)
    y0, x0 = (size - a.shape[0]) // 2, (size - a.shape[1]) // 2
    c[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    return c


# ---------------------------------------------------------------- thinning
def thin(img):
    """One-pixel skeleton of a binary drawing (scikit-image), specks removed first."""
    clean = remove_small_objects(img.astype(bool), max_size=3)
    return skeletonize(clean)


def skeleton_descriptor(bits):
    """The skeleton kept as an image: blurred skeleton plus HOG of the skeleton.
    Removes stroke-width differences between drawings of one sign."""
    sk = thin(canvas(bits)).astype(float)
    if sk.sum() < 3:
        return None
    im = Image.fromarray((sk * 255).astype("uint8"))
    sil = np.asarray(im.filter(ImageFilter.GaussianBlur(1.5)), dtype=float)
    sil /= np.linalg.norm(sil) + 1e-9
    h = sk_hog(sil, orientations=8, pixels_per_cell=(8, 8), cells_per_block=(1, 1), feature_vector=True)
    h = h / (np.linalg.norm(h) + 1e-9)
    return np.concatenate([sil.ravel() * 0.5, h * 0.5])


SC_POINTS, SC_R, SC_A = 50, 5, 12


def shape_context(bits):
    """Shape contexts of points sampled along the skeleton: for each point a
    log-polar histogram of where the other points lie. Returns an array of
    (points, SC_R * SC_A) histograms, or None."""
    sk = thin(canvas(bits))
    ys, xs = np.where(sk)
    if len(ys) < 5:
        return None
    pts = np.stack([xs, ys], 1).astype(float)
    if len(pts) > SC_POINTS:
        pts = pts[np.linspace(0, len(pts) - 1, SC_POINTS).astype(int)]
    d = np.linalg.norm(pts[:, None] - pts[None], axis=2)
    mean_d = d[d > 0].mean()
    ang = np.arctan2(pts[None, :, 1] - pts[:, None, 1], pts[None, :, 0] - pts[:, None, 0])
    rb = np.clip(np.floor(np.log2(np.maximum(d / mean_d, 1e-3) * 4) + 2), 0, SC_R - 1).astype(int)
    ab = ((ang + np.pi) / (2 * np.pi) * SC_A).astype(int) % SC_A
    H = np.zeros((len(pts), SC_R * SC_A))
    for i in range(len(pts)):
        for j in range(len(pts)):
            if i != j:
                H[i, rb[i, j] * SC_A + ab[i, j]] += 1
    H /= H.sum(1, keepdims=True) + 1e-9
    return H


def sc_similarity(Ha, Hb):
    """1 minus the mean chi-square distance between each point and its best match, symmetrised."""
    num = (Ha[:, None] - Hb[None]) ** 2
    den = Ha[:, None] + Hb[None] + 1e-9
    C = 0.5 * (num / den).sum(2)
    return 1 - 0.5 * (C.min(1).mean() + C.min(0).mean())


NB8 = np.ones((3, 3), int); NB8[1, 1] = 0


def stroke_descriptor(bits):
    c = canvas(bits)
    sk = thin(c)
    n_sk = sk.sum()
    if n_sk < 3:
        return None
    deg = ndimage.convolve(sk.astype(int), NB8, mode="constant") * sk
    endpoints = sk & (deg == 1)
    junctions = sk & (deg >= 3)
    # loops: holes in the filled drawing
    filled = ndimage.binary_fill_holes(c)
    holes = sk_label(filled & ~c, connectivity=1, return_num=True)[1]
    # branches: skeleton minus junction pixels
    branches, nb = sk_label(sk & ~ndimage.binary_dilation(junctions, structure=np.ones((3, 3))), connectivity=2, return_num=True)
    orient = np.zeros(6); lengths = np.zeros(4); curv = []
    for sl, lab in zip(ndimage.find_objects(branches), range(1, nb + 1)):
        ys, xs = np.where(branches[sl] == lab)
        L = len(ys)
        if L < 2:
            continue
        ys = ys + sl[0].start; xs = xs + sl[1].start
        # chord between the two most distant pixels along the principal axis
        pts = np.stack([xs, ys], 1).astype(float)
        cen = pts.mean(0)
        u, s, vt = np.linalg.svd(pts - cen, full_matrices=False)
        d = vt[0]
        proj = (pts - cen) @ d
        chord = proj.max() - proj.min() + 1
        ang = (np.arctan2(d[1], d[0]) + np.pi) % np.pi
        orient[min(5, int(ang / np.pi * 6))] += L
        lengths[min(3, int(np.log2(max(1, L)) / 1.5))] += 1
        curv.append(L / chord)
    def grid(mask):
        g = np.zeros(9)
        for i in range(3):
            for j in range(3):
                g[i * 3 + j] = mask[i * N // 3:(i + 1) * N // 3, j * N // 3:(j + 1) * N // 3].sum()
        return g
    blocks = [
        np.array([endpoints.sum(), junctions.sum(), nb, holes]) / 6.0,
        orient / max(1, orient.sum()),
        lengths / max(1, lengths.sum()),
        np.array([np.mean(curv) - 1 if curv else 0.0]),
        grid(sk) / max(1, n_sk),
        grid(endpoints) / max(1, endpoints.sum()),
        np.array([n_sk / N, bits.shape[0] / bits.shape[1] / 3]),
    ]
    v = np.concatenate(blocks)
    return v / (np.linalg.norm(v) + 1e-9)


def pixel_descriptor(bits):
    c = canvas(bits, 40)
    im = Image.fromarray((c * 255).astype("uint8"))
    sil = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), dtype=float)
    sil /= np.linalg.norm(sil) + 1e-9
    g = np.asarray(im, dtype=float)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) + np.pi) % np.pi
    hog = []
    for cy in range(5):
        for cx in range(5):
            sl = (slice(cy * 8, (cy + 1) * 8), slice(cx * 8, (cx + 1) * 8))
            hist, _ = np.histogram(ang[sl], bins=8, range=(0, np.pi), weights=mag[sl])
            hog.extend(hist)
    hog = np.array(hog); hog /= np.linalg.norm(hog) + 1e-9
    return np.concatenate([sil.ravel() * 0.5, hog * 0.5])


def describe_all(drawings):
    feats = {}
    for s, lst in drawings.items():
        for i, bits in enumerate(lst):
            st = stroke_descriptor(bits); stm = stroke_descriptor(bits[:, ::-1])
            px = pixel_descriptor(bits); pxm = pixel_descriptor(bits[:, ::-1])
            sk = skeleton_descriptor(bits); skm = skeleton_descriptor(bits[:, ::-1])
            sc = shape_context(bits); scm = shape_context(bits[:, ::-1])
            if st is None or stm is None or sk is None or skm is None or sc is None or scm is None:
                continue
            feats[(s, i)] = {"stroke": (st, stm), "pixel": (px, pxm), "skeleton": (sk, skm), "sc": (sc, scm),
                             "asp": bits.shape[0] / bits.shape[1]}
    return feats


def sim(fa, fb, kind):
    ratio = min(fa["asp"], fb["asp"]) / max(fa["asp"], fb["asp"])
    if kind == "sc":
        a, am = fa["sc"]; b, _ = fb["sc"]
        v = max(sc_similarity(a, b), sc_similarity(am, b))
        return v * np.sqrt(ratio)
    a, am = fa[kind]; b, bm = fb[kind]
    v = max(float(a @ b), float(a @ bm))
    return v * np.sqrt(ratio)


def sim_combo(fa, fb):
    return 0.5 * sim(fa, fb, "skeleton") + 0.5 * sim(fa, fb, "pixel")


if __name__ == "__main__":
    drawings = load_drawings()
    feats = describe_all(drawings)
    keys = sorted(feats)
    signs = sorted({k[0] for k in keys})
    idx = collections.defaultdict(list)
    for k in keys:
        idx[k[0]].append(k)
    rng = np.random.default_rng(5)

    # calibration on Barthel's variant pairs against random pairs
    within_pairs = [(a, b) for s in signs for i, a in enumerate(idx[s]) for b in idx[s][i + 1:]]
    rand_pairs = []
    while len(rand_pairs) < 6000:
        a, b = keys[rng.integers(len(keys))], keys[rng.integers(len(keys))]
        if a[0] != b[0]:
            rand_pairs.append((a, b))
    calib = {}
    for name, fn in (("pixel", lambda a, b: sim(feats[a], feats[b], "pixel")),
                     ("stroke counts", lambda a, b: sim(feats[a], feats[b], "stroke")),
                     ("skeleton image", lambda a, b: sim(feats[a], feats[b], "skeleton")),
                     ("shape context", lambda a, b: sim(feats[a], feats[b], "sc")),
                     ("pixel + skeleton", lambda a, b: sim_combo(feats[a], feats[b]))):
        w = np.array([fn(a, b) for a, b in within_pairs]); r = np.array([fn(a, b) for a, b in rand_pairs])
        thr995, thr99, thr95 = np.percentile(r, 99.5), np.percentile(r, 99), np.percentile(r, 95)
        calib[name] = {"within_median": float(np.median(w)), "random_median": float(np.median(r)),
                       "recall_at_99.5": float((w >= thr995).mean()), "recall_at_99": float((w >= thr99).mean()),
                       "recall_at_95": float((w >= thr95).mean()), "thr995": float(thr995)}
        # rank test: for each variant pair, share of random pairs it beats
        calib[name]["auc"] = float(np.mean([(r < x).mean() for x in w]))
    best = max(calib, key=lambda k: calib[k]["recall_at_99.5"])

    with open(out / "stroke_calibration.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["descriptor", "within_median", "random_median", "recall_at_99.5", "recall_at_99", "recall_at_95", "auc"])
        for k, v in calib.items():
            wr.writerow([k, f"{v['within_median']:.3f}", f"{v['random_median']:.3f}", f"{v['recall_at_99.5']:.3f}",
                         f"{v['recall_at_99']:.3f}", f"{v['recall_at_95']:.3f}", f"{v['auc']:.3f}"])

    # sign-level similarity with the best descriptor (best variant pair), nearest neighbours
    fn = {"pixel": lambda a, b: sim(feats[a], feats[b], "pixel"), "stroke counts": lambda a, b: sim(feats[a], feats[b], "stroke"),
          "skeleton image": lambda a, b: sim(feats[a], feats[b], "skeleton"), "shape context": lambda a, b: sim(feats[a], feats[b], "sc"),
          "pixel + skeleton": lambda a, b: sim_combo(feats[a], feats[b])}[best]
    main_key = {s: idx[s][0] for s in signs}
    S = np.zeros((len(signs), len(signs)))
    for i, a in enumerate(signs):
        for j in range(i + 1, len(signs)):
            b = signs[j]
            S[i, j] = S[j, i] = max(fn(x, y) for x in idx[a][:2] for y in idx[b][:2])
    thr = calib[best]["thr995"]
    K = 3
    nn = [set(np.argsort(-S[a])[:K]) for a in range(len(signs))]
    pairs_above = [(S[a, b], signs[a], signs[b]) for a in range(len(signs)) for b in range(a + 1, len(signs))
                   if S[a, b] >= thr and b in nn[a] and a in nn[b]]
    parent = {s: s for s in signs}; members = {s: {s} for s in signs}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for sc, a, b in sorted(pairs_above, reverse=True):
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        ia = [signs.index(x) for x in members[ra]]; ib = [signs.index(x) for x in members[rb]]
        if S[np.ix_(ia, ib)].min() >= thr:
            parent[ra] = rb; members[rb] |= members.pop(ra)
    classes = [sorted(m) for m in members.values() if len(m) > 1]
    with open(out / "stroke_similarity.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["sign", "nn1", "s1", "nn2", "s2", "nn3", "s3"])
        for a, s in enumerate(signs):
            order = np.argsort(-S[a])[:3]
            wr.writerow([s] + [x for b in order for x in (signs[b], f"{S[a, b]:.3f}")])

    # allograph candidates rescored
    allo = []
    p = out / "allograph_pairs.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            a, b = r["a"], r["b"]
            if a in signs and b in signs:
                allo.append((a, b, S[signs.index(a), signs.index(b)], r["passages"], r["same_series"]))
        allo.sort(key=lambda x: -x[2])

    # Metoro's pairs, the two-witness pairs of section 18
    metoro_pairs = [("004", "022"), ("400", "600"), ("040", "041"), ("206", "380")]
    mp = [(a, b, S[signs.index(a), signs.index(b)]) for a, b in metoro_pairs if a in signs and b in signs]

    md = ["# A stroke-based descriptor\n",
          f"{len(signs)} signs, {len(keys)} drawings, {len(within_pairs)} variant pairs of one sign against {len(rand_pairs)} random pairs.\n",
          "## Calibration: five descriptors on the same test\n",
          "| descriptor | within-sign median | random median | recall at 99.5th pct | at 99th | at 95th | rank AUC |",
          "|---|---|---|---|---|---|---|"]
    for k, v in calib.items():
        md.append(f"| {k} | {v['within_median']:.3f} | {v['random_median']:.3f} | {v['recall_at_99.5']:.0%} | {v['recall_at_99']:.0%} | "
                  f"{v['recall_at_95']:.0%} | {v['auc']:.3f} |")
    md.append(f"\nBest at the strict threshold: **{best}**. Recall = share of Barthel's own variant pairs scoring above the threshold "
              "that only the stated share of random pairs exceed. AUC = probability that a variant pair outscores a random pair.\n")
    md.append(f"## Look-alike classes with the {best} descriptor at the 99.5th-percentile threshold\n")
    md.append(f"{len(pairs_above)} reciprocal-neighbour pairs, {len(classes)} classes absorbing {sum(len(c) - 1 for c in classes)} signs "
              f"(section 9 with the pixel descriptor: 113 classes absorbing 171).\n")
    md.append("| class |\n|---|")
    for c in sorted(classes, key=len, reverse=True)[:30]:
        md.append(f"| {' '.join(c)} |")
    md.append("\n## Allograph candidates from copied passages, rescored\n")
    md.append("| a | b | similarity | passages | same series |\n|---|---|---|---|---|")
    for a, b, sc, pg, ss in allo[:25]:
        md.append(f"| {a} | {b} | {sc:.3f} | {pg} | {'yes' if ss == 'True' else ''} |")
    md.append(f"\nThreshold {thr:.3f}; random-pair median {calib[best]['random_median']:.3f}.\n")
    md.append("## Metoro's pairs of section 18\n")
    md.append("| a | b | similarity |\n|---|---|---|")
    for a, b, sc in mp:
        md.append(f"| {a} | {b} | {sc:.3f} |")
    (out / "stroke_shapes.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:14]))
    print(f"classes {len(classes)}, pairs {len(pairs_above)}")
