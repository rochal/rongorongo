"""A closer look at Tahua's secondary period.

Section 26 found that signs on Tahua's side a recur at distances of 22 to
24 more often than chance, the only hint of a longer rhythm in the corpus.
This script asks what carries it.

  drivers    for each distance from 18 to 28, which signs account for the
             matches, against each sign's expected share under shuffling
  returns    recurring groups of three or more signs whose occurrences are
             separated by 18 to 28 positions, with their positions and gaps
  stability  for the driving signs, the gaps between consecutive occurrences,
             so a fixed interval can be told from a drifting one
  lines      whether the driving occurrences respect line boundaries
  side b     the same lag profile for Ab

Outputs (out/): tahua_period.md, tahua_period.csv
"""
import collections, csv, json, pathlib, random, re

random.seed(6)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
LAGS = range(18, 29)
FOCUS = (22, 23, 24)
SHUFFLES = 300


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def side(s):
    seq, starts, pos = [], [], 0
    for lid in sorted((k for k in corpus if k.startswith(s)), key=lambda k: int(k[2:])):
        starts.append(pos)
        for u in corpus[lid]:
            c = clean(u)
            if c.startswith(("000", "999", "(")):
                continue
            seq.append(c.split(".")[0]); pos += 1
    return seq, starts


seq, starts = side("Aa")
n = len(seq)
freq = collections.Counter(seq)

# drivers per lag
def matches(s, lag):
    return collections.Counter(s[i] for i in range(len(s) - lag) if s[i] == s[i + lag])

driver_rows = []
for lag in LAGS:
    m = matches(seq, lag)
    exp = {h: (freq[h] / n) ** 2 * (n - lag) for h in freq}
    tot_exp = sum(exp.values())
    driver_rows.append((lag, sum(m.values()), tot_exp, sorted(m.items(), key=lambda kv: -(kv[1] - exp[kv[0]]))[:6], exp))

# focus signs: the signs with the largest excess summed over the focus lags
excess = collections.Counter()
for lag, tot, tot_exp, top, exp in driver_rows:
    if lag in FOCUS:
        m = matches(seq, lag)
        for h, c in m.items():
            excess[h] += c - exp[h]
drivers = [h for h, e in excess.most_common(8) if e > 1.5]

# returns: 3-grams recurring at a focus distance
grams = collections.defaultdict(list)
for i in range(n - 2):
    grams[tuple(seq[i:i + 3])].append(i)
returns = []
for g, idx in grams.items():
    for a, b in zip(idx, idx[1:]):
        if 18 <= b - a <= 28:
            returns.append((g, a, b, b - a))
returns.sort(key=lambda r: r[1])

# stability: gaps between consecutive occurrences of each driver
stab = {}
for h in drivers:
    pos = [i for i, x in enumerate(seq) if x == h]
    gaps = [b - a for a, b in zip(pos, pos[1:])]
    near = [g for g in gaps if 18 <= g <= 28]
    stab[h] = (pos, gaps, near)

# lines: position of driver occurrences relative to line starts
line_of = []
for i in range(n):
    k = max(j for j, s in enumerate(starts) if s <= i)
    line_of.append((k, i - starts[k]))
line_len = [b - a for a, b in zip(starts, starts[1:] + [n])]

# side b
seq_b, _ = side("Ab")
def zscore(s, lag):
    obs = sum(1 for i in range(len(s) - lag) if s[i] == s[i + lag])
    null = []
    for _ in range(SHUFFLES):
        sh = list(s); random.shuffle(sh)
        null.append(sum(1 for i in range(len(sh) - lag) if sh[i] == sh[i + lag]))
    mu = sum(null) / len(null); sd = (sum((x - mu) ** 2 for x in null) / len(null)) ** 0.5
    return obs, mu, (obs - mu) / (sd + 1e-9)
zb = {lag: zscore(seq_b, lag) for lag in LAGS}
za = {lag: zscore(seq, lag) for lag in LAGS}

with open(out / "tahua_period.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["lag", "Aa_matches", "Aa_expected", "Aa_z", "Ab_matches", "Ab_expected", "Ab_z"])
    for lag in LAGS:
        w.writerow([lag, za[lag][0], f"{za[lag][1]:.1f}", f"{za[lag][2]:.2f}", zb[lag][0], f"{zb[lag][1]:.1f}", f"{zb[lag][2]:.2f}"])

md = ["# Tahua's secondary period\n",
      f"Side a: {n} units on {len(starts)} lines of {', '.join(map(str, line_len))} units. Side b: {len(seq_b)} units.\n",
      "## Same-sign recurrence by distance, both sides\n",
      "| distance | Aa matches | expected | z | Ab matches | expected | z |\n|---|---|---|---|---|---|---|"]
for lag in LAGS:
    md.append(f"| {lag} | {za[lag][0]} | {za[lag][1]:.1f} | {za[lag][2]:+.1f} | {zb[lag][0]} | {zb[lag][1]:.1f} | {zb[lag][2]:+.1f} |")
md.append("\n## What carries the excess at 22 to 24 on side a\n")
md.append("| distance | matches | expected | signs with the largest excess (matches, expected) |\n|---|---|---|---|")
for lag, tot, tot_exp, top, exp in driver_rows:
    if lag in FOCUS:
        md.append(f"| {lag} | {tot} | {tot_exp:.1f} | " + ", ".join(f"{h} ({c}, {exp[h]:.1f})" for h, c in top) + " |")
md.append(f"\nDriving signs, by excess summed over the three distances: {', '.join(f'{h} (+{excess[h]:.1f})' for h in drivers)}.\n")
md.append("## Gaps between consecutive occurrences of the driving signs\n")
md.append("| sign | occurrences on Aa | gaps | gaps of 18 to 28 |\n|---|---|---|---|")
for h in drivers:
    pos, gaps, near = stab[h]
    md.append(f"| {h} | {len(pos)} | {' '.join(map(str, gaps))} | {len(near)} of {len(gaps)} |")
md.append(f"\n## Groups of three signs returning at 18 to 28 positions: {len(returns)}\n")
md.append("| group | first at | returns at | gap | line, offset of first |\n|---|---|---|---|---|")
for g, a, b, gap in returns[:30]:
    md.append(f"| {' '.join(g)} | {a} | {b} | {gap} | line {line_of[a][0] + 1}, +{line_of[a][1]} |")
md.append("\n## Where the driving signs fall in their lines\n")
for h in drivers[:4]:
    pos = stab[h][0]
    md.append(f"- {h}: " + ", ".join(f"line {line_of[i][0] + 1} +{line_of[i][1]}" for i in pos))
(out / "tahua_period.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
