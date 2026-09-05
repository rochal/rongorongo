"""Mine allograph candidates from the fuzzy parallel runs.

Input: out/parallel_runs_fuzzy.csv (from parallels.py --mismatch 1). Each row
aligns two runs unit by unit. Two kinds of variation are collected:

  substitutions   different head signs in the same slot of a shared passage
                  (the one mismatch the fuzzy pass allowed)
  component swaps same head sign, different secondary components, e.g.
                  380.001 against 380.001.003, or 522 against 522.006

A substitution pair is a candidate allograph when it occurs in at least
MIN_PASSAGES distinct passages (different side pairs, or the same pair at
positions more than 20 units apart). Candidates are grouped into classes by
union-find; each class gets its most frequent member as representative.

Outputs (out/):
  allograph_pairs.csv     every substitution pair with count, passages, flags
  allograph_components.csv secondary components that come and go between copies
  allograph_merge.csv     head -> representative, for parallels.py --merge
  allographs.md           report
"""
import collections, csv, pathlib, re

MIN_PASSAGES = 2
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
STROKES = {"000", "001", "002", "003", "004", "005", "999"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


src = out / "parallel_runs_fuzzy.csv"
if not src.exists():
    raise SystemExit("run: python scripts/parallels.py --min-run 4 --mismatch 1 --suffix _fuzzy")

pairs = collections.defaultdict(list)          # (a, b) sorted -> [passage keys]
comp_var = collections.Counter()               # (head, comps_a, comps_b) -> n
comp_added = collections.Counter()             # component -> n (present on one side only)
same_series = 0
with open(src, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        ua = row["text_a"].split("-")
        ub = row["text_b"].split("-")
        passage = (row["side_a"], row["side_b"], int(row["from_a"].split("@")[1]) // 20)
        for x, y in zip(ua, ub):
            cx, cy = clean(x).split("."), clean(y).split(".")
            if cx[0] != cy[0]:
                key = tuple(sorted((cx[0], cy[0])))
                pairs[key].append(passage)
            elif cx != cy:
                key = (cx[0], ".".join(cx[1:]) or "-", ".".join(cy[1:]) or "-")
                comp_var[key] += 1
                for c in set(cx[1:]) ^ set(cy[1:]):
                    comp_added[c] += 1

# tally
rows = []
for (a, b), lst in pairs.items():
    n_pass = len(set(lst))
    series = a[0] == b[0] and a != b
    near = abs(int(a) - int(b)) <= 10 if a.isdigit() and b.isdigit() else False
    stroke = a in STROKES or b in STROKES
    rows.append({"a": a, "b": b, "count": len(lst), "passages": n_pass,
                 "same_series": series, "numerically_near": near, "involves_stroke": stroke,
                 "candidate": n_pass >= MIN_PASSAGES and not stroke})
rows.sort(key=lambda r: (-r["passages"], -r["count"], r["a"]))
with open(out / "allograph_pairs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

with open(out / "allograph_components.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["head", "components_a", "components_b", "count"])
    for (h, ca, cb), n in comp_var.most_common():
        w.writerow([h, ca, cb, n])

# classes
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
freq = collections.Counter()
for r in rows:
    if r["candidate"]:
        parent[find(r["a"])] = find(r["b"])
    freq[r["a"]] += r["count"]
    freq[r["b"]] += r["count"]
classes = collections.defaultdict(list)
for r in rows:
    if r["candidate"]:
        for s in (r["a"], r["b"]):
            if s not in classes[find(s)]:
                classes[find(s)].append(s)
merge = {}
for members in classes.values():
    rep = max(members, key=lambda s: (freq[s], -int(s) if s.isdigit() else 0))
    for s in members:
        if s != rep:
            merge[s] = rep
with open(out / "allograph_merge.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["head", "representative"])
    for s, rep in sorted(merge.items()):
        w.writerow([s, rep])

# report
cands = [r for r in rows if r["candidate"]]
md = ["# Allograph candidates from copied passages\n",
      f"{sum(r['count'] for r in rows)} substitutions in {len(rows)} distinct sign pairs, read off the fuzzy parallel runs. "
      f"{len(cands)} pairs recur in at least {MIN_PASSAGES} passages and involve no stroke sign; "
      f"they form {len(classes)} classes covering {len(merge) + len(classes)} signs.\n"]
md.append("## Recurring substitution pairs\n")
md.append("| a | b | swaps | passages | same series | within 10 | note |\n|---|---|---|---|---|---|---|")
for r in rows:
    if r["passages"] >= MIN_PASSAGES:
        note = "stroke, excluded" if r["involves_stroke"] else "candidate"
        md.append(f"| {r['a']} | {r['b']} | {r['count']} | {r['passages']} | {'yes' if r['same_series'] else ''} | "
                  f"{'yes' if r['numerically_near'] else ''} | {note} |")
md.append("\n## Classes and chosen representative\n")
for members in sorted(classes.values(), key=lambda m: -len(m)):
    rep = next((s for s in members if s not in merge), members[0])
    md.append(f"- **{rep}** ← " + ", ".join(s for s in members if s != rep))
md.append("\n## One-off substitutions (seen in a single passage)\n")
once = [r for r in rows if r["passages"] < MIN_PASSAGES and not r["involves_stroke"]]
md.append(f"{len(once)} pairs. Those in the same Barthel series, which are the likeliest look-alikes: " +
          ", ".join(f"{r['a']}~{r['b']}" for r in once if r["same_series"]))
md.append("\n## Secondary components that come and go between copies\n")
md.append("| component | times added or dropped |\n|---|---|")
for c, n in comp_added.most_common(15):
    md.append(f"| {c} | {n} |")
md.append("\nMost frequent component swaps on one head sign:\n")
md.append("| head | copy A | copy B | n |\n|---|---|---|---|")
for (h, ca, cb), n in comp_var.most_common(15):
    md.append(f"| {h} | {ca} | {cb} | {n} |")
(out / "allographs.md").write_text("\n".join(md), encoding="utf-8")
print(f"{len(rows)} pairs, {len(cands)} candidates, {len(classes)} classes, merge table {len(merge)} entries")
