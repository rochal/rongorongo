"""Compare a regenerated out/ folder with the committed one.

    python scripts/check_reproduction.py <path to regenerated out/>

For every CSV and Markdown file present in both folders, reports whether
the contents are identical, and if not, how many lines differ and the
first differing line of each, so that nondeterminism (an unseeded shuffle,
an unordered dictionary) can be told from an expected difference (a data
source that is not in the repository, such as the Metraux page scans).
Files present in only one folder are listed separately.
"""
import difflib, pathlib, sys

here = pathlib.Path(__file__).resolve().parent.parent / "out"
other = pathlib.Path(sys.argv[1]).resolve()
names = sorted({p.name for p in here.glob("*") if p.suffix in (".csv", ".md")} | {p.name for p in other.glob("*") if p.suffix in (".csv", ".md")})
same, diff, only = [], [], []
for n in names:
    a, b = here / n, other / n
    if not (a.exists() and b.exists()):
        only.append((n, "committed" if a.exists() else "regenerated")); continue
    la = a.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").splitlines()
    lb = b.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").splitlines()
    if la == lb:
        same.append(n); continue
    changed = [d for d in difflib.unified_diff(la, lb, lineterm="", n=0) if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    first = next((d for d in changed if d.startswith("-")), changed[0] if changed else "")
    diff.append((n, len(la), len(changed), first[:110]))
print(f"identical: {len(same)}  differing: {len(diff)}  only in one folder: {len(only)}\n")
print("| file | lines | differing lines | first difference |\n|---|---|---|---|")
for n, nl, nc, first in sorted(diff, key=lambda x: -x[2]):
    print(f"| {n} | {nl} | {nc} | {first} |")
if only:
    print("\nonly in one folder: " + ", ".join(f"{n} ({w})" for n, w in only))
