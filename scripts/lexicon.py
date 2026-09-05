"""Build a Rapa Nui lexicon from public-domain word lists, and measure it.

Sources
  Churchill 1912, Rapanui-English vocabulary, pages 187 to 270: Roussel's
  1908 vocabulary with Geiseler's and Thomson's, one numbered or bare
  headword per entry, sub-entries and cognates indented after it.
  Thomson 1891, English-Rapanui list, pages 546 to 552, two pairs per line.

What is measured, over headword types rather than running text
  size            headwords per source and combined
  length          headword length in syllables
  reduplication   share of headwords that are full reduplications
  syllables       the inventory of (C)V syllables the lexicon uses, with
                  type frequencies, for comparison with the 46 syllable types
                  the 1886 recitations attest
  particles       headwords Churchill glosses as particles

Outputs (out/): lexicon.csv, lexicon_syllables.csv, lexicon.md
"""
import collections, csv, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "data" / "rapanui"
out = root / "out"
VALID = re.compile(r"^[aeiouhkmnprtvg]+$")
CONS = ["ng", "h", "k", "m", "n", "p", "r", "t", "v"]


def valid(w):
    return bool(VALID.match(w) and re.search(r"[aeiou]", w) and not re.search(r"(?<!n)g", w))


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


# ---------------------------------------------------------------- Churchill 1912
lines = (src / "sources" / "churchill1912.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
heads = [i for i, l in enumerate(lines) if re.match(r"\s*RAPANUI-ENG[LU]?ISH\s+VOCABULARY", l)]
finding = [i for i, l in enumerate(lines) if re.match(r"\s*ENGLISH-RAPANUI\s+FINDING", l) and i > heads[0]]
start, end = heads[0], (finding[0] if finding else heads[-1] + 400)
ENGLISH = {"to", "the", "of", "in", "on", "at", "or", "and", "as", "an", "be", "it", "is", "up", "one", "no", "not", "her",
           "him", "them", "then", "than", "there", "that", "this", "into", "upon", "out", "over", "under", "from", "with"}
entries = collections.OrderedDict()
prev = ""
for l in lines[start:end]:
    raw = l.strip()
    # a gloss wrapped onto the next line follows a line ending in a comma, a hyphen or an open bracket
    continuation = prev.endswith((",", "-", "(", ";")) or prev.endswith(" to")
    prev = raw
    if continuation:
        continue
    # an entry line starts at the margin with the headword, optionally after an entry number,
    # then a sense number or the gloss; cognate lines start with an abbreviation and a colon
    m = re.match(r"^(?:\d+\.\s+)?([a-z]{2,})\s+(?:\d+\s+)?([a-z][^:]*)$", raw)
    if not m:
        continue
    w, gloss = m.group(1), m.group(2).strip()
    if not valid(w) or w in ENGLISH or re.match(r"^(id|see|to)$", gloss):
        continue
    if re.match(r"^(mgv|mq|ta|sa|ma|ha|to|fu|pau|p|t|q|r)\b", gloss) and ":" in raw:
        continue
    if w not in entries:
        entries[w] = {"source": "Churchill/Roussel", "gloss": gloss[:80]}

# a headword that also occurs several times inside the English glosses is an
# English word caught at a line start (range, parent, other), not Rapa Nui
gloss_words = collections.Counter(t for e in entries.values() for t in re.findall(r"[a-z]+", e["gloss"]))
# and a word that recurs in Thomson's English prose, and is not a word of the
# Rapa Nui recitations, is English (orange, tent, error)
thomson_prose = (src / "thomson1891_djvu.txt").read_text(encoding="utf-8", errors="ignore").lower()
english = collections.Counter(re.findall(r"\b[a-z]+\b", thomson_prose))
rapanui_attested = set((src / "recitations_tokens.txt").read_text(encoding="utf-8").split())
KEEP = {"he", "te", "ki", "ka", "ariki", "moai", "ahu", "mana", "tapu", "rapa", "nui", "rongo"}
entries = collections.OrderedDict((w, e) for w, e in entries.items()
                                  if w in KEEP or w in rapanui_attested or (gloss_words[w] < 3 and english[w] < 2))

# ---------------------------------------------------------------- Thomson 1891
# Thomson's English-Rapanui list is set in two columns that the OCR broke into
# separate lines, so only the pairs that survived on one line are recoverable.
tl = (src / "thomson1891_djvu.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
vs = [i for i, l in enumerate(tl) if l.strip() == "VOCABULARY."]
thomson = collections.OrderedDict()
if vs:
    for l in tl[vs[-1]:vs[-1] + 700]:
        for m in re.finditer(r"([A-Z][a-z]+(?: \([a-z ]+\))?)\s+([A-Z][a-zé\-]+(?: [a-zé\-]+){0,3})\.", l):
            eng, rn = m.group(1), m.group(2).lower().replace("é", "e")
            words = [x for x in re.split(r"[\s\-]+", rn) if x]
            if all(valid(x) for x in words):
                thomson.setdefault(" ".join(words), eng)

# ---------------------------------------------------------------- measures
def describe(words):
    lens = collections.Counter(len(syllabify(w)) for w in words)
    redup = sum(1 for w in words if len(w) >= 4 and len(w) % 2 == 0 and w[:len(w) // 2] == w[len(w) // 2:])
    syl = collections.Counter(s for w in words for s in syllabify(w))
    return lens, redup, syl


all_words = list(entries) + [w.split()[0] for w in thomson if w.split()[0] not in entries]
c_lens, c_redup, c_syl = describe(list(entries))
a_lens, a_redup, a_syl = describe(all_words)
particles = [(w, e["gloss"]) for w, e in entries.items() if re.search(r"\bparticle\b|\barticle\b|\bpreposition\b|\bconjunction\b", e["gloss"])]

with open(out / "lexicon.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["headword", "syllables", "source", "gloss"])
    for word, e in entries.items():
        w.writerow([word, len(syllabify(word)), e["source"], e["gloss"]])
    for rn, eng in thomson.items():
        w.writerow([rn, len(syllabify(rn.split()[0])), "Thomson", eng])
with open(out / "lexicon_syllables.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["syllable", "headword_types_containing_it"])
    for s, n in a_syl.most_common():
        w.writerow([s, n])

rec = (src / "recitations_tokens.txt").read_text(encoding="utf-8").split()
rec_syl = collections.Counter(s for w in rec for s in syllabify(w))
md = ["# A Rapa Nui lexicon from public-domain word lists\n",
      f"Churchill 1912, carrying Roussel 1908: {len(entries)} headwords parsed. Thomson 1891: {len(thomson)} English-to-Rapa Nui pairs. "
      f"Combined distinct single-word headwords: {len(all_words)}.\n",
      "## Headword length in syllables, Churchill/Roussel\n",
      "| syllables | headwords | share |\n|---|---|---|"]
for k in sorted(c_lens):
    md.append(f"| {k} | {c_lens[k]} | {c_lens[k] / len(entries):.1%} |")
md.append(f"\nMean {sum(k * v for k, v in c_lens.items()) / len(entries):.2f} syllables per headword; "
          f"{c_redup} headwords ({c_redup / len(entries):.1%}) are full reduplications.\n")
md.append("## Syllable inventory\n")
md.append(f"Distinct (C)V syllables in the lexicon: {len(a_syl)}; in the 1886 recitations: {len(rec_syl)}. "
          f"Syllables in the lexicon absent from the recitations: {', '.join(s for s in a_syl if s not in rec_syl) or 'none'}.\n")
md.append("| syllable | lexicon types | recitation tokens |\n|---|---|---|")
for s, n in a_syl.most_common(20):
    md.append(f"| {s} | {n} | {rec_syl.get(s, 0)} |")
md.append(f"\n## Particles, as Churchill glosses them ({len(particles)})\n")
md.append(", ".join(f"*{w}* ({g[:40]})" for w, g in particles[:40]))
(out / "lexicon.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:12]))
print(f"particles: {len(particles)}")
