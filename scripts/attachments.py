"""Are the attached components a particle layer?

Sections 6, 8 and 13 leave one fork open: the script either leaves the
grammatical particles of Rapa Nui unwritten, or writes them as the small
components fused onto head signs. With a Rapa Nui corpus of running text
now available, the two layers can be compared on shape and on density.

  particles     the closed class of Rapa Nui function words: articles,
                prepositions, tense-aspect markers, deictics and the like
                (PARTICLES below), counted in the working corpus
  attachments   every component fused onto a head sign, one witness per
                family, from the transliteration
  content words all other Rapa Nui tokens, as the comparison class

Measures
  profile   how concentrated each class is: share of the single commonest
            item, of the five commonest, and the number of types covering
            90 percent of tokens
  density   particles per content word in Rapa Nui, against attachments per
            unit and against free simple signs (Barthel 1 to 99) per unit,
            since particles could also be written as free small signs
  fit       which Rapa Nui class the attachment profile is nearer to

Outputs (out/): attachments.md, attachments_profiles.csv
"""
import collections, csv, json, math, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
PARTICLES = {"te", "he", "e", "i", "o", "a", "ki", "ka", "ko", "kua", "ku", "ma", "mo", "no", "na", "ai", "ia", "ana",
             "ra", "nei", "ena", "era", "hoki", "ro", "atu", "mai", "ake", "iho", "koe", "au", "ta", "to", "tu", "hia"}

corpus_file = root / "data" / "rapanui" / "_combined_tokens.txt"
if not corpus_file.exists():
    corpus_file = root / "data" / "rapanui" / "recitations_tokens.txt"
words = corpus_file.read_text(encoding="utf-8").split()
particles = collections.Counter(w for w in words if w in PARTICLES)
content = collections.Counter(w for w in words if w not in PARTICLES)

corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


attached = collections.Counter()
heads = collections.Counter()
units = 0
free_simple = 0
for lid, us in corpus.items():
    if lid[0] in "PQK":
        continue
    for u in us:
        c = clean(u).split(".")
        if c[0] in ("000", "999") or c[0].startswith("("):
            continue
        units += 1
        heads[c[0]] += 1
        for x in c[1:]:
            if x not in ("000",):
                attached[x] += 1
        if len(c) == 1 and c[0].isdigit() and int(c[0]) < 100:
            free_simple += 1


def profile(counter):
    tot = sum(counter.values())
    mc = counter.most_common()
    top1 = mc[0][1] / tot
    top5 = sum(n for _, n in mc[:5]) / tot
    acc, k90 = 0, 0
    for k, (_, n) in enumerate(mc, 1):
        acc += n
        if acc / tot >= 0.9:
            k90 = k; break
    H = -sum(n / tot * math.log2(n / tot) for n in counter.values())
    return {"tokens": tot, "types": len(counter), "top1": top1, "top5": top5, "types_for_90": k90, "entropy_bits": H,
            "top": ", ".join(f"{w} {n / tot:.0%}" for w, n in mc[:6])}


P = {"Rapa Nui particles": profile(particles), "Rapa Nui content words": profile(content),
     "attached components": profile(attached), "head signs": profile(heads)}

# density
n_content = sum(content.values())
n_part = sum(particles.values())
dens = {"particles per content word, Rapa Nui": n_part / n_content,
        "particles per word token, Rapa Nui": n_part / len(words),
        "attachments per unit, rongorongo": sum(attached.values()) / units,
        "units with any attachment, rongorongo": sum(1 for lid, us in corpus.items() if lid[0] not in "PQK" for u in us
                                                     if "." in clean(u) and not clean(u).startswith(("000", "999", "("))) / units,
        "free simple signs per unit, rongorongo": free_simple / units}


def distance(a, b):
    """distance between two profiles on the three concentration measures, each scaled to its range"""
    keys = ("top1", "top5", "types_for_90")
    scale = {"top1": 1.0, "top5": 1.0, "types_for_90": 200.0}
    return math.sqrt(sum(((a[k] - b[k]) / scale[k]) ** 2 for k in keys))


d_part = distance(P["attached components"], P["Rapa Nui particles"])
d_cont = distance(P["attached components"], P["Rapa Nui content words"])

with open(out / "attachments_profiles.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["class", "tokens", "types", "top1_share", "top5_share", "types_for_90pct", "entropy_bits"])
    for k, p in P.items():
        w.writerow([k, p["tokens"], p["types"], f"{p['top1']:.3f}", f"{p['top5']:.3f}", p["types_for_90"], f"{p['entropy_bits']:.2f}"])

md = ["# Attachments as particles?\n",
      f"Rapa Nui corpus: {len(words)} tokens from {corpus_file.name}; {n_part} particle tokens of {len(particles)} types, "
      f"{n_content} content tokens. Rongorongo: {units} units one witness per family, {sum(attached.values())} attached components.\n",
      "## Concentration of each class\n",
      "| class | tokens | types | commonest item | five commonest | types for 90% | entropy, bits | the commonest |",
      "|---|---|---|---|---|---|---|---|"]
for k, p in P.items():
    md.append(f"| {k} | {p['tokens']} | {p['types']} | {p['top1']:.0%} | {p['top5']:.0%} | {p['types_for_90']} | {p['entropy_bits']:.2f} | {p['top']} |")
md.append(f"\nDistance of the attachment profile from the particle profile: {d_part:.2f}; from the content-word profile: {d_cont:.2f} "
          "(three concentration measures, scaled).\n")
md.append("## Density\n")
md.append("| measure | value |\n|---|---|")
for k, v in dens.items():
    md.append(f"| {k} | {v:.2f} |")
(out / "attachments.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
