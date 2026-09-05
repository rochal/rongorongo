"""The list format against the creation chant.

Ure Vaeiko's recitation for the Small Washington tablet (Thomson 1891, the
"Atua Matariri" chant) is a genealogy of some forty entries, each of the
form  A, ki ai ki roto ki B, ka pu te C : two names joined by a fixed
phrase and yielding a third. Fischer (1997) argued that the Santiago Staff
writes exactly this structure as triads X.76 Y Z, with sign 76 as the
"copulated with" phrase. The 380.1 lists of section 4 are the other
candidate for a written genealogy.

This script measures the shape of all three without reading anything:

  chant        entries parsed from the OCR text; length of each entry in
               content words (the fixed phrase and the particles a, kia,
               ki, te, o excluded); recurrence of names across entries
  380.1 lists  entries between consecutive delimiters on one side; length
               in units and in content units (bare strokes excluded);
               recurrence of content across entries
  Staff triads the Santiago Staff cut at every unit carrying component 76,
               as Fischer reads it; segment length in units. Also the Staff
               cut at its own carved dividers (999), and the 76-cut of the
               two other texts Fischer grouped with the Staff, Gv and Ta.

Outputs (out/): chant_entries.csv, chant_lengths.csv, chant.md
"""
import collections, csv, json, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
src = root / "data" / "rapanui" / "thomson1891_djvu.txt"
if not src.exists():
    raise SystemExit("run scripts/fetch_rapanui.py first")
lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()

# ---------------------------------------------------------------- chant
start = next(i for i, l in enumerate(lines) if l.strip().upper().startswith("ATUA MATARIRI."))
end = next(i for i, l in enumerate(lines) if i > start and "ENGLISH TRANSLATION OF THE ABOVE TABLET" in l)
block = []
for l in lines[start + 1:end]:
    if not l.strip() or "PLATE" in l or "Cat. No" in l or "TABLET" in l or "Report of National Museum" in l:
        continue
    if len(re.findall(r"[A-Za-z]{3,}", l)) < 2:          # scanner noise between plates
        continue
    block.append(l.strip())
text = " ".join(block)
text = re.sub(r"-\s+", "", text)                              # re-join hyphenated line breaks
PARTICLES = {"a", "kia", "ki", "te", "o", "e", "no", "mo", "i"}
pattern = re.compile(r"([A-Za-z][A-Za-z ]*?)\s*[;:,]?\s*ki\s*ai\s*ki\s*roto\s*[;:,]?\s*(.+?)\s*,?\s*[km]apu\s*t[eo]\s+([A-Za-z][A-Za-z ]*?)\s*\.",
                     re.IGNORECASE)


def content_words(s):
    return [w for w in re.findall(r"[A-Za-z]+", s.lower()) if w not in PARTICLES]


entries = []
for m in pattern.finditer(text):
    a, b, c = (content_words(m.group(k)) for k in (1, 2, 3))
    if not a or not b or not c or len(a) > 4 or len(c) > 4:
        continue
    entries.append({"A": " ".join(a), "B": " ".join(b), "C": " ".join(c), "len": len(a) + len(b) + len(c)})
names = collections.Counter(e["A"] for e in entries) + collections.Counter(e["B"] for e in entries) + collections.Counter(e["C"] for e in entries)
recurring_names = sum(1 for n in names.values() if n > 1)
entries_with_recurring = sum(1 for e in entries if any(names[e[k]] > 1 for k in "ABC"))
chant_len = collections.Counter(e["len"] for e in entries)

# ---------------------------------------------------------------- corpus
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
STROKES = {"001", "002", "003", "004", "005"}


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


sides = collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    sides[lid[:2]].extend(corpus[lid])

# 380.1 lists
list_entries = []
for s, seq in sides.items():
    d = [i for i, u in enumerate(seq) if clean(u).startswith("380.001")]
    for a, b in zip(d, d[1:]):
        chunk = [clean(u) for u in seq[a + 1:b]]
        if 0 < len(chunk) <= 12:
            content = tuple(u for u in chunk if u.split(".")[0] not in STROKES)
            list_entries.append({"side": s, "len": len(chunk), "content_len": len(content), "content": content})
list_len = collections.Counter(e["len"] for e in list_entries)
list_clen = collections.Counter(e["content_len"] for e in list_entries)
content_count = collections.Counter(e["content"] for e in list_entries if e["content"])
list_recurring = sum(1 for e in list_entries if e["content"] and content_count[e["content"]] > 1)


# Fischer-style segmentation: cut before every unit that carries component 076
def cut76(seq):
    units = [clean(u) for u in seq if head(u) not in ("000", "999") and not head(u).startswith("(")]
    idx = [i for i, u in enumerate(units) if "076" in u.split(".")[1:] or u.split(".")[0] == "076"]
    return [idx[j + 1] - idx[j] for j in range(len(idx) - 1)], len(units), len(idx)


staff76, staff_units, staff_n76 = cut76(sides["Ia"])
gv76, gv_units, gv_n76 = cut76(sides["Gv"])
ta76, ta_units, ta_n76 = cut76(sides["Ta"])
# null for the 76 cut: keep the number of 76-bearing units but shuffle where
# they fall; if 76 were sprinkled at random with this density, how often
# would a segment be exactly 3 units long?
import random
random.seed(7)


def null76(seq, trials=200):
    units = [clean(u) for u in seq if head(u) not in ("000", "999") and not head(u).startswith("(")]
    flags = [("076" in u.split(".")[1:] or u.split(".")[0] == "076") for u in units]
    share3, share24 = [], []
    for _ in range(trials):
        random.shuffle(flags)
        idx = [i for i, f in enumerate(flags) if f]
        segs = [idx[j + 1] - idx[j] for j in range(len(idx) - 1)]
        if segs:
            share3.append(sum(1 for s in segs if s == 3) / len(segs))
            share24.append(sum(1 for s in segs if 2 <= s <= 4) / len(segs))
    return sum(share3) / len(share3), sum(share24) / len(share24)


staff_null3, staff_null24 = null76(sides["Ia"])
gv_null3, gv_null24 = null76(sides["Gv"])
ta_null3, ta_null24 = null76(sides["Ta"])

# the Staff's own carved dividers, sign 999 in the CEIPP file
staff_units_all = [clean(u) for u in sides["Ia"]]
div = [i for i, u in enumerate(staff_units_all) if u == "999"]
staff999 = [div[j + 1] - div[j] - 1 for j in range(len(div) - 1)]
staff999 = [n for n in staff999 if n > 0]

# ---------------------------------------------------------------- output
with open(out / "chant_entries.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["n", "A", "B", "C", "content_words"])
    for i, e in enumerate(entries, 1):
        w.writerow([i, e["A"], e["B"], e["C"], e["len"]])


def dist(counter, n, ks=range(1, 10)):
    return [counter[k] / n if n else 0 for k in ks]


series = [("chant entries, content words", chant_len, len(entries)),
          ("380.1 entries, units", list_len, len(list_entries)),
          ("380.1 entries, content units", list_clen, len(list_entries)),
          ("Staff segments at 76", collections.Counter(staff76), len(staff76)),
          ("Staff segments at carved dividers", collections.Counter(staff999), len(staff999)),
          ("Gv segments at 76", collections.Counter(gv76), len(gv76)),
          ("Ta segments at 76", collections.Counter(ta76), len(ta76))]
with open(out / "chant_lengths.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["series", "n"] + [f"len_{k}" for k in range(1, 10)] + ["len_10_plus", "mean", "median"])
    for name, c, n in series:
        vals = sorted(k for k, v in c.items() for _ in range(v))
        mean = sum(vals) / n if n else 0
        med = vals[len(vals) // 2] if vals else 0
        w.writerow([name, n] + [f"{x:.3f}" for x in dist(c, n)] + [f"{sum(v for k, v in c.items() if k >= 10) / n if n else 0:.3f}", f"{mean:.2f}", med])


def row(name, c, n):
    vals = sorted(k for k, v in c.items() for _ in range(v))
    mean = sum(vals) / n if n else 0
    med = vals[len(vals) // 2] if vals else 0
    share3 = (c[2] + c[3] + c[4]) / n if n else 0
    return f"| {name} | {n} | {mean:.2f} | {med} | {c[3] / n if n else 0:.0%} | {share3:.0%} |"


md = ["# The list format against the creation chant\n",
      f"Chant: {len(entries)} entries parsed from Thomson 1891 with the fixed phrase intact. Each entry has three name slots; "
      f"lengths count content words only. {recurring_names} names recur in more than one entry and {entries_with_recurring} of "
      f"{len(entries)} entries contain a recurring name.\n",
      f"380.1 lists: {len(list_entries)} entries between consecutive delimiters; {list_recurring} of them repeat the content of "
      f"another entry exactly, strokes ignored.\n",
      f"Santiago Staff: {staff_units} legible units, {staff_n76} carrying sign 76, {len(staff999)} stretches between carved dividers. "
      f"Gv: {gv_units} units, {gv_n76} with 76. Ta: {ta_units} units, {ta_n76} with 76.\n",
      "## Entry length\n",
      "| series | n | mean | median | exactly 3 | 2 to 4 |\n|---|---|---|---|---|---|"]
for name, c, n in series:
    md.append(row(name, c, n))
md.append("\n## Length distributions\n")
md.append("| length | " + " | ".join(name for name, _, _ in series) + " |")
md.append("|---|" + "---|" * len(series))
for k in range(1, 10):
    md.append(f"| {k} | " + " | ".join(f"{c[k] / n:.0%}" if n else "-" for _, c, n in series) + " |")
md.append("\n## Null for the sign-76 cut: same number of 76 units, positions shuffled\n")
md.append("| text | observed exactly 3 | shuffled exactly 3 | observed 2 to 4 | shuffled 2 to 4 |\n|---|---|---|---|---|")
for name, segs, n3, n24 in (("Staff", staff76, staff_null3, staff_null24), ("Gv", gv76, gv_null3, gv_null24), ("Ta", ta76, ta_null3, ta_null24)):
    c = collections.Counter(segs)
    md.append(f"| {name} | {c[3] / len(segs):.0%} | {n3:.0%} | {(c[2] + c[3] + c[4]) / len(segs):.0%} | {n24:.0%} |")
md.append("\n## Slot lengths in the chant\n")
for slot in "ABC":
    c = collections.Counter(len(e[slot].split()) for e in entries)
    md.append(f"- slot {slot}: " + ", ".join(f"{k} word{'s' if k > 1 else ''} {v}" for k, v in sorted(c.items())))
md.append("\n## Recurrence\n")
md.append(f"- chant: {entries_with_recurring / len(entries):.0%} of entries share a name with another entry "
          f"(mostly the parent slot A, repeated across consecutive entries).")
md.append(f"- 380.1 lists: {list_recurring / len(list_entries):.0%} of entries repeat another entry's content exactly.")
(out / "chant.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
