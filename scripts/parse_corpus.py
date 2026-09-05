"""Parse the CEIPP transliteration pages into data/corpus.json.

Output format: {"Ev04": ["380.001", "088", "001", ...], ...}
Each list element is one Barthel unit exactly as the CEIPP writes it:
  - components joined by "." (linked), ":" or ";" (stacked), "'" (fused)
  - variant letters appended (e.g. 522fy, 204s)
  - "?" = identification uncertain, "!" = illegible (000!)
Line identifiers follow Barthel: object letter, side (a/b or r/v), line number.
"""
import html, json, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "data" / "html"
corpus = {}
for f in sorted(src.glob("*.html")):
    txt = f.read_text(encoding="latin-1")
    txt = html.unescape(re.sub(r"<[^>]+>", " ", txt)).replace("\r", "")
    # A line is "Xy00 <units separated by -> ... *" ; wrapped over several rows.
    for m in re.finditer(r"\b([A-Z][abrv]\d{2})\s+([^*]*?)\*", txt):
        lid, body = m.group(1), re.sub(r"\s+", "", m.group(2))
        units = [u for u in body.split("-") if u]
        corpus.setdefault(lid, units)

(root / "data" / "corpus.json").write_text(json.dumps(corpus, indent=0), encoding="utf-8")
n_units = sum(len(v) for v in corpus.values())
print(f"{len(corpus)} lines, {n_units} units")
