"""An honest statistical decipherment attempt, with the controls that make it honest.

Hypothesis under test: the N most frequent head signs write Rapa Nui
syllables, one syllable per sign. If so, there exists an assignment of
syllables to signs under which the sign sequences have high probability
under a Rapa Nui syllable model. The method is the one used on Ugaritic
and on substitution ciphers: search the space of assignments for the one
that maximises the bigram log-likelihood of the sign sequence.

  language model   syllable bigrams (with add-k smoothing) from the 1886
                   recitations in Thomson 1891, syllabified as (C)V; about
                   3,000 syllable tokens
  sign sequence    head signs, one witness per family, side by side; only the
                   N most frequent signs are assigned, all others break the
                   sequence so no pair spans them
  search           simulated annealing over the assignment of a syllable to
                   each sign (many signs may share a syllable), maximising
                   the sum over adjacent sign pairs of log P(syl_b | syl_a);
                   RESTARTS restarts, best kept
  score            best log-likelihood per sign pair

Controls, each searched exactly as the real sequence is:
  shuffled   the sign sequence in random order: keeps every sign's frequency,
             destroys adjacency. Any score above this comes from sign order.
  reversed   the sequence read backwards: keeps adjacency, flips direction.
             Rapa Nui bigrams are directional; a real syllabic text should
             score better forwards than backwards.
  english    the real sequence against a wrong language, English letter
             bigrams from Thomson's English prose. Since the search can fit
             any structured model to any structured sequence, the Rapa Nui
             score must beat the wrong language to mean anything.

Outputs (out/): decipher.md, decipher_mapping.csv, decipher_scores.csv
"""
import argparse, collections, csv, json, math, pathlib, random, re
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--signs", type=int, default=40, help="most frequent signs assigned, one syllable each, no two alike")
ap.add_argument("--restarts", type=int, default=12)
ap.add_argument("--iters", type=int, default=40000, help="annealing steps per restart")
ap.add_argument("--shuffles", type=int, default=5)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--lm", choices=["rapanui", "maori", "tahitian", "polynesian"], default="rapanui",
                help="language model: Rapa Nui alone, or Rapa Nui plus a related language's tokens from fetch_polynesian.py; outputs are suffixed")
args = ap.parse_args()
random.seed(args.seed); np.random.seed(args.seed)

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
N = args.signs
ADD_K = 0.5

# ---------------------------------------------------------------- Rapa Nui recitations, per text
lines = (root / "data" / "rapanui" / "thomson1891_djvu.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
TITLE = re.compile(r"^[A-Z][A-Z .,'\-]{4,}[.,]?\s*$")
VALID = re.compile(r"^[aeiouhkmnprtvg]+$")


def rn_tokens(line):
    toks = []
    for w in re.split(r"[\s\-]+", line.lower()):
        w = re.sub(r"[^a-z]", "", w)
        if not w:
            continue
        ok = VALID.match(w) and re.search(r"[aeiou]", w) and not re.search(r"(?<!n)g", w)
        toks.append(w if ok else None)
    return toks


recitations = {}
for m in [i for i, l in enumerate(lines) if "ENGLISH TRANSLATION" in l]:
    j = m - 1
    block = []
    while j > 0 and not TITLE.match(lines[j].strip()):
        block.append(lines[j]); j -= 1
    block.reverse()
    kept = []
    for l in block:
        if "PLATE" in l or "Cat. No" in l or "TABLET" in l:
            continue
        t = rn_tokens(l)
        if len(t) >= 3 and sum(x is not None for x in t) / len(t) >= 0.6:
            kept.extend(x for x in t if x)
    if len(kept) >= 20:
        recitations[lines[j].strip()] = kept
apai_key = next(k for k in recitations if k.upper().startswith("APAI"))
words = [w for k, v in recitations.items() for w in v]
words_no_apai = [w for k, v in recitations.items() if k != apai_key for w in v]
# Metraux 1940 text, if metraux_text.py has extracted it, enlarges the language model;
# Apai stays held out for the positive control
metraux_file = root / "data" / "metraux" / "rapanui_tokens.txt"
metraux_words = metraux_file.read_text(encoding="utf-8").split() if metraux_file.exists() else []
words += metraux_words
words_no_apai += metraux_words
LM_NOTE = f"Thomson recitations plus {len(metraux_words)} Metraux tokens" if metraux_words else "Thomson recitations"
# a related language, mapped to Rapa Nui phonotactics by fetch_polynesian.py, enlarges the model by
# two to three orders of magnitude; Apai is still held out, since it is not in those texts
extra_words = []
if args.lm != "rapanui":
    for lang in (["maori", "tahitian"] if args.lm == "polynesian" else [args.lm]):
        extra_words += (root / "data" / "polynesian" / f"{lang}_tokens.txt").read_text(encoding="utf-8").split()
    LM_NOTE += f" plus {len(extra_words)} {args.lm} tokens"
SUFFIX = "" if args.lm == "rapanui" else f"_{args.lm}"
CONS = ["ng", "h", "k", "m", "n", "p", "r", "t", "v"]


def syllabify(w):
    syl, i = [], 0
    while i < len(w):
        c = ""
        for cc in CONS:
            if w.startswith(cc, i):
                c, i = cc, i + len(cc); break
        if i < len(w) and w[i] in "aeiou":
            syl.append(c + w[i]); i += 1
        elif c:
            continue          # consonant without vowel (OCR slip): drop it
        else:
            i += 1
    return syl


_syl_cache = {}


def syllabify_cached(w):
    if w not in _syl_cache:
        _syl_cache[w] = syllabify(w)
    return _syl_cache[w]


extra_stream = [s for w in extra_words for s in syllabify_cached(w)]
rn_stream = [s for w in words for s in syllabify(w)] + extra_stream
rn_train = [s for w in words_no_apai for s in syllabify(w)] + extra_stream        # model for the positive control
apai_stream = [s for w in recitations[apai_key] for s in syllabify(w)]


def bigram_model(stream, min_count=1):
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


rn_vocab, rn_logP = bigram_model(rn_stream, min_count=3)
tr_vocab, tr_logP = bigram_model(rn_train, min_count=3)

# ---------------------------------------------------------------- English letter model, the wrong language
eng = (root / "data" / "rapanui" / "thomson1891_djvu.txt").read_text(encoding="utf-8", errors="ignore")
eng = re.sub(r"[^a-z ]", "", eng.lower())
eng = re.sub(r"\s+", " ", eng)
en_stream = [c for c in eng if c != " "]
en_vocab, en_logP = bigram_model(en_stream, min_count=50)

# ---------------------------------------------------------------- sign sequence
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))


def head(u):
    return re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])


seqs = collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    if lid[0] in "PQK":
        continue
    for u in corpus[lid]:
        h = head(u)
        if h in ("000", "999") or h.startswith("("):
            seqs[lid[:2]].append(None)
        else:
            seqs[lid[:2]].append(h)
freq = collections.Counter(h for s in seqs.values() for h in s if h)
signs = [s for s, _ in freq.most_common(N)]
sidx = {s: i for i, s in enumerate(signs)}


def pair_counts(sequences, index, n):
    C = np.zeros((n, n))
    for s in sequences:
        for a, b in zip(s, s[1:]):
            if a in index and b in index:
                C[index[a], index[b]] += 1
    return C


# ---------------------------------------------------------------- search
def anneal(C, logP, iters, rng):
    """Maximise sum_ij C[i,j] * logP[m[i], m[j]] over one-to-one assignments m: sign -> token.
    Moves: give a sign an unused token, or swap the tokens of two signs."""
    n, V = C.shape[0], logP.shape[0]
    m = rng.permutation(V)[:n]
    def total(m):
        return float((C * logP[np.ix_(m, m)]).sum())
    cur = total(m)
    best, best_m = cur, m.copy()
    T0, T1 = 3.0, 0.02
    for t in range(iters):
        T = T0 * (T1 / T0) ** (t / iters)
        trial = m.copy()
        if V > n and rng.random() < 0.5:
            i = rng.integers(n)
            used = set(m.tolist())
            free = [v for v in range(V) if v not in used]
            trial[i] = free[rng.integers(len(free))]
        else:
            i, j = rng.choice(n, 2, replace=False)
            trial[i], trial[j] = m[j], m[i]
        new = total(trial)
        delta = new - cur
        if delta >= 0 or rng.random() < math.exp(delta / T):
            m, cur = trial, new
            if cur > best:
                best, best_m = cur, m.copy()
    return best, best_m


def search(C, logP, label):
    rng = np.random.default_rng(abs(hash(label)) % (2 ** 32))
    best, best_m = -1e18, None
    for r in range(args.restarts):
        b, bm = anneal(C, logP, args.iters, rng)
        if b > best:
            best, best_m = b, bm
    return best / C.sum(), best_m


real_seqs = list(seqs.values())
C_real = pair_counts(real_seqs, sidx, N)
N_EN = min(N, len(en_vocab) - 2)                       # English has 26 letters; keep the mapping one-to-one
signs_en = signs[:N_EN]
sidx_en = {s: i for i, s in enumerate(signs_en)}
print(f"{N} signs, {int(C_real.sum())} adjacent pairs among them; Rapa Nui syllables {len(rn_vocab)}, "
      f"English letters {len(en_vocab)} (English control on {N_EN} signs); {args.restarts} restarts x {args.iters} steps", flush=True)

scores = collections.OrderedDict()
scores["real, Rapa Nui"], mapping = search(C_real, rn_logP, "real-rn")
print("real, Rapa Nui", round(scores["real, Rapa Nui"], 4), flush=True)
rev = [list(reversed(s)) for s in real_seqs]
scores["reversed, Rapa Nui"], _ = search(pair_counts(rev, sidx, N), rn_logP, "rev-rn")
print("reversed", round(scores["reversed, Rapa Nui"], 4), flush=True)
shuf_scores = []
flat = [h for s in real_seqs for h in s]
for k in range(args.shuffles):
    random.shuffle(flat)
    shuf_scores.append(search(pair_counts([flat], sidx, N), rn_logP, f"shuf-{k}")[0])
    print("shuffled", k, round(shuf_scores[-1], 4), flush=True)
scores["shuffled, Rapa Nui, mean"] = float(np.mean(shuf_scores))
scores["shuffled, Rapa Nui, max"] = float(np.max(shuf_scores))
C_real_en = pair_counts(real_seqs, sidx_en, N_EN)
scores[f"real, English letters ({N_EN} signs)"], _ = search(C_real_en, en_logP, "real-en")
print("real, English", round(scores[f"real, English letters ({N_EN} signs)"], 4), flush=True)
shuf_en = []
for k in range(min(3, args.shuffles)):
    random.shuffle(flat)
    shuf_en.append(search(pair_counts([flat], sidx_en, N_EN), en_logP, f"shuf-en-{k}")[0])
scores[f"shuffled, English letters ({N_EN} signs), mean"] = float(np.mean(shuf_en))
# Rapa Nui on the same reduced sign set, so the two languages are compared like for like
scores[f"real, Rapa Nui ({N_EN} signs)"], _ = search(C_real_en, rn_logP, "real-rn-small")
shuf_rn_small = []
for k in range(min(3, args.shuffles)):
    random.shuffle(flat)
    shuf_rn_small.append(search(pair_counts([flat], sidx_en, N_EN), rn_logP, f"shuf-rn-small-{k}")[0])
scores[f"shuffled, Rapa Nui ({N_EN} signs), mean"] = float(np.mean(shuf_rn_small))

# positive control: Apai's own syllables treated as unknown signs, against a
# model trained on the other recitations. The search should recover the truth.
apai_freq = collections.Counter(apai_stream)
apai_signs = [s for s, _ in apai_freq.most_common(N) if s in tr_vocab][:N]
aidx = {s: i for i, s in enumerate(apai_signs)}
C_apai = pair_counts([apai_stream], aidx, len(apai_signs))
pos_score, pos_map = search(C_apai, tr_logP, "positive")
recovered = sum(1 for s in apai_signs if tr_vocab[pos_map[aidx[s]]] == s) / len(apai_signs)
true_map = np.array([tr_vocab.index(s) for s in apai_signs])
true_score = float((C_apai * tr_logP[np.ix_(true_map, true_map)]).sum() / C_apai.sum())
ap_shuf = list(apai_stream); random.shuffle(ap_shuf)
pos_shuf, _ = search(pair_counts([ap_shuf], aidx, len(apai_signs)), tr_logP, "positive-shuf")
scores["positive control: Apai syllables as unknown signs, searched"] = pos_score
scores["positive control: Apai under the true assignment"] = true_score
scores["positive control: Apai shuffled, searched"] = pos_shuf
print(f"positive control: recovered {recovered:.0%} of {len(apai_signs)} syllables; searched {pos_score:.3f}, true {true_score:.3f}, shuffled {pos_shuf:.3f}", flush=True)

# reference: how well does real Rapa Nui score under its own model, and shuffled Rapa Nui?
def stream_score(stream, vocab, logP):
    idx = {t: i for i, t in enumerate(vocab)}
    tot = n = 0
    for a, b in zip(stream, stream[1:]):
        if a in idx and b in idx:
            tot += logP[idx[a], idx[b]]; n += 1
    return tot / n
scores["Rapa Nui text under its own model"] = stream_score(rn_stream, rn_vocab, rn_logP)
rs = list(rn_stream); random.shuffle(rs)
scores["shuffled Rapa Nui text under its own model"] = stream_score(rs, rn_vocab, rn_logP)

# ---------------------------------------------------------------- outputs
with open(out / f"decipher_scores{SUFFIX}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["condition", "log_likelihood_per_pair"])
    for k, v in scores.items():
        w.writerow([k, f"{v:.4f}"])
with open(out / f"decipher_mapping{SUFFIX}.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sign", "tokens", "syllable"])
    for s in signs:
        w.writerow([s, freq[s], rn_vocab[mapping[sidx[s]]]])

gain_rn = scores["real, Rapa Nui"] - scores["shuffled, Rapa Nui, mean"]
gain_en = scores[f"real, English letters ({N_EN} signs)"] - scores[f"shuffled, English letters ({N_EN} signs), mean"]
gain_rn_small = scores[f"real, Rapa Nui ({N_EN} signs)"] - scores[f"shuffled, Rapa Nui ({N_EN} signs), mean"]
gain_rev = scores["real, Rapa Nui"] - scores["reversed, Rapa Nui"]
gain_pos = pos_score - pos_shuf
md = ["# A statistical decipherment attempt\n",
      f"The {N} most frequent head signs, {int(C_real.sum())} adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by "
      f"simulated annealing ({args.restarts} restarts of {args.iters} steps) to maximise bigram log-likelihood under a model "
      f"built from {len(rn_stream)} syllables ({LM_NOTE}; {len(rn_vocab)} syllable types with 3+ occurrences).\n",
      "## Scores, log-likelihood per adjacent pair (higher is better)\n",
      "| condition | score |\n|---|---|"]
for k, v in scores.items():
    md.append(f"| {k} | {v:.3f} |")
md.append(f"\n- Gain of the real sequence over its shuffles under Rapa Nui, {N} signs: **{gain_rn:+.3f}**")
md.append(f"- Same on {N_EN} signs, Rapa Nui: **{gain_rn_small:+.3f}**; English letters, the wrong language: **{gain_en:+.3f}**")
md.append(f"- Forward minus reversed under Rapa Nui: **{gain_rev:+.3f}**")
md.append(f"- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **{gain_pos:+.3f}**, "
          f"{recovered:.0%} of {len(apai_signs)} syllables recovered correctly, searched score {pos_score:.3f} against {true_score:.3f} for the true assignment.\n")
md.append("## The best assignment, for what it is worth\n")
md.append("| sign | tokens | syllable |\n|---|---|---|")
for s in signs[:25]:
    md.append(f"| {s} | {freq[s]} | {rn_vocab[mapping[sidx[s]]]} |")
(out / f"decipher{SUFFIX}.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:14]))
