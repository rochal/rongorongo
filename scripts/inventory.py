"""Sign inventory and frequency curves.

Counts three inventories over the corpus:

  heads       first component of every unit (the main sign)
  attached    every later component (what is fused onto a main sign)
  units       whole compounds as written, after stripping ?/! and variant letters

For each: distinct signs, hapax legomena, how many signs cover 50/90/95/99 %
of the text, and the rank-frequency curve with a Zipf exponent fitted by
least squares on log-log axes.

Everything is computed twice: on the full corpus and on one witness per
family (P, Q and K dropped, since they copy H and G), so that copied texts
do not inflate the counts.

Outputs (out/): inventory.md, inventory_heads.csv, inventory_attached.csv,
inventory_units.csv
"""
import collections, csv, json, math, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
COPIES = set("PQK")
ILLEGIBLE = {"000", "999"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def counters(lines):
    heads, attached, units = collections.Counter(), collections.Counter(), collections.Counter()
    for lid in lines:
        for u in corpus[lid]:
            c = clean(u).split(".")
            if c[0] in ILLEGIBLE or c[0].startswith("("):
                continue
            heads[c[0]] += 1
            units[".".join(c)] += 1
            for x in c[1:]:
                if x not in ILLEGIBLE:
                    attached[x] += 1
    return {"heads": heads, "attached": attached, "units": units}


def coverage(counter):
    total = sum(counter.values())
    acc, marks, k = 0, {}, 0
    for _, n in counter.most_common():
        k += 1
        acc += n
        for p in (50, 90, 95, 99):
            if p not in marks and acc / total >= p / 100:
                marks[p] = k
    return marks


def zipf(counter, top=None):
    freqs = [n for _, n in counter.most_common()]
    if top:
        freqs = freqs[:top]
    xs = [math.log(r + 1) for r in range(len(freqs))]
    ys = [math.log(f) for f in freqs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return -sxy / sxx


def describe(name, c):
    total = sum(c.values())
    hapax = sum(1 for n in c.values() if n == 1)
    cov = coverage(c)
    return {
        "inventory": name, "tokens": total, "distinct": len(c), "hapax": hapax,
        "hapax_share": hapax / len(c),
        "cov50": cov.get(50), "cov90": cov.get(90), "cov95": cov.get(95), "cov99": cov.get(99),
        "zipf_all": zipf(c), "zipf_top50": zipf(c, 50), "zipf_top200": zipf(c, 200),
    }


sets = {
    "full corpus": sorted(corpus),
    "one witness per family": sorted(k for k in corpus if k[0] not in COPIES),
}
summary = []
curves = {}
for label, lines in sets.items():
    cs = counters(lines)
    for name, c in cs.items():
        d = describe(name, c)
        d["set"] = label
        summary.append(d)
        curves[(label, name)] = c

for name in ("heads", "attached", "units"):
    with open(out / f"inventory_{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "sign", "count_full", "share_full", "cum_share_full", "count_one_witness"])
        full = curves[("full corpus", name)]
        one = curves[("one witness per family", name)]
        total = sum(full.values())
        acc = 0
        for r, (s, n) in enumerate(full.most_common(), 1):
            acc += n
            w.writerow([r, s, n, f"{n / total:.4f}", f"{acc / total:.4f}", one.get(s, 0)])

# report
md = ["# Sign inventory\n",
      "Illegible signs (000, 999) and the Staff's divider are excluded. Variant letters and ?/! are stripped; "
      "so 522fy and 522 count as one sign, and 380.001 and 380.001.003 are one head with different attachments.\n"]
md.append("## Summary\n")
md.append("| set | inventory | tokens | distinct | hapax | hapax share | signs for 50% | 90% | 95% | 99% | Zipf slope all | top 50 | top 200 |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for d in summary:
    md.append(f"| {d['set']} | {d['inventory']} | {d['tokens']} | {d['distinct']} | {d['hapax']} | {d['hapax_share']:.0%} | "
              f"{d['cov50']} | {d['cov90']} | {d['cov95']} | {d['cov99']} | {d['zipf_all']:.2f} | {d['zipf_top50']:.2f} | {d['zipf_top200']:.2f} |")

md.append("\n## Rank-frequency curve, head signs, one witness per family\n")
c = curves[("one witness per family", "heads")]
total = sum(c.values())
mc = c.most_common()
md.append("| rank | sign | count | share | cumulative |\n|---|---|---|---|---|")
acc = 0
marks = {1, 2, 3, 5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500}
for r, (s, n) in enumerate(mc, 1):
    acc += n
    if r in marks or r == len(mc):
        md.append(f"| {r} | {s} | {n} | {n / total:.1%} | {acc / total:.1%} |")

md.append("\n## Head signs by Barthel series, one witness per family\n")
md.append("Barthel numbered geometric signs below 100, human figures 200 to 399, heads and limbs 400 to 599, birds 600 to 699, fish and animals 700 to 799.\n")
md.append("| series | distinct signs | tokens | share of text |\n|---|---|---|---|")
series = collections.defaultdict(lambda: [0, 0])
for s, n in c.items():
    k = (int(s) // 100) * 100 if s.isdigit() else "other"
    series[k][0] += 1
    series[k][1] += n
for k in sorted(series, key=lambda x: (isinstance(x, str), x)):
    d, n = series[k]
    md.append(f"| {k} | {d} | {n} | {n / total:.1%} |")

md.append("\n## Top attached components, one witness per family\n")
a = curves[("one witness per family", "attached")]
ta = sum(a.values())
md.append("| component | count | share of attachments |\n|---|---|---|")
for s, n in a.most_common(15):
    md.append(f"| {s} | {n} | {n / ta:.1%} |")

md.append("\n## Reference points\n")
md.append("- Rapa Nui has about 55 syllables (10 consonants x 5 vowels, plus bare vowels). A pure syllabary would need "
          "roughly that many signs, and almost every sign would recur.\n"
          "- Linear B, a syllabary with some logograms, has about 90 signs; Cypriot about 55.\n"
          "- Logographic and mixed scripts run to hundreds or thousands of signs with a long tail of rare ones: "
          "Maya about 800 known signs, Egyptian about 700 in the classical period, Chinese several thousand.")
(out / "inventory.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:9]))
