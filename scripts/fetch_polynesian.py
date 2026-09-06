"""Fetch public-domain Maori and Tahitian texts from archive.org and reduce them to Rapa Nui-shaped tokens.

Rapa Nui's surviving corpus is a few thousand words, too small to constrain a
syllable model (section 23). Its nearest well-attested relatives are not:
nineteenth-century scripture and Grey's collections of Maori traditions
run to hundreds of thousands of words, all out of copyright. This script
downloads the OCR text of each and keeps the words that fit Rapa Nui
phonotactics after a sound mapping, so that a syllable model built from
them speaks Rapa Nui's syllabary:

  Maori     wh -> h, w -> v (Maori wh, w answer to Rapa Nui h, v in cognates:
            whare / hare, wai / vai); k and ng kept; macrons dropped
  Tahitian  f -> h; the glottal stop dropped (old printings omit it, so
            ta'ata is taata); Tahitian has no k or ng, which Rapa Nui keeps,
            so its model lacks those syllables altogether

A token is kept if it consists of (C)V syllables over Rapa Nui's consonants
h k m n ng p r t v and is not an English word; a small stoplist removes the
English that passes (a, me, no, he ...) only where it is not also a common
word of the language. Line-level page furniture (verse numbers, headers)
falls out with the letter filter.

Sources (archive.org identifiers)
  Maori     kotepaiperatapua00barl      Ko te Paipera Tapu, 1868, the Bible
            kotekawenatahou00yategoog   Ko te Kawenata Hou, 1841, the New Testament
            kongamahingaang00greygoog   Grey, Ko nga mahinga a nga tupuna Maori, 1854
            kongamoteateame00greygoog   Grey, Ko nga moteatea, 1853
  Tahitian  tebibiliamoaraoi00lone      Te Bibilia Moa Ra, 1878, the Bible
            tefaufaaapiatot00unkngoog   Te Faufaa Api, 1853, the New Testament

Writes data/polynesian/<id>_djvu.txt (not committed) and
data/polynesian/maori_tokens.txt, tahitian_tokens.txt, plus a counts table
out/polynesian_sources.csv.
"""
import csv, pathlib, re, sys, time, unicodedata, urllib.request

SOURCES = {
    "maori": ["kotepaiperatapua00barl", "kotekawenatahou00yategoog", "kongamahingaang00greygoog", "kongamoteateame00greygoog"],
    "tahitian": ["tebibiliamoaraoi00lone", "tefaufaaapiatot00unkngoog"],
}
UA = "rongorongo-research/0.1 (structural analysis; https://github.com/rochal/rongorongo)"
root = pathlib.Path(__file__).resolve().parent.parent
ddir = root / "data" / "polynesian"
ddir.mkdir(parents=True, exist_ok=True)
SYLLABLE = re.compile(r"^(?:(?:ng|[hkmnprtv])?[aeiou])+$")
ENGLISH = {"a", "an", "the", "and", "of", "to", "in", "is", "it", "he", "me", "no", "on", "or", "at", "up", "am", "not", "one", "our", "out", "are", "her",
           "him", "his", "man", "men", "more", "name", "none", "note", "page", "take", "time", "into", "unto", "have", "mine", "thine", "thee", "thou",
           "make", "made", "upon", "over", "even", "ever", "never", "more", "here", "there", "thing", "then", "them", "than", "that", "this", "then"}
# common words of the languages that happen to look English are kept
KEEP = {"a", "he", "me", "no", "e", "i", "o", "te", "ki", "ka", "kia", "ko", "ana", "ai", "ra", "na", "nei", "mai", "atu", "ake", "iho", "ta", "to", "tona", "ona",
        "hoki", "one", "tera", "tenei", "hei", "ma", "mo", "ua", "ia", "oia", "ore", "aore", "eita", "roa", "rahi", "teie", "tei", "vau", "oe", "tatou", "mau"}


def fetch(ident):
    f = ddir / f"{ident}_djvu.txt"
    if f.exists() and f.stat().st_size > 10000:
        return f
    url = f"https://archive.org/download/{ident}/{ident}_djvu.txt"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=300).read()
            f.write_bytes(data); print(ident, len(data) // 1000, "kB", flush=True)
            time.sleep(3)
            return f
        except Exception as e:
            print(ident, "retry", e, file=sys.stderr); time.sleep(20 * (attempt + 1))
    return None


def normalise(word, lang):
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    w = re.sub(r"[ʻ‘’'`^]", "", w)
    if lang == "maori":
        w = w.replace("wh", "h").replace("w", "v")
    else:
        w = w.replace("f", "h")
    return w


def tokens(text, lang):
    outp = []
    for raw in re.split(r"[^A-Za-zÀ-ɏʻ‘’'`^]+", text):
        if not raw:
            continue
        w = normalise(raw, lang)
        if not w or not SYLLABLE.match(w):
            continue
        if w in ENGLISH and w not in KEEP:
            continue
        outp.append(w)
    return outp


rows = []
for lang, idents in SOURCES.items():
    all_tokens = []
    for ident in idents:
        f = fetch(ident)
        if f is None:
            rows.append([lang, ident, 0, 0]); continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        t = tokens(text, lang)
        rows.append([lang, ident, len(text.split()), len(t)])
        all_tokens.extend(t)
    (ddir / f"{lang}_tokens.txt").write_text(" ".join(all_tokens), encoding="utf-8")
    print(lang, len(all_tokens), "tokens,", len(set(all_tokens)), "types", flush=True)
(root / "out").mkdir(exist_ok=True)
with open(root / "out" / "polynesian_sources.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["language", "identifier", "ocr_words", "tokens_kept"]); w.writerows(rows)
