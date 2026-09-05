"""Download the white-filled prints and rubbings of the tablets from Commons.

These are photographs in which the glyphs were filled white for legibility,
mostly from Chauvet 1935, plus a few rubbings and one unretouched photograph.
They are the nearest thing to binary images of the objects themselves, and
the first source in this project that is not a drawing. Fetched through the
Commons API at rendered size, at a polite pace. Writes data/photos/<side>.jpg.
Tahua's prints come in three overlapping parts per side and are saved as
Aa_left, Aa_center, Aa_right and likewise for Ab.
"""
import json, pathlib, sys, time, urllib.error, urllib.parse, urllib.request

FILES = {
    "Aa_left": "Rongorongo A-a Tahua left.jpg", "Aa_center": "Rongorongo A-a Tahua center.jpg", "Aa_right": "Rongorongo A-a Tahua right.jpg",
    "Ab_left": "Rongorongo A-b Tahua left.jpg", "Ab_center": "Rongorongo A-b Tahua center.jpg", "Ab_right": "Rongorongo A-b Tahua right.jpg",
    "Br": "Rongorongo B-r Aruku-Kurenga.jpg", "Bv": "Rongorongo B-v Aruku-Kurenga.jpg",
    "Ca": "Rongorongo C-a Mamari.jpg", "Cb": "Rongorongo C-b Mamari.jpg",
    "Da": "Rongorongo D-a Échancrée.jpg", "Db": "Rongorongo D-b Échancrée.jpg",
    "Er": "Rongorongo E-r Keiti.jpg", "Ev": "Rongorongo E-v Keiti.jpg",
    "Gr": "Rongorongo G-r Small Santiago.jpg", "Gv": "Rongorongo G-v Small Santiago.jpg",
    "Hr": "Rongorongo H-r Great Santiago.jpg", "Hv": "Rongorongo H-v Great Santiago.jpg",
    "Hv_unretouched": "Rongorongo H-v Great Santiago (unretouched).jpg",
    "Kr": "Rongorongo K-r Small London.jpg", "Kv": "Rongorongo K-v Small London.jpg",
    "Na": "Rongorongo N-a Small Vienna.png", "Nb": "Rongorongo N-b Small Vienna.png",
    "Pr": "Rongorongo P-r Great St Petersburg.jpg", "Pv": "Rongorongo P-v Great St Petersburg.jpg",
    "Qv": "Rongorongo Q-v Small St Petersburg.jpg",
    "Ra": "Rongorongo R-a Atua-Mata-Riri.jpg", "Rb": "Rongorongo R-b Atua-Mata-Riri.jpg",
    "Sa": "Rongorongo S-a Great Washington.jpg", "Sb": "Rongorongo S-b Great Washington.jpg",
    "Sa_rubbing": "Rongorongo S-a (rubbing).jpg",
}
UA = "rongorongo-research/0.1 (structural analysis; https://github.com/rochal/rongorongo)"
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "photos"
out.mkdir(parents=True, exist_ok=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            data = urllib.request.urlopen(req, timeout=120).read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (attempt + 1)); continue
            raise
    return None


for side, name in FILES.items():
    ext = name.rsplit(".", 1)[1].lower()
    f = out / f"{side}.{ext}"
    if f.exists() and f.stat().st_size > 1000:
        continue
    title = urllib.parse.quote("File:" + name)
    info = get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url|size&format=json")
    page = next(iter(info["query"]["pages"].values()))
    if "imageinfo" not in page:
        print(side, "not on Commons", file=sys.stderr); continue
    width = page["imageinfo"][0]["width"]
    thumb = get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url&iiurlwidth={width - 1}&format=json")
    url = next(iter(thumb["query"]["pages"].values()))["imageinfo"][0].get("thumburl")
    data = get(url, binary=True) if url else None
    if data:
        f.write_bytes(data); print(side, len(data), flush=True)
    else:
        print(side, "FAILED", file=sys.stderr)
    time.sleep(5)
