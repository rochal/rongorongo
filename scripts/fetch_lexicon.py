"""Download public-domain sources of Rapa Nui vocabulary and text.

  churchill1912  W. Churchill, Easter Island: the Rapanui speech and the
                 peopling of southeast Polynesia, Carnegie Institution 1912.
                 Carries Roussel's 1908 vocabulary in English with Geiseler's
                 and Thomson's, about 2,500 headwords. Public domain.
  routledge1919  K. Routledge, The mystery of Easter Island, 1919. A few
                 Rapa Nui passages. Public domain.

Thomson 1891, already fetched by fetch_rapanui.py, holds a second word list.
Writes data/rapanui/sources/<name>.txt (Internet Archive OCR).
"""
import pathlib, sys, urllib.request

ITEMS = {"churchill1912": "easterislandrapa00churrich", "routledge1919": "mysteryofeasteri00rout"}
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "rapanui" / "sources"
out.mkdir(parents=True, exist_ok=True)
for name, ident in ITEMS.items():
    f = out / f"{name}.txt"
    if f.exists() and f.stat().st_size > 10000:
        continue
    url = f"https://archive.org/download/{ident}/{ident}_djvu.txt"
    req = urllib.request.Request(url, headers={"User-Agent": "rongorongo-research/0.1"})
    try:
        f.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        print(name, f.stat().st_size, "bytes")
    except Exception as e:  # noqa: BLE001
        print(name, "FAILED", e, file=sys.stderr)
