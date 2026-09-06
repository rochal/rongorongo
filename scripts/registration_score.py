"""How good are the automatic print boxes? Scored against the boxes drawn by hand.

The hand-corrected boxes of a side (data/boxes/<side>.json, lines whose count
matches the transliteration) are the reference. The automatic boxes for the
same side, placed with the corrections ignored
(register.py --sides <side> --ignore-hand --tag auto), are scored against
them glyph by glyph:

  overlap     intersection over union of the two boxes
  offset      distance between their centres, in print pixels and as a share
              of the hand box's width
  width       the automatic ink width against the hand box's ink width, as
              the correlation of relative widths per line, since the
              narrowing-along-lines result rests on widths
  where       the same by position along the line (first fifth, middle,
              last fifth) and by glyph width (thin strokes against the rest),
              since those are where the registration was expected to fail

Outputs: out/registration_score.csv (per glyph), out/registration_score.md
"""
import argparse, collections, csv, json, pathlib
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--side", default="Ev")
ap.add_argument("--tag", default="auto")
args = ap.parse_args()
root = pathlib.Path(__file__).resolve().parent.parent
PAD = 0.3            # register.py pads each automatic box by this share of its width on each side
out = root / "out"

hand = json.load(open(root / "data" / "boxes" / f"{args.side}.json", encoding="utf-8"))
auto = {(r["line"], int(r["position"])): r for r in csv.DictReader(open(out / f"photo_instances_{args.tag}.csv", encoding="utf-8")) if r["side"] == args.side}
manual_rows = {(r["line"], int(r["position"])): r for r in csv.DictReader(open(out / "photo_instances.csv", encoding="utf-8")) if r["side"] == args.side and r.get("source") == "manual"}
n_units = collections.Counter(b["line"] for b in hand["boxes"])
finished = {lid for lid in n_units if all(b["unit"] != "?" for b in hand["boxes"] if b["line"] == lid)}
# lines whose hand count equals the unit count are the ones register.py used; the manual rows tell which those were
finished = {lid for lid in finished if any(k[0] == lid for k in manual_rows)}


def iou(a, b):
    ix = max(0, min(a[1], b[1]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[2], b[2]))
    inter = ix * iy
    ua = (a[1] - a[0]) * (a[3] - a[2]) + (b[1] - b[0]) * (b[3] - b[2]) - inter
    return inter / ua if ua > 0 else 0.0


rows = []
by_line = collections.defaultdict(list)
for b in hand["boxes"]:
    if b["line"] in finished:
        by_line[b["line"]].append(b)
for lid, bs in by_line.items():
    bs.sort(key=lambda b: b["position"]); n = len(bs)
    for b in bs:
        a = auto.get((lid, b["position"]))
        if not a:
            continue
        # both boxes are tight to the ink: the hand box by drawing, the automatic one by snapping (register.py)
        ab = (int(a["x0"]), int(a["x1"]), int(a["y0"]), int(a["y1"])); hb = (b["x0"], b["x1"], b["y0"], b["y1"])
        hw = hb[1] - hb[0]
        dx = ((ab[0] + ab[1]) - (hb[0] + hb[1])) / 2; dy = ((ab[2] + ab[3]) - (hb[2] + hb[3])) / 2
        pos = b["position"] / max(1, n - 1)
        where = "first fifth" if pos < 0.2 else ("last fifth" if pos > 0.8 else "middle")
        mr = manual_rows.get((lid, b["position"]))
        rows.append({"line": lid, "position": b["position"], "unit": b["unit"], "iou": iou(ab, hb), "dx": dx, "dy": dy,
                     "offset_px": float(np.hypot(dx, dy)), "offset_rel": float(np.hypot(dx, dy)) / max(1, hw), "hand_width": hw,
                     "auto_ink_width": int(a["print_ink_width"]), "hand_ink_width": int(mr["print_ink_width"]) if mr else 0,
                     "where": where, "thin": hw < 0.4 * np.median([x["x1"] - x["x0"] for x in bs]), "local_score": float(a["local_score"])})

with open(out / "registration_score.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})


def summary(sel):
    if not sel:
        return "n/a"
    i = np.array([r["iou"] for r in sel]); o = np.array([r["offset_px"] for r in sel]); orl = np.array([r["offset_rel"] for r in sel])
    return f"{len(sel)} | {np.median(i):.2f} | {np.mean(i >= 0.5):.0%} | {np.mean(i >= 0.7):.0%} | {np.median(o):.1f} | {np.median(orl):.2f}"


def width_corr(sel):
    by = collections.defaultdict(list)
    for r in sel:
        if r["hand_ink_width"] > 0 and r["auto_ink_width"] > 0:
            by[r["line"]].append((r["auto_ink_width"], r["hand_ink_width"]))
    a = []
    for lid, lst in by.items():
        aw = np.array([x[0] for x in lst], float); hw = np.array([x[1] for x in lst], float)
        a.extend(zip(aw / np.median(aw), hw / np.median(hw)))
    a = np.array(a)
    return float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]) if len(a) > 5 else float("nan")


md = [f"# The automatic registration scored against hand-drawn boxes on {args.side}\n",
      f"{len(rows)} glyphs on {len(finished)} hand-corrected lines ({', '.join(sorted(finished))}). Automatic boxes placed with the corrections ignored.\n",
      "| glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median centre offset, px | offset over hand width |", "|---|---|---|---|---|---|"]
md.append("| all: " + summary(rows) + " |")
md.append("\n## By position along the line\n")
md.append("| where | glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |\n|---|---|---|---|---|---|---|")
for w_ in ("first fifth", "middle", "last fifth"):
    md.append(f"| {w_} | " + summary([r for r in rows if r["where"] == w_]) + " |")
md.append("\n## Thin strokes against the rest\n")
md.append("| glyphs | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |\n|---|---|---|---|---|---|---|")
md.append("| thin, under 0.4 of the line's median width | " + summary([r for r in rows if r["thin"]]) + " |")
md.append("| the rest | " + summary([r for r in rows if not r["thin"]]) + " |")
md.append("\n## By the local match score the registration reported\n")
md.append("| local score | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |\n|---|---|---|---|---|---|---|")
for lo, hi, lab in ((-1, 0.2, "below 0.2, flagged"), (0.2, 0.35, "0.2 to 0.35"), (0.35, 9, "above 0.35")):
    md.append(f"| {lab} | " + summary([r for r in rows if lo <= r["local_score"] < hi]) + " |")
md.append("\n## By line\n")
md.append("| line | glyphs | median IoU | IoU at least 0.5 | median offset, px | median signed offset, px |\n|---|---|---|---|---|---|")
for lid in sorted(by_line):
    sel = [r for r in rows if r["line"] == lid]
    md.append(f"| {lid} | {len(sel)} | {np.median([r['iou'] for r in sel]):.2f} | {np.mean([r['iou'] >= 0.5 for r in sel]):.0%} | "
              f"{np.median([r['offset_px'] for r in sel]):.1f} | {np.median([r['dx'] for r in sel]):+.1f} |")
md.append(f"\n## Widths\n\nCorrelation of relative ink width, automatic against hand boxes, per line medians: **{width_corr(rows):.2f}** over all glyphs, "
          f"**{width_corr([r for r in rows if not r['thin']]):.2f}** without the thin strokes.")
(out / "registration_score.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
