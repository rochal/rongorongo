"""Affix test for the small stroke signs.

Question: do signs 1, 2, 4, 20, 90 (and a few relatives) behave like affixes,
i.e. attach to a restricted class of host signs on one side while being
indifferent to what stands on the other side, and chain in a fixed order?

For every candidate sign we measure, across the whole corpus:

  free / bound      free = stands as its own unit; bound = written as a
                    component fused into a compound (e.g. 062.001, 380.001)
  host selectivity  distribution of the unit before it (prev) and after it
                    (next), each compared with the corpus background by
                    Kullback-Leibler divergence in bits. A suffix should show
                    KL(prev) well above KL(next); a prefix the reverse; a
                    content sign roughly equal and low.
  enrichment        top neighbours with observed / expected ratio.
  stacking          ordered pairs of two candidates standing side by side.
  edge behaviour    share of occurrences at the very start or end of a line.

Copied passages would count the same evidence several times, so each
(prev, sign, next) context is down-weighted by the number of tablets in the
copying group G, H, P, Q, K that contain it.

Outputs (out/): affix_test.md, affix_contexts.csv
"""
import collections, csv, json, math, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))
out = root / "out"
out.mkdir(exist_ok=True)

CANDIDATES = ["001", "002", "004", "020", "090", "003", "005", "009", "022"]
CONTROLS = ["600", "700", "200", "006", "040", "380"]
COPY_GROUP = set("GHPQK")
BEGIN, END = "<line-start>", "<line-end>"


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def head(u):
    return clean(u).split(".")[0]


def comps(u):
    return clean(u).split(".")


# --- collect contexts ---------------------------------------------------
ctx = collections.defaultdict(list)          # sign -> [(tablet, prev, next, pos)]
bound = collections.Counter()                # sign -> bound occurrences
bound_host = collections.defaultdict(collections.Counter)  # sign -> host head
bound_position = collections.defaultdict(collections.Counter)  # first/later component
background = collections.Counter()
total_units = 0
for lid, units in corpus.items():
    tab = lid[0]
    heads = [head(u) for u in units]
    for i, u in enumerate(units):
        c = comps(u)
        total_units += 1
        background[heads[i]] += 1
        if len(c) == 1:
            s = c[0]
            prev = heads[i - 1] if i > 0 else BEGIN
            nxt = heads[i + 1] if i + 1 < len(units) else END
            ctx[s].append((tab, prev, nxt, i, len(units)))
        else:
            for k, s in enumerate(c):
                if s in CANDIDATES or s in CONTROLS:
                    bound[s] += 1
                    bound_position[s]["first" if k == 0 else "later"] += 1
                    host = c[0] if k > 0 else c[1]
                    bound_host[s][host] += 1

# copy-group weights: a context that appears on n tablets of the group
# counts 1/n on each of them
ctx_tablets = collections.defaultdict(set)
for s, lst in ctx.items():
    for tab, prev, nxt, _, _ in lst:
        if tab in COPY_GROUP:
            ctx_tablets[(s, prev, nxt)].add(tab)


def weight(s, tab, prev, nxt):
    if tab in COPY_GROUP:
        return 1.0 / max(1, len(ctx_tablets[(s, prev, nxt)]))
    return 1.0


bg_total = sum(background.values())
bg_p = {k: v / bg_total for k, v in background.items()}


def kl(counter):
    """KL divergence of a weighted neighbour distribution from background, bits."""
    tot = sum(counter.values())
    if tot == 0:
        return 0.0
    d = 0.0
    for k, v in counter.items():
        if k in (BEGIN, END):
            continue
        p = v / tot
        q = bg_p.get(k, 1 / bg_total)
        d += p * math.log2(p / q)
    return d


def enriched(counter, n=6):
    tot = sum(counter.values())
    rows = []
    for k, v in counter.most_common(40):
        if k in (BEGIN, END):
            continue
        exp = tot * bg_p.get(k, 0)
        rows.append((k, v, v / exp if exp else float("inf")))
    rows.sort(key=lambda r: -r[1])
    return rows[:n]


results = {}
csv_rows = []
for s in CANDIDATES + CONTROLS:
    lst = ctx.get(s, [])
    prev_c, next_c = collections.Counter(), collections.Counter()
    w_total = 0.0
    edge_start = edge_end = 0.0
    for tab, prev, nxt, i, n in lst:
        w = weight(s, tab, prev, nxt)
        w_total += w
        prev_c[prev] += w
        next_c[nxt] += w
        if i == 0: edge_start += w
        if i == n - 1: edge_end += w
    free = len(lst)
    results[s] = {
        "free": free, "free_w": w_total, "bound": bound[s],
        "bound_pos": dict(bound_position[s]),
        "bound_hosts": bound_host[s].most_common(6),
        "kl_prev": kl(prev_c), "kl_next": kl(next_c),
        "top_prev": enriched(prev_c), "top_next": enriched(next_c),
        "edge_start": edge_start / w_total if w_total else 0,
        "edge_end": edge_end / w_total if w_total else 0,
        "distinct_prev": len([k for k in prev_c if k not in (BEGIN, END)]),
        "distinct_next": len([k for k in next_c if k not in (BEGIN, END)]),
    }
    for k, v, e in results[s]["top_prev"]:
        csv_rows.append([s, "prev", k, f"{v:.1f}", f"{e:.2f}"])
    for k, v, e in results[s]["top_next"]:
        csv_rows.append([s, "next", k, f"{v:.1f}", f"{e:.2f}"])

with open(out / "affix_contexts.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sign", "side", "neighbour", "weighted_count", "enrichment"])
    w.writerows(csv_rows)

# --- stacking: ordered pairs of free candidates side by side --------------
stack = collections.Counter()
for lid, units in corpus.items():
    hs = [comps(u) for u in units]
    for a, b in zip(hs, hs[1:]):
        if len(a) == 1 and len(b) == 1 and a[0] in CANDIDATES and b[0] in CANDIDATES:
            stack[(a[0], b[0])] += 1

# --- report ---------------------------------------------------------------
md = ["# Affix test for the stroke signs\n",
      f"Corpus: {len(corpus)} lines, {total_units} units. Contexts on tablets G, H, P, Q, K are "
      "down-weighted by the number of those tablets sharing the same context, so copied passages count once.\n",
      "KL = divergence of the neighbour distribution from the corpus background, in bits. "
      "Higher = the sign is choosier about that neighbour. A suffix should have KL(prev) well above KL(next).\n"]

md.append("## Summary\n")
md.append("| sign | role | free | bound | bound as later comp. | KL prev | KL next | prev minus next | distinct prev | distinct next | at line start | at line end |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in CANDIDATES + CONTROLS:
    r = results[s]
    role = "candidate" if s in CANDIDATES else "control"
    later = r["bound_pos"].get("later", 0)
    md.append(f"| {s} | {role} | {r['free']} | {r['bound']} | {later} | {r['kl_prev']:.2f} | {r['kl_next']:.2f} | "
              f"{r['kl_prev'] - r['kl_next']:+.2f} | {r['distinct_prev']} | {r['distinct_next']} | "
              f"{r['edge_start']:.0%} | {r['edge_end']:.0%} |")

md.append("\n## Neighbours with enrichment (observed / expected)\n")
for s in CANDIDATES + CONTROLS:
    r = results[s]
    md.append(f"\n**{s}** · before it: " + ", ".join(f"{k} {v:.0f}× ({e:.1f})" for k, v, e in r["top_prev"]))
    md.append(f"\n**{s}** · after it: " + ", ".join(f"{k} {v:.0f}× ({e:.1f})" for k, v, e in r["top_next"]))
    if r["bound_hosts"]:
        md.append(f"\n**{s}** · fused to: " + ", ".join(f"{k} ({v})" for k, v in r["bound_hosts"]))

md.append("\n## Stacking: two free candidates side by side (row = first, column = second)\n")
md.append("| first \\ second | " + " | ".join(CANDIDATES) + " |")
md.append("|---|" + "---|" * len(CANDIDATES))
for a in CANDIDATES:
    md.append(f"| {a} | " + " | ".join(str(stack[(a, b)]) if stack[(a, b)] else "·" for b in CANDIDATES) + " |")
asym = []
for a in CANDIDATES:
    for b in CANDIDATES:
        if a < b and stack[(a, b)] + stack[(b, a)] >= 4:
            asym.append((a, b, stack[(a, b)], stack[(b, a)]))
md.append("\nOrder preference for pairs seen at least 4 times: " +
          "; ".join(f"{a}→{b} {ab} vs {b}→{a} {ba}" for a, b, ab, ba in asym))

(out / "affix_test.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:20]))
