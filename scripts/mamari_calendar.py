"""Rebuild the Mamari calendar from the transliteration alone.

Lines Ca6 to Ca9 of the Mamari tablet are the one passage of rongorongo
whose nature specialists accept: Barthel identified it as a lunar calendar
and Guy (1990) worked out its structure. This script rebuilds that
structure from the CEIPP transliteration without assuming it, so that the
counts can be checked against the length of a lunar month.

Every unit on the lines is classified:
  crescent   head sign 40, or a compound containing 40
  marker     a unit inside the recurring group that opens with 390.41 (or
             600.390.41) and closes with the unit containing 711
  other      anything else
The sequence is then cut into crescent runs separated by marker groups.

Outputs (out/): calendar_sequence.csv (one row per unit with its class,
run and position), calendar.md
"""
import collections, csv, json, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
LINES = ["Ca06", "Ca07", "Ca08", "Ca09"]


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


units = []
for lid in LINES:
    for i, u in enumerate(corpus[lid]):
        units.append({"line": lid, "pos": i, "raw": u, "clean": clean(u), "comps": clean(u).split(".")})

# classify. A marker group opens at a unit holding 390 and 41 and runs to
# the unit holding 711; a group that lacks its tail ends where the next
# plain crescent begins.
in_marker = False
for k, u in enumerate(units):
    c = u["comps"]
    if in_marker and c[0] == "040":
        in_marker = False
    if not in_marker and ("390" in c and "041" in c):
        in_marker = True
    if in_marker:
        u["class"] = "marker"
        if "711" in c:
            in_marker = False
        continue
    u["class"] = "crescent" if "040" in c else "other"

# runs between marker groups, on the calendar proper (Ca6 from the first
# marker group to the last marker group on Ca8)
first = next(k for k, u in enumerate(units) if u["class"] == "marker")
last = max(k for k, u in enumerate(units) if u["class"] == "marker")
runs, cur, group = [], None, 0
for k in range(first, last + 1):
    u = units[k]
    if u["class"] == "marker":
        if cur is not None and cur["units"]:
            runs.append(cur); cur = None
        if k == first or units[k - 1]["class"] != "marker":
            group += 1
            u["marker_group"] = group
        u["run"] = ""
        continue
    if cur is None:
        cur = {"after_marker": group, "units": [], "crescents": 0, "other": []}
    cur["units"].append(u)
    u["run"] = len(runs) + 1
    if u["class"] == "crescent":
        cur["crescents"] += 1
    else:
        cur["other"].append(u["clean"])
if cur is not None and cur["units"]:
    runs.append(cur)

markers = collections.OrderedDict()
for u in units[first:last + 1]:
    if u["class"] == "marker":
        g = u.get("marker_group") or max(markers) if markers else 1
        if "marker_group" in u:
            markers[u["marker_group"]] = []
        markers[max(markers)].append(u["clean"])

total_cres = sum(r["crescents"] for r in runs)
cres_before = sum(1 for u in units[:first] if u["class"] == "crescent")
cres_after = sum(1 for u in units[last + 1:] if u["class"] == "crescent")
cres_in_markers = sum(1 for u in units[first:last + 1] if u["class"] == "marker" and "040" in u["comps"])
others_all = collections.Counter(x for r in runs for x in r["other"])

with open(out / "calendar_sequence.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["index", "line", "pos", "unit", "class", "run", "marker_group"])
    for k, u in enumerate(units):
        w.writerow([k, u["line"], u["pos"], u["raw"], u["class"], u.get("run", ""), u.get("marker_group", "")])

md = ["# The Mamari calendar, rebuilt\n",
      f"Lines {', '.join(LINES)}: {len(units)} units. Crescents (units containing sign 40) before the first marker group: {cres_before}; "
      f"between the first and last marker groups: {total_cres}; after the last: {cres_after}. Crescents fused into marker units: {cres_in_markers}.\n",
      f"## Marker groups: {len(markers)}\n",
      "| group | line | units |\n|---|---|---|"]
for g, us in markers.items():
    line = next(u["line"] for u in units if u.get("marker_group") == g)
    md.append(f"| {g} | {line} | {' '.join(us)} |")
core = collections.Counter(tuple(x.split(".")[0] for x in us) for us in markers.values())
md.append("\nHead-sign skeleton of the groups: " + "; ".join(f"{'-'.join(k)} x{n}" for k, n in core.most_common()) + ".\n")
md.append("## Crescent runs between the groups\n")
md.append("| run | after group | crescents | other units inside the run |\n|---|---|---|---|")
for i, r in enumerate(runs, 1):
    md.append(f"| {i} | {r['after_marker']} | {r['crescents']} | {' '.join(r['other']) or ''} |")
md.append(f"\nRun lengths: {', '.join(str(r['crescents']) for r in runs)}; sum {total_cres}. "
          f"Cumulative: {', '.join(str(s) for s in __import__('itertools').accumulate(r['crescents'] for r in runs))}.\n")
md.append("## Against a lunar month\n")
md.append(f"A synodic month is 29.53 days; Polynesian calendars name 29 or 30 nights. Crescents inside the calendar proper: {total_cres}; "
          f"with the crescents fused into marker units: {total_cres + cres_in_markers}; with those before the first group: "
          f"{total_cres + cres_in_markers + cres_before}. Other signs standing inside the runs, which a night count would have to "
          f"account for: {sum(others_all.values())} ({', '.join(f'{k} x{n}' for k, n in others_all.most_common())}).\n")
(out / "calendar.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
