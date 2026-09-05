"""Shape similarity between Barthel's sign drawings.

Input: data/signs/gif/*.gif row images (five signs per row, 669 x 78) and
data/signs/rows.json mapping each row to its five sign numbers.

Steps
  1. slice each row into five cells; inside a cell, split drawings separated
     by a horizontal gap of GAP+ blank columns into variants of the same sign
  2. normalise each drawing: crop to ink, pad to square, resize to N x N,
     light blur; also keep its horizontal mirror
  3. similarity = max over mirror of the cosine similarity of the two blurred
     bitmaps, times a size-ratio penalty so a tall stroke and a squat figure
     never match
  4. calibrate: similarity between variants of the same sign gives the
     within-sign distribution; the threshold is its lower quartile
  5. cluster signs above threshold (single linkage), recompute the head-sign
     inventory of the corpus under those shape classes, and score the
     allograph candidate pairs from allographs.py

Outputs (out/): sign_similarity.csv (nearest neighbours), sign_shape_classes.csv,
sign_shapes.md, sign_pairs.png (contact sheet of the closest pairs)
"""
import collections, csv, json, pathlib, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 40
GAP = 6
root = pathlib.Path(__file__).resolve().parent.parent
sd = root / "data" / "signs"
out = root / "out"
rows = json.load(open(sd / "rows.json"))
(sd / "png").mkdir(exist_ok=True)

# 1. slice
drawings = {}          # sign -> [np.array bitmaps]
for row, names in rows.items():
    f = next(iter(sd.glob(f"gif/{row}.*")), None)
    if f is None:
        continue
    im = Image.open(f).convert("L")
    a = np.array(im) < 128
    w = a.shape[1] / 5
    for k, name in enumerate(names):
        if not name:
            continue
        cell = a[:, int(k * w):int((k + 1) * w)]
        cols = cell.sum(axis=0) > 0
        # split into variants by blank gaps
        segs, x, inseg, last = [], 0, False, 0
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
            if piece.sum() < 12:
                continue
            drawings.setdefault(name, []).append(piece)

# 2. normalise and describe
#    Two descriptors, each L2-normalised, concatenated:
#      bitmap  N x N binary silhouette with a light blur (where the ink is)
#      hog     gradient-orientation histograms, 8 bins over a 5 x 5 grid
#              (how the strokes run), computed on the unblurred bitmap
def canvas_of(bits):
    h, w = bits.shape
    side = max(h, w)
    c = np.zeros((side, side), bool)
    c[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = bits
    return Image.fromarray((c * 255).astype("uint8")).resize((N, N), Image.LANCZOS)


def hog(img, cells=5, bins=8):
    a = np.asarray(img, dtype=float) / 255.0
    gy, gx = np.gradient(a)
    mag = np.hypot(gx, gy)
    ang = (np.arctan2(gy, gx) + np.pi) % np.pi          # unsigned orientation
    step = N // cells
    h = np.zeros((cells, cells, bins))
    for i in range(cells):
        for j in range(cells):
            m = mag[i * step:(i + 1) * step, j * step:(j + 1) * step]
            t = ang[i * step:(i + 1) * step, j * step:(j + 1) * step]
            hist, _ = np.histogram(t, bins=bins, range=(0, np.pi), weights=m)
            h[i, j] = hist / (hist.sum() + 1e-9)
    return h.ravel()


def describe(bits):
    img = canvas_of(bits)
    bm = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), dtype=float).ravel()
    bm /= np.linalg.norm(bm) + 1e-9
    hg = hog(img)
    hg /= np.linalg.norm(hg) + 1e-9
    return np.concatenate([bm * W_BITMAP, hg * W_HOG])


W_BITMAP, W_HOG = 0.5 ** 0.5, 0.5 ** 0.5     # equal weight, unit total norm
feats = {}             # (sign, variant) -> (vec, mirrored vec, aspect)
for s, lst in drawings.items():
    for i, bits in enumerate(lst):
        feats[(s, i)] = (describe(bits), describe(bits[:, ::-1]), bits.shape[0] / bits.shape[1])
        Image.fromarray((np.pad(bits, 2) * 255).astype("uint8")).save(sd / "png" / f"{s}_{i}.png")

keys = sorted(feats)
V = np.stack([feats[k][0] for k in keys])
VM = np.stack([feats[k][1] for k in keys])
ASP = np.array([feats[k][2] for k in keys])
S = np.maximum(V @ V.T, V @ VM.T)
ratio = np.minimum(ASP[:, None], ASP[None, :]) / np.maximum(ASP[:, None], ASP[None, :])
S = S * ratio                                   # a 2:1 aspect mismatch halves the score
np.fill_diagonal(S, 0)

# sign-level similarity = best variant pair
signs = sorted(set(k[0] for k in keys))
idx = {s: [i for i, k in enumerate(keys) if k[0] == s] for s in signs}
SS = np.zeros((len(signs), len(signs)))
for a, sa in enumerate(signs):
    for b, sb in enumerate(signs):
        if a < b:
            SS[a, b] = SS[b, a] = S[np.ix_(idx[sa], idx[sb])].max()

# 4. calibrate on variants of the same sign
within = [S[i, j] for s in signs for i in idx[s] for j in idx[s] if i < j]
between = SS[np.triu_indices(len(signs), 1)]
within = np.array(within)
# threshold: stricter than 199 of 200 unrelated pairs; report how many
# genuine variant pairs it still catches (recall)
thr = float(np.percentile(between, 99.5))
recall = float((within >= thr).mean()) if len(within) else 0.0

# nearest neighbours
with open(out / "sign_similarity.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sign", "variants", "nn1", "s1", "nn2", "s2", "nn3", "s3", "nn4", "s4", "nn5", "s5"])
    for a, sa in enumerate(signs):
        order = np.argsort(-SS[a])[:5]
        row = [sa, len(idx[sa])]
        for b in order:
            row += [signs[b], f"{SS[a, b]:.3f}"]
        w.writerow(row)

# 5. clusters: a link needs the score above threshold AND each sign among
#    the other's K nearest neighbours, which stops chaining through hubs
#    Classes are then built by complete linkage: two classes merge only if
#    every cross pair is above threshold, so a class is a clique of look-alikes
#    and cannot grow by chaining through intermediates.
K = 3
nn = [set(np.argsort(-SS[a])[:K]) for a in range(len(signs))]
parent = {s: s for s in signs}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
pairs_above = []
for a, sa in enumerate(signs):
    for b in range(a + 1, len(signs)):
        if SS[a, b] >= thr and b in nn[a] and a in nn[b]:
            pairs_above.append((SS[a, b], sa, signs[b]))
members = {s: {s} for s in signs}
for sc, sa, sb in sorted(pairs_above, reverse=True):
    ra, rb = find(sa), find(sb)
    if ra == rb:
        continue
    ia = [signs.index(x) for x in members[ra]]
    ib = [signs.index(x) for x in members[rb]]
    if SS[np.ix_(ia, ib)].min() >= thr:
        parent[ra] = rb
        members[rb] |= members.pop(ra)
classes = collections.defaultdict(list)
for s in signs:
    classes[find(s)].append(s)
multi = {k: v for k, v in classes.items() if len(v) > 1}

# corpus inventory under shape classes
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
def head(u):
    return re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])
rep = {s: find(s) for s in signs}
heads = collections.Counter()
merged = collections.Counter()
for lid, units in corpus.items():
    if lid[0] in "PQK":
        continue
    for u in units:
        h = head(u)
        if h in ("000", "999") or h.startswith("("):
            continue
        heads[h] += 1
        merged[rep.get(h, h)] += 1
def cov(c, p):
    tot, acc = sum(c.values()), 0
    for k, (_, n) in enumerate(c.most_common(), 1):
        acc += n
        if acc / tot >= p:
            return k
with open(out / "sign_shape_classes.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["class", "members", "corpus_tokens"])
    for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        w.writerow([k, " ".join(v), sum(heads[s] for s in v)])

# allograph candidates
allo = []
try:
    for r in csv.DictReader(open(out / "allograph_pairs.csv", encoding="utf-8")):
        a, b = r["a"], r["b"]
        if a in signs and b in signs:
            allo.append((a, b, SS[signs.index(a), signs.index(b)], r["passages"], r["same_series"]))
except FileNotFoundError:
    pass
allo.sort(key=lambda x: -x[2])

# contact sheet of closest pairs
top = sorted(pairs_above, reverse=True)[:30]
cell, cols = 64, 6
sheet = Image.new("L", (cols * cell * 2 + 20, ((len(top) + cols - 1) // cols) * (cell + 18) + 10), 255)
d = ImageDraw.Draw(sheet)
def thumb(s):
    bits = drawings[s][0]
    im = Image.fromarray(((~np.pad(bits, 3)) * 255).astype("uint8"))
    im.thumbnail((cell - 6, cell - 6))
    return im
for n, (sc, a, b) in enumerate(top):
    x = (n % cols) * cell * 2 + 10
    y = (n // cols) * (cell + 18) + 4
    ta, tb = thumb(a), thumb(b)
    sheet.paste(ta, (x + (cell - ta.width) // 2, y + (cell - ta.height) // 2))
    sheet.paste(tb, (x + cell + (cell - tb.width) // 2, y + (cell - tb.height) // 2))
    d.text((x + 4, y + cell), f"{a} ~ {b}  {sc:.2f}", fill=0)
sheet.save(out / "sign_pairs.png")

# report
md = ["# Shape similarity of Barthel's signs\n",
      f"{len(signs)} signs with drawings, {len(keys)} drawings in all ({len(keys) - len(signs)} extra variants). "
      f"Similarity is the cosine of blurred {N}x{N} bitmaps, best of direct and mirrored, scaled by aspect-ratio agreement.\n",
      "## Calibration\n",
      f"Variant pairs of the same sign: n = {len(within)}, median {np.median(within):.3f}, lower quartile {np.percentile(within, 25):.3f}. "
      f"Unrelated sign pairs: median {np.median(between):.3f}, 99th percentile {np.percentile(between, 99):.3f}. "
      f"Threshold = 99.5th percentile of unrelated pairs = {thr:.3f}; it catches {recall:.0%} of the genuine variant pairs.\n"]
md.append("## Shape classes at threshold\n")
md.append(f"{len(pairs_above)} reciprocal-neighbour pairs at or above threshold, forming {len(multi)} classes that absorb "
          f"{sum(len(v) for v in multi.values()) - len(multi)} signs.\n")
md.append("| class members | corpus tokens |\n|---|---|")
for k, v in sorted(multi.items(), key=lambda kv: -sum(heads[s] for s in kv[1]))[:40]:
    md.append(f"| {' '.join(v)} | {sum(heads[s] for s in v)} |")
md.append("\n## Effect on the head-sign inventory, one witness per family\n")
md.append("| inventory | distinct | signs for 50% | 90% | 95% | 99% |\n|---|---|---|---|---|---|")
md.append(f"| Barthel heads | {len(heads)} | {cov(heads, .5)} | {cov(heads, .9)} | {cov(heads, .95)} | {cov(heads, .99)} |")
md.append(f"| shape classes | {len(merged)} | {cov(merged, .5)} | {cov(merged, .9)} | {cov(merged, .95)} | {cov(merged, .99)} |")
md.append("\n## Allograph candidates from copied passages, scored by shape\n")
md.append("| a | b | shape similarity | passages | same series |\n|---|---|---|---|---|")
for a, b, sc, p, ss in allo:
    md.append(f"| {a} | {b} | {sc:.3f} | {p} | {'yes' if ss == 'True' else ''} |")
md.append(f"\nFor comparison the median similarity of an arbitrary pair is {np.median(between):.3f} and the threshold {thr:.3f}.")
md.append("\n## Closest pairs\n")
md.append("| a | b | similarity |\n|---|---|---|")
for sc, a, b in sorted(pairs_above, reverse=True)[:40]:
    md.append(f"| {a} | {b} | {sc:.3f} |")
(out / "sign_shapes.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:8]))
print(f"classes: {len(multi)}, merged inventory {len(merged)} vs {len(heads)}")
