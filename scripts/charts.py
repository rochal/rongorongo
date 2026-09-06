"""Charts for the README, drawn from the out/ tables. Writes PNGs to docs/img.

Run after inventory.py, parallels.py (strict and _fuzzy), affix_test.py,
genre_entropy.py and alternations.py.

  rank_frequency.png    log-log rank-frequency of heads, units, components
  parallel_coverage.png share of each side with a parallel, strict and fuzzy
  genre_map.png         2-D map of sides by vocabulary similarity
  entropy_curve.png     conditional entropy against vocabulary size
  affix_test.png        left against right choosiness of the stroke signs
  stroke_order.png      order matrix of adjacent stroke pairs
"""
import collections, csv, json, pathlib, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

root = pathlib.Path(__file__).resolve().parent.parent
out = root / "out"
img = root / "docs" / "img"
img.mkdir(parents=True, exist_ok=True)

# palette: categorical slots 1-3 (validated all-pairs), sequential blue ramp, chrome
C = ["#2a78d6", "#eb6834", "#1baf7a"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
for f in ("Segoe UI", "DejaVu Sans"):
    if any(x.name == f for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "font.size": 10, "legend.frameon": False, "savefig.dpi": 160, "figure.dpi": 100,
})


def read(name):
    return list(csv.DictReader(open(out / name, encoding="utf-8")))


def finish(fig, ax, title, sub, name):
    ax.set_title(title, pad=26)
    ax.annotate(sub, (0, 1), xycoords="axes fraction", xytext=(0, 7), textcoords="offset points",
                color=INK2, fontsize=9.5, va="bottom")
    ax.tick_params(length=0)
    fig.savefig(img / name, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


# 1 rank-frequency ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.6))
series = [("heads", "Head signs", C[0]), ("units", "Whole units", C[1]), ("attached", "Attached components", C[2])]
for key, label, col in series:
    rows = read(f"inventory_{key}.csv")
    r = np.array([int(x["rank"]) for x in rows])
    n = np.array([int(x["count_one_witness"]) for x in rows])
    keep = n > 0
    r, n = np.arange(1, keep.sum() + 1), np.sort(n[keep])[::-1]
    ax.plot(r, n, color=col, lw=2, solid_joinstyle="round", label=label)
ax.axvline(55, color=AXIS, lw=1)
ax.text(57, 300, "Rapa Nui syllables, about 55", color=INK2, fontsize=9)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Rank"); ax.set_ylabel("Occurrences, one witness per family")
ax.set_xlim(1, 4000)
ax.legend(loc="lower left")
finish(fig, ax, "Three inventories, three shapes",
       "Head signs keep a long tail past any syllabary; whole units fall like words", "rank_frequency.png")

# 2 parallel coverage --------------------------------------------------------
def coverage(md):
    cov = {}
    for line in open(out / md, encoding="utf-8"):
        m = re.match(r"\| ([A-Z][abrv]) \| (\d+) \| (\d+) \| (\d+)%", line)
        if m:
            cov[m.group(1)] = (int(m.group(2)), int(m.group(4)))
    return cov
strict, fuzzy = coverage("parallel_map.md"), coverage("parallel_map_fuzzy.md")
sides = [s for s in fuzzy if fuzzy[s][1] >= 2 and fuzzy[s][0] >= 40]
sides.sort(key=lambda s: -fuzzy[s][1])
fig, ax = plt.subplots(figsize=(8, 0.34 * len(sides) + 1.6))
y = np.arange(len(sides))
h = 0.36
ax.barh(y - h / 2, [strict.get(s, (0, 0))[1] for s in sides], height=h - 0.04, color=C[0], label="Strict, 5+ signs exact")
ax.barh(y + h / 2, [fuzzy[s][1] for s in sides], height=h - 0.04, color=C[1], label="Fuzzy, 4+ signs, one substitution")
for i, s in enumerate(sides):
    ax.text(fuzzy[s][1] + 0.8, y[i] + h / 2, f"{fuzzy[s][1]}%", va="center", color=INK2, fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(sides); ax.invert_yaxis()
ax.set_xlabel("Share of the side's signs inside a passage shared with another place")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
finish(fig, ax, "How much of each text is found elsewhere",
       "Sides with at least 40 units and any parallel; Tahua, Mamari, the Staff and Keiti recto have none", "parallel_coverage.png")

# 3 genre map ----------------------------------------------------------------
rows = read("genre_mds.csv")
fam = {"G": "Small Santiago, London", "K": "Small Santiago, London",
       "H": "Great Santiago, St Petersburg", "P": "Great Santiago, St Petersburg", "Q": "Great Santiago, St Petersburg"}
groups = collections.OrderedDict([("Great Santiago, St Petersburg", C[0]), ("Small Santiago, London", C[1]), ("All other objects", C[2])])
fig, ax = plt.subplots(figsize=(8, 6.4))
for g, col in groups.items():
    pts = [r for r in rows if fam.get(r["side"][0], "All other objects") == g]
    ax.scatter([float(r["x"]) for r in pts], [float(r["y"]) for r in pts], s=[max(40, int(r["units"]) / 6) for r in pts],
               color=col, edgecolor=SURFACE, linewidth=2, label=g, zorder=3)
for r in rows:
    ax.annotate(r["side"], (float(r["x"]), float(r["y"])), xytext=(6, 4), textcoords="offset points", color=INK2, fontsize=8.5)
ax.set_xticks([]); ax.set_yticks([])
ax.set_xlabel("Classical scaling of vocabulary distance; marker size = length of side")
ax.legend(loc="upper left")
finish(fig, ax, "Sides mapped by the signs they favour",
       "tf-idf head-sign profiles, cosine distance; copied families cluster, the rest spread", "genre_map.png")

# 4 entropy curve ------------------------------------------------------------
rows = read("entropy_curve.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
for key, label, col in [("heads", "Head signs", C[0]), ("units", "Whole units", C[1])]:
    pts = [r for r in rows if r["layer"] == key]
    x = [int(r["top_n"]) for r in pts]
    ax.plot(x, [float(r["H2"]) for r in pts], color=col, lw=2, marker="o", ms=7, mec=SURFACE, mew=2, label=f"{label}, as written")
    ax.plot(x, [float(r["H2_shuffled"]) for r in pts], color=col, lw=2, alpha=0.35, marker="o", ms=7, mec=SURFACE, mew=2, label=f"{label}, shuffled")
    ax.annotate(f"{label}", (x[-1], float(pts[-1]["H2"])), xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=9, va="center")
ax.set_xscale("log")
ax.set_xticks([20, 30, 50, 100, 200, 300]); ax.set_xticklabels(["20", "30", "50", "100", "200", "300"])
ax.set_xlabel("N most frequent tokens kept"); ax.set_ylabel("Conditional entropy, bits per token")
ax.set_xlim(18, 420)
ax.legend(loc="upper left", ncol=2)
finish(fig, ax, "How much the previous sign predicts the next",
       "Solid: the texts. Faded: the same tokens shuffled. The gap is sequential structure", "entropy_curve.png")

# 5 affix test ---------------------------------------------------------------
rows = read("affix_contexts.csv")   # not needed; summary values come from the md table
vals = []
for line in open(out / "affix_test.md", encoding="utf-8"):
    m = re.match(r"\| (\d{3}) \| (candidate|control) \| \d+ \| \d+ \| \d+ \| ([\d.]+) \| ([\d.]+) \|", line)
    if m:
        vals.append((m.group(1), m.group(2), float(m.group(3)), float(m.group(4))))
fig, ax = plt.subplots(figsize=(6.4, 6))
lim = (0.6, 3.0)
ax.plot(lim, lim, color=AXIS, lw=1, zorder=1)
for role, col, label in [("candidate", C[0], "Stroke signs, candidates"), ("control", C[1], "Content signs, controls")]:
    pts = [v for v in vals if v[1] == role]
    ax.scatter([v[2] for v in pts], [v[3] for v in pts], s=70, color=col, edgecolor=SURFACE, linewidth=2, label=label, zorder=3)
    for v in pts:
        dx, dy = (6, -11) if v[0] == "005" else (6, 4)
        ax.annotate(str(int(v[0])), (v[2], v[3]), xytext=(dx, dy), textcoords="offset points", color=INK2, fontsize=9)
ax.text(2.55, 0.78, "suffix-like zone\nchoosy about the sign before,\nfree about the sign after", color=INK2, fontsize=8.5, ha="center")
ax.text(0.68, 2.2, "prefix-like zone", color=INK2, fontsize=8.5)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("Choosiness about the sign before, bits"); ax.set_ylabel("Choosiness about the sign after, bits")
ax.legend(loc="upper left")
finish(fig, ax, "No stroke sign behaves like a suffix",
       "KL divergence of neighbour distributions from background; a suffix would sit far below the diagonal", "affix_test.png")

# 6 stroke order matrix ------------------------------------------------------
signs, M = None, None
for line in open(out / "affix_test.md", encoding="utf-8"):
    if line.startswith("| first"):
        signs = [c.strip() for c in line.split("|")[2:-1]]
        M = []
    elif signs is not None and M is not None and re.match(r"\| \d{3} \|", line):
        M.append([0 if c.strip() == "·" else int(c) for c in line.split("|")[2:-1]])
    elif M and not line.startswith("|"):
        break
M = np.array(M)
order = ["004", "002", "001", "009", "003", "005", "020", "090", "022"]
ix = [signs.index(s) for s in order]
M = M[np.ix_(ix, ix)]
fig, ax = plt.subplots(figsize=(6.2, 5.6))
from matplotlib.colors import ListedColormap, BoundaryNorm
cmap = ListedColormap([SURFACE] + SEQ)
norm = BoundaryNorm([0, 1, 2, 4, 6, 9, 13, 18, 30], cmap.N)
ax.imshow(M, cmap=cmap, norm=norm, aspect="equal")
for i in range(len(order)):
    for j in range(len(order)):
        if M[i, j]:
            ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=9,
                    color=SURFACE if M[i, j] >= 9 else INK)
ax.set_xticks(range(len(order))); ax.set_xticklabels([str(int(s)) for s in order])
ax.set_yticks(range(len(order))); ax.set_yticklabels([str(int(s)) for s in order])
ax.set_xlabel("Second sign"); ax.set_ylabel("First sign")
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
ax.plot([-0.5, 3.5, 3.5, -0.5, -0.5], [-0.5, -0.5, 3.5, 3.5, -0.5], color=INK, lw=1.2)
finish(fig, ax, "Adjacent strokes keep a fixed order",
       "Free stroke pairs, first sign by row, second by column. Boxed: 4, 2, 1, 9, where above the diagonal wins", "stroke_order.png")
# 7 collocations ------------------------------------------------------------
rows = [r for r in read("collocation_pairs.csv") if r["collocation"] == "True"]
for r in rows:
    r["G2"], r["count"], r["sides"] = float(r["G2"]), int(r["count"]), int(r["sides"])
wide = sorted([r for r in rows if r["sides"] >= 3], key=lambda r: -r["G2"])[:18]
local = sorted([r for r in rows if r["sides"] < 3], key=lambda r: -r["G2"])[:18]
fig, axes = plt.subplots(1, 2, figsize=(10, 6.2), sharex=False)
for ax, data, title, col in [(axes[0], wide, "Spread over 3 or more sides", C[0]), (axes[1], local, "Confined to 1 or 2 sides", C[1])]:
    y = np.arange(len(data))
    ax.barh(y, [r["G2"] for r in data], height=0.62, color=col)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{int(r['a'])} → {int(r['b'])}" if r['a'].isdigit() and r['b'].isdigit() else f"{r['a']} → {r['b']}" for r in data])
    ax.invert_yaxis()
    for i, r in enumerate(data):
        ax.text(r["G2"] + 1.5, i, f"×{r['count']}, {r['sides']} side{'s' if r['sides'] > 1 else ''}", va="center", color=INK2, fontsize=8)
    ax.set_xlim(0, max(r["G2"] for r in data) * 1.45)
    ax.set_xlabel("Log-likelihood ratio G²")
    ax.set_title(title, pad=8, fontsize=11)
    ax.grid(axis="y", visible=False)
    ax.tick_params(length=0)
fig.suptitle("Sign pairs that stick together", x=0.02, ha="left", fontsize=13, fontweight="semibold", color=INK, y=1.02)
fig.text(0.02, 0.975, "Adjacent head-sign pairs seen 4+ times, one witness per family; label gives count and the number of sides", color=INK2, fontsize=9.5)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(img / "collocations.png", bbox_inches="tight", pad_inches=0.25)
plt.close(fig)

# 8 decomposition ------------------------------------------------------------
if (out / "decomposition.csv").exists():
    def share(name):
        rows = read(name)
        return np.mean([r["decomposes"] == "True" for r in rows]) if rows else np.nan

    def share_ctrl(name):
        by = collections.defaultdict(list)
        for r in read(name):
            by[r["control"]].append(r["decomposes"] == "True")
        return [np.mean(v) for _, v in sorted(by.items())]

    runs = [("1 px", "decomposition.csv", "decomposition_control.csv", "decomposition_positive.csv"),
            ("2 px", "decomposition_tol2.csv", "decomposition_control_tol2.csv", "decomposition_positive_tol2.csv")]
    runs = [r for r in runs if (out / r[1]).exists()]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = np.arange(len(runs))
    w = 0.16
    freq_s = [share(r[1]) for r in runs]
    ctrl_s = [share_ctrl(r[2]) if (out / r[2]).exists() else [] for r in runs]
    pos_s = [share(r[3]) if (out / r[3]).exists() else np.nan for r in runs]
    ax.bar(x - 1.5 * w, freq_s, width=w - 0.02, color=C[0], label="55 most frequent signs as parts")
    for k in range(3):
        vals = [c[k] if len(c) > k else np.nan for c in ctrl_s]
        ax.bar(x + (k - 0.5) * w, vals, width=w - 0.02, color=C[1], alpha=1 if k == 0 else 0.55,
               label="Random rare signs as parts, three runs" if k == 0 else None)
    ax.bar(x + 2.5 * w, pos_s, width=w - 0.02, color=C[2], label="Positive control: a basic sign on its own variants")
    for i in range(len(runs)):
        ax.text(x[i] - 1.5 * w, freq_s[i] + 0.015, f"{freq_s[i]:.0%}", ha="center", color=INK2, fontsize=9)
        if ctrl_s[i]:
            ax.text(x[i] + 0.5 * w, max(ctrl_s[i]) + 0.015, f"{min(ctrl_s[i]):.0%} to {max(ctrl_s[i]):.0%}", ha="center", color=INK2, fontsize=9)
        ax.text(x[i] + 2.5 * w, pos_s[i] + 0.015, f"{pos_s[i]:.0%}", ha="center", color=INK2, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"tolerance {r[0]}" for r in runs])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Share of signs reaching the decomposition threshold")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=9)
    finish(fig, ax, "Frequent signs explain rare signs no better than random ones",
           "Up to three parts, mirrored and rescaled, on a 48 px canvas; 80% coverage and 70% precision to count", "decomposition.png")
# 9 Rapa Nui comparison -----------------------------------------------------
if (out / "rapanui_lengths.csv").exists():
    rows = read("rapanui_lengths.csv")
    k = np.array([int(r["length"]) for r in rows])
    rn = np.array([float(r["rapanui_word_share"]) for r in rows])
    rr = np.array([float(r["rongorongo_unit_share"]) for r in rows])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    w = 0.36
    ax.bar(k - w / 2, rn, width=w - 0.03, color=C[0], label="Rapa Nui words, length in syllables")
    ax.bar(k + w / 2, rr, width=w - 0.03, color=C[1], label="Rongorongo units, length in components")
    for i in range(len(k)):
        if rn[i] >= 0.02:
            ax.text(k[i] - w / 2, rn[i] + 0.01, f"{rn[i]:.0%}", ha="center", color=INK2, fontsize=9)
        if rr[i] >= 0.02:
            ax.text(k[i] + w / 2, rr[i] + 0.01, f"{rr[i]:.0%}", ha="center", color=INK2, fontsize=9)
    ax.set_xticks(k); ax.set_xlabel("Length")
    ax.set_ylabel("Share of tokens")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylim(0, max(rn.max(), rr.max()) * 1.18)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right")
    finish(fig, ax, "Word length against unit length",
           "Rapa Nui recitations of 1886 (Thomson 1891) against the rongorongo corpus, one witness per family", "rapanui_lengths.png")
# 10 chant comparison -------------------------------------------------------
if (out / "chant_lengths.csv").exists():
    rows = {r["series"]: r for r in read("chant_lengths.csv")}
    pick = [("chant entries, content words", "Creation chant entries, content words", C[0]),
            ("380.1 entries, content units", "380.1 list entries, content units", C[1]),
            ("Staff segments at 76", "Santiago Staff cut at sign 76, units", C[2])]
    k = np.arange(1, 10)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    w = 0.27
    for i, (key, label, col) in enumerate(pick):
        r = rows[key]
        vals = np.array([float(r[f"len_{j}"]) for j in k])
        ax.bar(k + (i - 1) * w, vals, width=w - 0.03, color=col, label=f"{label} (n = {r['n']})")
    ax.set_xticks(k); ax.set_xlabel("Entry or segment length")
    ax.set_ylabel("Share of entries")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", fontsize=9)
    finish(fig, ax, "Does either written list have the shape of the chant?",
           "Genealogy entries of 1886 against the 380.1 lists and Fischer's Staff triads; fixed phrase, strokes and dividers excluded", "chant_lengths.png")
# 11 chaining test ----------------------------------------------------------
if (out / "staff_chain.csv").exists():
    rows = read("staff_chain.csv")
    texts = ["chant", "Staff", "Gv", "Ta"]
    labels = {"chant": "Chant", "Staff": "Staff", "Gv": "Gv", "Ta": "Ta"}
    measures = [("last reappears as a later first", "Last unit returns as a later first"),
                ("last equals next first", "Last unit equals the next first"),
                ("consecutive same first", "Consecutive segments share a first")]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9))
    for ax, (key, title) in zip(axes, measures):
        obs = [float(next(r["observed"] for r in rows if r["text"] == t and r["measure"] == key)) for t in texts]
        nul = [float(next(r["null_mean"] for r in rows if r["text"] == t and r["measure"] == key)) for t in texts]
        pv = [float(next(r["p"] for r in rows if r["text"] == t and r["measure"] == key)) for t in texts]
        x = np.arange(len(texts)); w = 0.36
        ax.bar(x - w / 2, obs, width=w - 0.03, color=C[0], label="Observed")
        ax.bar(x + w / 2, nul, width=w - 0.03, color=C[1], label="Shuffled order")
        top = max(max(obs), max(nul), 0.01)
        for i in range(len(texts)):
            ax.text(x[i], max(obs[i], nul[i]) + top * 0.04, f"p {pv[i]:.2f}", ha="center", color=INK2, fontsize=8.5)
        ax.set_xticks(x); ax.set_xticklabels([labels[t] for t in texts])
        ax.set_ylim(0, top * 1.3)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.set_title(title, pad=8, fontsize=10.5)
        ax.grid(axis="x", visible=False)
        ax.tick_params(length=0)
    axes[0].legend(loc="upper left", fontsize=9)
    fig.suptitle("Do the sign-76 triads chain like a genealogy? Only the chant repeats its parents", x=0.02, ha="left",
                 fontsize=13, fontweight="semibold", color=INK, y=1.06)
    fig.text(0.02, 0.975, "Share of segments, observed against the mean of 500 shuffles of segment order; p = share of shuffles at or above the observation",
             color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(img / "staff_chain.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
# 12 divider stretches ------------------------------------------------------
if (out / "staff_stretches.csv").exists():
    rows = read("staff_stretches.csv")
    tri = np.array([int(r["triads_76"]) for r in rows])
    cats = list(range(1, 13)) + ["13+"]
    counts = [int((tri == k).sum()) for k in range(1, 13)] + [int((tri >= 13).sum())]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(cats))
    ax.bar(x, np.array(counts) / len(tri), width=0.7, color=C[0])
    for i, c in enumerate(counts):
        if c:
            ax.text(x[i], c / len(tri) + 0.006, str(c), ha="center", color=INK2, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([str(c) for c in cats])
    ax.set_xlabel("Sign-76 triads between two carved dividers")
    ax.set_ylabel("Share of the 95 stretches")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="x", visible=False)
    finish(fig, ax, "The carved dividers cut the Staff at triad boundaries, but not at regular intervals",
           "95% of stretches open on a 76-bearing unit against 34% for random dividers; 55% hold one to three triads, the longest holds 55",
           "staff_dividers.png")
# 13 Metoro consistency ----------------------------------------------------
if (out / "metoro_signs.csv").exists():
    rows = sorted(read("metoro_signs.csv"), key=lambda r: -int(r["occurrences"]))[:24]
    null_mean = None
    for line in open(out / "metoro.md", encoding="utf-8"):
        m = re.search(r"\*\*([\d.]+)\*\* observed, \*\*([\d.]+)\*\* when", line)
        if m:
            null_mean = float(m.group(2))
    fig, ax = plt.subplots(figsize=(8, 0.3 * len(rows) + 1.8))
    y = np.arange(len(rows))
    ax.barh(y, [float(r["p_top"]) for r in rows], height=0.62, color=C[0])
    for i, r in enumerate(rows):
        ax.text(float(r["p_top"]) + 0.01, y[i], f"{r['top_word']}  ×{r['occurrences']}", va="center", color=INK2, fontsize=8.5)
    if null_mean:
        ax.axvline(null_mean, color=AXIS, lw=1)
        ax.text(null_mean + 0.01, -0.9, f"shuffled lines: {null_mean:.2f}", color=INK2, fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels([str(int(r["sign"])) for r in rows]); ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Probability of the sign's most frequent word in Metoro's chant")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="y", visible=False)
    finish(fig, ax, "Metoro named the same sign with the same word far more often than chance",
           "The 24 most frequent signs on the four tablets he chanted over, 1873; word alignment by expectation maximisation", "metoro.png")
# 14 merge witnesses -------------------------------------------------------
if (out / "metoro_merge_tests.csv").exists():
    rows = read("metoro_merge_tests.csv")
    base = int(next(r["shared_runs"] for r in rows if r["merge_table"].startswith("Barthel")))
    rows = [r for r in rows if not r["merge_table"].startswith("Barthel")]
    labels = {"Metoro pairs, all": "Metoro's word, 4 pairs", "Metoro pairs backed by shape or copies": "Metoro plus shape or copies, 2 pairs",
              "copy substitutions only": "Copy substitutions, 3 pairs", "shape look-alikes, loose": "Shape look-alikes, 20 pairs"}
    fig, ax = plt.subplots(figsize=(8, 3.9))
    y = np.arange(len(rows))
    cols = [C[1] if r["merge_table"].startswith("random") else C[0] for r in rows]
    gains = [int(r["shared_runs"]) - base for r in rows]
    ax.barh(y, gains, height=0.6, color=cols)
    for i, g in enumerate(gains):
        ax.text(g + 0.4, y[i], f"+{g}", va="center", color=INK2, fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels([labels.get(r["merge_table"], "Random pairs of matched frequency, mean of 5") for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel(f"Shared runs gained over Barthel's numbering as is ({base} runs)")
    ax.grid(axis="y", visible=False)
    finish(fig, ax, "Which merges make more text align?",
           "Strict parallel map after merging sign pairs proposed by each witness; orange is the chance level for merging frequent signs", "merge_witnesses.png")
# 15 calendar sequence ------------------------------------------------------
if (out / "calendar_sequence.csv").exists():
    rows = read("calendar_sequence.csv")
    lines = []
    for r in rows:
        if not lines or lines[-1][0] != r["line"]:
            lines.append((r["line"], []))
        lines[-1][1].append(r)
    fig, ax = plt.subplots(figsize=(10, 0.9 * len(lines) + 1.6))
    colors = {"crescent": C[0], "marker": C[1], "other": C[2]}
    for yi, (lid, us) in enumerate(lines):
        y = len(lines) - 1 - yi
        for xi, r in enumerate(us):
            ax.add_patch(plt.Rectangle((xi, y - 0.35), 0.9, 0.7, color=colors[r["class"]], linewidth=0))
            if r["marker_group"]:
                ax.text(xi + 0.45, y + 0.42, f"M{r['marker_group']}", ha="center", va="bottom", fontsize=7.5, color=INK2)
        ax.text(-0.6, y, lid, ha="right", va="center", fontsize=10, color=INK)
    ax.set_xlim(-2.5, max(len(us) for _, us in lines) + 0.5)
    ax.set_ylim(-0.7, len(lines) - 0.2)
    ax.set_yticks([]); ax.set_xticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=C[0], label="Crescent, sign 40"), Patch(color=C[1], label="Marker group, 390.41 … 711"),
                       Patch(color=C[2], label="Other sign")], loc="lower right", ncol=1, fontsize=9, frameon=False)
    finish(fig, ax, "The Mamari calendar as a sequence",
           "Each block is one unit in reading order; marker groups are numbered where they begin", "calendar.png")
# 16 attachments as particles ------------------------------------------------
if (out / "attachments_profiles.csv").exists():
    rows = read("attachments_profiles.csv")
    order = ["Rapa Nui particles", "attached components", "head signs", "Rapa Nui content words"]
    rows = sorted(rows, key=lambda r: order.index(r["class"]))
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6))
    specs = [("top1_share", "Share of the commonest item", True), ("top5_share", "Share of the five commonest", True),
             ("types_for_90pct", "Types needed for 90% of tokens", False)]
    for ax, (key, title, pct) in zip(axes, specs):
        vals = [float(r[key]) for r in rows]
        cols = [C[0] if "Rapa Nui" in r["class"] else C[1] for r in rows]
        y = np.arange(len(rows))
        ax.barh(y, vals, height=0.6, color=cols)
        for i, v in enumerate(vals):
            ax.text(v + (0.01 if pct else max(vals) * 0.02), y[i], f"{v:.0%}" if pct else f"{int(v)}", va="center", color=INK2, fontsize=9)
        ax.set_yticks(y); ax.set_yticklabels([r["class"] for r in rows] if ax is axes[0] else [""] * len(rows))
        ax.invert_yaxis()
        if pct:
            ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        else:
            ax.set_xlim(0, max(vals) * 1.25)
        ax.set_title(title, pad=8, fontsize=10.5)
        ax.grid(axis="y", visible=False); ax.tick_params(length=0)
    from matplotlib.patches import Patch
    axes[0].legend(handles=[Patch(color=C[0], label="Rapa Nui, running text"), Patch(color=C[1], label="Rongorongo, one witness per family")],
                   loc="lower right", fontsize=8.5)
    fig.suptitle("The attached components are shaped like a particle class, not like a vocabulary", x=0.02, ha="left",
                 fontsize=13, fontweight="semibold", color=INK, y=1.06)
    fig.text(0.02, 0.975, "Concentration of four classes of item: a closed grammatical class is dominated by a few members; an open lexical class has a long tail",
             color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(img / "attachments.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
# 17 line planning ----------------------------------------------------------
if (out / "tracings_planning.csv").exists():
    rows = [r for r in read("tracings_planning.csv") if int(r["lines"]) >= 4]
    rows.sort(key=lambda r: float(r["width_slope"]))
    fig, ax = plt.subplots(figsize=(8, 0.4 * len(rows) + 1.8))
    y = np.arange(len(rows))
    vals = [float(r["width_slope"]) for r in rows]
    ax.barh(y, vals, height=0.6, color=[C[1] if v < 0 else C[0] for v in vals])
    for i, r in enumerate(rows):
        v = vals[i]
        ax.text(v + (0.01 if v >= 0 else -0.01), y[i], f"{r['lines']} lines, {r['instances']} glyphs", va="center",
                ha="left" if v >= 0 else "right", color=INK2, fontsize=8.5)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(y); ax.set_yticklabels([r["side"] for r in rows]); ax.invert_yaxis()
    lim = max(abs(v) for v in vals) * 1.6
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("Change in relative glyph width from the start of a line to its end")
    ax.grid(axis="y", visible=False)
    finish(fig, ax, "Do glyphs narrow toward the end of a line?",
           "Slope of width, relative to the line's median, against position along the line; sides with at least four aligned lines", "planning.png")
# 18 periodicity of four sides ----------------------------------------------
if (out / "untyped_autocorr.csv").exists():
    rows = read("untyped_autocorr.csv")
    picks = [("Aa", "Tahua side a, untyped"), ("Bv", "Aruku Kurenga verso, untyped"), ("Hv", "Great Santiago verso, copied text"), ("Gr", "Small Santiago recto, delimited list")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharex=True, sharey=True)
    for ax, (side, label) in zip(axes.ravel(), picks):
        pts = [r for r in rows if r["side"] == side]
        lags = [int(r["lag"]) for r in pts]; z = [float(r["z"]) for r in pts]
        ax.bar(lags, z, width=0.8, color=[C[0] if v >= 3 else "#c3c2b7" for v in z])
        ax.axhline(3, color=AXIS, lw=1)
        best = max(range(len(z)), key=lambda i: z[i])
        ax.text(lags[best] + 1.2, z[best], f"lag {lags[best]}", va="center", color=INK2, fontsize=9)
        ax.set_title(label, pad=6, fontsize=10.5)
        ax.grid(axis="x", visible=False); ax.tick_params(length=0)
    for ax in axes[1]:
        ax.set_xlabel("Distance between two positions, in signs")
    for ax in axes[:, 0]:
        ax.set_ylabel("z-score of same-sign recurrence")
    fig.suptitle("Signs recur at short fixed distances on every side; no side has a verse-length period", x=0.02, ha="left",
                 fontsize=13, fontweight="semibold", color=INK, y=1.02)
    fig.text(0.02, 0.955, "How often the sign at one position equals the sign a fixed distance later, against 200 shuffles; bars above z 3 in colour",
             color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(img / "periodicity.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
print("charts written to", img)
# 19 the prints against the tracings ----------------------------------------
if (out / "photos_planning.csv").exists() and (out / "hands_prints.csv").exists():
    tr = {r["side"]: r for r in read("tracings_planning.csv") if int(r["lines"]) >= 4}
    ph = {r["side"]: r for r in read("photos_planning.csv") if int(r["lines"]) >= 4}
    both = sorted(set(tr) & set(ph))
    st = [r for r in read("hands_prints.csv") if r["status"] == "measured"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})
    xs = [float(tr[s]["width_slope"]) for s in both]; ys = [float(ph[s]["width_slope"]) for s in both]
    lim = max(abs(v) for v in xs + ys) * 1.15
    ax1.plot([-lim, lim], [-lim, lim], color=AXIS, lw=1, ls="--")
    ax1.axhline(0, color=GRID, lw=1); ax1.axvline(0, color=GRID, lw=1)
    ax1.scatter(xs, ys, s=42, color=C[0], zorder=3)
    for s, x, y in zip(both, xs, ys):
        ax1.annotate(s, (x, y), xytext=(5, 3), textcoords="offset points", fontsize=8.5, color=INK2)
    ax1.set_xlim(-lim, lim); ax1.set_ylim(-lim, lim)
    ax1.set_xlabel("Narrowing slope on Barthel's tracing"); ax1.set_ylabel("Narrowing slope on the print")
    ax1.set_title("Do glyphs narrow the same way on the print?", pad=26)
    ax1.annotate("Sides with at least four lines in both; dashed line is agreement", (0, 1), xycoords="axes fraction", xytext=(0, 7),
                 textcoords="offset points", color=INK2, fontsize=9.5, va="bottom")
    ax1.tick_params(length=0)
    st.sort(key=lambda r: float(r["stroke_ratio"]))
    y = np.arange(len(st)); vals = [float(r["stroke_ratio"]) for r in st]; iqr = [float(r["stroke_ratio_iqr"]) for r in st]
    objs = collections.defaultdict(list)
    for i, r in enumerate(st):
        objs[r["side"][0]].append(i)
    palette = {}
    for k, (o, idx) in enumerate(sorted(objs.items())):
        if len(idx) == 2:
            palette[o] = C[k % 3]
    ax2.barh(y, vals, xerr=[[q / 2 for q in iqr], [q / 2 for q in iqr]], height=0.6, error_kw={"ecolor": AXIS, "lw": 1},
             color=[palette.get(r["side"][0], "#c3c2b7") for r in st])
    for o, idx in objs.items():
        if len(idx) == 2:
            i, j = idx
            ax2.plot([vals[i], vals[j]], [y[i], y[j]], color=palette[o], lw=1.2, alpha=0.7)
    ax2.set_yticks(y); ax2.set_yticklabels([r["side"] for r in st]); ax2.invert_yaxis()
    ax2.set_xlabel("Stroke width over glyph height, median with interquartile range")
    ax2.grid(axis="y", visible=False)
    ax2.set_title("Stroke weight per side on the prints", pad=26)
    ax2.annotate("Colour links the two sides of one object; grey sides have no measured partner", (0, 1), xycoords="axes fraction", xytext=(0, 7),
                 textcoords="offset points", color=INK2, fontsize=9.5, va="bottom")
    ax2.tick_params(length=0)
    fig.tight_layout(w_pad=3)
    fig.savefig(img / "prints.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
# 20 the decipherment control under four language models -------------------
if (out / "decipher_maori.md").exists():
    models = [("rapanui", "Rapa Nui alone\n6,000 syllables"), ("maori", "plus Maori\n3 million"), ("tahitian", "plus Tahitian\n3 million"), ("polynesian", "plus both\n6 million")]
    rec, gain_pos, gain_real, gain_en, names = [], [], [], [], []
    for key, label in models:
        suffix = "" if key == "rapanui" else f"_{key}"
        if not (out / f"decipher{suffix}.md").exists():
            continue
        md = (out / f"decipher{suffix}.md").read_text(encoding="utf-8")
        m = re.search(r"(\d+)% of (\d+) syllables recovered", md)
        sc = {r["condition"]: float(r["log_likelihood_per_pair"]) for r in read(f"decipher_scores{suffix}.csv")}
        rec.append(int(m.group(1)) if m else 0)
        gain_pos.append(sc["positive control: Apai syllables as unknown signs, searched"] - sc["positive control: Apai shuffled, searched"])
        gain_real.append(sc["real, Rapa Nui"] - sc["shuffled, Rapa Nui, mean"])
        names.append(label)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    x = np.arange(len(names))
    ax1.bar(x, rec, width=0.6, color=[C[2] if v >= 50 else C[1] for v in rec])
    for i, v in enumerate(rec):
        ax1.text(i, v + 1.5, f"{v}%", ha="center", color=INK2, fontsize=9)
    ax1.axhline(50, color=AXIS, lw=1, ls="--")
    ax1.set_xticks(x); ax1.set_xticklabels(names, fontsize=9); ax1.set_ylim(0, 105)
    ax1.set_ylabel("Syllables of a known Rapa Nui text recovered")
    ax1.grid(axis="x", visible=False); ax1.tick_params(length=0)
    ax1.set_title("Can the search recover Rapa Nui from Rapa Nui?", pad=26)
    ax1.annotate("Apai's syllables treated as unknown signs and searched under each model", (0, 1), xycoords="axes fraction",
                 xytext=(0, 7), textcoords="offset points", color=INK2, fontsize=9.5, va="bottom")
    w = 0.36
    ax2.bar(x - w / 2, gain_pos, width=w, color=C[0], label="known Rapa Nui text as signs")
    ax2.bar(x + w / 2, gain_real, width=w, color=C[1], label="the tablets' signs")
    ax2.axhline(0, color=AXIS, lw=1)
    ax2.set_xticks(x); ax2.set_xticklabels(names, fontsize=9)
    ax2.set_ylabel("Gain of the searched score over shuffles")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(axis="x", visible=False); ax2.tick_params(length=0)
    ax2.set_title("What the search gains from sign order", pad=26)
    ax2.annotate("Log-likelihood per pair, searched sequence minus its shuffles, under each model", (0, 1), xycoords="axes fraction",
                 xytext=(0, 7), textcoords="offset points", color=INK2, fontsize=9.5, va="bottom")
    fig.tight_layout(w_pad=3)
    fig.savefig(img / "decipher_models.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
# 21 how much text the search needs ------------------------------------------
if (out / "decipher_length.csv").exists():
    rows = read("decipher_length.csv")
    L = [int(r["syllables"]) for r in rows]; rec = [100 * float(r["recovered"]) for r in rows]
    gap = [float(r["searched"]) - float(r["true"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(L, rec, marker="o", color=C[0], lw=2, label="syllables recovered, %")
    ax.set_xscale("log"); ax.set_xticks(L); ax.set_xticklabels([f"{v:,}" for v in L], fontsize=9)
    ax.set_ylim(0, 105); ax.set_ylabel("Syllables of the known text recovered, %")
    ax.set_xlabel("Length of the known Māori text given to the search, in syllables")
    for x, lab in ((1100, "Apai"), (2600, "the tablets' pairs")):
        ax.axvline(x, color=C[1], lw=1.2, ls="--")
        ax.text(x * 1.05, 96, lab, color=C[1], fontsize=9, va="top")
    ax2 = ax.twinx()
    ax2.plot(L, gap, marker="s", color=MUTED, lw=1.5, ls=":", label="false assignment's lead over the truth")
    ax2.set_ylabel("Searched score minus true score, per pair", color=INK2)
    ax2.axhline(0, color=AXIS, lw=1)
    ax2.tick_params(length=0)
    ax.grid(axis="x", visible=False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=9)
    finish(fig, ax, "How much text the search needs",
           "A held-out Māori text as unknown signs under a Māori model of 2.6 million syllables; 40 signs, one syllable each", "decipher_length.png")
# 22 glyphs against words and syllables at matched size ---------------------
if (out / "matched_stats_curves.csv").exists():
    cur = collections.defaultdict(list)
    for r in read("matched_stats_curves.csv"):
        cur[r["series"]].append((int(r["tokens"]), float(r["types_mean"]), float(r["types_lo"]), float(r["types_hi"])))
    st = {r["series"]: r for r in read("matched_stats.csv")}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
    style = {"maori words": (C[0], "Māori words"), "tahitian words": (C[2], "Tahitian words"),
             "maori syllables": (C[0], "Māori syllables"), "tahitian syllables": (C[2], "Tahitian syllables")}
    for key, (col, lab) in style.items():
        pts = cur[key]; x = [p[0] for p in pts]
        ax1.fill_between(x, [p[2] for p in pts], [p[3] for p in pts], color=col, alpha=0.18, lw=0)
        ax1.plot(x, [p[1] for p in pts], color=col, lw=1.2, ls="--" if "syll" in key else "-", label=lab)
    for key, lab, col in (("units", "whole glyphs (units)", C[1]), ("heads", "head signs", INK)):
        pts = cur[key]; ax1.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=2.2, marker="o", ms=3.5, label=lab)
    ax1.set_xlabel("Tokens read, in corpus order"); ax1.set_ylabel("Distinct types seen so far")
    ax1.legend(fontsize=8.5, loc="upper left"); ax1.tick_params(length=0)
    ax1.set_title("Type-token curves at the corpus's size", pad=26, loc="left")
    ax1.annotate("Bands: 2.5 to 97.5 percentile over 300 contiguous windows of 8,688 tokens", (0, 1), xycoords="axes fraction",
                 xytext=(0, 7), textcoords="offset points", color=INK2, fontsize=9.5, va="bottom")
    measures = [("hapax_share", "hapax share of types", 100), ("top10_share", "tokens in the ten commonest", 100), ("zipf_top200", "Zipf slope, top 200", 1)]
    series = ["maori words", "tahitian words", "maori syllables", "tahitian syllables"]
    # one strip per measure, on its own scale
    ax2.axis("off")
    inner = fig.add_gridspec(3, 1, left=0.62, right=0.98, top=0.86, bottom=0.12, hspace=0.9)
    for mi, (k, lab, mult) in enumerate(measures):
        ax = fig.add_subplot(inner[mi])
        y = np.arange(len(series))
        for i, s_ in enumerate(series):
            base = {"hapax_share": "hapax", "top10_share": "top10", "zipf_top200": "zipf"}[k]
            r = st[s_]; lo, hi, m = float(r[base + "_lo"]) * mult, float(r[base + "_hi"]) * mult, float(r[k]) * mult
            col = C[0] if "maori" in s_ else C[2]
            ax.plot([lo, hi], [i, i], color=col, lw=6, alpha=0.3, solid_capstyle="butt"); ax.plot([m], [i], "o", color=col, ms=4)
        for s_, col, mk in (("units", C[1], "D"), ("heads", INK, "s")):
            v = float(st[s_][k]) * mult
            ax.axvline(v, color=col, lw=1.6, label=("whole glyphs (units)" if s_ == "units" else "head signs") if mi == 0 else None)
        if mi == 0:
            ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, 2.05), ncol=2, frameon=False)
        ax.set_yticks(y); ax.set_yticklabels([style[s_][1] for s_ in series], fontsize=8); ax.invert_yaxis()
        ax.set_title(lab, fontsize=9.5, loc="left", pad=10, color=INK2); ax.tick_params(length=0, labelsize=8); ax.grid(axis="y", visible=False)
    fig.suptitle("Whole glyphs are more diverse than words; head signs have a word's type count but a flatter top", x=0.02, ha="left",
                 fontsize=13, fontweight="semibold", color=INK, y=1.08)
    fig.savefig(img / "matched_stats.png", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
