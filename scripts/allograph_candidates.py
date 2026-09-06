"""Are the rare signs of a Barthel series variants of its common one? A context test with controls.

The hand pass over the boxes (data/boxes/notes.md) found carved glyphs that
the transliteration labels with two numbers of one Barthel series: 607 and
650y on Keiti's verso, 680 and 684 on the same tablet. Barthel's numbering
splits each series by small details of the drawing, and a rare number may
be nothing but a variant of the common one. Copies settle this only where
copies exist (section 7); this test uses the whole corpus instead.

  contexts      one witness per family; for every head sign the left and
                right head-sign neighbours of each occurrence, illegible
                units breaking the pair
  score         for a rare sign r (RARE_MIN to RARE_MAX occurrences) and a
                common sign c (at least COMMON_MIN), how likely r's
                neighbourhoods are under c's neighbour distribution: the
                sum over r's contexts of log P(neighbour | c, side), with
                add-k smoothing. If r is a variant of c it should sit in
                c's neighbourhoods
  rank          c's score ranked among all common signs; the series-mate
                (same hundred of Barthel's numbering) is the candidate and
                its rank is the result: 1 means no common sign fits r's
                contexts better than the one it is drawn like
  controls      positive: pairs that copies substitute for one another
                (section 7); if the test has power their ranks are low.
                Null: the rank of the series-mate when series labels are
                shuffled among the common signs, 2000 times, giving the
                chance of the observed number of series-mates at rank 1
                to 3
  shape         catalogue drawings: the similarity of section 9; and where
                both signs have glyphs cut from the prints, the descriptor
                similarity across the pair against within the common sign

Outputs: out/allograph_candidates.csv, out/allograph_candidates.md
"""
import collections, csv, json, math, pathlib, re
import numpy as np
from PIL import Image, ImageFilter

RARE_MIN, RARE_MAX, COMMON_MIN, ADD_K = 2, 12, 20, 0.5
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
rng = np.random.default_rng(5)


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


seqs = []
for lid in sorted(corpus, key=lambda k: (k[:2], int(re.sub(r"\D", "", k[2:]) or 0))):
    if lid[0] in "PQK":
        continue
    seq = []
    for u in corpus[lid]:
        h = clean(u).split(".")[0]
        seq.append(None if h in ("000", "999") or h.startswith("(") else h)
    seqs.append((lid, seq))

freq = collections.Counter(h for _, s in seqs for h in s if h)
ctx = collections.defaultdict(collections.Counter)         # sign -> Counter of ("L"/"R", neighbour)
occ_ctx = collections.defaultdict(list)                     # sign -> list of contexts per occurrence
for lid, s in seqs:
    for i, h in enumerate(s):
        if not h:
            continue
        c = []
        if i > 0 and s[i - 1]:
            c.append(("L", s[i - 1]))
        if i + 1 < len(s) and s[i + 1]:
            c.append(("R", s[i + 1]))
        for x in c:
            ctx[h][x] += 1
        occ_ctx[h].append((lid, i, c))

common = sorted(h for h, n in freq.items() if n >= COMMON_MIN)
rare = sorted(h for h, n in freq.items() if RARE_MIN <= n <= RARE_MAX)
V = len(freq)
tot = {c: {"L": sum(n for (sd, _), n in ctx[c].items() if sd == "L"), "R": sum(n for (sd, _), n in ctx[c].items() if sd == "R")} for c in common}


def score(r, c):
    """log-likelihood of r's contexts under c's neighbour distribution, per context. (A base-rate term
    log P(nb) was tried and dropped: it does not depend on c, so it cannot change the ranking.)"""
    s, n = 0.0, 0
    for _, _, cs in occ_ctx[r]:
        for sd, nb in cs:
            s += math.log((ctx[c][(sd, nb)] + ADD_K) / (tot[c][sd] + ADD_K * V)); n += 1
    return s / max(1, n)


def series(h):
    try:
        return int(h) // 100
    except ValueError:
        return -1


def rank_of(r, target):
    scores = {c: score(r, c) for c in common if c != r}
    order = sorted(scores, key=lambda c: -scores[c])
    return (order.index(target) + 1 if target in scores else None), scores, order


# catalogue shape similarity, section 9
sim_signs = (out / "sign_similarity_signs.txt").read_text(encoding="utf-8").split() if (out / "sign_similarity_signs.txt").exists() else []
sim_M = np.load(out / "sign_similarity_matrix.npy") if (out / "sign_similarity_matrix.npy").exists() else None
sim_idx = {s: i for i, s in enumerate(sim_signs)}


def cat_sim(a, b):
    if sim_M is None or a not in sim_idx or b not in sim_idx:
        return float("nan")
    return float(sim_M[sim_idx[a], sim_idx[b]])


# print glyphs, where they exist
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


def dsim(d1, d2):
    return float(d1[0] @ d2[0]) * np.sqrt(min(d1[1], d2[1]) / max(d1[1], d2[1]))


print_feats = collections.defaultdict(list)
pi = out / "photo_instances.csv"
if pi.exists():
    for r in csv.DictReader(open(pi, encoding="utf-8")):
        if float(r["local_score"]) < 0.2 and r.get("source") != "manual":
            continue
        p = root / "data" / "photos" / "instances" / r["side"] / f"{r['line']}_{int(r['position']):03d}.png"
        if p.exists():
            d = descriptor(np.asarray(Image.open(p).convert("L")) < 128)
            if d is not None:
                print_feats[r["head"]].append(d)


def print_sim(a, b):
    A, B = print_feats.get(a, []), print_feats.get(b, [])
    if len(A) < 1 or len(B) < 3:
        return float("nan"), float("nan"), len(A), len(B)
    B = B[:40]
    cross = np.mean([dsim(x, y) for x in A for y in B])
    within = np.mean([dsim(B[i], B[j]) for i in range(len(B)) for j in range(i + 1, len(B))])
    return float(cross), float(within), len(A), len(B)


# the test over every rare sign with a common series-mate
rows = []
for r in rare:
    mates = [c for c in common if series(c) == series(r) and series(r) >= 0]
    if not mates:
        continue
    rk, scores, order = rank_of(r, mates[0])
    best_mate = max(mates, key=lambda c: scores[c])
    rk = order.index(best_mate) + 1
    cs, ws, na, nb = print_sim(r, best_mate)
    rows.append({"rare": r, "count": freq[r], "series_mate": best_mate, "mate_count": freq[best_mate], "mate_rank": rk, "of": len(order),
                 "best_overall": order[0], "catalogue_shape": cat_sim(r, best_mate), "print_cross": cs, "print_within_mate": ws, "print_n": f"{na}/{nb}"})

# positive control: copy-substitution pairs of section 7
pos = []
if (out / "allograph_pairs.csv").exists():
    for p in csv.DictReader(open(out / "allograph_pairs.csv", encoding="utf-8")):
        a, b = p["a"], p["b"]
        if p["candidate"] != "True":
            continue
        r, c = (a, b) if freq[a] <= freq[b] else (b, a)
        if c in common and r in occ_ctx and r != c:
            rk, scores, order = rank_of(r, c)
            pos.append((r, c, freq[r], freq[c], rk, len(order)))

# null: series labels shuffled among the common signs
obs_top3 = sum(1 for x in rows if x["mate_rank"] <= 3)
common_series = [series(c) for c in common]
orders = {}
for x in rows:
    _, scores, order = rank_of(x["rare"], x["series_mate"])
    orders[x["rare"]] = order
null = []
for _ in range(2000):
    perm = dict(zip(common, rng.permutation(common_series)))
    k = 0
    for x in rows:
        r = x["rare"]; order = orders[r]
        mates = [c for c in order if perm[c] == series(r)]
        if mates and min(order.index(c) for c in mates) + 1 <= 3:
            k += 1
    null.append(k)
p_top3 = float(np.mean(np.array(null) >= obs_top3))

with open(out / "allograph_candidates.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for x in rows:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in x.items()})

md = ["# Rare signs against the common sign of their series: a context test\n",
      f"{len(rare)} rare signs ({RARE_MIN} to {RARE_MAX} occurrences, one witness per family), {len(common)} common signs ({COMMON_MIN}+). "
      f"For each rare sign with a common series-mate, the rank of that mate among all {len(common)} common signs by how well its neighbourhoods "
      f"predict the rare sign's.\n",
      f"Series-mates at rank 1 to 3: **{obs_top3} of {len(rows)}**; with series labels shuffled among the common signs, as many or more in {p_top3:.3f} of 2000 shuffles "
      f"(mean {np.mean(null):.1f}).\n"]
if pos:
    md.append(f"Positive control, the {len(pos)} pairs that copies substitute (section 7): ranks " + ", ".join(f"{r}/{c} {rk} of {n}" for r, c, _, _, rk, n in pos) + ".\n")
md.append("## The two pairs from the hand pass\n")
md.append("| rare | count | partner | count | rank of the partner | best-fitting common sign | catalogue shape similarity | print shape: across / within the partner (n) |\n|---|---|---|---|---|---|---|---|")
for r, c in (("650", "607"), ("684", "680")):
    if c in common:
        rk, scores, order = rank_of(r, c)
        cs, ws, na, nb = print_sim(r, c)
        md.append(f"| {r} | {freq[r]} | {c} | {freq[c]} | {rk} of {len(order)} | {order[0]} | {cat_sim(r, c):.2f} | {cs:.2f} / {ws:.2f} ({na}/{nb}) |")
    else:
        md.append(f"| {r} | {freq[r]} | {c} | {freq[c]} | {c} has fewer than {COMMON_MIN} occurrences | | {cat_sim(r, c):.2f} | |")
md.append("\n## All rare signs with a common series-mate, best-supported first\n")
md.append("| rare | count | common series-mate | count | rank | best-fitting common sign | catalogue shape | print across / within (n) |\n|---|---|---|---|---|---|---|---|")
for x in sorted(rows, key=lambda x: (x["mate_rank"], -x["count"])):
    md.append(f"| {x['rare']} | {x['count']} | {x['series_mate']} | {x['mate_count']} | {x['mate_rank']} | {x['best_overall']} | {x['catalogue_shape']:.2f} | "
              f"{x['print_cross']:.2f} / {x['print_within_mate']:.2f} ({x['print_n']}) |")
(out / "allograph_candidates.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:12]))
