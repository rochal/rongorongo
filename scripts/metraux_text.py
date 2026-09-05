"""Extract Rapa Nui running text from page scans of Metraux 1940.

Metraux, A. 1940. Ethnology of Easter Island. Bishop Museum Bulletin 160.
Public domain in the United States (HathiTrust full view), in copyright
elsewhere, so the scans, the OCR and the extracted text stay in
data/metraux/, which git ignores. Only statistics are written to out/.

Pages saved from HathiTrust as data/metraux/*seq_N.jpg are OCR'd with
Tesseract into data/metraux/ocr/N.txt. Lines whose tokens are mostly valid
Rapa Nui (letters a e i o u h k m n ng p r t v, a vowel present) are kept,
which selects the legends, chants and lists printed in the original
language and skips Metraux's English.

The kept tokens are appended to the working corpus
data/rapanui/_combined_tokens.txt together with Thomson's recitations, for
rapanui.py and decipher.py to use.
"""
import collections, glob, pathlib, re, shutil, subprocess

root = pathlib.Path(__file__).resolve().parent.parent
mdir = root / "data" / "metraux"
ocr = mdir / "ocr"
ocr.mkdir(parents=True, exist_ok=True)
out = root / "out"
VALID = re.compile(r"^[aeiouhkmnprtvg]+$")
PARTICLE_FREE = True

tess = shutil.which("tesseract") or next((p for p in glob.glob(r"C:\Program Files*\Tesseract-OCR\tesseract.exe")), None)
pages = sorted(mdir.glob("*seq_*.jpg"), key=lambda p: int(re.search(r"seq_(\d+)", p.name).group(1)))
for p in pages:
    n = re.search(r"seq_(\d+)", p.name).group(1)
    if not (ocr / f"{n}.txt").exists() and tess:
        subprocess.run([tess, str(p), str(ocr / n), "-l", "eng", "--psm", "6"], capture_output=True)


# A token counts as Rapa Nui only if it parses entirely into (C)V syllables
# with Rapa Nui consonants. That rejects "the", "man", "moon", "tree" and
# nearly all English on phonotactics alone; the few English words that pass
# ("home", "time", "one") are listed.
SYLLABLE = re.compile(r"^(?:(?:ng|[hkmnprtv])?[aeiou])+$")
ENGLISH_CV = {"home", "time", "name", "here", "one", "to", "me", "he", "none", "mine", "hate", "take", "make", "made", "note",
              "tone", "tune", "hope", "rope", "nine", "tape", "pane", "mate", "rate", "ripe", "pipe", "mere", "hero", "ore",
              "toe", "tie", "pie", "hue", "we", "no", "a", "i", "o", "e"}
RAPANUI_SHORT = {"he", "to", "no", "a", "i", "o", "e", "me"}   # genuine Rapa Nui particles that the list above would catch


def tokens(line):
    toks = []
    for w in re.split(r"[\s\-]+", line.lower()):
        w = re.sub(r"[^a-z]", "", w)
        if not w:
            continue
        ok = SYLLABLE.match(w) and (w in RAPANUI_SHORT or w not in ENGLISH_CV)
        toks.append(w if ok else None)
    return toks


per_page = []
kept = []
for f in sorted(ocr.glob("*.txt"), key=lambda p: int(p.stem)):
    words = []
    for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = tokens(l)
        if len(t) >= 4 and sum(x is not None for x in t) / len(t) >= 0.75:
            words.extend(x for x in t if x)
    per_page.append((int(f.stem), len(words)))
    kept.extend(words)

thomson = (root / "data" / "rapanui" / "recitations_tokens.txt").read_text(encoding="utf-8").split()
combined = thomson + kept
(root / "data" / "rapanui" / "_combined_tokens.txt").write_text(" ".join(combined), encoding="utf-8")
(mdir / "rapanui_tokens.txt").write_text(" ".join(kept), encoding="utf-8")

syl = collections.Counter(len(re.findall(r"[aeiou]", w)) for w in kept)
distinct = len(set(kept))
md = ["# Rapa Nui text from Metraux 1940\n",
      f"{len(pages)} page scans, {len(per_page)} OCR'd. Rapa Nui-language lines yielded {len(kept)} word tokens, "
      f"{distinct} distinct. With Thomson's {len(thomson)} recitation tokens the working corpus is {len(combined)} tokens.\n",
      "The text is not stored in the repository; this file records only its size and shape.\n",
      "| page scan | Rapa Nui words |\n|---|---|"]
for n, k in per_page:
    if k:
        md.append(f"| seq {n} | {k} |")
md.append("\n## Word length in syllables, Metraux sample\n")
md.append("| syllables | share |\n|---|---|")
for k in sorted(syl):
    md.append(f"| {k} | {syl[k] / len(kept):.1%} |")
(out / "metraux_text.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:4]))
