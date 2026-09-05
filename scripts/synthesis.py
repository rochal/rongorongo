"""Bring the analyses together: a typology of texts and a dossier of signs.

Reads the tables the other scripts wrote to out/ and the corpus, and
produces two reference tables.

typology.csv / typology.md   one row per side of each object: size, copy
    family, share with a parallel elsewhere, internal repeats, 380.1
    delimiters and list entries, alternating series, share of units carrying
    sign 76, carved dividers, vocabulary neighbours, whether Metoro chanted
    it, and a type label derived from those facts.

sign_dossier.csv / sign_dossier.md   one row per head sign with at least
    MIN_TOKENS tokens (one witness per family): frequency and series, how
    often it is bare or carries attachments and which, what it attaches to,
    its strongest left and right neighbours, shape look-alikes, Metoro's
    word and consistency, copy-substitution partners, roles as alternation
    head, list-entry member, and Staff triad slot.
"""
import collections, csv, json, pathlib, re

MIN_TOKENS = 20
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
COPIES = set("PQK")
NAMES = {"A": "Tahua", "B": "Aruku Kurenga", "C": "Mamari", "D": "Échancrée", "E": "Keiti", "F": "Chauvet fragment",
         "G": "Small Santiago", "H": "Great Santiago", "I": "Santiago Staff", "J": "Reimiro 1", "K": "Small London",
         "L": "Reimiro 2", "M": "Great Vienna", "N": "Small Vienna", "O": "Berlin", "P": "Great St Petersburg",
         "Q": "Small St Petersburg", "R": "Small Washington", "S": "Great Washington", "T": "Honolulu 1", "U": "Honolulu 2",
         "V": "Honolulu 3", "W": "Honolulu 4", "X": "Tangata manu", "Y": "Paris snuffbox", "Z": "Poike"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def read(name):
    p = out / name
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def md_pct(line, side):
    m = re.search(rf"\| {side} \| (\d+) \| (\d+) \| (\d+)%", line)
    return int(m.group(3)) if m else None


# ------------------------------------------------------------------ sides
sides = collections.defaultdict(list)
lines_per_side = collections.Counter()
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    sides[lid[:2]].extend(corpus[lid])
    lines_per_side[lid[:2]] += 1

coverage = {}
for name, key in (("parallel_map.md", "strict"), ("parallel_map_fuzzy.md", "fuzzy")):
    if (out / name).exists():
        for line in open(out / name, encoding="utf-8"):
            m = re.match(r"\| ([A-Z][abrv]) \| (\d+) \| (\d+) \| (\d+)%", line)
            if m:
                coverage.setdefault(m.group(1), {})[key] = int(m.group(4))

families = {}
for line in open(out / "parallel_map_fuzzy.md", encoding="utf-8"):
    m = re.match(r"- \*\*(.+?)\*\*", line)
    if m:
        members = [s.strip() for s in m.group(1).split(",")]
        label = "/".join(members)
        for s in members:
            families[s] = label

internal = collections.Counter()
for r in read("parallel_runs.csv"):
    if r["side_a"] == r["side_b"]:
        internal[r["side_a"]] += 1

genre = {r["side"]: r for r in read("genre_mds.csv")}
alts = collections.Counter(r["line"][:2] for r in read("alternations_exact.csv"))
lists = collections.Counter(r["side"] for r in read("list_entries.csv"))
metoro_sides = {"Aa", "Ab", "Br", "Bv", "Ca", "Cb", "Er", "Ev"}

rows = []
for s in sorted(sides):
    units = [u for u in sides[s]]
    heads = [head(u) for u in units if not head(u).startswith("(")]
    n = sum(1 for h in heads if h not in ("000", "999"))
    delims = sum(1 for u in units if clean(u).startswith("380.001"))
    has76 = sum(1 for u in units if "076" in clean(u).split(".")[1:] or head(u) == "076")
    dividers = sum(1 for h in heads if h == "999")
    illegible = sum(1 for h in heads if h == "000")
    crescents = sum(1 for h in heads if h == "040")
    cov = coverage.get(s, {})
    g = genre.get(s)
    fam = families.get(s, "")
    # type label
    if n < 40:
        typ = "too short to type"
    elif fam and s[0] in "HPQ":
        typ = "copied text, Great Santiago group"
    elif fam and s[0] in "GK":
        typ = "copied text, Small Santiago group"
    elif has76 / max(1, n) > 0.25:
        typ = "triadic, marked by sign 76"
    elif crescents / max(1, n) > 0.06 and internal[s] >= 3:
        typ = "calendar-like, crescent runs" + (", with lists" if delims >= 4 else "")
    elif delims >= 4:
        typ = "delimited list"
    elif internal[s] >= 3:
        typ = "isolated, with refrains"
    else:
        typ = "isolated"
    rows.append({
        "side": s, "object": NAMES.get(s[0], s[0]), "lines": lines_per_side[s], "units": n, "illegible": illegible,
        "family": fam or "none", "parallel_strict_pct": cov.get("strict", 0), "parallel_fuzzy_pct": cov.get("fuzzy", 0),
        "internal_repeats": internal[s], "delimiters_380_1": delims, "list_entries": lists.get(s, 0),
        "alternating_series": alts.get(s, 0), "units_with_76_pct": round(100 * has76 / max(1, n)),
        "carved_dividers": dividers, "crescent_40_pct": round(100 * crescents / max(1, n)),
        "vocab_neighbour": f"{g['nn1']} ({float(g['s1']):.2f})" if g else "",
        "metoro": "yes" if s in metoro_sides else "", "type": typ,
    })

with open(out / "typology.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

md = ["# A typology of the texts\n",
      "One row per side. Percentages are shares of the side's units. Family and parallel shares come from the parallel map, "
      "vocabulary neighbour from the genre clustering, list entries and series from their own scripts. The type label is a rule "
      "applied to the row: copied family first, then sign-76 triads above 25 percent of units, then four or more 380.1 delimiters, "
      "then crescent runs, then internal repeats.\n",
      "| side | object | units | family | parallel, strict / fuzzy | internal repeats | 380.1 | list entries | series | units with 76 | dividers | vocabulary neighbour | Metoro | type |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['side']} | {r['object']} | {r['units']} | {r['family']} | {r['parallel_strict_pct']}% / {r['parallel_fuzzy_pct']}% | "
              f"{r['internal_repeats']} | {r['delimiters_380_1']} | {r['list_entries']} | {r['alternating_series']} | {r['units_with_76_pct']}% | "
              f"{r['carved_dividers']} | {r['vocab_neighbour']} | {r['metoro']} | {r['type']} |")
types = collections.Counter(r["type"] for r in rows)
md.append("\n## Types\n")
for t, n in types.most_common():
    md.append(f"- {t}: {n} sides, " + ", ".join(r["side"] for r in rows if r["type"] == t))
(out / "typology.md").write_text("\n".join(md), encoding="utf-8")

# condensed table for the README: sides with at least 40 units
short = ["| side | object | units | parallel elsewhere | 380.1 | series | units with 76 | dividers | closest vocabulary | Metoro | type |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    if r["units"] < 40:
        continue
    short.append(f"| {r['side']} | {r['object']} | {r['units']} | {r['parallel_fuzzy_pct']}% | {r['delimiters_380_1'] or ''} | "
                 f"{r['alternating_series'] or ''} | {r['units_with_76_pct']}% | {r['carved_dividers'] or ''} | {r['vocab_neighbour']} | "
                 f"{r['metoro']} | {r['type']} |")
(out / "typology_short.md").write_text("\n".join(short), encoding="utf-8")

# ------------------------------------------------------------------ signs
freq = collections.Counter()
series_of = {}
bare = collections.Counter()
attached_on = collections.defaultdict(collections.Counter)     # head -> components attached to it
attaches_to = collections.defaultdict(collections.Counter)     # component -> heads it is attached to
for lid, units in corpus.items():
    if lid[0] in COPIES:
        continue
    for u in units:
        c = clean(u).split(".")
        h = c[0]
        if h in ("000", "999") or h.startswith("("):
            continue
        freq[h] += 1
        if len(c) == 1:
            bare[h] += 1
        for x in c[1:]:
            attached_on[h][x] += 1
            attaches_to[x][h] += 1

coll = read("collocation_pairs.csv")
left = collections.defaultdict(list)     # sign -> (partner before it, G2)
right = collections.defaultdict(list)
for r in coll:
    if r["collocation"] == "True":
        right[r["a"]].append((r["b"], float(r["G2"])))
        left[r["b"]].append((r["a"], float(r["G2"])))
shape = {r["sign"]: r for r in read("sign_similarity.csv")}
metoro = {r["sign"]: r for r in read("metoro_signs.csv")}
subs = collections.defaultdict(list)
for r in read("allograph_pairs.csv"):
    subs[r["a"]].append(r["b"]); subs[r["b"]].append(r["a"])
alt_head = collections.Counter(r["head"] for r in read("alternations_exact.csv"))
list_member = collections.Counter()
for r in read("list_entries.csv"):
    for u in r["entry"].split("-"):
        list_member[head(u)] += 1
slot = collections.defaultdict(collections.Counter)
for r in read("staff_triads.csv"):
    hs = r["head_signs"].split()
    if len(hs) == 3:
        for k, name in enumerate(("first", "middle", "last")):
            slot[hs[k]][name] += 1
classes = {}
for r in read("sign_shape_classes.csv"):
    for m in r["members"].split():
        classes[m] = r["members"]


def series(h):
    return f"{(int(h) // 100) * 100}s" if h.isdigit() else "other"


def top(counter, k=3):
    return " ".join(f"{a}({n})" for a, n in counter.most_common(k))


drows = []
for h, n in freq.most_common():
    if n < MIN_TOKENS:
        break
    sh = shape.get(h)
    mt = metoro.get(h)
    sl = slot.get(h, collections.Counter())
    drows.append({
        "sign": h, "tokens": n, "series": series(h), "bare_pct": round(100 * bare[h] / n),
        "attachments_distinct": len(attached_on[h]), "top_attachments": top(attached_on[h]),
        "attaches_to": top(attaches_to[h]), "attached_total": sum(attaches_to[h].values()),
        "left_collocates": " ".join(f"{a}" for a, _ in sorted(left[h], key=lambda x: -x[1])[:3]),
        "right_collocates": " ".join(f"{b}" for b, _ in sorted(right[h], key=lambda x: -x[1])[:3]),
        "shape_neighbours": f"{sh['nn1']}({float(sh['s1']):.2f}) {sh['nn2']}({float(sh['s2']):.2f})" if sh else "",
        "shape_class": classes.get(h, ""),
        "metoro_word": mt["top_word"] if mt else "", "metoro_p": f"{float(mt['p_top']):.2f}" if mt else "",
        "metoro_occurrences": mt["occurrences"] if mt else "",
        "copy_substitutes": " ".join(sorted(set(subs[h]))),
        "alternation_head": alt_head.get(h, 0), "list_entry_member": list_member.get(h, 0),
        "staff_slots_first_middle_last": f"{sl['first']}/{sl['middle']}/{sl['last']}" if sl else "",
    })

with open(out / "sign_dossier.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(drows[0].keys()))
    w.writeheader()
    w.writerows(drows)

md = ["# Sign dossier\n",
      f"{len(drows)} head signs with at least {MIN_TOKENS} tokens, one witness per family. Full table in sign_dossier.csv; "
      "the columns below are a selection.\n",
      "| sign | tokens | series | bare | top attachments | attaches to | before it | after it | shape neighbours | Metoro | copies swap with | series head | list member | Staff slots |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in drows:
    md.append(f"| {r['sign']} | {r['tokens']} | {r['series']} | {r['bare_pct']}% | {r['top_attachments']} | {r['attaches_to']} | "
              f"{r['left_collocates']} | {r['right_collocates']} | {r['shape_neighbours']} | "
              f"{r['metoro_word']} {r['metoro_p']} | {r['copy_substitutes']} | {r['alternation_head']} | {r['list_entry_member']} | "
              f"{r['staff_slots_first_middle_last']} |")
(out / "sign_dossier.md").write_text("\n".join(md), encoding="utf-8")
print(f"{len(rows)} sides typed; {len(drows)} signs in the dossier")
print("\n".join(f"- {t}: {n}" for t, n in types.most_common()))
