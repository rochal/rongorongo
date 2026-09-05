"""Genre clustering by sign vocabulary, and sequence entropy.

Part 1, genre. Each side of each object is a document; its vocabulary is
the head signs it uses. Sides are compared by cosine similarity of
tf-idf weighted head-sign profiles, so a side is characterised by which
signs it favours relative to the corpus, not by whether it copies another
side. Average-linkage clustering and a classical 2-D scaling of the
distances are written for the chart script.

Part 2, entropy. For heads, whole units and attached components:
  H1   unigram entropy, bits per token
  H2   conditional entropy H(next | previous), bits per token
  H2/H1 the share of a sign's information not predicted by its neighbour
plus the same for the corpus shuffled (which destroys sequence structure
but keeps frequencies). Following Rao et al. 2009 the conditional entropy
is also computed over the N most frequent tokens for N from 20 to 300,
which lets the curve be compared with published ones for other symbol
systems. The corpus is taken one witness per family so copies do not
count as predictable text.

Outputs (out/): genre_similarity.csv, genre_clusters.md, genre_mds.csv,
entropy.md, entropy_curve.csv
"""
import collections, csv, json, math, pathlib, re
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
COPIES = set("PQK")
SKIP = {"000", "999"}
MIN_SIDE = 40          # sides shorter than this are too small to profile


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


# ---------------------------------------------------------------- sides
sides = collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    sides[lid[:2]].extend(corpus[lid])
sides = {s: [u for u in v if head(u) not in SKIP and not head(u).startswith("(")] for s, v in sides.items()}
sides = {s: v for s, v in sides.items() if len(v) >= MIN_SIDE}
names = sorted(sides)

# ---------------------------------------------------------------- part 1
vocab = sorted({head(u) for v in sides.values() for u in v})
vi = {h: i for i, h in enumerate(vocab)}
tf = np.zeros((len(names), len(vocab)))
for i, s in enumerate(names):
    for u in sides[s]:
        tf[i, vi[head(u)]] += 1
tf = tf / tf.sum(axis=1, keepdims=True)
df = (tf > 0).sum(axis=0)
idf = np.log((len(names) + 1) / (df + 1)) + 1
X = tf * idf
X = X / np.linalg.norm(X, axis=1, keepdims=True)
S = X @ X.T
np.fill_diagonal(S, 1.0)
D = 1 - S

with open(out / "genre_similarity.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side"] + names)
    for i, s in enumerate(names):
        w.writerow([s] + [f"{S[i, j]:.3f}" for j in range(len(names))])

# clustering
iu = np.triu_indices(len(names), 1)
Z = linkage(D[iu], method="average")
order = dendrogram(Z, no_plot=True, labels=names)["ivl"]
labels = fcluster(Z, t=0.75, criterion="distance")
clusters = collections.defaultdict(list)
for s, c in zip(names, labels):
    clusters[c].append(s)

# classical MDS to 2-D for the chart
n = len(names)
J = np.eye(n) - np.ones((n, n)) / n
B = -0.5 * J @ (D ** 2) @ J
vals, vecs = np.linalg.eigh(B)
idx = np.argsort(vals)[::-1][:2]
coords = vecs[:, idx] * np.sqrt(np.maximum(vals[idx], 0))
with open(out / "genre_mds.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side", "units", "cluster", "x", "y", "nn1", "s1", "nn2", "s2"])
    for i, s in enumerate(names):
        nn = np.argsort(-S[i])[1:3]
        w.writerow([s, len(sides[s]), int(labels[i]), f"{coords[i, 0]:.4f}", f"{coords[i, 1]:.4f}",
                    names[nn[0]], f"{S[i, nn[0]]:.3f}", names[nn[1]], f"{S[i, nn[1]]:.3f}"])

md = ["# Genre clustering by sign vocabulary\n",
      f"{len(names)} sides with at least {MIN_SIDE} units, profiled by tf-idf weighted head-sign frequencies, "
      "compared by cosine similarity. This measures shared vocabulary, not shared passages.\n",
      "## Nearest neighbours\n", "| side | units | nearest | sim | second | sim |\n|---|---|---|---|---|---|"]
for i, s in enumerate(names):
    nn = np.argsort(-S[i])[1:3]
    md.append(f"| {s} | {len(sides[s])} | {names[nn[0]]} | {S[i, nn[0]]:.2f} | {names[nn[1]]} | {S[i, nn[1]]:.2f} |")
md.append("\n## Average-linkage clusters at distance 0.75\n")
for c, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
    md.append(f"- {', '.join(members)}")
md.append("\nDendrogram order: " + " ".join(order))
# recto vs verso of the same object
md.append("\n## Recto against verso of the same object\n")
md.append("| object | sim(recto, verso) | rank of verso among recto's neighbours |\n|---|---|---|")
for s in names:
    if s[1] in "ar":
        t = s[0] + ("b" if s[1] == "a" else "v")
        if t in names:
            i, j = names.index(s), names.index(t)
            rank = int((S[i] > S[i, j]).sum())
            md.append(f"| {s[0]} | {S[i, j]:.2f} | {rank} of {len(names) - 1} |")
(out / "genre_clusters.md").write_text("\n".join(md), encoding="utf-8")

# ---------------------------------------------------------------- part 2
def sequences(kind):
    """Token sequences, one per side, one witness per family."""
    seqs = []
    for s, v in sides.items():
        if s[0] in COPIES:
            continue
        if kind == "heads":
            seqs.append([head(u) for u in v])
        elif kind == "units":
            seqs.append([clean(u) for u in v])
        elif kind == "components":
            seqs.append([c for u in v for c in clean(u).split(".")])
    return seqs


def entropies(seqs, top=None):
    uni = collections.Counter(t for s in seqs for t in s)
    keep = None
    if top:
        keep = {t for t, _ in uni.most_common(top)}
        seqs = [[t for t in s if t in keep] for s in seqs]
        uni = collections.Counter(t for s in seqs for t in s)
    N = sum(uni.values())
    H1 = -sum(n / N * math.log2(n / N) for n in uni.values())
    big = collections.Counter((a, b) for s in seqs for a, b in zip(s, s[1:]))
    M = sum(big.values())
    left = collections.Counter()
    for (a, b), n in big.items():
        left[a] += n
    H2 = -sum(n / M * math.log2(n / left[a]) for (a, b), n in big.items())
    return H1, H2, N


rng = np.random.default_rng(7)
rows, curve = [], []
for kind in ("heads", "units", "components"):
    seqs = sequences(kind)
    H1, H2, N = entropies(seqs)
    flat = [t for s in seqs for t in s]
    shuffled = [list(rng.permutation(flat))]
    H1s, H2s, _ = entropies(shuffled)
    rows.append((kind, N, H1, H2, H2 / H1, H2s, H2s / H1s))
    for top in (20, 30, 50, 75, 100, 150, 200, 300):
        h1, h2, n = entropies(seqs, top)
        _, h2s, _ = entropies(shuffled, top)
        curve.append((kind, top, n, h1, h2, h2s))

with open(out / "entropy_curve.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["layer", "top_n", "tokens", "H1", "H2", "H2_shuffled"])
    for r in curve:
        w.writerow([r[0], r[1], r[2], f"{r[3]:.3f}", f"{r[4]:.3f}", f"{r[5]:.3f}"])

md = ["# Sequence entropy\n",
      "One witness per family (P, Q, K dropped). H1 = unigram entropy, H2 = conditional entropy of a token given "
      "the previous one, both in bits per token. Shuffled = same tokens in random order, which keeps H1 and "
      "removes all sequential structure, so H2 shuffled is the ceiling H2 could reach without any syntax. "
      "The gap between H2 and H2 shuffled is the information carried by adjacency.\n",
      "| layer | tokens | H1 | H2 | H2/H1 | H2 shuffled | H2/H1 shuffled | adjacency gain, bits |\n|---|---|---|---|---|---|---|---|"]
for kind, N, H1, H2, r, H2s, rs in rows:
    md.append(f"| {kind} | {N} | {H1:.2f} | {H2:.2f} | {r:.2f} | {H2s:.2f} | {rs:.2f} | {H2s - H2:.2f} |")
md.append("\n## Conditional entropy over the N most frequent tokens\n")
md.append("| layer | N | tokens kept | H1 | H2 | H2 shuffled |\n|---|---|---|---|---|---|")
for r in curve:
    md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} |")
md.append("\nNote on the shuffled baseline: with a finite sample, conditional entropy of a random sequence sits "
          "below H1 because rare bigrams are never seen; the shuffled column is the fair comparison, not H1 itself.")
(out / "entropy.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:8]))
print(f"{len(names)} sides, {len(clusters)} clusters")
