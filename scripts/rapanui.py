"""Compare the shape of rongorongo units with the shape of Rapa Nui words.

Rapa Nui text: the recitations Ure Vaeiko gave in 1886, printed in Rapa Nui
by W. J. Thomson, "Te Pito te Henua, or Easter Island", Smithsonian Report
for 1889 (published 1891), public domain. The OCR text from the Internet
Archive (data/rapanui/thomson1891_djvu.txt) is scanned for the Rapa Nui
passages that precede each "ENGLISH TRANSLATION" heading, and cleaned to
tokens made only of Rapa Nui letters.

Measures, for the Rapa Nui words and for the rongorongo units (one witness
per family):
  length          word length in syllables (vowel count, since every Rapa Nui
                  syllable is (C)V) against unit length in components
  doubling        share of word tokens that are full reduplications
                  (horahora, avaava) or an immediate repeat (ava ava),
                  against the share of head-sign tokens followed by the same
                  sign or units with a repeated component
  frequent items  the fifteen most frequent words and units with their lengths

Outputs (out/): rapanui.md, rapanui_words.csv, rapanui_lengths.csv
and data/rapanui/recitations_tokens.txt (the cleaned word list)
"""
import collections, csv, json, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "data" / "rapanui" / "thomson1891_djvu.txt"
out = root / "out"
if not src.exists():
    raise SystemExit("download the OCR text first: see README, section 13")

lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
VALID = re.compile(r"^[aeiouhkmnprtvg]+$")
TITLE = re.compile(r"^[A-Z][A-Z .,'\-]{4,}[.,]?\s*$")


def tokens(line):
    toks = []
    for w in re.split(r"[\s\-]+", line.lower()):
        w = re.sub(r"[^a-z]", "", w)
        if not w:
            continue
        # Rapa Nui letters only; g is allowed only as part of ng
        if VALID.match(w) and re.search(r"[aeiou]", w) and not re.search(r"(?<!n)g", w):
            toks.append(w)
        else:
            toks.append(None)
    return toks


# 1. cut the Rapa Nui passages: from a heading back to the previous heading,
#    keeping lines where most tokens are valid Rapa Nui words
passages, words = [], []
marks = [i for i, l in enumerate(lines) if "ENGLISH TRANSLATION" in l]
for m in marks:
    j = m - 1
    block = []
    while j > 0 and not TITLE.match(lines[j].strip()):
        block.append(lines[j])
        j -= 1
    block.reverse()
    title = lines[j].strip()
    kept = []
    for l in block:
        if "PLATE" in l or "Cat. No" in l or "TABLET" in l:
            continue
        t = tokens(l)
        if len(t) >= 3 and sum(x is not None for x in t) / len(t) >= 0.6:
            kept.extend(x for x in t if x)
    if len(kept) >= 20:
        passages.append((title, len(kept)))
        words.extend(kept)
(root / "data" / "rapanui" / "recitations_tokens.txt").write_text(" ".join(words), encoding="utf-8")

# if metraux_text.py has built a larger working corpus, use it for the statistics
combined = root / "data" / "rapanui" / "_combined_tokens.txt"
SOURCE_NOTE = "Thomson 1891 recitations"
if combined.exists():
    extra = combined.read_text(encoding="utf-8").split()
    if len(extra) > len(words):
        SOURCE_NOTE = f"Thomson 1891 recitations plus Metraux 1940 texts ({len(extra) - len(words)} tokens from Metraux)"
        words = extra


def syllables(w):
    return len(re.findall(r"[aeiou]", w))


def reduplicated(w):
    n = len(w)
    return n >= 4 and n % 2 == 0 and w[:n // 2] == w[n // 2:]


# 2. Rapa Nui statistics
rn_len = collections.Counter(syllables(w) for w in words)
rn_freq = collections.Counter(words)
rn_redup = sum(1 for w in words if reduplicated(w))
rn_repeat = sum(1 for a, b in zip(words, words[1:]) if a == b)
rn_doubling = (rn_redup + rn_repeat) / len(words)

# 3. rongorongo statistics, one witness per family
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))
units, heads = [], []
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    if lid[0] in "PQK":
        continue
    for u in corpus[lid]:
        c = clean(u)
        h = c.split(".")[0]
        if h in ("000", "999") or h.startswith("("):
            continue
        units.append(c)
        heads.append(h)
rr_len = collections.Counter(len(u.split(".")) for u in units)
rr_freq = collections.Counter(units)
rr_pair = sum(1 for a, b in zip(heads, heads[1:]) if a == b)
rr_inner = sum(1 for u in units if len(set(u.split("."))) < len(u.split(".")))
rr_doubling = (rr_pair + rr_inner) / len(units)

# 4. outputs
with open(out / "rapanui_words.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["word", "count", "syllables", "reduplicated"])
    for word, n in rn_freq.most_common():
        w.writerow([word, n, syllables(word), reduplicated(word)])
with open(out / "rapanui_lengths.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["length", "rapanui_word_share", "rongorongo_unit_share"])
    for k in range(1, 8):
        w.writerow([k, f"{rn_len[k] / len(words):.4f}", f"{rr_len[k] / len(units):.4f}"])


def mean(c, n):
    return sum(k * v for k, v in c.items()) / n


md = ["# Rongorongo units against Rapa Nui words\n",
      f"Rapa Nui sample: {len(words)} word tokens, {len(rn_freq)} distinct. Source: {SOURCE_NOTE}. Thomson's recitations: "
      + "; ".join(f"{t.title().strip('.,')} ({n})" for t, n in passages) + ". OCR errors remain in the sample; tokens with "
      "letters outside the Rapa Nui alphabet were dropped, and lines with fewer than 60 percent valid tokens were skipped.\n",
      f"Rongorongo sample: {len(units)} units, {len(rr_freq)} distinct, one witness per family.\n",
      "## Length\n",
      "| length | Rapa Nui words, syllables | rongorongo units, components |\n|---|---|---|"]
for k in range(1, 8):
    md.append(f"| {k} | {rn_len[k] / len(words):.1%} | {rr_len[k] / len(units):.1%} |")
md.append(f"\nMean length: Rapa Nui {mean(rn_len, len(words)):.2f} syllables per word, rongorongo {mean(rr_len, len(units)):.2f} components per unit.\n")
md.append("## Doubling\n")
md.append("| | Rapa Nui | rongorongo |\n|---|---|---|")
md.append(f"| full reduplication inside the word / repeated component inside the unit | {rn_redup / len(words):.1%} | {rr_inner / len(units):.1%} |")
md.append(f"| immediate repeat of the previous word / head sign | {rn_repeat / len(words):.1%} | {rr_pair / len(units):.1%} |")
md.append(f"| either | {rn_doubling:.1%} | {rr_doubling:.1%} |")
md.append("\n## Most frequent items\n")
md.append("| rank | Rapa Nui word | count | syllables | rongorongo unit | count | components |\n|---|---|---|---|---|---|---|")
top_rn, top_rr = rn_freq.most_common(15), rr_freq.most_common(15)
for i in range(15):
    w, n = top_rn[i]
    u, m = top_rr[i]
    md.append(f"| {i + 1} | {w} | {n} | {syllables(w)} | {u} | {m} | {len(u.split('.'))} |")
md.append(f"\nShare of tokens in the fifteen most frequent items: Rapa Nui {sum(n for _, n in top_rn) / len(words):.0%}, "
          f"rongorongo {sum(n for _, n in top_rr) / len(units):.0%}.")
md.append(f"\nMean length of the fifteen most frequent: Rapa Nui {sum(syllables(w) for w, _ in top_rn) / 15:.1f} syllables, "
          f"rongorongo {sum(len(u.split('.')) for u, _ in top_rr) / 15:.1f} components.")
(out / "rapanui.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
