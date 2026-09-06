"""Do whole glyphs have the statistics of Polynesian words, at matched sample size?

Section 8 found that whole units (compound glyphs) have a word-like
frequency profile and head signs do not, but the only language it could
compare with was Rapa Nui, three thousand tokens against the corpus's
nine thousand. The Maori and Tahitian streams from fetch_polynesian.py
allow the comparison to be made like for like: contiguous windows of
exactly the corpus's size are drawn from each language, as words and as
syllables, and the same statistics computed on each, so that the glyph
values can be placed inside or outside the bands that real words and
real syllables produce at that size.

  glyph streams   units (whole compounds) and heads (main signs), one
                  witness per family as in inventory.py; the corpus in its
                  own order, side by side
  reference       Maori words, Tahitian words, Maori syllables, Tahitian
                  syllables; WINDOWS contiguous windows of the glyph
                  stream's length at random starts, so that each window is
                  a run of text, not a bag of words
  statistics      distinct types; hapax share of types; share of tokens in
                  the ten commonest types; Zipf slope over the top 200
                  ranks; the type-token curve at STEPS points
  Rapa Nui        the recitations and Metraux texts are too short to window
                  at the corpus's size, so the comparison there is made the
                  other way round: windows of the glyph streams at Rapa
                  Nui's size against Rapa Nui's single values

Outputs: out/matched_stats.csv, out/matched_stats_curves.csv, out/matched_stats.md
"""
import collections, csv, json, pathlib, re
import numpy as np

WINDOWS = 300
STEPS = 12
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
rng = np.random.default_rng(11)
CONS = ["ng", "h", "k", "m", "n", "p", "r", "t", "v"]


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


units, heads = [], []
for lid in sorted(corpus, key=lambda k: (k[:2], int(re.sub(r"\D", "", k[2:]) or 0))):
    if lid[0] in "PQK":
        continue
    for u in corpus[lid]:
        c = clean(u).split(".")
        if c[0] in ("000", "999") or c[0].startswith("("):
            continue
        units.append(".".join(c)); heads.append(c[0])


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


def load_words(path):
    return path.read_text(encoding="utf-8").split()


refs = {}
for lang in ("maori", "tahitian"):
    w = load_words(root / "data" / "polynesian" / f"{lang}_tokens.txt")
    refs[f"{lang} words"] = w
    refs[f"{lang} syllables"] = [s for x in w for s in syllabify(x)]
rn_file = root / "data" / "rapanui" / "_combined_tokens.txt"
if not rn_file.exists():
    rn_file = root / "data" / "rapanui" / "recitations_tokens.txt"
rapanui = load_words(rn_file)
rapanui_syl = [s for x in rapanui for s in syllabify(x)]


def stats(stream):
    c = collections.Counter(stream)
    n = len(stream)
    freqs = sorted(c.values(), reverse=True)
    top = freqs[:200]
    x = np.log(np.arange(1, len(top) + 1)); y = np.log(top)
    slope = -float(np.polyfit(x, y, 1)[0]) if len(top) > 5 else float("nan")
    return {"tokens": n, "types": len(c), "hapax_share": sum(1 for v in c.values() if v == 1) / len(c),
            "top10_share": sum(freqs[:10]) / n, "zipf_top200": slope}


def ttr_curve(stream, n):
    pts = np.linspace(n / STEPS, n, STEPS).astype(int)
    seen, curve, j = set(), [], 0
    for p in pts:
        for t in stream[j:p]:
            seen.add(t)
        j = p
        curve.append(len(seen))
    return pts, curve


def windows(stream, n, k):
    starts = rng.integers(0, len(stream) - n, k)
    return [stream[s:s + n] for s in starts]


KEYS = ["types", "hapax_share", "top10_share", "zipf_top200"]
rows, curve_rows = [], []
n = len(units)
glyph = {"units": units, "heads": heads}
for name, stream in glyph.items():
    st = stats(stream)
    rows.append({"series": name, "size": n, **{k: st[k] for k in KEYS}, "lo": "", "hi": "", "kind": "glyphs"})
    pts, cv = ttr_curve(stream, n)
    for p, v in zip(pts, cv):
        curve_rows.append([name, p, v, v, v])
for name, stream in refs.items():
    vals = collections.defaultdict(list); curves = []
    for w in windows(stream, n, WINDOWS):
        st = stats(w)
        for k in KEYS:
            vals[k].append(st[k])
        curves.append(ttr_curve(w, n)[1])
    rows.append({"series": name, "size": n, **{k: float(np.mean(vals[k])) for k in KEYS},
                 "lo": {k: float(np.percentile(vals[k], 2.5)) for k in KEYS}, "hi": {k: float(np.percentile(vals[k], 97.5)) for k in KEYS}, "kind": "reference"})
    curves = np.array(curves)
    for i, p in enumerate(pts):
        curve_rows.append([name, p, float(np.mean(curves[:, i])), float(np.percentile(curves[:, i], 2.5)), float(np.percentile(curves[:, i], 97.5))])

# the Rapa Nui comparison, at Rapa Nui's size
n_rn = min(len(rapanui), len(units) - 1)
rn_rows = []
for name, stream in (("Rapa Nui words", rapanui), ("Rapa Nui syllables", rapanui_syl[:n_rn])):
    st = stats(stream[:n_rn]); rn_rows.append({"series": name, "size": n_rn, **{k: st[k] for k in KEYS}, "lo": "", "hi": "", "kind": "Rapa Nui"})
for name, stream in glyph.items():
    vals = collections.defaultdict(list)
    for w in windows(stream, n_rn, WINDOWS):
        st = stats(w)
        for k in KEYS:
            vals[k].append(st[k])
    rn_rows.append({"series": f"{name} at Rapa Nui's size", "size": n_rn, **{k: float(np.mean(vals[k])) for k in KEYS},
                    "lo": {k: float(np.percentile(vals[k], 2.5)) for k in KEYS}, "hi": {k: float(np.percentile(vals[k], 97.5)) for k in KEYS}, "kind": "glyph windows"})

with open(out / "matched_stats.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["series", "kind", "size", "types", "types_lo", "types_hi", "hapax_share", "hapax_lo", "hapax_hi", "top10_share", "top10_lo", "top10_hi", "zipf_top200", "zipf_lo", "zipf_hi"])
    for r in rows + rn_rows:
        line = [r["series"], r["kind"], r["size"]]
        for k in KEYS:
            v = r[k]; lo = r["lo"][k] if r["lo"] else ""; hi = r["hi"][k] if r["hi"] else ""
            line += [f"{v:.4f}" if isinstance(v, float) else v, f"{lo:.4f}" if lo != "" else "", f"{hi:.4f}" if hi != "" else ""]
        w.writerow(line)
with open(out / "matched_stats_curves.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["series", "tokens", "types_mean", "types_lo", "types_hi"]); w.writerows(curve_rows)


def cell(r, k):
    v = r[k]
    s = f"{v:,.0f}" if k == "types" else (f"{v:.2f}" if k == "zipf_top200" else f"{v:.0%}")
    if r["lo"]:
        lo, hi = r["lo"][k], r["hi"][k]
        s += " (" + (f"{lo:,.0f} to {hi:,.0f}" if k == "types" else (f"{lo:.2f} to {hi:.2f}" if k == "zipf_top200" else f"{lo:.0%} to {hi:.0%}")) + ")"
    return s


def place(r, ref):
    """where a glyph value falls against a reference band"""
    outp = []
    for k in KEYS:
        lo, hi = ref["lo"][k], ref["hi"][k]
        outp.append("inside" if lo <= r[k] <= hi else ("below" if r[k] < lo else "above"))
    return outp


md = ["# Glyph statistics against Polynesian words and syllables, at matched sample size\n",
      f"Glyph streams of {n:,} tokens, one witness per family. Reference values are the mean over {WINDOWS} contiguous windows of {n:,} tokens, with the 2.5 to 97.5 percentile range.\n",
      "| series | distinct types | hapax share of types | tokens in the ten commonest | Zipf slope, top 200 |", "|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['series']} | " + " | ".join(cell(r, k) for k in KEYS) + " |")
md.append("\n## Where the glyph values fall\n")
md.append("| glyphs | against | types | hapax share | top-ten share | Zipf slope |\n|---|---|---|---|---|---|")
for g in rows[:2]:
    for ref in rows[2:]:
        md.append(f"| {g['series']} | {ref['series']} | " + " | ".join(place(g, ref)) + " |")
md.append(f"\n## At Rapa Nui's size, {n_rn:,} tokens\n")
md.append("| series | distinct types | hapax share of types | tokens in the ten commonest | Zipf slope, top 200 |\n|---|---|---|---|---|")
for r in rn_rows:
    md.append(f"| {r['series']} | " + " | ".join(cell(r, k) for k in KEYS) + " |")
(out / "matched_stats.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
