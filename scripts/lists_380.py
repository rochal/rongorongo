"""Extract and cluster the entries of the 380.1-delimited lists.

The compound 380.1 (seated figure + stroke; written 380.1.3 on G and K and
380.1.52 on N) separates short groups of signs on tablets E, G, K, C, N, S, Q.
This script:

  1. joins the lines of each side in reading order, so entries that run over
     a line break are kept whole;
  2. cuts every stretch that lies between two consecutive delimiters and
     treats it as one entry (stretches before the first or after the last
     delimiter of a side are not entries);
  3. clusters the entries three ways:
       exact    identical after stripping ?/! and variant letters
       head     identical when only the first component of each unit counts
       family   union-find over entries that share a non-stroke unit pair
                (bigram) or at least two non-stroke units, ligature-tolerant;
  4. tabulates the internal shape of entries: length, first and last unit,
     where the strokes sit.

Outputs (out/):
  list_entries.csv        every entry with side, line, position, text, length
  list_clusters.md        report: exact/head clusters, families, structure
  list_families.csv       family id -> members
"""
import collections, csv, json, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
out.mkdir(exist_ok=True)

MAX_ENTRY = 12          # longer stretches are treated as text between two lists
STROKES = {"001", "002", "003", "004", "005"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def is_delim(u):
    return clean(u).startswith("380.001")


# 1. join sides in reading order
sides = collections.defaultdict(list)          # "Gr" -> [(line, unit), ...]
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    for i, u in enumerate(corpus[lid]):
        sides[lid[:2]].append((lid, i, u))

# 2. cut entries
entries = []
for side, seq in sides.items():
    delims = [k for k, (_, _, u) in enumerate(seq) if is_delim(u)]
    if len(delims) < 2:
        continue
    for a, b in zip(delims, delims[1:]):
        chunk = seq[a + 1:b]
        if not chunk or len(chunk) > MAX_ENTRY:
            continue
        units = [u for _, _, u in chunk]
        entries.append({
            "id": len(entries), "tablet": side[0], "side": side,
            "line": chunk[0][0], "pos": chunk[0][1],
            "delim": clean(seq[a][2]),
            "raw": "-".join(units),
            "exact": tuple(clean(u) for u in units),
            "head": tuple(head(u) for u in units),
            "len": len(units),
        })

with open(out / "list_entries.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "tablet", "side", "line", "pos", "delimiter", "len", "entry"])
    for e in entries:
        w.writerow([e["id"], e["tablet"], e["side"], e["line"], e["pos"], e["delim"], e["len"], e["raw"]])

# 3. clusters
def group(key):
    g = collections.defaultdict(list)
    for e in entries:
        g[e[key]].append(e)
    return {k: v for k, v in g.items() if len(v) > 1}

exact_clusters = group("exact")
head_clusters = group("head")

# family: union-find over shared non-stroke bigrams / two shared non-stroke units
parent = list(range(len(entries)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    parent[find(a)] = find(b)

def content(e):
    return [h for h in e["head"] if h not in STROKES and h != "000"]

bigram_index = collections.defaultdict(list)
unit_index = collections.defaultdict(set)
for e in entries:
    c = content(e)
    for x, y in zip(c, c[1:]):
        bigram_index[(x, y)].append(e["id"])
    for x in set(c):
        unit_index[x].add(e["id"])
for ids in bigram_index.values():
    for i in ids[1:]:
        union(ids[0], i)
for e in entries:
    c = set(content(e))
    if len(c) < 2:
        continue
    for f in entries:
        if f["id"] <= e["id"]:
            continue
        if len(c & set(content(f))) >= 2:
            union(e["id"], f["id"])
families = collections.defaultdict(list)
for e in entries:
    families[find(e["id"])].append(e)
families = {k: v for k, v in families.items() if len(v) > 1}
families = dict(sorted(families.items(), key=lambda kv: (-len({e["tablet"] for e in kv[1]}), -len(kv[1]))))

with open(out / "list_families.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["family", "tablets", "members", "line", "entry"])
    for n, (k, members) in enumerate(families.items(), 1):
        tabs = "".join(sorted({e["tablet"] for e in members}))
        for e in members:
            w.writerow([n, tabs, len(members), e["line"], e["raw"]])

# 4. structure
lengths = collections.Counter(e["len"] for e in entries)
first = collections.Counter(e["head"][0] for e in entries)
last = collections.Counter(e["head"][-1] for e in entries)
stroke_pos = collections.Counter()
for e in entries:
    for i, h in enumerate(e["head"]):
        if h in STROKES:
            if i == 0: stroke_pos["first"] += 1
            elif i == e["len"] - 1: stroke_pos["last"] += 1
            else: stroke_pos["middle"] += 1
per_tablet = collections.Counter(e["tablet"] for e in entries)
delims = collections.Counter(e["delim"] for e in entries)

# report
md = [f"# 380.1 list entries\n",
      f"{len(entries)} entries bounded on both sides by a 380.1 delimiter, max {MAX_ENTRY} units, "
      f"on {len(per_tablet)} tablets: " + ", ".join(f"{t} {n}" for t, n in per_tablet.most_common()) + ".",
      "Delimiter forms: " + ", ".join(f"{d} ({n})" for d, n in delims.most_common()) + ".\n"]

md.append("## Entries repeated exactly\n")
md.append("| entry | n | tablets | lines |\n|---|---|---|---|")
for k, v in sorted(exact_clusters.items(), key=lambda kv: (-len({e['tablet'] for e in kv[1]}), -len(kv[1]))):
    md.append(f"| {'-'.join(k)} | {len(v)} | {''.join(sorted({e['tablet'] for e in v}))} | {' '.join(e['line'] for e in v)} |")

md.append("\n## Entries repeated when ligatures are ignored (first component only)\n")
md.append("| entry (heads) | n | tablets | forms |\n|---|---|---|---|")
for k, v in sorted(head_clusters.items(), key=lambda kv: (-len({e['tablet'] for e in kv[1]}), -len(kv[1]))):
    if k in exact_clusters and len(exact_clusters[k]) == len(v):
        continue
    forms = " / ".join(sorted({e['raw'] for e in v}))
    md.append(f"| {'-'.join(k)} | {len(v)} | {''.join(sorted({e['tablet'] for e in v}))} | {forms} |")

md.append(f"\n## Families: entries sharing a sign pair or two content signs ({len(families)} families)\n")
for n, (k, members) in enumerate(families.items(), 1):
    tabs = "".join(sorted({e["tablet"] for e in members}))
    md.append(f"\n**Family {n}** · {len(members)} entries · tablets {tabs}\n")
    for e in sorted(members, key=lambda e: e["line"]):
        md.append(f"- {e['line']} @{e['pos']}: `{e['raw']}`")

md.append("\n## Shape of an entry\n")
md.append("Length in units: " + ", ".join(f"{l}: {n}" for l, n in sorted(lengths.items())))
md.append("\nStroke signs (1 to 5) by position inside the entry: " + ", ".join(f"{k} {n}" for k, n in stroke_pos.most_common()))
md.append("\nMost common first sign: " + ", ".join(f"{s} ({n})" for s, n in first.most_common(8)))
md.append("\nMost common last sign: " + ", ".join(f"{s} ({n})" for s, n in last.most_common(8)))

singletons = sum(1 for e in entries if find(e["id"]) not in families)
md.append(f"\n{singletons} entries belong to no family (unique content).")

(out / "list_clusters.md").write_text("\n".join(md), encoding="utf-8")
print(f"{len(entries)} entries; {len(exact_clusters)} exact clusters; {len(head_clusters)} head clusters; {len(families)} families; {singletons} singletons")
