"""Compound decomposition: are the rare signs built from the frequent ones?

Pozdniakov's reduction of Barthel's inventory to about 52 basic signs rests
on the claim that most other signs are compounds of those. This script
tests the claim on Barthel's catalogue drawings.

  basic set   the N_BASIC most frequent head signs in the corpus
  targets     every other sign with a drawing (the "rare" signs)
  fit         each target drawing (S x S canvas) is explained greedily by up
              to MAX_PARTS basic drawings, each tried mirrored and at several
              scales, slid over the canvas by batched FFT correlation.
              Matching is tolerant: a target pixel counts as explained when it
              lies within TOL pixels of part ink, and a part pixel counts as a
              hit when it lies within TOL pixels of target ink. A placement is
              scored by the F1 of those two rates inside its window, and must
              explain at least MIN_INK of the target's ink. After each part
              the explained ink is removed.
              coverage  = share of target ink explained by all parts
              precision = share of part ink that hit target ink
              A target decomposes at coverage >= COV and precision >= PREC.
  controls    random  the same fit with N_BASIC random rare signs as
                      templates, repeated N_CONTROL times
              positive Barthel's own variant drawings of the basic signs,
                      fitted with the basic templates; they should be
                      explained by their own sign

Targets are fitted in parallel with a process pool.

Outputs (out/): decomposition.csv, decomposition_control.csv,
decomposition_positive.csv, decomposition.md,
docs/img/decomposition_sheet.png (targets with their fitted parts)
"""
import argparse, collections, csv, json, os, pathlib, re, time
# one BLAS thread per process: the pool provides the parallelism, and 30
# workers each starting 32 OpenBLAS threads exhausts memory
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation

S = 48
FFT = 2 * S
MAX_PARTS = 3
SCALES = (1.0, 0.8, 0.65, 0.5, 0.4)
GAP = 6
root = pathlib.Path(__file__).resolve().parent.parent
sd = root / "data" / "signs"
out = root / "out"
img_dir = root / "docs" / "img"


# ---------------------------------------------------------------- drawings
def load_drawings():
    rows_map = json.load(open(sd / "rows.json"))
    drawings, variants = {}, {}
    for row, names in rows_map.items():
        f = next(iter(sd.glob(f"gif/{row}.*")), None)
        if f is None:
            continue
        a = np.array(Image.open(f).convert("L")) < 128
        w = a.shape[1] / 5
        for k, name in enumerate(names):
            if not name:
                continue
            cell = a[:, int(k * w):int((k + 1) * w)]
            cols = cell.sum(axis=0) > 0
            segs, inseg, last = [], False, 0
            for i, v in enumerate(cols):
                if v and not inseg:
                    start, inseg = i, True
                if v:
                    last = i
                if inseg and not v and i - last >= GAP:
                    segs.append((start, last + 1)); inseg = False
            if inseg:
                segs.append((start, last + 1))
            segs.sort(key=lambda se: -(se[1] - se[0]))
            for v, (s, e) in enumerate(segs):
                piece = cell[:, s:e]
                ys = np.where(piece.sum(axis=1) > 0)[0]
                if len(ys) == 0:
                    continue
                piece = piece[ys[0]:ys[-1] + 1]
                if piece.sum() < 12:
                    continue
                if v == 0 and name not in drawings:
                    drawings[name] = piece
                elif v > 0:
                    variants.setdefault(name, []).append(piece)
    return drawings, variants


def canvas(bits, size):
    h, w = bits.shape
    scale = size / max(h, w)
    im = Image.fromarray((bits * 255).astype("uint8")).resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    a = np.asarray(im) > 100
    c = np.zeros((size, size), bool)
    y0, x0 = (size - a.shape[0]) // 2, (size - a.shape[1]) // 2
    c[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    return c


def tight(bits):
    ys, xs = np.where(bits)
    return bits[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# ---------------------------------------------------------------- templates
def build_templates(drawings, names, tol):
    """Every variant of every basic sign with two precomputed spectra: the
    part itself and the part dilated by tol pixels."""
    T, spec, spec_d = [], [], []
    for n in names:
        base = tight(drawings[n])
        for mir in (False, True):
            b = base[:, ::-1] if mir else base
            for sc in SCALES:
                size = max(6, int(round(S * sc)))
                c = canvas(b, size)
                if not c.any():
                    continue
                part = tight(c)
                if part.sum() < 8 or part.shape[0] > S or part.shape[1] > S:
                    continue
                dil = binary_dilation(np.pad(part, tol), iterations=tol)
                T.append((n, mir, sc, part, dil, part.sum()))
                spec.append(np.conj(np.fft.rfft2(part.astype(float), s=(FFT, FFT))))
                spec_d.append(np.conj(np.fft.rfft2(dil.astype(float), s=(FFT, FFT))))
    return T, np.stack(spec), np.stack(spec_d)


# ---------------------------------------------------------------- worker
G = {}


def init_worker(T, spec_path, spec_d_path, tol, min_ink, min_score):
    """Workers memory-map the template spectra instead of receiving a copy."""
    G.update(T=T, spec=np.load(spec_path, mmap_mode="r"), spec_d=np.load(spec_d_path, mmap_mode="r"),
             tol=tol, min_ink=min_ink, min_score=min_score)


def save_spectra(spec, spec_d, tag):
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    p1, p2 = tmp / f"spec_{tag}.npy", tmp / f"spec_d_{tag}.npy"
    np.save(p1, spec.astype(np.complex64))
    np.save(p2, spec_d.astype(np.complex64))
    return str(p1), str(p2)


def fit(target):
    """Greedy tolerant decomposition of one S x S target canvas."""
    T, spec, spec_d, tol = G["T"], G["spec"], G["spec_d"], G["tol"]
    remaining = target.copy()
    total = target.sum()
    parts, explained_total, part_ink, hit_ink = [], 0, 0, 0
    for _ in range(MAX_PARTS):
        rem_f = remaining.astype(float)
        rem_dil = binary_dilation(remaining, iterations=tol).astype(float)
        F_rem = np.fft.rfft2(rem_f, s=(FFT, FFT))
        F_dil = np.fft.rfft2(rem_dil, s=(FFT, FFT))
        # explained[t, y, x]: remaining ink within tol of the part placed at (y, x)
        explained = np.fft.irfft2(F_rem[None] * spec_d, s=(FFT, FFT), axes=(1, 2))
        # the dilated part is padded by tol on each side, so its origin sits
        # tol pixels up and left of the part's origin: shift the map back
        explained = np.roll(explained, tol, axis=(1, 2))
        # hits[t, y, x]: part ink within tol of remaining ink
        hits = np.fft.irfft2(F_dil[None] * spec, s=(FFT, FFT), axes=(1, 2))
        rem_total = max(1.0, rem_f.sum())
        best = None
        for t, (n, mir, sc, part, dil, ink) in enumerate(T):
            ph, pw = part.shape
            H, W = S - ph + 1, S - pw + 1
            ex = explained[t, :H, :W]
            ht = hits[t, :H, :W]
            # recall against all remaining ink, so a whole-sign match beats a
            # fragment that fits well inside a small window
            recall = ex / rem_total
            precision = ht / ink
            f1 = 2 * recall * precision / np.maximum(recall + precision, 1e-9)
            f1[ex < G["min_ink"] * total] = 0
            k = np.argmax(f1)
            v = f1.flat[k]
            if best is None or v > best[0]:
                y, x = divmod(k, W)
                best = (v, t, y, x, ht.flat[k])
        if best is None or best[0] < G["min_score"]:
            break
        v, t, y, x, ht = best
        n, mir, sc, part, dil, ink = T[t]
        window = np.zeros((S + 2 * tol, S + 2 * tol), bool)
        window[y:y + dil.shape[0], x:x + dil.shape[1]] = dil
        window = window[tol:tol + S, tol:tol + S]
        gained = (window & remaining).sum()
        explained_total += gained
        part_ink += ink
        hit_ink += ht
        remaining &= ~window
        parts.append((n, mir, sc, float(v), int(y), int(x)))
    return parts, explained_total / total, (hit_ink / part_ink if part_ink else 0.0)


def run(drawings, names, targets, tol, min_ink, min_score, workers, label):
    T, spec, spec_d = build_templates(drawings, names, tol)
    p1, p2 = save_spectra(spec, spec_d, label.replace(" ", "_"))
    jobs = [(s, canvas(drawings[s], S)) for s in targets if s not in names]
    t0 = time.time()
    with Pool(workers, initializer=init_worker, initargs=(T, p1, p2, tol, min_ink, min_score)) as pool:
        fits = pool.map(fit, [c for _, c in jobs], chunksize=8)
    print(f"  {label}: {len(jobs)} targets in {time.time() - t0:.0f}s", flush=True)
    return [{"sign": s, "parts": p, "coverage": cov, "precision": prec} for (s, _), (p, cov, prec) in zip(jobs, fits)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="only fit the first N targets")
    ap.add_argument("--controls", type=int, default=3, help="random-template control runs")
    ap.add_argument("--basic", type=int, default=55, help="size of the basic set")
    ap.add_argument("--tol", type=int, default=2, help="pixel tolerance for a match")
    ap.add_argument("--cov", type=float, default=0.8, help="coverage needed to decompose")
    ap.add_argument("--prec", type=float, default=0.7, help="precision needed to decompose")
    ap.add_argument("--min-ink", type=float, default=0.10, help="a part must explain this share of the target's ink")
    ap.add_argument("--min-score", type=float, default=0.3, help="minimum F1 for a placement")
    ap.add_argument("--workers", type=int, default=max(1, min(16, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args()
    out.mkdir(exist_ok=True)

    drawings, variants = load_drawings()
    corpus = json.load(open(root / "data" / "corpus.json", encoding="utf-8"))

    def head(u):
        return re.sub(r"[a-zA-Z]+$", "", re.split(r"[.:;']", re.sub(r"[?!]", "", u))[0])

    freq = collections.Counter()
    for lid, units in corpus.items():
        if lid[0] in "PQK":
            continue
        for u in units:
            h = head(u)
            if h in drawings:
                freq[h] += 1
    basic = [s for s, _ in freq.most_common()][:args.basic]
    targets = [s for s in drawings if s not in basic]
    if args.limit:
        targets = targets[:args.limit]
    rng = np.random.default_rng(11)
    dec = lambda r: r["coverage"] >= args.cov and r["precision"] >= args.prec and len(r["parts"]) >= 1
    print(f"{len(drawings)} drawings, {len(basic)} basic, {len(targets)} targets, {args.workers} workers, tol {args.tol}px", flush=True)

    main_res = run(drawings, basic, targets, args.tol, args.min_ink, args.min_score, args.workers, "basic set")
    for r in main_res:
        r["tokens"] = freq[r["sign"]]
        r["decomposes"] = dec(r)

    # positive control: variants of basic signs against the basic templates
    T, spec, spec_d = build_templates(drawings, basic, args.tol)
    p1, p2 = save_spectra(spec, spec_d, "positive")
    pos_jobs = [(s, canvas(v, S)) for s in basic for v in variants.get(s, [])]
    with Pool(args.workers, initializer=init_worker, initargs=(T, p1, p2, args.tol, args.min_ink, args.min_score)) as pool:
        fits = pool.map(fit, [c for _, c in pos_jobs], chunksize=4)
    positive = [{"sign": s, "parts": p, "coverage": cov, "precision": prec,
                 "self": bool(p) and p[0][0] == s} for (s, _), (p, cov, prec) in zip(pos_jobs, fits)]
    for r in positive:
        r["decomposes"] = dec(r)
    print(f"  positive control: {len(positive)} variant drawings", flush=True)

    controls = []
    for c in range(args.controls):
        pick = list(rng.choice(targets, args.basic, replace=False))
        res = run(drawings, pick, targets, args.tol, args.min_ink, args.min_score, args.workers, f"control {c + 1}")
        for r in res:
            r["tokens"] = freq[r["sign"]]
            r["decomposes"] = dec(r)
        controls.append(res)

    # ------------------------------------------------------------ outputs
    def fmt_parts(parts):
        return " + ".join(f"{n}{'m' if mir else ''}@{sc}" for n, mir, sc, _, _, _ in parts)

    with open(out / "decomposition.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sign", "tokens", "coverage", "precision", "decomposes", "n_parts", "parts"])
        for r in sorted(main_res, key=lambda r: -r["coverage"]):
            w.writerow([r["sign"], r["tokens"], f"{r['coverage']:.3f}", f"{r['precision']:.3f}", r["decomposes"], len(r["parts"]), fmt_parts(r["parts"])])
    if controls:
        with open(out / "decomposition_control.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["control", "sign", "coverage", "precision", "decomposes"])
            for c, res in enumerate(controls, 1):
                for r in res:
                    w.writerow([c, r["sign"], f"{r['coverage']:.3f}", f"{r['precision']:.3f}", r["decomposes"]])
    with open(out / "decomposition_positive.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sign", "coverage", "precision", "first_part", "matched_itself", "decomposes"])
        for r in positive:
            w.writerow([r["sign"], f"{r['coverage']:.3f}", f"{r['precision']:.3f}", r["parts"][0][0] if r["parts"] else "", r["self"], r["decomposes"]])

    def summary(res):
        cov = np.array([r["coverage"] for r in res]); prec = np.array([r["precision"] for r in res])
        d = np.array([r["decomposes"] for r in res]); toks = np.array([r.get("tokens", 0) for r in res])
        return dict(n=len(res), mean_cov=cov.mean(), median_cov=np.median(cov), mean_prec=prec.mean(), share=d.mean(),
                    tokens=toks[d].sum() / max(1, toks.sum()), one=np.mean([len(r["parts"]) == 1 and r["decomposes"] for r in res]))

    sm, sc_ = summary(main_res), [summary(c) for c in controls]
    tokens_basic = sum(freq[s] for s in basic)
    tokens_rare = sum(freq[s] for s in targets)
    tokens_dec = sum(r["tokens"] for r in main_res if r["decomposes"])
    part_use = collections.Counter(p[0] for r in main_res if r["decomposes"] for p in r["parts"])
    md = ["# Compound decomposition\n",
          f"Basic set: the {len(basic)} most frequent head signs with drawings, {tokens_basic / (tokens_basic + tokens_rare):.0%} of head-sign "
          f"tokens (one witness per family). Targets: the other {len(targets)} drawn signs. Tolerance {args.tol} px; a placement needs "
          f"F1 >= {args.min_score} and must explain >= {args.min_ink:.0%} of the target's ink; a target decomposes at coverage >= "
          f"{args.cov:.0%} and precision >= {args.prec:.0%} with up to {MAX_PARTS} parts.\n",
          "## Result\n",
          "| template set | targets | mean coverage | median coverage | mean precision | share decomposing | share of rare tokens decomposing | single-part fits |",
          "|---|---|---|---|---|---|---|---|",
          f"| {len(basic)} most frequent signs | {sm['n']} | {sm['mean_cov']:.2f} | {sm['median_cov']:.2f} | {sm['mean_prec']:.2f} | {sm['share']:.0%} | {sm['tokens']:.0%} | {sm['one']:.0%} |"]
    for i, s in enumerate(sc_, 1):
        md.append(f"| control {i}, random rare signs | {s['n']} | {s['mean_cov']:.2f} | {s['median_cov']:.2f} | {s['mean_prec']:.2f} | {s['share']:.0%} | {s['tokens']:.0%} | {s['one']:.0%} |")
    pc = np.array([r["coverage"] for r in positive])
    md.append(f"\n## Positive control\n\n{len(positive)} variant drawings that Barthel gave for basic signs, fitted with the basic templates: "
              f"mean coverage {pc.mean():.2f}, median {np.median(pc):.2f}; {np.mean([r['self'] for r in positive]):.0%} matched their own sign "
              f"first; {np.mean([r['decomposes'] for r in positive]):.0%} reach the decomposition threshold.\n")
    md.append(f"If every decomposing sign were replaced by its parts, the head inventory would fall from {len(basic) + len(targets)} to "
              f"{len(basic) + sum(1 for r in main_res if not r['decomposes'])} drawn signs, and {tokens_dec} of {tokens_rare} rare tokens "
              f"({tokens_dec / max(1, tokens_rare):.0%}) would be rewritten with basic signs.\n")
    md.append("## Basic signs most used as parts\n\n| basic sign | corpus tokens | used in decompositions |\n|---|---|---|")
    for s, n in part_use.most_common(20):
        md.append(f"| {s} | {freq[s]} | {n} |")
    md.append("\n## Decomposing rare signs, most frequent first\n\n| sign | tokens | coverage | precision | parts |\n|---|---|---|---|---|")
    for r in sorted([r for r in main_res if r["decomposes"]], key=lambda r: -r["tokens"])[:40]:
        md.append(f"| {r['sign']} | {r['tokens']} | {r['coverage']:.2f} | {r['precision']:.2f} | {fmt_parts(r['parts'])} |")
    md.append("\n## Frequent rare signs that do not decompose\n\n| sign | tokens | coverage | precision | best parts |\n|---|---|---|---|---|")
    for r in sorted([r for r in main_res if not r["decomposes"]], key=lambda r: -r["tokens"])[:20]:
        md.append(f"| {r['sign']} | {r['tokens']} | {r['coverage']:.2f} | {r['precision']:.2f} | {fmt_parts(r['parts'])} |")
    (out / "decomposition.md").write_text("\n".join(md), encoding="utf-8")

    # contact sheet
    show = sorted([r for r in main_res if r["decomposes"]], key=lambda r: -r["tokens"])[:24]
    cell, cols = 52, 4
    sheet = Image.new("L", (cols * (cell * 4 + 30), max(1, (len(show) + cols - 1) // cols) * (cell + 22) + 8), 255)
    d = ImageDraw.Draw(sheet)

    def thumb(bits):
        im = Image.fromarray(((~bits) * 255).astype("uint8"))
        im.thumbnail((cell - 6, cell - 6))
        return im

    for k, r in enumerate(show):
        x0 = (k % cols) * (cell * 4 + 30) + 6
        y0 = (k // cols) * (cell + 22) + 4
        t = thumb(canvas(drawings[r["sign"]], S))
        sheet.paste(t, (x0 + (cell - t.width) // 2, y0 + (cell - t.height) // 2))
        d.text((x0 + 2, y0 + cell), f"{r['sign']} ({r['tokens']}) =", fill=0)
        for j, (n, mir, sc, _, _, _) in enumerate(r["parts"]):
            b = drawings[n][:, ::-1] if mir else drawings[n]
            t = thumb(canvas(b, S))
            px = x0 + cell * (j + 1) + 8
            sheet.paste(t, (px + (cell - t.width) // 2, y0 + (cell - t.height) // 2))
            d.text((px + 2, y0 + cell), f"{n}{'m' if mir else ''} {sc}", fill=0)
    sheet.save(img_dir / "decomposition_sheet.png")
    for f in (out / "_tmp").glob("spec*.npy"):
        f.unlink()
    print("\n".join(md[3:12]))


if __name__ == "__main__":
    main()
