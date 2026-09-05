"""Download Barthel's sign catalogue drawings from kohaumotu.org.

The catalogue pages (signs/gNNNNNN.html) show one GIF per row of five
signs, 669 x 78 pixels, with a label row underneath naming the five sign
numbers (or "(no sign NNN)" for gaps). A cell may hold several drawn
variants of one sign. Each page also offers a zip of its GIFs.

This script parses the eight pages, records which sign numbers sit in each
row image, downloads the zips (falling back to the row GIFs), and writes
data/signs/rows.json:  {"005": ["005","006","007","008","009"], ...}
"""
import io, json, pathlib, re, sys, urllib.request, zipfile

BASE = "http://kohaumotu.org/rongorongo_org/signs/"
PAGES = ["g001099", "g100199", "g200299", "g300399", "g400499", "g500599", "g600699", "g700799"]
root = pathlib.Path(__file__).resolve().parent.parent / "data" / "signs"
(root / "html").mkdir(parents=True, exist_ok=True)
(root / "gif").mkdir(exist_ok=True)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rongorongo-research/0.1"})
    return urllib.request.urlopen(req, timeout=60).read()


rows = {}
for p in PAGES:
    f = root / "html" / f"{p}.html"
    if not f.exists():
        f.write_bytes(get(BASE + p + ".html"))
    html = f.read_text(encoding="latin-1")
    # sequence of <IMG src="gif/NNN.gif"> followed by a label row of five <TD>
    for m in re.finditer(r'<IMG src="gif/(\d{3})\.gif"[^>]*>(.*?)</TR>\s*<TR>(.*?)</TR>', html, re.S):
        row, labels = m.group(1), m.group(3)
        cells = re.findall(r"<TD[^>]*>(.*?)</TD>", labels, re.S)
        names = []
        for c in cells:
            c = re.sub(r"<[^>]+>", "", c).strip()
            mm = re.match(r"(\d{3})", c)
            names.append(mm.group(1) if mm and not c.startswith("(") else None)
        rows[row] = names
    zips = re.findall(r'href="(g\d{3}-\d{3}\.zip)"', html)
    for z in zips:
        try:
            data = get(BASE + z)
            zf = zipfile.ZipFile(io.BytesIO(data))
            n = 0
            for name in zf.namelist():
                if name.lower().endswith(".gif"):
                    (root / "gif" / pathlib.Path(name).name).write_bytes(zf.read(name))
                    n += 1
            print(f"{z}: {n} gifs")
        except Exception as e:  # noqa: BLE001
            print(f"{z}: zip failed ({e}), fetching row gifs", file=sys.stderr)
            for row in re.findall(r'<IMG src="gif/(\d{3})\.gif"', html):
                out = root / "gif" / f"{row}.gif"
                if not out.exists():
                    out.write_bytes(get(BASE + f"gif/{row}.gif"))

json.dump(rows, open(root / "rows.json", "w"), indent=0)
print(f"{len(rows)} rows, {sum(1 for v in rows.values() for x in v if x)} sign cells, "
      f"{len(list((root / 'gif').glob('*.gif')))} gif files")
