"""Robustness pass: which findings survive a change of sign inventory?

Several candidate inventories now exist, each a table of head signs merged
into a representative:
  barthel     Barthel's numbering as is
  copies      the three recurring copy substitutions (allographs.py)
  shape       the loose shape look-alike merge, 20 pairs (allographs.py)
  metoro      Metoro's four same-word pairs (metoro_merge.py)
  consensus   Metoro pairs backed by shape or copies, 2 pairs
  union       every merge above combined

Under each, the headline measures are recomputed on the same corpus:
  families           number of copy families and their members (parallels.py)
  shared runs        strict parallel runs
  distinct heads     one witness per family
  heads for 90%      signs needed to cover 90% of tokens
  H2 gain            adjacency gain in bits, heads, against shuffled order
  doubling           share of head tokens followed by the same head
  collocations       pairs at p < 0.001 with 4+ occurrences
  stroke order       2 before 1 against 1 before 2, and 4 before 2 against 2 before 4
  list entries       380.1 entries and the share that are unique
  Staff triads       share of sign-76 segments of exactly three units

A measure is called stable when its relative change from Barthel's
numbering stays within 10 percent under every inventory.

Outputs (out/): robustness.csv, robustness.md
"""
import collections, csv, json, math, pathlib, random, re, subprocess, sys

random.seed(2)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
COPIES = set("PQK")
SKIP = {"000", "999"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def load_merge(name):
    p = out / name
    m = {}
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            m[r["head"]] = r["representative"]
    return m


def resolve(m):
    """Follow chains so every head maps to a final representative."""
    def f(x):
        seen = set()
        while x in m and x not in seen:
            seen.add(x); x = m[x]
        return x
    return {k: f(k) for k in m}


inventories = collections.OrderedDict()
inventories["barthel"] = {}
inventories["copies"] = load_merge("allograph_merge.csv")
inventories["shape"] = load_merge("allograph_merge_loose.csv")
inventories["metoro"] = load_merge("metoro_merge.csv")
inventories["consensus"] = load_merge("metoro_merge_agreed.csv")
union = {}
for k in ("copies", "shape", "metoro"):
    union.update(inventories[k])
inventories["union"] = resolve(union)
for k in inventories:
    inventories[k] = resolve(inventories[k])
    (out / "_tmp").mkdir(exist_ok=True)
    with open(out / "_tmp" / f"merge_{k}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["head", "representative"])
        for a, b in sorted(inventories[k].items()):
            w.writerow([a, b])


def heads_by_side(merge):
    sides = collections.defaultdict(list)
    units = collections.defaultdict(list)
    for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
        if lid[0] in COPIES:
            continue
        for u in corpus[lid]:
            c = clean(u).split(".")
            h = c[0]
            if h in SKIP or h.startswith("("):
                continue
            h = merge.get(h, h)
            sides[lid[:2]].append(h)
            units[lid[:2]].append(".".join([h] + c[1:]))
    return sides, units


def entropy_gain(seqs):
    def H(seqs_):
        uni = collections.Counter(t for s in seqs_ for t in s)
        big = collections.Counter((a, b) for s in seqs_ for a, b in zip(s, s[1:]))
        M = sum(big.values())
        left = collections.Counter()
        for (a, b), n in big.items():
            left[a] += n
        return -sum(n / M * math.log2(n / left[a]) for (a, b), n in big.items())
    flat = [t for s in seqs for t in s]
    sh = list(flat)
    random.shuffle(sh)
    return H([sh]) - H(seqs)


def g2(ab, a, b, n):
    def ll(k, m, p):
        return k * math.log(p) + (m - k) * math.log(1 - p) if 0 < p < 1 else 0.0
    p, p1, p2 = b / n, ab / a, (b - ab) / (n - a)
    return 2 * (ll(ab, a, p1) + ll(b - ab, n - a, p2) - ll(ab, a, p) - ll(b - ab, n - a, p))


def collocations(seqs):
    uni = collections.Counter(t for s in seqs for t in s)
    big = collections.Counter((a, b) for s in seqs for a, b in zip(s, s[1:]))
    n = sum(big.values())
    return sum(1 for (a, b), ab in big.items() if ab >= 4 and g2(ab, uni[a], uni[b], n) >= 10.83)


def families(name):
    subprocess.run([sys.executable, str(root / "scripts" / "parallels.py"), "--merge", str(out / "_tmp" / f"merge_{name}.csv"),
                    "--suffix", "_robust"], cwd=root, check=True, capture_output=True)
    txt = (out / "parallel_map_robust.md").read_text(encoding="utf-8")
    runs = int(re.search(r"(\d+) maximal shared runs", txt).group(1))
    fams = re.findall(r"- \*\*(.+?)\*\*", txt)
    return runs, len(fams), "; ".join(f.replace(", ", "/") for f in fams)


results = collections.OrderedDict()
for name, merge in inventories.items():
    sides, units = heads_by_side(merge)
    seqs = list(sides.values())
    flat = [t for s in seqs for t in s]
    freq = collections.Counter(flat)
    tot = sum(freq.values())
    acc, cov90 = 0, 0
    for k, (_, n) in enumerate(freq.most_common(), 1):
        acc += n
        if acc / tot >= 0.9:
            cov90 = k; break
    doubling = sum(1 for s in seqs for a, b in zip(s, s[1:]) if a == b) / tot
    # stroke order, using the representatives of 1, 2, 4
    r1, r2, r4 = merge.get("001", "001"), merge.get("002", "002"), merge.get("004", "004")
    pair = collections.Counter((a, b) for s in seqs for a, b in zip(s, s[1:]))
    order21 = pair[(r2, r1)] / max(1, pair[(r1, r2)]) if r1 != r2 else float("nan")
    order42 = pair[(r4, r2)] / max(1, pair[(r2, r4)]) if r4 != r2 else float("nan")
    # lists
    d = merge.get("380", "380")
    entries = []
    for lid_side, us in units.items():
        idx = [i for i, u in enumerate(us) if u.startswith(d + ".001")]
        for a, b in zip(idx, idx[1:]):
            chunk = tuple(us[a + 1:b])
            if 0 < len(chunk) <= 12:
                entries.append(chunk)
    ec = collections.Counter(entries)
    unique_share = sum(1 for e in entries if ec[e] == 1) / max(1, len(entries))
    # Staff triads at 76 (attachment-based, so head merges can only touch it through sign 76 itself)
    ia = []
    for lid in sorted((k for k in corpus if k.startswith("Ia")), key=lambda k: int(k[2:])):
        ia.extend(clean(u) for u in corpus[lid])
    ia = [u for u in ia if not u.startswith("000") and not u.startswith("999") and not u.startswith("(")]
    idx = [i for i, u in enumerate(ia) if "076" in u.split(".")[1:] or u.split(".")[0] == "076"]
    segs = [idx[j + 1] - idx[j] for j in range(len(idx) - 1)]
    tri3 = sum(1 for s in segs if s == 3) / max(1, len(segs))
    runs, nfam, fam_txt = families(name)
    # unit-level
    ufreq = collections.Counter(u for us in units.values() for u in us)
    hapax = sum(1 for v in ufreq.values() if v == 1) / len(ufreq)
    results[name] = collections.OrderedDict([
        ("signs merged", len(merge)),
        ("copy families", nfam),
        ("shared runs, strict", runs),
        ("distinct heads", len(freq)),
        ("heads for 90% of tokens", cov90),
        ("adjacency gain, bits", round(entropy_gain(seqs), 3)),
        ("doubling share", round(doubling, 4)),
        ("collocations", collocations(seqs)),
        ("order 2 before 1, ratio", round(order21, 2)),
        ("order 4 before 2, ratio", round(order42, 2)),
        ("380.1 entries", len(entries)),
        ("unique entries share", round(unique_share, 3)),
        ("Staff segments of 3", round(tri3, 3)),
        ("distinct units", len(ufreq)),
        ("unit hapax share", round(hapax, 3)),
        ("families", fam_txt),
    ])
    print(name, "done", flush=True)

for f in out.glob("parallel_*_robust.*"):
    f.unlink()

metrics = [m for m in results["barthel"] if m not in ("signs merged", "families")]
with open(out / "robustness.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["measure"] + list(results) + ["max relative change", "verdict"])
    rows_md = []
    for m in metrics:
        base = results["barthel"][m]
        vals = [results[k][m] for k in results]
        rel = [abs(v - base) / abs(base) if isinstance(v, (int, float)) and base not in (0, None) and v == v else 0 for v in vals]
        mx = max(rel)
        verdict = "stable" if mx <= 0.10 else ("moves" if mx <= 0.25 else "inventory-dependent")
        w.writerow([m] + vals + [f"{mx:.0%}", verdict])
        rows_md.append((m, vals, mx, verdict))

md = ["# Robustness to the choice of inventory\n",
      "Each measure is recomputed under six inventories. Stable: every relative change from Barthel's numbering within 10 percent. "
      "Moves: within 25 percent. Inventory-dependent: beyond that.\n",
      "| measure | " + " | ".join(results) + " | max change | verdict |",
      "|---|" + "---|" * (len(results) + 2)]
md.append("| signs merged | " + " | ".join(str(results[k]["signs merged"]) for k in results) + " | | |")
for m, vals, mx, verdict in rows_md:
    md.append(f"| {m} | " + " | ".join(str(v) for v in vals) + f" | {mx:.0%} | {verdict} |")
md.append("\n## Families under each inventory\n")
for k in results:
    md.append(f"- {k}: {results[k]['families']}")
(out / "robustness.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
