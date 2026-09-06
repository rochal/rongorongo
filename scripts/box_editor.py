"""Hand-correct the glyph boxes on a print.

    python scripts/box_editor.py Ev                      # open Keiti's verso, the print
    python scripts/box_editor.py Ev --auto               # start again from the automatic boxes
    python scripts/box_editor.py Ev --source tracing     # the same for Barthel's tracing of the side
    python scripts/box_editor.py Ev --source tracing --seed-from-print
                                                         # first tracing boxes placed from the finished print boxes

With --source tracing the image is Barthel's drawing, the starting boxes
are the count-aligned ones from tracings.py, every line is upright, and
the corrections go to data/boxes/tracing/<side>.json, which tracings.py
then uses. With --seed-from-print, on every line whose print boxes are
finished and at least four in five of them hand-edited, the tracing boxes
are placed by mapping the print boxes onto the tracing line, anchored on
the tracing's own box where the two agree, and shrunk to the ink under
them; other lines keep the count-aligned boxes. Boxes you have edited are
drawn solid, untouched automatic ones dashed.

Opens the print with the boxes that register.py found, or with the saved
corrections in data/boxes/<side>.json if there are any, and lets you fix
them. On save, register.py uses the corrected boxes for that side from
then on, so the corrections are part of the reproducible run and are
committed with the repository.

Mouse
  drag inside a box        move it
  drag an edge or corner   resize it
  click                    select; click empty space to deselect
  wheel                    zoom around the pointer
  right drag               pan
  drag on empty ground     draw a new box on the line of the nearest box
                           (or the line chosen in the box at the top); it
                           is selected at once
Keys
  Tab                      step forward: a box's left and top edges, then its
                           right and bottom edges, then the next box in
                           reading order; Shift+Tab steps back
  arrows                   move the active edges one pixel; hold the key to
                           keep going
  Shift+arrows             move the whole box
  Ctrl                     with either, five pixels at a time
  Delete                   delete the selected box
  Ctrl+S                   save
  Escape                   cancel drawing

The label on each box is its reading position and the transliterated unit
at that position in the CEIPP line, assigned by order along the line, left
to right for upright lines and right to left for lines that are upside
down on the print. The status bar shows, for the selected line, how many
units the transliteration has and how many boxes there are; make them
match and the labels are right. Boxes beyond the unit count are labelled ?.
"""
import argparse, csv, json, pathlib, re, sys, tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

root_dir = pathlib.Path(__file__).resolve().parent.parent
BOXES = root_dir / "data" / "boxes"
BOXES.mkdir(parents=True, exist_ok=True)
COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#b3529b", "#c9a227", "#3aa7c9", "#d9534f", "#6c8e3a"]
EDGE = 6          # screen pixels within which a press grabs an edge


def clean(u):
    u = re.sub(r"[?!]", "", u)
    return ".".join(re.sub(r"[a-zA-Z]+$", "", c) for c in re.split(r"[.:;']", u))


def line_units(corpus, lid):
    return [u for u in corpus[lid] if not clean(u).startswith("(") and clean(u).split(".")[0] not in ("000", "999")]


def line_number(lid):
    return int(re.sub(r"\D", "", lid[2:]) or 0)


def load_auto(side, source="print"):
    boxes, lines = [], {}
    p = root_dir / "out" / ("photo_instances.csv" if source == "print" else "glyph_instances.csv")
    if not p.exists():
        return boxes, lines
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r["side"] != side:
            continue
        boxes.append({"line": r["line"], "x0": int(r["x0"]), "x1": int(r["x1"]), "y0": int(r["y0"]), "y1": int(r["y1"])})
        lines[r["line"]] = r["orientation"] if source == "print" else "upright"
    return boxes, lines


def seed_from_print(side, tracing_img, auto_boxes, units):
    """Place tracing boxes from the finished print boxes: per line, a linear map from the print line's extent to the
    tracing line's extent (reversed for lines upside down on the print), then each box shrunk to the ink under it."""
    pj = BOXES / f"{side}.json"
    if not pj.exists():
        return None
    pd = json.load(open(pj, encoding="utf-8"))
    ink = (tracing_img < 128)
    out = []
    by_line = {}
    for b in pd["boxes"]:
        by_line.setdefault(b["line"], []).append(b)
    auto_by = {}
    for b in auto_boxes:
        auto_by.setdefault(b["line"], []).append(b)
    for lid, pb in by_line.items():
        n_ed = sum(1 for b in pb if b.get("edited"))
        if len(pb) != len(units.get(lid, [])) or lid not in auto_by or n_ed < 0.8 * len(pb):
            out.extend(auto_by.get(lid, []))       # unfinished on the print, or mostly automatic: keep the tracing's own boxes
            continue
        ab = sorted(auto_by[lid], key=lambda b: b["x0"])
        tx0, tx1 = min(b["x0"] for b in ab), max(b["x1"] for b in ab)
        ty0, ty1 = min(b["y0"] for b in ab), max(b["y1"] for b in ab)
        px0, px1 = min(b["x0"] for b in pb), max(b["x1"] for b in pb)
        flipped = pd["lines"].get(lid) == "flipped"
        scale = (tx1 - tx0) / max(1, px1 - px0)
        pbs = sorted(pb, key=lambda b: b["position"])
        for k, b in enumerate(pbs):
            if flipped:
                a0, a1 = tx0 + (px1 - b["x1"]) * scale, tx0 + (px1 - b["x0"]) * scale
            else:
                a0, a1 = tx0 + (b["x0"] - px0) * scale, tx0 + (b["x1"] - px0) * scale
            # where the tracing's own box at this position agrees with the map to within a glyph, it is used as
            # it is, width included: the print's widths are the thing under test, not a guide to Barthel's.
            # The mapped box is used only where the count alignment put its box somewhere else
            if k < len(ab):
                t = ab[k]; w = a1 - a0
                if abs((t["x0"] + t["x1"]) / 2 - (a0 + a1) / 2) < max(8, w):
                    out.append({"line": lid, "x0": t["x0"], "x1": t["x1"], "y0": t["y0"], "y1": t["y1"]})
                    continue
            a0, a1 = max(0, int(round(a0)) - 2), int(round(a1)) + 2
            band = ink[ty0:ty1, a0:a1]
            cols = band.any(axis=0)
            xs = [i for i, v in enumerate(cols) if v]
            if xs:
                a0, a1 = a0 + xs[0], a0 + xs[-1] + 1
            rows = ink[ty0:ty1, a0:a1].any(axis=1)
            ys = [i for i, v in enumerate(rows) if v]
            y0, y1 = (ty0 + ys[0], ty0 + ys[-1] + 1) if ys else (ty0, ty1)
            out.append({"line": lid, "x0": int(a0), "x1": int(a1), "y0": int(y0), "y1": int(y1)})
    for lid, ab in auto_by.items():
        if lid not in by_line:
            out.extend(ab)
    # neighbours may not overlap: the boundary between two overlapping boxes goes to the emptiest column between their centres
    by = {}
    for b in out:
        by.setdefault(b["line"], []).append(b)
    for lst in by.values():
        lst.sort(key=lambda b: b["x0"])
        for a, b in zip(lst, lst[1:]):
            if b["x0"] < a["x1"]:
                # the two share the union of their extents, cut at the emptiest column between their centres,
                # or in the middle when one lies inside the other
                u0, u1 = a["x0"], max(a["x1"], b["x1"])
                lo, hi = int((a["x0"] + a["x1"]) / 2), int((b["x0"] + b["x1"]) / 2)
                if hi - lo < 2:
                    lo, hi = u0 + (u1 - u0) // 3, u1 - (u1 - u0) // 3
                y0, y1 = min(a["y0"], b["y0"]), max(a["y1"], b["y1"])
                col = ink[y0:y1, lo:hi].sum(axis=0) if hi > lo else None
                cut = lo + int(col.argmin()) if col is not None and len(col) else (u0 + u1) // 2
                a["x0"], a["x1"], b["x0"], b["x1"] = u0, cut, cut, u1
    return out


def order_boxes(boxes, lines):
    """Assign positions by reading order within each line."""
    by = {}
    for b in boxes:
        by.setdefault(b["line"], []).append(b)
    for lid, lst in by.items():
        if lines.get(lid) == "flipped":
            lst.sort(key=lambda b: -b["x1"])
        else:
            lst.sort(key=lambda b: b["x0"])
        for k, b in enumerate(lst):
            b["position"] = k
    return boxes


class Editor:
    def __init__(self, side, auto, source="print", seed=False):
        self.side = side; self.source = source
        folder = root_dir / "data" / ("photos" if source == "print" else "tracings")
        self.image_path = next(p for p in folder.glob(side + ".*") if p.suffix.lower() in (".jpg", ".png"))
        self.img = Image.open(self.image_path).convert("RGB")
        self.corpus = json.load(open(root_dir / "data" / "corpus.json", encoding="utf-8"))
        key = "Ia" if side == "I" else side
        self.units = {lid: line_units(self.corpus, lid) for lid in self.corpus if lid.startswith(key)}
        self.json_path = (BOXES if source == "print" else BOXES / "tracing") / f"{side}.json"
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        if self.json_path.exists() and not auto and not seed:
            d = json.load(open(self.json_path, encoding="utf-8"))
            self.boxes, self.lines = d["boxes"], d["lines"]
        else:
            self.boxes, self.lines = load_auto(side, source)
            if seed and source == "tracing":
                import numpy as np
                seeded = seed_from_print(side, np.asarray(self.img.convert("L")), self.boxes, self.units)
                if seeded is not None:
                    self.boxes = seeded
        for lid in self.units:
            self.lines.setdefault(lid, "upright")
        order_boxes(self.boxes, self.lines)
        self.zoom = 1.0; self.ox = 0; self.oy = 0
        self.sel = None; self.mode = None; self.drag = None; self.add_mode = False; self.dirty = False
        self.edge_mode = 0          # 0: left and top edges take the arrows; 1: right and bottom

        self.root = tk.Tk()
        self.root.title(f"Boxes on {side}, " + ("the print" if source == "print" else "the tracing"))
        bar = ttk.Frame(self.root); bar.pack(side="top", fill="x")
        ttk.Button(bar, text="Add box (A)", command=self.start_add).pack(side="left", padx=2)
        ttk.Button(bar, text="Delete (Del)", command=self.delete).pack(side="left", padx=2)
        ttk.Button(bar, text="Save (Ctrl+S)", command=self.save).pack(side="left", padx=2)
        ttk.Button(bar, text="Reset to automatic", command=self.reset).pack(side="left", padx=2)
        ttk.Label(bar, text="  line for new boxes:").pack(side="left")
        self.line_var = tk.StringVar(value="nearest")
        ttk.Combobox(bar, textvariable=self.line_var, values=["nearest"] + sorted(self.units, key=line_number), width=9, state="readonly").pack(side="left")
        ttk.Label(bar, text="  orientation of that line:").pack(side="left")
        self.orient_var = tk.StringVar(value="")
        ttk.Combobox(bar, textvariable=self.orient_var, values=["upright", "flipped"], width=8, state="readonly").pack(side="left")
        ttk.Button(bar, text="apply", command=self.set_orientation).pack(side="left", padx=2)
        self.status = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.status, anchor="w").pack(side="bottom", fill="x")
        self.canvas = tk.Canvas(self.root, width=1500, height=600, bg="#333", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.fit()
        self.canvas.bind("<ButtonPress-1>", self.press); self.canvas.bind("<B1-Motion>", self.motion); self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.bind("<ButtonPress-3>", self.pan_start); self.canvas.bind("<B3-Motion>", self.pan_move)
        self.canvas.bind("<MouseWheel>", self.wheel); self.canvas.bind("<Button-4>", self.wheel); self.canvas.bind("<Button-5>", self.wheel)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.root.bind("<Delete>", lambda e: self.delete()); self.root.bind("<Control-s>", lambda e: self.save())
        self.root.bind("<Key-a>", lambda e: self.start_add()); self.root.bind("<Key-A>", lambda e: self.start_add())
        self.root.bind("<Escape>", lambda e: self.cancel_add())
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            self.root.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self.nudge(dx, dy))
            self.root.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self.nudge(dx, dy, whole=True))
            self.root.bind(f"<Control-{key}>", lambda e, dx=dx, dy=dy: self.nudge(5 * dx, 5 * dy))
            self.root.bind(f"<Control-Shift-{key}>", lambda e, dx=dx, dy=dy: self.nudge(5 * dx, 5 * dy, whole=True))
        # Tab and Shift+Tab step through the boxes; the focus-traversal events are taken over so that
        # Tk does not move the focus between the toolbar widgets instead
        self.root.bind_all("<<NextWindow>>", lambda e: self.step(1)); self.root.bind_all("<<PrevWindow>>", lambda e: self.step(-1))
        self.root.bind("<Tab>", lambda e: self.step(1)); self.root.bind("<Shift-Tab>", lambda e: self.step(-1))
        self.root.bind("<KeyPress>", self.keypress)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.redraw()

    # ------------------------------------------------------------ geometry
    def fit(self):
        self.root.update_idletasks()
        cw, ch = max(200, self.canvas.winfo_width()), max(200, self.canvas.winfo_height())
        self.zoom = min(cw / self.img.width, ch / self.img.height); self.ox = self.oy = 0

    def to_screen(self, x, y):
        return x * self.zoom + self.ox, y * self.zoom + self.oy

    def to_image(self, sx, sy):
        return (sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom

    def redraw(self):
        c = self.canvas; c.delete("all")
        w, h = max(1, int(self.img.width * self.zoom)), max(1, int(self.img.height * self.zoom))
        # render only the visible part at this zoom to keep it quick
        cw, ch = c.winfo_width(), c.winfo_height()
        x0, y0 = self.to_image(0, 0); x1, y1 = self.to_image(cw, ch)
        x0, y0 = max(0, int(x0)), max(0, int(y0)); x1, y1 = min(self.img.width, int(x1) + 1), min(self.img.height, int(y1) + 1)
        if x1 > x0 and y1 > y0:
            part = self.img.crop((x0, y0, x1, y1)).resize((max(1, int((x1 - x0) * self.zoom)), max(1, int((y1 - y0) * self.zoom))), Image.BILINEAR)
            self.tkimg = ImageTk.PhotoImage(part)
            sx, sy = self.to_screen(x0, y0)
            c.create_image(sx, sy, anchor="nw", image=self.tkimg)
        lids = sorted(self.units, key=line_number)
        colour = {lid: COLOURS[i % len(COLOURS)] for i, lid in enumerate(lids)}
        for i, b in enumerate(self.boxes):
            sx0, sy0 = self.to_screen(b["x0"], b["y0"]); sx1, sy1 = self.to_screen(b["x1"], b["y1"])
            col = colour.get(b["line"], "#ffffff")
            width = 3 if i == self.sel else 1
            c.create_rectangle(sx0, sy0, sx1, sy1, outline=col, width=width, dash=() if b.get("edited") else (3, 3))
            if i == self.sel:
                # the edges the arrow keys move, in white
                if self.edge_mode == 0:
                    c.create_line(sx0, sy0, sx0, sy1, fill="#ffffff", width=3); c.create_line(sx0, sy0, sx1, sy0, fill="#ffffff", width=3)
                else:
                    c.create_line(sx1, sy0, sx1, sy1, fill="#ffffff", width=3); c.create_line(sx0, sy1, sx1, sy1, fill="#ffffff", width=3)
            units = self.units.get(b["line"], [])
            k = b.get("position", 0)
            label = f"{k}:{units[k] if k < len(units) else '?'}"
            if self.zoom > 0.45:
                c.create_text(sx0 + 2, sy0 - 2, text=label, anchor="sw", fill=col, font=("TkDefaultFont", 8))
        self.update_status()
        self.canvas.focus_set()      # so that Space and the arrows reach the editor, not a toolbar button

    def update_status(self):
        parts = []
        if self.sel is not None:
            b = self.boxes[self.sel]; lid = b["line"]
            n_units, n_boxes = len(self.units.get(lid, [])), sum(1 for x in self.boxes if x["line"] == lid)
            flag = "" if n_units == n_boxes else "   MISMATCH"
            n_ed = sum(1 for x in self.boxes if x["line"] == lid and x.get("edited"))
            parts.append(f"{lid} ({self.lines.get(lid)}): {n_units} units, {n_boxes} boxes, {n_ed} edited{flag}   selected box {b['position']}   "
                         f"arrows move the {'right and bottom' if self.edge_mode else 'left and top'} edges (Tab to switch, Shift for the whole box, Ctrl for five pixels)")
            self.orient_var.set(self.lines.get(lid, ""))
        else:
            bad = [lid for lid in self.units if len(self.units[lid]) != sum(1 for x in self.boxes if x["line"] == lid)]
            parts.append(f"{len(self.boxes)} boxes; lines whose box count differs from the unit count: {', '.join(sorted(bad, key=line_number)) or 'none'}")
        parts.append("ADD MODE: drag to draw" if self.add_mode else "")
        parts.append("unsaved" if self.dirty else "saved")
        self.status.set("   ".join(p for p in parts if p))

    # ------------------------------------------------------------ hit testing
    def hit(self, sx, sy):
        """Return (index, edges) of the box under the pointer; edges is a set of 'l','r','t','b'."""
        best = None
        for i, b in enumerate(self.boxes):
            sx0, sy0 = self.to_screen(b["x0"], b["y0"]); sx1, sy1 = self.to_screen(b["x1"], b["y1"])
            if sx0 - EDGE <= sx <= sx1 + EDGE and sy0 - EDGE <= sy <= sy1 + EDGE:
                edges = set()
                if abs(sx - sx0) <= EDGE: edges.add("l")
                if abs(sx - sx1) <= EDGE: edges.add("r")
                if abs(sy - sy0) <= EDGE: edges.add("t")
                if abs(sy - sy1) <= EDGE: edges.add("b")
                area = (sx1 - sx0) * (sy1 - sy0)
                if edges or (sx0 <= sx <= sx1 and sy0 <= sy <= sy1):
                    if best is None or edges and not best[2] or area < best[3]:
                        best = (i, edges, bool(edges), area)
        return (best[0], best[1]) if best else (None, set())

    def press(self, e):
        self.canvas.focus_set()
        ix, iy = self.to_image(e.x, e.y)
        if self.add_mode:
            self.drag = ("new", ix, iy); return
        i, edges = self.hit(e.x, e.y)
        if i != self.sel:
            self.edge_mode = 0
        self.sel = i
        if i is not None:
            b = self.boxes[i]
            self.drag = ("resize" if edges else "move", ix, iy, dict(b), edges)
        else:
            self.drag = ("new", ix, iy)       # a drag on empty ground draws a new box
        self.redraw()

    def motion(self, e):
        if not self.drag:
            return
        ix, iy = self.to_image(e.x, e.y)
        if self.drag[0] == "new":
            self.redraw()
            sx0, sy0 = self.to_screen(self.drag[1], self.drag[2])
            self.canvas.create_rectangle(sx0, sy0, e.x, e.y, outline="#ffffff", dash=(4, 2))
            return
        kind, x_start, y_start, orig, edges = self.drag
        dx, dy = int(round(ix - x_start)), int(round(iy - y_start))
        b = self.boxes[self.sel]
        if dx or dy:
            b["edited"] = True
        if kind == "move":
            b["x0"], b["x1"], b["y0"], b["y1"] = orig["x0"] + dx, orig["x1"] + dx, orig["y0"] + dy, orig["y1"] + dy
        else:
            if "l" in edges: b["x0"] = min(orig["x0"] + dx, orig["x1"] - 2)
            if "r" in edges: b["x1"] = max(orig["x1"] + dx, orig["x0"] + 2)
            if "t" in edges: b["y0"] = min(orig["y0"] + dy, orig["y1"] - 2)
            if "b" in edges: b["y1"] = max(orig["y1"] + dy, orig["y0"] + 2)
        self.dirty = True
        self.redraw()

    def release(self, e):
        if self.drag and self.drag[0] == "new":
            ix, iy = self.to_image(e.x, e.y)
            x0, x1 = sorted((int(self.drag[1]), int(ix))); y0, y1 = sorted((int(self.drag[2]), int(iy)))
            if x1 - x0 >= 3 and y1 - y0 >= 3:
                lid = self.line_var.get()
                if lid == "nearest":
                    lid = self.nearest_line((x0 + x1) / 2, (y0 + y1) / 2)
                if lid:
                    self.boxes.append({"line": lid, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "edited": True})
                    self.sel = len(self.boxes) - 1; self.edge_mode = 0; self.dirty = True
            self.add_mode = False
        elif self.drag:
            order_boxes(self.boxes, self.lines)
        self.drag = None
        order_boxes(self.boxes, self.lines)
        self.redraw()

    def nearest_line(self, x, y):
        best = None
        for b in self.boxes:
            cx, cy = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2
            d = (cx - x) ** 2 + 4 * (cy - y) ** 2
            if best is None or d < best[0]:
                best = (d, b["line"])
        return best[1] if best else (sorted(self.units, key=line_number)[0] if self.units else None)

    # ------------------------------------------------------------ commands
    def start_add(self):
        self.add_mode = True; self.sel = None; self.redraw()

    def cancel_add(self):
        self.add_mode = False; self.drag = None; self.redraw()

    def delete(self):
        if self.sel is not None:
            del self.boxes[self.sel]; self.sel = None; self.dirty = True
            order_boxes(self.boxes, self.lines); self.redraw()

    def nudge(self, dx, dy, whole=False):
        if self.sel is None:
            return "break"
        b = self.boxes[self.sel]
        b["edited"] = True
        if whole:
            for k, d in (("x0", dx), ("x1", dx), ("y0", dy), ("y1", dy)):
                b[k] += d
        else:
            if dx:
                k = "x1" if self.edge_mode else "x0"
                b[k] += dx
                if b["x1"] - b["x0"] < 2:
                    b[k] -= dx
            if dy:
                k = "y1" if self.edge_mode else "y0"
                b[k] += dy
                if b["y1"] - b["y0"] < 2:
                    b[k] -= dy
        self.dirty = True; order_boxes(self.boxes, self.lines); self.redraw()
        return "break"

    def keypress(self, e):
        if e.keysym in ("Tab", "ISO_Left_Tab") and (e.state & 1 or e.keysym == "ISO_Left_Tab"):
            return self.step(-1)

    def toggle_edges(self):
        self.edge_mode ^= 1; self.redraw()
        return "break"

    def step(self, direction):
        """Step the cursor: left/top edges of a box, then its right/bottom edges, then the next box; backwards with Shift."""
        if not self.boxes:
            return "break"
        order = sorted(range(len(self.boxes)), key=lambda i: (line_number(self.boxes[i]["line"]), self.boxes[i].get("position", 0)))
        if self.sel is None or self.sel not in order:
            self.sel = order[0] if direction > 0 else order[-1]
            self.edge_mode = 0 if direction > 0 else 1
        elif direction > 0 and self.edge_mode == 0:
            self.edge_mode = 1
        elif direction < 0 and self.edge_mode == 1:
            self.edge_mode = 0
        else:
            self.sel = order[(order.index(self.sel) + direction) % len(order)]
            self.edge_mode = 0 if direction > 0 else 1
        b = self.boxes[self.sel]
        sx0, sy0 = self.to_screen(b["x0"], b["y0"]); sx1, sy1 = self.to_screen(b["x1"], b["y1"])
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if sx0 < 40 or sx1 > cw - 40 or sy0 < 40 or sy1 > ch - 40:
            cx, cy = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2
            self.ox, self.oy = cw / 2 - cx * self.zoom, ch / 2 - cy * self.zoom
        self.redraw()
        return "break"

    def set_orientation(self):
        if self.sel is None or not self.orient_var.get():
            return
        self.lines[self.boxes[self.sel]["line"]] = self.orient_var.get()
        self.dirty = True; order_boxes(self.boxes, self.lines); self.redraw()

    def reset(self):
        if messagebox.askyesno("Reset", "Discard the corrections and start again from the automatic boxes?"):
            self.boxes, self.lines = load_auto(self.side, self.source)
            for lid in self.units:
                self.lines.setdefault(lid, "upright")
            order_boxes(self.boxes, self.lines); self.sel = None; self.dirty = True; self.redraw()

    def save(self):
        order_boxes(self.boxes, self.lines)
        out = {"side": self.side, "image": self.image_path.name, "lines": {k: v for k, v in self.lines.items() if k in self.units},
               "boxes": []}
        for b in sorted(self.boxes, key=lambda b: (line_number(b["line"]), b["position"])):
            units = self.units.get(b["line"], []); k = b["position"]
            out["boxes"].append({"line": b["line"], "position": k, "unit": units[k] if k < len(units) else "?",
                                 "x0": int(b["x0"]), "x1": int(b["x1"]), "y0": int(b["y0"]), "y1": int(b["y1"]),
                                 "edited": bool(b.get("edited", False))})
        self.json_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        self.dirty = False; self.redraw()

    def close(self):
        if self.dirty and not messagebox.askyesno("Unsaved", "Close without saving?"):
            return
        self.root.destroy()

    # ------------------------------------------------------------ view
    def wheel(self, e):
        f = 1.15 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else 1 / 1.15
        ix, iy = self.to_image(e.x, e.y)
        self.zoom = max(0.05, min(8.0, self.zoom * f))
        self.ox, self.oy = e.x - ix * self.zoom, e.y - iy * self.zoom
        self.redraw()

    def pan_start(self, e):
        self.pan = (e.x, e.y, self.ox, self.oy)

    def pan_move(self, e):
        self.ox, self.oy = self.pan[2] + e.x - self.pan[0], self.pan[3] + e.y - self.pan[1]
        self.redraw()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("side")
    ap.add_argument("--auto", action="store_true", help="ignore saved corrections and start from the automatic boxes")
    ap.add_argument("--source", choices=["print", "tracing"], default="print", help="which image to correct boxes on")
    ap.add_argument("--seed-from-print", action="store_true", help="tracing only: place the boxes from the finished print boxes")
    ap.add_argument("--smoke", action="store_true", help="open, save nothing, close at once (for testing)")
    args = ap.parse_args()
    ed = Editor(args.side, args.auto, args.source, args.seed_from_print)
    if args.smoke:
        ed.root.after(500, ed.root.destroy)
    ed.root.mainloop()
