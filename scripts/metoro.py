"""Was Metoro consistent? His 1873 chanted readings against Barthel's signs.

Jaussen wrote down one word group per sign as Metoro chanted over four
tablets (A, B, C, E). The groups are transcribed line by line on kohaumotu
(see fetch_metoro.py). Metoro's segmentation into signs differs from
Barthel's, so the groups cannot simply be paired with the units of a line.
Instead each line is treated as a sentence pair, Barthel head signs on one
side and Metoro's word groups on the other, and a word-alignment model
(IBM Model 1, expectation maximisation) estimates for every sign the
distribution of words Metoro said for it.

Consistency of a sign = the probability of its single most likely word.
If Metoro named signs consistently, that will be high for frequent signs.
The null keeps every line's words but pairs them with the wrong lines of
the same tablet, so any consistency above the null comes from the pairing
of words with the signs actually in front of him.

Also reported: what Metoro said for each Barthel series (birds, fish,
figures, strokes), which tests Metraux's view that he described what the
signs looked like.

Outputs (out/): metoro_lines.csv, metoro_signs.csv, metoro.md
"""
import collections, csv, html, json, math, pathlib, random, re

random.seed(3)
EM_ITER = 20
NULL_TRIALS = 20
MIN_SIGN = 8
root = pathlib.Path(__file__).resolve().parent.parent
src = root / "data" / "metoro" / "html"
out = root / "out"
PARTICLES = {"te", "e", "ko", "a", "o", "i", "ki", "ka", "kua", "ku", "he", "ma", "mo", "na", "no", "hia", "ia", "ai"}


def parse_line(path):
    t = path.read_text(encoding="latin-1")
    t = re.sub(r"<I>.*?</I>", " ", t, flags=re.S | re.I)          # Jaussen's comments and the =NN= markers
    body = re.sub(r"<[^>]+>", " ", t)
    body = html.unescape(body).replace("\xa0", " ")
    if "hieroglyphs" in body:                                       # the reading follows the [Show hieroglyphs] link
        body = body.split("hieroglyphs", 1)[1].split("]", 1)[-1]
    body = body.split("Home")[0] if "Home" in body else body        # trailing navigation
    body = re.sub(r"\[p\.\s*\d+\]", " ", body)
    body = re.sub(r"=\d+=", " ", body)
    body = re.sub(r"\([A-Z]+\)\.", " ", body)
    groups = []
    for g in re.split(r"__|--|—|–", body):
        g = re.sub(r"[^a-z' ]", " ", g.lower())
        words = [w for w in g.split() if w]
        if not words:
            continue
        content = [w for w in words if w not in PARTICLES] or words
        groups.append(" ".join(content))
    return groups


corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))


def head(u):
    return re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])


pairs = []          # (line id, [signs], [words])
for f in sorted(src.glob("*.html")):
    if f.stem == "layout":
        continue
    lid = f.stem[0].upper() + f.stem[1] + f.stem[2:]        # ev04 -> Ev04
    if lid not in corpus:
        continue
    words = parse_line(f)
    signs = [head(u) for u in corpus[lid] if not head(u).startswith("(") and head(u) not in ("000", "999")]
    if len(words) >= 3 and signs:
        pairs.append((lid, signs, words))


def model1(pairs, iters=EM_ITER):
    """t[word][sign]: probability Metoro says word for sign. NULL sign absorbs extras."""
    t = collections.defaultdict(lambda: collections.defaultdict(lambda: 1.0))
    for _ in range(iters):
        count = collections.defaultdict(lambda: collections.defaultdict(float))
        total = collections.defaultdict(float)
        for _, signs, words in pairs:
            src_ = ["NULL"] + signs
            for w in words:
                z = sum(t[w][s] for s in src_)
                for s in src_:
                    c = t[w][s] / z
                    count[w][s] += c
                    total[s] += c
        t = collections.defaultdict(lambda: collections.defaultdict(float))
        for w in count:
            for s in count[w]:
                t[w][s] = count[w][s] / total[s]
    # invert to sign -> word distribution
    by_sign = collections.defaultdict(dict)
    for w in t:
        for s, p in t[w].items():
            by_sign[s][w] = p
    return by_sign


def consistency(by_sign, sign_freq):
    rows = []
    for s, n in sign_freq.items():
        if n < MIN_SIGN or s == "NULL":
            continue
        dist = by_sign.get(s, {})
        if not dist:
            continue
        top = max(dist.items(), key=lambda kv: kv[1])
        ent = -sum(p * math.log2(p) for p in dist.values() if p > 0)
        rows.append((s, n, top[0], top[1], ent))
    return rows


sign_freq = collections.Counter(s for _, signs, _ in pairs for s in signs)
by_sign = model1(pairs)
rows = consistency(by_sign, sign_freq)
mean_top = sum(r[3] * r[1] for r in rows) / sum(r[1] for r in rows)

# null: shuffle which Metoro line goes with which sign line, within a tablet
null_means = []
for _ in range(NULL_TRIALS):
    shuffled = []
    for tab in "ABCE":
        tp = [p for p in pairs if p[0][0] == tab]
        ws = [p[2] for p in tp]
        random.shuffle(ws)
        shuffled += [(lid, signs, w) for (lid, signs, _), w in zip(tp, ws)]
    bs = model1(shuffled, iters=10)
    r = consistency(bs, sign_freq)
    null_means.append(sum(x[3] * x[1] for x in r) / sum(x[1] for x in r))
null_mean = sum(null_means) / len(null_means)

# what he said per Barthel series
series_words = collections.defaultdict(collections.Counter)
for s, n, top, p, ent in rows:
    k = (int(s) // 100) * 100 if s.isdigit() else -1
    series_words[k][top] += n

# per-line counts
with open(out / "metoro_lines.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["line", "barthel_units", "metoro_groups", "ratio"])
    for lid, signs, words in pairs:
        w.writerow([lid, len(signs), len(words), f"{len(words) / len(signs):.2f}"])
with open(out / "metoro_signs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sign", "occurrences", "top_word", "p_top", "entropy_bits", "second_word", "p_second"])
    for s, n, top, p, ent in sorted(rows, key=lambda r: -r[1]):
        dist = sorted(by_sign[s].items(), key=lambda kv: -kv[1])
        second = dist[1] if len(dist) > 1 else ("", 0)
        w.writerow([s, n, top, f"{p:.3f}", f"{ent:.2f}", second[0], f"{second[1]:.3f}"])

ratios = [len(w_) / len(s_) for _, s_, w_ in pairs]
md = ["# Metoro's readings against Barthel's signs\n",
      f"{len(pairs)} lines on four tablets; {sum(len(s) for _, s, _ in pairs)} Barthel units against "
      f"{sum(len(w) for _, _, w in pairs)} of Metoro's word groups. Groups per unit: median {sorted(ratios)[len(ratios) // 2]:.2f}, "
      f"range {min(ratios):.2f} to {max(ratios):.2f}. Alignment by IBM Model 1, {EM_ITER} iterations, particles stripped from the groups.\n",
      "## Consistency\n",
      f"Weighted mean probability of a sign's top word, over signs seen at least {MIN_SIGN} times: **{mean_top:.2f}** observed, "
      f"**{null_mean:.2f}** when Metoro's lines are paired with the wrong lines of the same tablet ({NULL_TRIALS} shuffles). "
      "The difference is what the actual signs in front of him contributed.\n",
      "## The most frequent signs and what he said for them\n",
      "| sign | occurrences | top word | p | entropy, bits |\n|---|---|---|---|---|"]
for s, n, top, p, ent in sorted(rows, key=lambda r: -r[1])[:30]:
    md.append(f"| {s} | {n} | {top} | {p:.2f} | {ent:.1f} |")
md.append("\n## The most consistent signs\n")
md.append("| sign | occurrences | top word | p |\n|---|---|---|---|")
for s, n, top, p, ent in sorted([r for r in rows if r[1] >= 15], key=lambda r: -r[3])[:20]:
    md.append(f"| {s} | {n} | {top} | {p:.2f} |")
md.append("\n## What he said for each Barthel series\n")
md.append("| series | signs | top words (sign occurrences) |\n|---|---|---|")
for k in sorted(series_words):
    c = series_words[k]
    md.append(f"| {k if k >= 0 else 'other'} | {sum(1 for r in rows if ((int(r[0]) // 100) * 100 if r[0].isdigit() else -1) == k)} | "
              + ", ".join(f"{w} ({n})" for w, n in c.most_common(6)) + " |")
vocab = collections.Counter(w for _, _, ws in pairs for w in ws)
md.append(f"\n## Metoro's vocabulary\n\n{sum(vocab.values())} word groups, {len(vocab)} distinct. The twenty commonest: "
          + ", ".join(f"{w} ({n})" for w, n in vocab.most_common(20)) + ".")
(out / "metoro.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
