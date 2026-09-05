"""Two islanders on one tablet: Metoro (1873) against Ure Vaeiko (1886).

Metoro chanted sign by sign over Jaussen's four tablets. Thirteen years
later Ure Vaeiko recited over photographs of several tablets for Thomson;
two of his texts belong to tablets Metoro also chanted: "Apai" for Keiti
(E) and the song "Ate-a-renga" for Mamari (C). Ure's texts are continuous,
not divided by sign, so the two men can be compared only by what they
said, not sign by sign.

The test: does Ure's text for a tablet share more vocabulary with Metoro's
chant for that same tablet than with Metoro's chants for the other three,
and more than Ure's other recitations share with it? Vocabulary is compared
as frequency-weighted cosine similarity over content words, particles
stripped. The null is the distribution of similarities between texts that
do not belong to the same tablet.

Outputs (out/): two_islanders.csv, two_islanders.md
"""
import collections, csv, html, math, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
PARTICLES = {"te", "e", "ko", "a", "o", "i", "ki", "ka", "kua", "ku", "he", "ma", "mo", "na", "no", "hia", "ia", "ai", "ra", "nei", "to"}
VALID = re.compile(r"^[aeiouhkmnprtvg]+$")

# ---------------------------------------------------------------- Ure Vaeiko, from Thomson's OCR
lines = (root / "data" / "rapanui" / "thomson1891_djvu.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
TITLE = re.compile(r"^[A-Z][A-Z .,'\-]{4,}[.,]?\s*$")


def tokens(line):
    toks = []
    for w in re.split(r"[\s\-]+", line.lower()):
        w = re.sub(r"[^a-z]", "", w)
        if w and VALID.match(w) and re.search(r"[aeiou]", w) and not re.search(r"(?<!n)g", w):
            toks.append(w)
        elif w:
            toks.append(None)
    return toks


ure = {}
for m in [i for i, l in enumerate(lines) if "ENGLISH TRANSLATION" in l]:
    j = m - 1
    block = []
    while j > 0 and not TITLE.match(lines[j].strip()):
        block.append(lines[j]); j -= 1
    block.reverse()
    title = lines[j].strip().strip(".,").title()
    kept = []
    for l in block:
        if "PLATE" in l or "Cat. No" in l or "TABLET" in l:
            continue
        t = tokens(l)
        if len(t) >= 3 and sum(x is not None for x in t) / len(t) >= 0.6:
            kept.extend(x for x in t if x and x not in PARTICLES)
    if len(kept) >= 20:
        ure[title] = kept
# titles as the OCR block extraction names them; "Translation Of Easter Island Tablet" heads the
# love song Ate-a-renga (Mamari), "Father Mourning" is the English name of the dirge Ka ihi uiga (D),
# "Plate Xxxix" is the second half of Atua Matariri (R)
URE_TABLET = {"Apai": "E", "Translation": "C", "Eaha": "S", "Plate Xxxix": "R", "Father": "D"}
URE_NAMES = {"Apai": "Apai", "Translation": "Ate-a-renga, love song", "Eaha": "Eaha to ran ariiki kete",
             "Plate Xxxix": "Atua Matariri, second half", "Father": "Ka ihi uiga, dirge"}


def tablet_of(title):
    for k, v in URE_TABLET.items():
        if title.startswith(k):
            return v
    return None


def name_of(title):
    for k, v in URE_NAMES.items():
        if title.startswith(k):
            return v
    return title


ure = {name_of(t): w for t, w in ure.items()}
URE_TABLET = {name_of(k): v for k, v in URE_TABLET.items()}


# ---------------------------------------------------------------- Metoro, from Jaussen via kohaumotu
def parse_line(path):
    t = path.read_text(encoding="latin-1")
    t = re.sub(r"<I>.*?</I>", " ", t, flags=re.S | re.I)
    body = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    if "hieroglyphs" in body:
        body = body.split("hieroglyphs", 1)[1].split("]", 1)[-1]
    body = body.split("Home")[0] if "Home" in body else body
    body = re.sub(r"\[p\.\s*\d+\]", " ", body)
    body = re.sub(r"=\d+=", " ", body)
    words = []
    for g in re.split(r"__|--|—|–", body):
        for w in re.sub(r"[^a-z' ]", " ", g.lower()).split():
            if w not in PARTICLES:
                words.append(w)
    return words


metoro = collections.defaultdict(list)
for f in sorted((root / "data" / "metoro" / "html").glob("*.html")):
    if f.stem == "layout":
        continue
    metoro[f.stem[0].upper()].extend(parse_line(f))


def cosine(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    num = sum(ca[w] * cb[w] for w in ca if w in cb)
    return num / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())) or 1)


def shared(a, b, k=15):
    ca, cb = collections.Counter(a), collections.Counter(b)
    return sorted(((w, ca[w], cb[w]) for w in ca if w in cb), key=lambda x: -min(x[1], x[2]))[:k]


rows = []
for title, words in ure.items():
    for tab in "ABCE":
        rows.append({"ure_text": title, "ure_words": len(words), "ure_tablet": tablet_of(title) or "",
                     "metoro_tablet": tab, "metoro_words": len(metoro[tab]),
                     "same_tablet": tablet_of(title) == tab, "cosine": cosine(words, metoro[tab])})
with open(out / "two_islanders.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

matched = [r for r in rows if r["same_tablet"]]
unmatched = [r for r in rows if not r["same_tablet"]]
um = sorted(r["cosine"] for r in unmatched)
def rank_p(x):
    return sum(1 for v in um if v >= x) / len(um)

md = ["# Two islanders on one tablet\n",
      f"Ure Vaeiko's recitations (Thomson 1891), content words after stripping particles: "
      + "; ".join(f"{t} ({len(w)} words, tablet {tablet_of(t) or 'unknown'})" for t, w in ure.items()) + ".",
      "Metoro's chants (Jaussen 1893), content words: " + "; ".join(f"{t} ({len(w)})" for t, w in metoro.items()) + ".\n",
      "Two of Ure's texts belong to tablets Metoro chanted: Apai to Keiti (E), Ate-a-renga to Mamari (C).\n",
      "## Vocabulary similarity, cosine over content-word frequencies\n",
      "| Ure's text | words | for tablet | Metoro A | Metoro B | Metoro C | Metoro E |\n|---|---|---|---|---|---|---|"]
for title, words in ure.items():
    cells = []
    for tab in "ABCE":
        r = next(x for x in rows if x["ure_text"] == title and x["metoro_tablet"] == tab)
        cells.append(f"**{r['cosine']:.3f}**" if r["same_tablet"] else f"{r['cosine']:.3f}")
    md.append(f"| {title} | {len(words)} | {tablet_of(title) or ''} | " + " | ".join(cells) + " |")
md.append("\nBold cells are the two same-tablet pairs. Of the " + f"{len(unmatched)} pairs that are not the same tablet, the share scoring at least as high as each same-tablet pair: "
          + "; ".join(f"{r['ure_text']} with Metoro {r['metoro_tablet']}: {r['cosine']:.3f}, p = {rank_p(r['cosine']):.2f}" for r in matched) + ".\n")
md.append("## Words the two men share on Keiti\n")
md.append("| word | Ure, Apai | Metoro, Keiti |\n|---|---|---|")
for w, a, b in shared(ure.get("Apai", []), metoro["E"]):
    md.append(f"| {w} | {a} | {b} |")
md.append("\n## Words the two men share on Mamari\n")
md.append("| word | Ure, Ate-a-renga | Metoro, Mamari |\n|---|---|---|")
ate = ure.get("Ate-a-renga, love song", [])
for w, a, b in shared(ate, metoro["C"]):
    md.append(f"| {w} | {a} | {b} |")
# Metoro's overall vocabulary vs Ure's: how much of Ure's Keiti text is in Metoro's Keiti chant at all
if "Apai" in ure:
    mv = set(metoro["E"])
    md.append(f"\nShare of Ure's Apai word tokens that occur anywhere in Metoro's Keiti chant: "
              f"{sum(1 for w in ure['Apai'] if w in mv) / len(ure['Apai']):.0%}; in Metoro's chant for Tahua, the largest of his: "
              f"{sum(1 for w in ure['Apai'] if w in set(metoro['A'])) / len(ure['Apai']):.0%}.")
(out / "two_islanders.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
