"""What is in the twelve untyped sides?

Section 19 left twelve sides without a type: nothing in them recurs in the
corpus at the resolution of the earlier tests. This script asks what those
tests could have missed, running the same battery on every side with at
least 40 units so that the untyped sides can be read against the typed ones.

  periodicity   the chance that the sign at position i is the sign at i + lag,
                for lags 1 to 60, against the same chance under shuffling. A
                peak at a lag means repeats at a fixed interval, the signature
                of verse or refrain; the largest z-score over lags is reported
  lines         whether the transliterated lines are units of text: the
                distribution of line-initial and line-final head signs against
                the side's background, as KL divergence, against random cuts
  internal      loose repeats inside the side: runs of three or more signs
                with one substitution allowed that recur within the side,
                as the share of units they cover, against a shuffled side
  affinity      mean vocabulary similarity to each typed group (copied H/P/Q,
                copied G/K, delimited lists, triadic, refrains), from the
                genre similarity matrix
  profile       shares of stroke signs, of units with attachments, of units
                carrying sign 76, and of doubled signs, against corpus means
  distinctive   signs over-represented on the side, count at least five

Outputs (out/): untyped.csv, untyped_autocorr.csv, untyped.md
"""
import collections, csv, json, math, pathlib, random, re

random.seed(4)
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
UNTYPED = ["Aa", "Ab", "Bv", "Da", "Db", "Gv", "La", "Ma", "Nb", "Oa", "Ra", "Rb"]
GROUPS = {"copied H/P/Q": ["Hr", "Hv", "Pr", "Pv", "Qr", "Qv"], "copied G/K": ["Gr", "Kr", "Kv"],
          "delimited lists": ["Cb", "Ev", "Na", "Sa", "Ca"], "triadic": ["Ia", "Ta"], "refrains": ["Br", "Er", "Sb"]}
SHUFFLES = 200
MAX_LAG = 60


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


sides, lines = collections.defaultdict(list), collections.defaultdict(list)
for lid in sorted(corpus, key=lambda k: (k[:2], int(k[2:]))):
    us = [clean(u) for u in corpus[lid]]
    us = [u for u in us if not u.startswith(("000", "999", "("))]
    sides[lid[:2]].extend(us)
    lines[lid[:2]].append(us)
heads = {s: [u.split(".")[0] for u in v] for s, v in sides.items()}
names = sorted(s for s in sides if len(sides[s]) >= 40)

# corpus background, one witness per family
bg = collections.Counter(h for s, v in heads.items() if s[0] not in "PQK" for h in v)
bg_total = sum(bg.values())


def autocorr(seq, max_lag):
    n = len(seq)
    return [sum(1 for i in range(n - lag) if seq[i] == seq[i + lag]) / max(1, n - lag) for lag in range(1, max_lag + 1)]


def kl(counter, background):
    tot = sum(counter.values())
    return sum(n / tot * math.log2((n / tot) / (background[k] / sum(background.values()))) for k, n in counter.items() if background[k])


def loose_repeats(seq, min_len=3):
    """share of positions covered by a run of min_len that recurs elsewhere in the sequence with at most one substitution"""
    n = len(seq)
    covered = set()
    grams = collections.defaultdict(list)
    for i in range(n - min_len + 1):
        g = tuple(seq[i:i + min_len])
        grams[g].append(i)
    # exact recurrences plus one-substitution recurrences via wildcard keys
    wild = collections.defaultdict(list)
    for i in range(n - min_len + 1):
        g = seq[i:i + min_len]
        for k in range(min_len):
            wild[tuple(g[:k]) + ("*",) + tuple(g[k + 1:])].append(i)
    for key, idx in wild.items():
        if len(idx) >= 2 and sum(1 for x in key if x != "*") >= 2:
            for i in idx:
                covered.update(range(i, i + min_len))
    return len(covered) / n


genre = {}
for r in csv.DictReader(open(out / "genre_similarity.csv", encoding="utf-8")):
    genre[r["side"]] = {k: float(v) for k, v in r.items() if k != "side"}

rows, ac_rows = [], []
for s in names:
    seq = heads[s]
    n = len(seq)
    # periodicity
    obs = autocorr(seq, MAX_LAG)
    null = []
    for _ in range(SHUFFLES):
        sh = list(seq); random.shuffle(sh)
        null.append(autocorr(sh, MAX_LAG))
    null = list(zip(*null))
    z = [(o - sum(c) / len(c)) / (math.sqrt(sum((x - sum(c) / len(c)) ** 2 for x in c) / len(c)) + 1e-9) for o, c in zip(obs, null)]
    best_lag = max(range(MAX_LAG), key=lambda k: z[k]) + 1
    for lag in range(1, MAX_LAG + 1):
        ac_rows.append([s, lag, f"{obs[lag - 1]:.4f}", f"{sum(null[lag - 1]) / SHUFFLES:.4f}", f"{z[lag - 1]:.2f}"])
    # lines
    firsts = collections.Counter(l[0].split(".")[0] for l in lines[s] if l)
    lasts = collections.Counter(l[-1].split(".")[0] for l in lines[s] if l)
    side_bg = collections.Counter(seq)
    kl_first, kl_last = kl(firsts, side_bg), kl(lasts, side_bg)
    null_kl = []
    for _ in range(SHUFFLES):
        cuts = sorted(random.sample(range(1, n), len(lines[s]) - 1)) if len(lines[s]) > 1 else []
        starts = [0] + cuts
        null_kl.append(kl(collections.Counter(seq[i] for i in starts), side_bg))
    p_lines = sum(1 for x in null_kl if x >= kl_first) / SHUFFLES
    # internal loose repeats
    cov = loose_repeats(seq)
    cov_null = []
    for _ in range(40):
        sh = list(seq); random.shuffle(sh)
        cov_null.append(loose_repeats(sh))
    # affinity
    aff = {g: sum(genre.get(s, {}).get(t, 0) for t in members if t != s) / max(1, sum(1 for t in members if t != s and t in genre.get(s, {})))
           for g, members in GROUPS.items()}
    nearest = max(aff, key=aff.get)
    # profile
    units = sides[s]
    strokes = sum(1 for h in seq if h.isdigit() and int(h) < 10) / n
    attached = sum(1 for u in units if "." in u) / n
    s76 = sum(1 for u in units if "076" in u.split(".")[1:] or u.split(".")[0] == "076") / n
    doubled = sum(1 for a, b in zip(seq, seq[1:]) if a == b) / n
    # distinctive signs
    cnt = collections.Counter(seq)
    dist = sorted(((h, c, math.log2((c / n) / (bg[h] / bg_total))) for h, c in cnt.items() if c >= 5 and bg[h]), key=lambda x: -x[2])[:5]
    rows.append({"side": s, "untyped": s in UNTYPED, "units": n, "lines": len(lines[s]), "best_lag": best_lag, "best_lag_z": round(z[best_lag - 1], 2),
                 "lag1_z": round(z[0], 2), "kl_line_first": round(kl_first, 3), "p_lines": p_lines, "internal_cover": round(cov, 3),
                 "internal_cover_shuffled": round(sum(cov_null) / len(cov_null), 3), "nearest_group": nearest, "nearest_sim": round(aff[nearest], 3),
                 **{f"aff_{g}": round(v, 3) for g, v in aff.items()},
                 "stroke_share": round(strokes, 3), "attached_share": round(attached, 3), "sign76_share": round(s76, 3), "doubled_share": round(doubled, 3),
                 "distinctive": " ".join(f"{h}(x{2 ** lo:.1f})" for h, c, lo in dist)})

with open(out / "untyped.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
with open(out / "untyped_autocorr.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["side", "lag", "observed", "shuffled_mean", "z"]); w.writerows(ac_rows)

corpus_means = {k: sum(r[k] for r in rows) / len(rows) for k in ("stroke_share", "attached_share", "sign76_share", "doubled_share")}
md = ["# The untyped sides\n",
      f"{len(names)} sides with at least 40 units, {sum(1 for r in rows if r['untyped'])} of them untyped in section 19. "
      f"Periodicity z-scores from {SHUFFLES} shuffles; line test p from {SHUFFLES} random cuts.\n",
      "## Periodicity, line structure, internal repeats\n",
      "| side | typed as | units | best lag | z at best lag | z at lag 1 | line-initial KL | p | loose internal cover | shuffled |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for r in sorted(rows, key=lambda r: (not r["untyped"], r["side"])):
    md.append(f"| {r['side']} | {'untyped' if r['untyped'] else 'typed'} | {r['units']} | {r['best_lag']} | {r['best_lag_z']:+.1f} | {r['lag1_z']:+.1f} | "
              f"{r['kl_line_first']:.2f} | {r['p_lines']:.2f} | {r['internal_cover']:.0%} | {r['internal_cover_shuffled']:.0%} |")
md.append("\n## Affinity to the typed groups, mean vocabulary similarity\n")
md.append("| side | " + " | ".join(GROUPS) + " | nearest |\n|---|" + "---|" * (len(GROUPS) + 1))
for r in sorted(rows, key=lambda r: (not r["untyped"], r["side"])):
    if r["untyped"]:
        md.append(f"| {r['side']} | " + " | ".join(f"{r[f'aff_{g}']:.2f}" for g in GROUPS) + f" | {r['nearest_group']} |")
md.append("\n## Profile against the corpus mean\n")
md.append("| side | strokes | attached | sign 76 | doubled | distinctive signs (enrichment) |\n|---|---|---|---|---|---|")
md.append(f"| corpus mean | {corpus_means['stroke_share']:.0%} | {corpus_means['attached_share']:.0%} | {corpus_means['sign76_share']:.0%} | {corpus_means['doubled_share']:.1%} | |")
for r in sorted(rows, key=lambda r: (not r["untyped"], r["side"])):
    if r["untyped"]:
        md.append(f"| {r['side']} | {r['stroke_share']:.0%} | {r['attached_share']:.0%} | {r['sign76_share']:.0%} | {r['doubled_share']:.1%} | {r['distinctive']} |")
(out / "untyped.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
