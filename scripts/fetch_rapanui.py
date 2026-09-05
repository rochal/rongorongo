"""Download the OCR text of Thomson 1891 from the Internet Archive.

W. J. Thomson, "Te Pito te Henua, or Easter Island", Report of the U.S.
National Museum for 1889, Smithsonian Institution, 1891. Public domain.
The Cornell University copy, item cu31924105726222, carries a note that
there are no known copyright restrictions on the text.

Writes data/rapanui/thomson1891_djvu.txt.
"""
import pathlib, urllib.request

URL = "https://archive.org/download/cu31924105726222/cu31924105726222_djvu.txt"
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "rapanui"
out.mkdir(parents=True, exist_ok=True)
req = urllib.request.Request(URL, headers={"User-Agent": "rongorongo-research/0.1"})
data = urllib.request.urlopen(req, timeout=120).read()
(out / "thomson1891_djvu.txt").write_bytes(data)
print(f"{len(data)} bytes")
