"""Download Barthel's tracings of every inscribed side from Wikimedia Commons.

The files are named Barthel_<side>.png (Ra is a jpg; the Santiago Staff is
Barthel_I.png). Commons rate-limits direct downloads of original files and
asks for rendered sizes instead, so each file is requested through the API
as a render at its own width, which returns the same pixels for a PNG of
this size, with a pause between requests. Writes data/tracings/<side>.<ext>.
Sides not on Commons (F verso, M, O, U, V, W, X, Y, Z) are skipped.
"""
import json, pathlib, sys, time, urllib.error, urllib.parse, urllib.request

SIDES = ["Aa", "Ab", "Br", "Bv", "Ca", "Cb", "Da", "Db", "Er", "Ev", "Fa", "Gr", "Gv", "Hr", "Hv", "I", "Ja", "Kr", "Kv",
         "La", "Na", "Nb", "Pr", "Pv", "Qr", "Qv", "Ra", "Rb", "Sa", "Sb", "Ta"]
UA = "rongorongo-research/0.1 (structural analysis; https://github.com/rochal/rongorongo)"
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "tracings"
out.mkdir(parents=True, exist_ok=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            data = urllib.request.urlopen(req, timeout=120).read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            raise
    return None


for side in SIDES:
    ext = "jpg" if side == "Ra" else "png"
    f = out / f"{side}.{ext}"
    if f.exists() and f.stat().st_size > 1000:
        continue
    title = urllib.parse.quote(f"File:Barthel_{side}.{ext}")
    info = get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url|size&format=json")
    if not info:
        print(side, "FAILED: no metadata", file=sys.stderr); continue
    page = next(iter(info["query"]["pages"].values()))
    if "imageinfo" not in page:
        print(side, "not on Commons", file=sys.stderr); continue
    ii = page["imageinfo"][0]
    width = ii["width"]
    # a render one pixel narrower than the original forces the thumbnail path Commons prefers
    thumb = get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url&iiurlwidth={width - 1}&format=json")
    url = next(iter(thumb["query"]["pages"].values()))["imageinfo"][0].get("thumburl")
    data = get(url, binary=True) if url else None
    if data:
        f.write_bytes(data)
        print(side, len(data), flush=True)
    else:
        print(side, "FAILED", file=sys.stderr)
    time.sleep(5)
