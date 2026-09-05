"""Download Metoro's chanted readings, line by line, from kohaumotu.org.

Jaussen, T. 1893. L'ile de Paques: historique, ecriture, et repertoire des
signes des tablettes ou bois d'hibiscus intelligents. Bulletin de
Geographie Historique et Descriptive. Public domain. The site transcribes
Jaussen's notebook: Metoro's words for each sign, separated by hyphens,
for the four tablets Jaussen owned (A Tahua, B Aruku Kurenga, C Mamari,
E Keiti).

Writes data/metoro/html/<line>.html, 83 pages.
"""
import pathlib, sys, urllib.request

BASE = "http://kohaumotu.org/rongorongo_org/metoro/{}.html"
LINES = ([f"br{i:02d}" for i in range(1, 11)] + [f"bv{i:02d}" for i in range(1, 13)] +
         [f"ab{i:02d}" for i in range(1, 9)] + [f"aa{i:02d}" for i in range(1, 9)] +
         [f"cb{i:02d}" for i in range(1, 15)] + [f"ca{i:02d}" for i in range(1, 15)] +
         [f"er{i:02d}" for i in range(1, 10)] + [f"ev{i:02d}" for i in range(1, 9)])
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "metoro" / "html"
out.mkdir(parents=True, exist_ok=True)
for name in LINES:
    f = out / f"{name}.html"
    if f.exists() and f.stat().st_size > 0:
        continue
    req = urllib.request.Request(BASE.format(name), headers={"User-Agent": "rongorongo-research/0.1"})
    try:
        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:  # noqa: BLE001
        print(f"{name}: FAILED {e}", file=sys.stderr)
print(f"{sum(1 for _ in out.glob('*.html'))} pages")
