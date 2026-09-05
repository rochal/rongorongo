"""Collocation lexicon: sign pairs and triples that co-occur beyond chance.

Adjacent head-sign pairs are scored with Dunning's log-likelihood ratio
(G2), which is robust for sparse counts, and with pointwise mutual
information (PMI) for readability. A pair is a collocation when it occurs
at least MIN_COUNT times and G2 is above 10.83 (p < 0.001 for one degree
of freedom). Triples are kept when both of their pairs are collocations.
The same is done for whole units, which finds fixed multi-unit phrases.

Copies are excluded (one witness per family). Pairs where both members are
strokes are reported separately as stroke chains, and for every chain the
head signs that immediately precede it are listed.

Outputs (out/): collocation_pairs.csv, collocation_triples.csv,
collocation_units.csv, collocations.md
"""
import collections, csv, json, math, pathlib, re

MIN_COUNT = 4
G2_MIN = 10.83
root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
COPIES = set("PQK")
SKIP = {"000", "999"}
STROKES = {"001", "002", "003", "004", "005", "009", "020", "022", "090"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


# sequences per side, one witness per family
sides = collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    if lid[0] in COPIES:
        continue
    sides[lid[:2]].extend(u for u in corpus[lid] if head(u) not in SKIP and not head(u).startswith("("))
seq_h = [[head(u) for u in v] for v in sides.values()]
seq_u = [[clean(u) for u in v] for v in sides.values()]


def g2(ab, a, b, n):
    """Log-likelihood ratio for a 2x2 contingency table of adjacent pairs."""
    def ll(k, m, p):
        return k * math.log(p) + (m - k) * math.log(1 - p) if 0 < p < 1 else 0.0
    p, p1, p2 = b / n, ab / a, (b - ab) / (n - a)
    return 2 * (ll(ab, a, p1) + ll(b - ab, n - a, p2) - ll(ab, a, p) - ll(b - ab, n - a, p))


def score(seqs):
    uni = collections.Counter(t for s in seqs for t in s)
    big = collections.Counter((a, b) for s in seqs for a, b in zip(s, s[1:]))
    spread = collections.defaultdict(set)          # pair -> sides it occurs on
    for k, s in enumerate(seqs):
        for a, b in zip(s, s[1:]):
            spread[(a, b)].add(k)
    n = sum(big.values())
    rows = []
    for (a, b), ab in big.items():
        if ab < MIN_COUNT:
            continue
        fa, fb = uni[a], uni[b]
        g = g2(ab, fa, fb, n)
        pmi = math.log2(ab * n / (fa * fb))
        rows.append({"a": a, "b": b, "count": ab, "sides": len(spread[(a, b)]), "freq_a": fa, "freq_b": fb,
                     "G2": g, "PMI": pmi, "expected": fa * fb / n})
    rows.sort(key=lambda r: -r["G2"])
    return rows, uni, big


pairs, uni_h, big_h = score(seq_h)
colls = {(r["a"], r["b"]) for r in pairs if r["G2"] >= G2_MIN}
for r in pairs:
    r["collocation"] = (r["a"], r["b"]) in colls
    r["kind"] = ("stroke chain" if r["a"] in STROKES and r["b"] in STROKES else
                 "sign + stroke" if r["b"] in STROKES else
                 "stroke + sign" if r["a"] in STROKES else "sign + sign")

# triples
tri = collections.Counter((a, b, c) for s in seq_h for a, b, c in zip(s, s[1:], s[2:]))
triples = [(abc, n) for abc, n in tri.items()
           if n >= 3 and (abc[0], abc[1]) in colls and (abc[1], abc[2]) in colls]
triples.sort(key=lambda x: -x[1])

# whole-unit pairs
upairs, uni_u, _ = score(seq_u)
ucolls = [r for r in upairs if r["G2"] >= G2_MIN]

# stroke chains and their hosts
chain_hosts = collections.defaultdict(collections.Counter)
for s in seq_h:
    i = 0
    while i < len(s):
        if s[i] in STROKES and i > 0 and s[i - 1] not in STROKES:
            j = i
            while j < len(s) and s[j] in STROKES:
                j += 1
            if j - i >= 2:
                chain_hosts[" ".join(s[i:j])][s[i - 1]] += 1
            i = j
        else:
            i += 1
chains = sorted(chain_hosts.items(), key=lambda kv: -sum(kv[1].values()))

# write
with open(out / "collocation_pairs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["a", "b", "count", "sides", "expected", "freq_a", "freq_b", "G2", "PMI", "collocation", "kind"])
    w.writeheader()
    for r in pairs:
        w.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in r.items()})
with open(out / "collocation_triples.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["a", "b", "c", "count"])
    for (a, b, c), n in triples:
        w.writerow([a, b, c, n])
with open(out / "collocation_units.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["a", "b", "count", "sides", "expected", "freq_a", "freq_b", "G2", "PMI"])
    w.writeheader()
    for r in ucolls:
        w.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in r.items() if k in w.fieldnames})

n_pairs = sum(1 for r in pairs if r["collocation"])
kinds = collections.Counter(r["kind"] for r in pairs if r["collocation"])
md = ["# Collocations\n",
      f"One witness per family, {sum(len(s) for s in seq_h)} head-sign tokens. Adjacent pairs seen at least {MIN_COUNT} times "
      f"and with G2 at or above {G2_MIN} (p < 0.001): {n_pairs} collocations out of {len(pairs)} candidate pairs. "
      + ", ".join(f"{k}: {v}" for k, v in kinds.most_common()) + ".\n"]
wide = [r for r in pairs if r["collocation"] and r["sides"] >= 3]
local = [r for r in pairs if r["collocation"] and r["sides"] < 3]
md.append(f"A collocation confined to one or two sides is a refrain inside a text; one spread over three or more sides "
          f"is a habit of the script. {len(wide)} are spread, {len(local)} are local.\n")
md.append("## Collocations spread over three or more sides\n")
md.append("| a | b | count | sides | expected | PMI | G2 | kind |\n|---|---|---|---|---|---|---|---|")
for r in wide:
    md.append(f"| {r['a']} | {r['b']} | {r['count']} | {r['sides']} | {r['expected']:.1f} | {r['PMI']:.1f} | {r['G2']:.0f} | {r['kind']} |")
md.append("\n## Local collocations: refrains inside one or two texts\n")
md.append("| a | b | count | sides | expected | PMI | G2 | kind |\n|---|---|---|---|---|---|---|---|")
for r in local[:30]:
    md.append(f"| {r['a']} | {r['b']} | {r['count']} | {r['sides']} | {r['expected']:.1f} | {r['PMI']:.1f} | {r['G2']:.0f} | {r['kind']} |")
md.append(f"\n## Triples whose both halves are collocations ({len(triples)})\n")
md.append("| a | b | c | count |\n|---|---|---|---|")
for (a, b, c), n in triples[:30]:
    md.append(f"| {a} | {b} | {c} | {n} |")
md.append(f"\n## Whole-unit pairs, ligatures included ({len(ucolls)} collocations)\n")
md.append("| a | b | count | expected | PMI | G2 |\n|---|---|---|---|---|---|")
for r in ucolls[:30]:
    md.append(f"| {r['a']} | {r['b']} | {r['count']} | {r['expected']:.1f} | {r['PMI']:.1f} | {r['G2']:.0f} |")
md.append("\n## Stroke chains of two or more and the head sign before them\n")
md.append("| chain | occurrences | preceding signs (count) |\n|---|---|---|")
for chain, hosts in chains[:25]:
    md.append(f"| {chain} | {sum(hosts.values())} | " + ", ".join(f"{h} ({n})" for h, n in hosts.most_common(6)) + " |")
(out / "collocations.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:14]))
print(f"triples: {len(triples)}, unit collocations: {len(ucolls)}, chains: {len(chains)}")
