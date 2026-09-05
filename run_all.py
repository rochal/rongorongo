"""Run every analysis in order and regenerate the charts.

    python run_all.py            # everything, fetching data if it is missing
    python run_all.py --fast     # skip the decomposition test (about 5 minutes)
    python run_all.py --refetch  # re-download the transliteration and sign pages

Each step is a script in scripts/; all write to out/ and docs/img/.
"""
import argparse, pathlib, shutil, subprocess, sys, time

root = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--fast", action="store_true", help="skip decompose.py")
ap.add_argument("--refetch", action="store_true", help="re-download data even if present")
args = ap.parse_args()

steps = []
if args.refetch or not (root / "data" / "html").exists():
    steps.append(["fetch_corpus.py"])
steps.append(["parse_corpus.py"])
if args.refetch or not (root / "data" / "signs" / "rows.json").exists():
    steps.append(["fetch_signs.py"])
steps += [
    ["alternations.py"],
    ["lists_380.py"],
    ["affix_test.py"],
    ["parallels.py"],
    ["parallels.py", "--min-run", "4", "--mismatch", "1", "--suffix", "_fuzzy"],
    ["allographs.py"],
    ["parallels.py", "--merge", "out/allograph_merge.csv", "--suffix", "_merged"],
    ["inventory.py"],
    ["sign_shapes.py"],
    ["genre_entropy.py"],
    ["collocations.py"],
]
if args.refetch or not (root / "data" / "rapanui" / "thomson1891_djvu.txt").exists():
    steps.append(["fetch_rapanui.py"])
if (root / "data" / "metraux").exists():
    steps.append(["metraux_text.py"])         # needs Tesseract; pages are not in the repository
steps.append(["rapanui.py"])
if args.refetch or not (root / "data" / "rapanui" / "sources" / "churchill1912.txt").exists():
    steps.append(["fetch_lexicon.py"])
steps.append(["lexicon.py"])
steps.append(["chant.py"])
steps.append(["staff_chain.py"])
steps.append(["staff_dividers.py"])
if args.refetch or not (root / "data" / "metoro" / "html").exists():
    steps.append(["fetch_metoro.py"])
steps.append(["metoro.py"])
steps.append(["metoro_merge.py"])
steps.append(["synthesis.py"])
steps.append(["robustness.py"])
steps.append(["mamari_calendar.py"])
if (root / "data" / "rapanui" / "nights.txt").exists():
    steps.append(["calendar_names.py"])
steps.append(["two_islanders.py"])
if not args.fast:
    steps.append(["decipher.py"])            # about 3 minutes
steps.append(["attachments.py"])
if args.refetch or not (root / "data" / "tracings").exists():
    steps.append(["fetch_tracings.py"])       # slow: Commons rate-limits, about a file every few seconds
steps += [["tracings.py"], ["tracings_analysis.py"], ["parity_check.py"]]
if not args.fast:
    # the 2 px run first; its outputs are copied to *_tol2 before the 1 px run overwrites them
    steps += [["decompose.py", "--tol", "2"], ["__keep_tol2__"], ["decompose.py", "--tol", "1"]]
steps.append(["charts.py"])
steps.append(["glyphs.py"])

t0 = time.time()
for step in steps:
    if step[0] == "__keep_tol2__":
        for name in ("decomposition.csv", "decomposition_control.csv", "decomposition_positive.csv", "decomposition.md"):
            src = root / "out" / name
            if src.exists():
                shutil.copy(src, src.with_name(src.stem + "_tol2" + src.suffix))
        continue
    t = time.time()
    print(f"== {' '.join(step)}", flush=True)
    r = subprocess.run([sys.executable, str(root / "scripts" / step[0]), *step[1:]], cwd=root)
    if r.returncode:
        sys.exit(f"{step[0]} failed with exit code {r.returncode}")
    print(f"   done in {time.time() - t:.0f}s", flush=True)
print(f"all done in {time.time() - t0:.0f}s")
