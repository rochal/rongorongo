"""How much text does the decipherment search need? A known Maori text at increasing lengths.

Section 23's positive control fails at every size of language model (decipher.py
--lm ...): a real Rapa Nui recitation of 1,100 syllables, treated as unknown
signs, is not recovered even under a model of six million syllables, and the
search always prefers a false assignment to the true one. That points at the
other input, the length of the text being deciphered. This script measures it
where the data allows: Maori.

  model     syllable bigrams from the Maori Bible, the 1841 New Testament and
            Grey's songs (fetch_polynesian.py), the same (C)V syllabification
            and smoothing as decipher.py
  text      Grey's 1854 prose traditions, held out entirely; its first L
            syllables for each L in LENGTHS, the 40 most frequent syllable
            types among them treated as unknown signs, the rest breaking the
            sequence, exactly as the tablets' signs are handled
  search    simulated annealing over one-to-one assignments, as decipher.py
  report    per length: syllables recovered, searched score, true score, and
            the searched score of the same text shuffled

The tablets offer 2,593 adjacent pairs among their 40 frequent signs, with
one witness per family; Apai offers about 1,100 syllables. Where the curve
crosses reliable recovery says how far short those are.

Outputs: out/decipher_length.csv, out/decipher_length.md
"""
import argparse, collections, csv, math, pathlib, re, unicodedata
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--signs", type=int, default=40)
ap.add_argument("--restarts", type=int, default=8)
ap.add_argument("--iters", type=int, default=40000)
ap.add_argument("--lengths", type=int, nargs="*", default=[500, 1000, 2000, 4000, 8000, 16000, 32000, 64000])
ap.add_argument("--seed", type=int, default=1)
args = ap.parse_args()

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
ddir = root / "data" / "polynesian"
TRAIN = ["kotepaiperatapua00barl", "kotekawenatahou00yategoog", "kongamoteateame00greygoog"]
HELD = "kongamahingaang00greygoog"
N, ADD_K = args.signs, 0.5
SYLLABLE = re.compile(r"^(?:(?:ng|[hkmnprtv])?[aeiou])+$")
CONS = ["ng", "h", "k", "m", "n", "p", "r", "t", "v"]


def tokens(text):
    outp = []
    for raw in re.split(r"[^A-Za-zÀ-ɏʻ‘’'`^]+", text):
        w = unicodedata.normalize("NFKD", raw.lower())
        w = "".join(c for c in w if not unicodedata.combining(c))
        w = re.sub(r"[ʻ‘’'`^]", "", w).replace("wh", "h").replace("w", "v")
        if w and SYLLABLE.match(w):
            outp.append(w)
    return outp


def syllabify(w):
    syl, i = [], 0
    while i < len(w):
        c = ""
        for cc in CONS:
            if w.startswith(cc, i):
                c, i = cc, i + len(cc); break
        if i < len(w) and w[i] in "aeiou":
            syl.append(c + w[i]); i += 1
        elif not c:
            i += 1
    return syl


def stream_of(ident):
    text = (ddir / f"{ident}_djvu.txt").read_text(encoding="utf-8", errors="ignore")
    return [s for w in tokens(text) for s in syllabify(w)]


def bigram_model(stream, min_count=3):
    uni = collections.Counter(stream)
    vocab = [t for t, n in uni.most_common() if n >= min_count]
    idx = {t: i for i, t in enumerate(vocab)}
    V = len(vocab)
    C = np.zeros((V, V))
    for a, b in zip(stream, stream[1:]):
        if a in idx and b in idx:
            C[idx[a], idx[b]] += 1
    P = (C + ADD_K) / (C.sum(axis=1, keepdims=True) + ADD_K * V)
    return vocab, np.log(P)


def pair_counts(seq, index, n):
    C = np.zeros((n, n))
    for a, b in zip(seq, seq[1:]):
        if a in index and b in index:
            C[index[a], index[b]] += 1
    return C


def anneal(C, logP, iters, rng):
    n, V = C.shape[0], logP.shape[0]
    m = rng.permutation(V)[:n]
    total = lambda m: float((C * logP[np.ix_(m, m)]).sum())
    cur = total(m); best, best_m = cur, m.copy()
    T0, T1 = 3.0, 0.02
    for t in range(iters):
        T = T0 * (T1 / T0) ** (t / iters)
        trial = m.copy()
        if V > n and rng.random() < 0.5:
            i = rng.integers(n); used = set(m.tolist()); free = [v for v in range(V) if v not in used]
            trial[i] = free[rng.integers(len(free))]
        else:
            i, j = rng.choice(n, 2, replace=False); trial[i], trial[j] = m[j], m[i]
        new = total(trial); delta = new - cur
        if delta >= 0 or rng.random() < math.exp(delta / T):
            m, cur = trial, new
            if cur > best:
                best, best_m = cur, m.copy()
    return best, best_m


def search(C, logP, seed):
    rng = np.random.default_rng(seed)
    best, best_m = -1e18, None
    for r in range(args.restarts):
        b, bm = anneal(C, logP, args.iters, rng)
        if b > best:
            best, best_m = b, bm
    return best / C.sum(), best_m


train = []
for ident in TRAIN:
    train += stream_of(ident)
held = stream_of(HELD)
vocab, logP = bigram_model(train)
print(f"model: {len(train)} syllables, {len(vocab)} types; held-out text: {len(held)} syllables", flush=True)

rows = []
rng_shuf = np.random.default_rng(args.seed)
for L in args.lengths:
    text = held[:L]
    if len(text) < L:
        break
    freq = collections.Counter(text)
    signs = [s for s, _ in freq.most_common(N) if s in vocab][:N]
    idx = {s: i for i, s in enumerate(signs)}
    C = pair_counts(text, idx, len(signs))
    score, m = search(C, logP, args.seed + L)
    recovered = sum(1 for s in signs if vocab[m[idx[s]]] == s) / len(signs)
    true_m = np.array([vocab.index(s) for s in signs])
    true_score = float((C * logP[np.ix_(true_m, true_m)]).sum() / C.sum())
    shuf = list(text); rng_shuf.shuffle(shuf)
    shuf_score, _ = search(pair_counts(shuf, idx, len(signs)), logP, args.seed + L + 7)
    rows.append([L, int(C.sum()), len(signs), round(recovered, 3), round(score, 4), round(true_score, 4), round(shuf_score, 4)])
    print(f"L={L}: pairs {int(C.sum())}, recovered {recovered:.0%}, searched {score:.3f}, true {true_score:.3f}, shuffled {shuf_score:.3f}", flush=True)

with open(out / "decipher_length.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["syllables", "pairs_among_signs", "signs", "recovered", "searched", "true", "shuffled_searched"]); w.writerows(rows)
md = ["# How much text does the search need?\n",
      f"A Maori syllable model from {len(train)} syllables ({len(vocab)} types); Grey's 1854 traditions held out, {len(held)} syllables. "
      f"The first L syllables, their {N} most frequent syllable types as unknown signs, searched with {args.restarts} restarts of {args.iters} steps.\n",
      "| syllables | pairs among the signs | recovered | searched | true | shuffled, searched |", "|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r[0]} | {r[1]} | {r[3]:.0%} | {r[4]:.3f} | {r[5]:.3f} | {r[6]:.3f} |")
md.append("\nThe tablets: 2,593 pairs among their 40 frequent signs. Apai: about 1,100 syllables.")
(out / "decipher_length.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
