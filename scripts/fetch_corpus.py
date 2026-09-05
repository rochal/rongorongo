"""Download the CEIPP numerical transliteration of the rongorongo corpus.

Source: kohaumotu.org (Cercle d'Etudes sur l'Ile de Paques et la Polynesie),
Thomas Barthel's numbering as extended by the CEIPP. The site only serves
plain http and its TLS certificate has expired, so use http://.

Writes one HTML file per object into data/html/.
"""
import pathlib, sys, urllib.request

BASE = "http://kohaumotu.org/rongorongo_org/translit/{}.html"
# Tablet C is served under "mamari"; every other object uses its letter.
ITEMS = ["a", "b", "mamari", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
         "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

out = pathlib.Path(__file__).resolve().parent.parent / "data" / "html"
out.mkdir(parents=True, exist_ok=True)
for item in ITEMS:
    url = BASE.format(item)
    req = urllib.request.Request(url, headers={"User-Agent": "rongorongo-research/0.1"})
    try:
        data = urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:  # noqa: BLE001
        print(f"{item}: FAILED {e}", file=sys.stderr)
        continue
    (out / f"{item}.html").write_bytes(data)
    print(f"{item}: {len(data)} bytes")
