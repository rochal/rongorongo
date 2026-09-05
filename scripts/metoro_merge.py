"""Three witnesses for merging signs: Metoro, shape, and copies.

Section 17 showed Metoro named sign shapes consistently. If two of Barthel's
numbers are one sign, Metoro should have used the same word for both, the
drawings should look alike, and copies of a passage should swap one for the
other. This script puts the three sources side by side.

  metoro pairs  two signs, each seen at least MIN_OCC times in the chanted
                tablets, whose most likely word is the same and whose
                consistency (probability of that word) is at least P_MIN
                for both. Words Metoro used as a top word for many signs
                are generic and excluded (GENERIC_MAX distinct signs).
  shape         the similarity of the two drawings from sign_shapes.py,
                against the 95th and 99.5th percentiles of unrelated pairs
  copies        whether the pair appears among the substitution pairs of
                allographs.py

Then the merges are tested the only way a merge can be: by rerunning the
strict parallel map with them and seeing whether more text aligns.

Outputs (out/): metoro_pairs.csv, metoro_merge.csv, metoro_merge_agreed.csv,
metoro_merge.md
"""
import collections, csv, pathlib, re, subprocess, sys
import numpy as np

MIN_OCC = 8
P_MIN = 0.35
GENERIC_MAX = 3
CONTROL_TRIALS = 5
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"

signs_m = {}
for r in csv.DictReader(open(out / "metoro_signs.csv", encoding="utf-8")):
    if int(r["occurrences"]) >= MIN_OCC:
        signs_m[r["sign"]] = (r["top_word"], float(r["p_top"]), int(r["occurrences"]))

by_word = collections.defaultdict(list)
for s, (w, p, n) in signs_m.items():
    by_word[w].append(s)
generic = {w for w, ss in by_word.items() if len(ss) > GENERIC_MAX}

SS = np.load(out / "sign_similarity_matrix.npy")
shape_signs = (out / "sign_similarity_signs.txt").read_text(encoding="utf-8").split("\n")
si = {s: i for i, s in enumerate(shape_signs)}
tri = SS[np.triu_indices(len(shape_signs), 1)]
p95, p995 = float(np.percentile(tri, 95)), float(np.percentile(tri, 99.5))

copy_pairs = {}
for r in csv.DictReader(open(out / "allograph_pairs.csv", encoding="utf-8")):
    copy_pairs[tuple(sorted((r["a"], r["b"])))] = int(r["passages"])

pairs = []
for w, ss in by_word.items():
    if w in generic or len(ss) < 2:
        continue
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            a, b = sorted((ss[i], ss[j]))
            pa, pb = signs_m[a][1], signs_m[b][1]
            if pa < P_MIN or pb < P_MIN:
                continue
            shape = SS[si[a], si[b]] if a in si and b in si else float("nan")
            pairs.append({"a": a, "b": b, "word": w, "p_a": pa, "p_b": pb, "occ_a": signs_m[a][2], "occ_b": signs_m[b][2],
                          "shape": shape, "shape_95": bool(shape >= p95), "shape_995": bool(shape >= p995),
                          "copies": copy_pairs.get((a, b), 0),
                          "same_series": a[0] == b[0]})
pairs.sort(key=lambda r: (-(r["shape"] if r["shape"] == r["shape"] else -1)))

with open(out / "metoro_pairs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(pairs[0].keys()))
    w.writeheader()
    for r in pairs:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})

# random-pair baseline for shape agreement among Metoro pairs
rng = np.random.default_rng(1)
rand = [SS[i, j] for i, j in zip(rng.integers(0, len(shape_signs), 5000), rng.integers(0, len(shape_signs), 5000)) if i != j]
share_rand95 = float(np.mean([x >= p95 for x in rand]))
valid = [r for r in pairs if r["shape"] == r["shape"]]
share_m95 = float(np.mean([r["shape_95"] for r in valid])) if valid else 0
share_m995 = float(np.mean([r["shape_995"] for r in valid])) if valid else 0

# the reverse check: do shape look-alike classes get the same Metoro word?
classes = []
for r in csv.DictReader(open(out / "sign_shape_classes.csv", encoding="utf-8")):
    classes.append(r["members"].split())
agree = total = 0
for members in classes:
    ms = [m for m in members if m in signs_m]
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            total += 1
            agree += signs_m[ms[i]][0] == signs_m[ms[j]][0]
# baseline: random pairs of Metoro-attested signs
attested = list(signs_m)
rt = ra = 0
for _ in range(5000):
    a, b = rng.choice(attested, 2, replace=False)
    rt += 1
    ra += signs_m[a][0] == signs_m[b][0]


# merge tables and the parallel-map test
def write_merge(rows, path):
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for r in rows:
        parent[find(r["b"])] = find(r["a"])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["head", "representative"])
        n = 0
        for s in sorted(parent):
            if find(s) != s:
                w.writerow([s, find(s)]); n += 1
    return n


n_all = write_merge(pairs, out / "metoro_merge.csv")
agreed = [r for r in pairs if r["shape_95"] or r["copies"] >= 2]
n_agreed = write_merge(agreed, out / "metoro_merge_agreed.csv")


def parallel_runs(merge, suffix):
    subprocess.run([sys.executable, str(root / "scripts" / "parallels.py"), "--merge", str(merge), "--suffix", suffix],
                   cwd=root, check=True, capture_output=True)
    txt = (out / f"parallel_map{suffix}.md").read_text(encoding="utf-8")
    runs = int(re.search(r"(\d+) maximal shared runs", txt).group(1))
    hr = re.search(r"\| Hr \| (\d+) \| (\d+) \| (\d+)%", txt)
    return runs, int(hr.group(3)) if hr else None


base_txt = (out / "parallel_map.md").read_text(encoding="utf-8")
base_runs = int(re.search(r"(\d+) maximal shared runs", base_txt).group(1))
base_hr = int(re.search(r"\| Hr \| (\d+) \| (\d+) \| (\d+)%", base_txt).group(3))
tests = [("Barthel as is", base_runs, base_hr)]
tests.append(("Metoro pairs, all", *parallel_runs(out / "metoro_merge.csv", "_metoro")))
tests.append(("Metoro pairs backed by shape or copies", *parallel_runs(out / "metoro_merge_agreed.csv", "_metoro_agreed")))

# control: merge the same number of random pairs, each drawn from signs of
# similar corpus frequency to a real Metoro pair, so the gain from merging
# frequent signs by chance is measured
import json
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
freq = collections.Counter()
for lid, units in corpus.items():
    for u in units:
        h = re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])
        if h.isdigit():
            freq[h] += 1
ranked = [s for s, _ in freq.most_common()]
rank = {s: i for i, s in enumerate(ranked)}
ctrl_runs = []
for t in range(CONTROL_TRIALS):
    rows = []
    used = set()
    for r in pairs:
        picks = []
        for s in (r["a"], r["b"]):
            i = rank.get(s, len(ranked) // 2)
            window = [x for x in ranked[max(0, i - 15):i + 16] if x not in used and x not in (r["a"], r["b"])]
            c = str(rng.choice(window)) if window else s
            used.add(c); picks.append(c)
        rows.append({"a": picks[0], "b": picks[1]})
    write_merge(rows, out / "_tmp_control_merge.csv")
    ctrl_runs.append(parallel_runs(out / "_tmp_control_merge.csv", "_control")[0])
(out / "_tmp_control_merge.csv").unlink(missing_ok=True)
for suf in ("_control",):
    for f in out.glob(f"parallel_*{suf}.*"):
        f.unlink()
tests.append((f"random frequency-matched pairs, mean of {CONTROL_TRIALS}", round(sum(ctrl_runs) / len(ctrl_runs)), None))
for label, f, suf in (("copy substitutions only", "allograph_merge.csv", "_merged"), ("shape look-alikes, loose", "allograph_merge_loose.csv", "_loose")):
    if (out / f"parallel_map{suf}.md").exists():
        t = (out / f"parallel_map{suf}.md").read_text(encoding="utf-8")
        tests.append((label, int(re.search(r"(\d+) maximal shared runs", t).group(1)),
                      int(re.search(r"\| Hr \| (\d+) \| (\d+) \| (\d+)%", t).group(3))))

md = ["# Three witnesses for merging signs\n",
      f"{len(signs_m)} signs seen at least {MIN_OCC} times in the four chanted tablets. Generic words, used as top word for more than "
      f"{GENERIC_MAX} signs, excluded: " + ", ".join(sorted(generic)) + f". Metoro pairs need consistency at least {P_MIN:.0%} on both signs.\n",
      f"## Metoro pairs: {len(pairs)}\n",
      f"Shape agreement: {share_m95:.0%} of Metoro pairs are above the 95th percentile of unrelated pairs in shape similarity "
      f"({p95:.3f}), and {share_m995:.0%} above the 99.5th ({p995:.3f}); for random pairs of signs the 95th-percentile rate is "
      f"{share_rand95:.0%} by construction. {sum(1 for r in pairs if r['copies'])} Metoro pairs also appear as copy substitutions.\n",
      "| a | b | Metoro's word | p(a) | p(b) | shape | above 95th | above 99.5th | copy passages | same series |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for r in pairs:
    md.append(f"| {r['a']} | {r['b']} | {r['word']} | {r['p_a']:.2f} | {r['p_b']:.2f} | {r['shape']:.2f} | "
              f"{'yes' if r['shape_95'] else ''} | {'yes' if r['shape_995'] else ''} | {r['copies'] or ''} | {'yes' if r['same_series'] else ''} |")
md.append("\n## The reverse check: shape classes judged by Metoro\n")
md.append(f"Among the look-alike classes of section 9, {total} pairs have both members in Metoro's chant; Metoro gave the same top word "
          f"to {agree} of them ({agree / max(1, total):.0%}). For random pairs of signs he chanted over, the rate is {ra / rt:.0%}.\n")
md.append("## Do the merges help the parallel map?\n")
md.append("| merge table | signs merged | strict shared runs | Great Santiago recto covered |\n|---|---|---|---|")
merged_n = {"Barthel as is": 0, "Metoro pairs, all": n_all, "Metoro pairs backed by shape or copies": n_agreed}
with open(out / "metoro_merge_tests.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["merge_table", "signs_merged", "shared_runs", "hr_covered_pct"])
    for label, runs, hr in tests:
        n = merged_n.get(label, "")
        if label == "copy substitutions only":
            n = sum(1 for _ in open(out / "allograph_merge.csv")) - 1
        if label == "shape look-alikes, loose":
            n = sum(1 for _ in open(out / "allograph_merge_loose.csv")) - 1
        if label.startswith("random"):
            n = n_all
        md.append(f"| {label} | {n} | {runs} | {'' if hr is None else str(hr) + '%'} |")
        w.writerow([label, n, runs, "" if hr is None else hr])
(out / "metoro_merge.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
