"""Render labelled glyph strips for the README from Barthel's catalogue drawings.

Each strip is a row of sign drawings with the Barthel number under each,
written to docs/img/glyphs/<name>.png. Signs are taken from the catalogue
row images fetched by fetch_signs.py; the main drawing of each sign is used.
A "|" in a group inserts a gap, for showing pairs side by side.
"""
import json, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

root = pathlib.Path(__file__).resolve().parent.parent
sd = root / "data" / "signs"
out = root / "docs" / "img" / "glyphs"
out.mkdir(parents=True, exist_ok=True)
GAP = 6
H = 60            # glyph height in pixels
PAD = 14

GROUPS = {
    "delimiter":     ["380", "001"],
    "ev4_entries":   ["088", "047", "280", "521", "061"],
    "ev6_formula":   ["027", "077", "034", "004", "522", "700", "600", "059"],
    "strokes":       ["001", "002", "003", "004", "005", "009", "020", "022", "090"],
    "controls":      ["600", "700", "200", "006", "040"],
    "attachments":   ["076", "003", "001", "010", "006", "009", "074", "064"],
    "lookalikes":    ["212", "216", "|", "022", "024", "|", "622", "624", "|", "700", "710", "|", "090", "091"],
    "collocations":  ["040", "700", "|", "007", "600", "|", "280", "001", "|", "027", "077"],
    "staff":         ["076", "090", "604", "606"],
    "copies":        ["022", "380", "|", "200", "050", "132"],
    "alternation":   ["092", "035", "073", "006", "|", "710", "020", "090"],
    "list_tablets":  ["380", "001", "003", "052"],
    "series":        ["001", "022", "200", "300", "430", "522", "600", "700"],
    "metoro":        ["001", "005", "040", "600", "700", "006", "380", "522"],
}

rows = json.load(open(sd / "rows.json"))
drawings = {}
for row, names in rows.items():
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
        if not segs:
            continue
        s, e = max(segs, key=lambda se: se[1] - se[0])
        piece = cell[:, s:e]
        ys = np.where(piece.sum(axis=1) > 0)[0]
        if len(ys) and piece.sum() >= 12 and name not in drawings:
            drawings[name] = piece[ys[0]:ys[-1] + 1]

try:
    font = ImageFont.truetype("segoeui.ttf", 13)
except OSError:
    font = ImageFont.load_default()


def glyph_image(sign):
    bits = drawings[sign]
    h, w = bits.shape
    scale = H / h
    im = Image.fromarray(((~bits) * 255).astype("uint8")).resize((max(8, round(w * scale)), H), Image.LANCZOS)
    return im


for name, signs in GROUPS.items():
    tiles = []
    for s in signs:
        if s == "|":
            tiles.append(None)
            continue
        if s not in drawings:
            print("missing drawing for", s)
            continue
        tiles.append((s, glyph_image(s)))
    width = PAD
    for t in tiles:
        width += 22 if t is None else max(t[1].width, 34) + PAD
    sheet = Image.new("L", (width, H + 30), 255)
    d = ImageDraw.Draw(sheet)
    x = PAD
    for t in tiles:
        if t is None:
            x += 22
            continue
        s, im = t
        cw = max(im.width, 34)
        sheet.paste(im, (x + (cw - im.width) // 2, 4))
        label = str(int(s))
        tw = d.textlength(label, font=font)
        d.text((x + (cw - tw) / 2, H + 8), label, fill=60, font=font)
        x += cw + PAD
    sheet.save(out / f"{name}.png")
print(f"{len(GROUPS)} strips written to {out}")
