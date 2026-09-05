"""Map every alternating series in the rongorongo corpus.

An alternating series is a run  X a X b X c ...  where the same head sign X
recurs at every second position and the fillers a, b, c between them are
each a single unit. We report every series with at least MIN_REPEATS heads.

Two matching modes are run:
  exact : units compared after stripping "?" "!" and variant letters
          (522fy -> 522, 380.001.003 stays 380.001.003)
  head  : only the first component is compared (380.001.003 -> 380)
Both are written out; "head" mode catches ligature variation, "exact" is
stricter. Fillers are always reported in exact form.

Outputs (out/):
  alternations_exact.csv, alternations_head.csv   one row per series
  fillers_by_head.csv                             head sign -> filler inventory
  filler_summary.csv                              filler sign -> heads it follows
  alternations_report.md                          human-readable summary
"""
import collections, csv, json, pathlib, re

MIN_REPEATS = 3
# Bare strokes are so frequent that they alternate by chance; they are not
# allowed as head signs but are of course allowed as fillers.
STROKES = {"001", "002", "003", "004", "000"}

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
out.mkdir(exist_ok=True)


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def find_series(units, key):
    """Yield (start, head, repeats, fillers) for maximal alternating runs."""
    k = [key(u) for u in units]
    i = 0
    while i < len(k):
        x = k[i]
        if x in STROKES or x.startswith("(") or x == "":
            i += 1
            continue
        j = i
        reps = 0
        while j < len(k) and k[j] == x and (j + 1 >= len(k) or k[j + 1] != x):
            reps += 1
            j += 2
        if reps >= MIN_REPEATS:
            fillers = [clean(units[p]) for p in range(i + 1, i + 2 * reps - 1, 2)]
            yield i, x, reps, fillers
            i = i + 2 * reps - 1  # allow the last head to start a new run
        else:
            i += 1


results = {}
for mode, key in (("exact", clean), ("head", head)):
    rows = []
    for lid in sorted(corpus):
        units = corpus[lid]
        for start, x, reps, fillers in find_series(units, key):
            # Barthel numbers below 100 are the simple geometric signs
            # (strokes, ovals, crescents). A series whose fillers are mostly
            # simple signs looks like head + affix; one whose fillers are
            # complex signs looks like a delimited list of items.
            simple = sum(1 for f in fillers if f.split(".")[0].isdigit() and int(f.split(".")[0]) < 100)
            kind = "affix-like" if simple * 3 >= len(fillers) * 2 else "list-like"
            rows.append({
                "line": lid, "tablet": lid[0], "start": start, "head": x,
                "repeats": reps, "fillers": " ".join(fillers),
                "distinct_fillers": len(set(fillers)),
                "simple_fillers": simple, "kind": kind,
                "text": "-".join(units[start:start + 2 * reps - 1]),
            })
    rows.sort(key=lambda r: (-r["repeats"], r["line"], r["start"]))
    results[mode] = rows
    with open(out / f"alternations_{mode}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

# Filler inventories (head mode, so 380.001 and 380.001.003 pool together)
by_head = collections.defaultdict(collections.Counter)
by_filler = collections.defaultdict(collections.Counter)
tablets_by_head = collections.defaultdict(set)
for r in results["head"]:
    for f in r["fillers"].split():
        by_head[r["head"]][f] += 1
        by_filler[f][r["head"]] += 1
    tablets_by_head[r["head"]].add(r["tablet"])

with open(out / "fillers_by_head.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["head", "series", "tablets", "filler_slots", "distinct_fillers", "fillers (count)"])
    for h, c in sorted(by_head.items(), key=lambda kv: -sum(kv[1].values())):
        n_series = sum(1 for r in results["head"] if r["head"] == h)
        w.writerow([h, n_series, "".join(sorted(tablets_by_head[h])), sum(c.values()), len(c),
                    " ".join(f"{f}({n})" for f, n in c.most_common())])

# Overall frequency of each unit in the corpus, to judge whether a filler is
# over-represented in alternations relative to its background rate.
background = collections.Counter(clean(u) for v in corpus.values() for u in v)
total_units = sum(background.values())
total_filler_slots = sum(sum(c.values()) for c in by_filler.values())
with open(out / "filler_summary.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["filler", "slots", "distinct_heads", "share_of_slots", "share_of_corpus", "enrichment", "heads (count)"])
    for f, c in sorted(by_filler.items(), key=lambda kv: -sum(kv[1].values())):
        slots = sum(c.values())
        share_slots = slots / total_filler_slots
        share_corpus = background[f] / total_units
        w.writerow([f, slots, len(c), f"{share_slots:.3f}", f"{share_corpus:.3f}",
                    f"{share_slots / share_corpus:.1f}" if share_corpus else "",
                    " ".join(f"{h}({n})" for h, n in c.most_common())])

# Markdown report
md = []
md.append("# Alternating series in the rongorongo corpus\n")
md.append(f"Corpus: {len(corpus)} lines, {total_units} units (CEIPP transliteration). "
          f"Series = same head sign at every second position, at least {MIN_REPEATS} heads, "
          "fillers of one unit. Bare strokes 1 to 4 are excluded as heads.\n")
for mode in ("exact", "head"):
    rows = results[mode]
    md.append(f"\n## {mode} matching: {len(rows)} series on "
              f"{len({r['tablet'] for r in rows})} objects\n")
    md.append("| line | pos | head | reps | kind | fillers |\n|---|---|---|---|---|---|")
    for r in rows:
        md.append(f"| {r['line']} | {r['start']} | {r['head']} | {r['repeats']} | {r['kind']} | {r['fillers']} |")
    kinds = collections.Counter(r["kind"] for r in rows)
    md.append(f"\n{kinds['affix-like']} affix-like, {kinds['list-like']} list-like.")

md.append("\n## Filler inventory by head sign (head matching)\n")
md.append("| head | series | tablets | slots | distinct | fillers |\n|---|---|---|---|---|---|")
for h, c in sorted(by_head.items(), key=lambda kv: -sum(kv[1].values())):
    n_series = sum(1 for r in results["head"] if r["head"] == h)
    md.append(f"| {h} | {n_series} | {''.join(sorted(tablets_by_head[h]))} | {sum(c.values())} | {len(c)} | "
              + " ".join(f"{f}({n})" for f, n in c.most_common()) + " |")

md.append("\n## Fillers ranked by how many different heads they follow\n")
md.append("| filler | slots | heads | enrichment vs corpus | heads |\n|---|---|---|---|---|")
for f, c in sorted(by_filler.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()))):
    slots = sum(c.values())
    share_slots = slots / total_filler_slots
    share_corpus = background[f] / total_units
    enr = f"{share_slots / share_corpus:.1f}x" if share_corpus else "-"
    md.append(f"| {f} | {slots} | {len(c)} | {enr} | " + " ".join(f"{h}({n})" for h, n in c.most_common()) + " |")

(out / "alternations_report.md").write_text("\n".join(md), encoding="utf-8")
print(f"exact: {len(results['exact'])} series; head: {len(results['head'])} series")
print(f"heads: {len(by_head)}, distinct fillers: {len(by_filler)}, filler slots: {total_filler_slots}")
