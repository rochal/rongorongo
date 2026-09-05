# Structure Without Reading

What the Barthel transliteration of the rongorongo corpus shows about its texts when you look for structure and refuse to guess at meaning. Started from the verso of the Keiti tablet.

| | |
|---|---|
| Corpus | 26 objects, 301 lines, 11,216 units |
| Source | CEIPP numerical transliteration, kohaumotu.org |
| Tracings | Thomas Barthel, 1958, via Wikimedia Commons |
| Status | Working report, September 2026 |

Rongorongo is undeciphered and this report does not change that. It records nine structural results obtained by scripting over the published numerical transliteration and Barthel's sign catalogue, each with its evidence and its caveat, so that they can be checked against the literature and built on. Every result is reproducible from the scripts in this repository.

**In one paragraph.** The corpus divides into three families of copied texts and a majority of isolated ones; Keiti's verso is isolated but borrows two list entries from the Small Santiago tablet and one eight-sign formula shared by three tablets. The 380.1-delimited lists are a corpus-wide format whose entries are mostly unique and word-length. Alternating series are two devices, not one. The free-standing stroke signs fail a test for suffix behaviour but chain in a fixed order, and the affix-like behaviour lives in fused components instead. Copies of a text vary in those attached components far more than in head signs. Counted by head sign the inventory is far too large for a syllabary; counted by whole compound unit it has the statistics of words. Merging signs by drawn shape shrinks the head inventory by a quarter, not by the order of magnitude a syllabary would need.

## Contents

1. [Keiti's verso against Barthel](#1-keitis-verso-against-barthel)
2. [Parallel passages and families](#2-parallel-passages-and-families)
3. [Two plates: what Keiti shares](#3-two-plates-what-keiti-shares)
4. [The 380.1 lists](#4-the-3801-lists)
5. [Alternating series](#5-alternating-series)
6. [The affix test](#6-the-affix-test)
7. [Allographs and how copies differ](#7-allographs-and-how-copies-differ)
8. [The inventory](#8-the-inventory)
9. [Shape similarity of the signs](#9-shape-similarity-of-the-signs)
10. [Genre by vocabulary, and entropy](#10-genre-by-vocabulary-and-entropy)
11. [Charts](#11-charts)
12. [What it means and what it does not](#12-what-it-means-and-what-it-does-not)
13. [Method, data, reproducibility](#13-method-data-reproducibility)

## 1. Keiti's verso against Barthel

Tablet E, Keiti, was destroyed in the burning of Louvain in 1914 and survives as photographs, rubbings, and Barthel's 1958 tracing. The photograph that started this work shows the verso, eight lines, Ev1 at the top. Alignment with Barthel's tracing and with the CEIPP transliteration confirmed the orientation from the opening signs of Ev1, and confirmed that the three signs Barthel marked illegible on the verso all fall on Ev1, where the photograph shows holes.

A first reading from the photograph alone got the glyph classes right and the specifics mostly wrong, which is the expected result at roughly 30 pixels per glyph. Everything below rests on the transliteration, not on the photograph.

Three features of the verso set the agenda for the rest of the report: the compound 380.1 occurs 22 times across Ev2 to Ev5 and never twice in a row; Ev7 holds two alternating series, sign 35 five times and sign 92 eight times; and the recto's last line joins the verso's first through a sequence shared with other tablets, which Pozdniakov used to confirm Barthel's line order.

## 2. Parallel passages and families

Every maximal run of signs shared between two places in the corpus was collected, comparing only the first component of each unit so that ligature differences do not break a match. Two settings were run: strict, five or more signs with no substitution, and fuzzy, four or more with one substitution allowed inside the run.

| Setting | Shared runs | Families | Hr and Qr, covered signs | Share of Qr with a parallel | Share of Keiti verso |
|---|---|---|---|---|---|
| Strict, 5+ exact | 134 | 3 | 162 | 47% | 4% |
| Fuzzy, 4+ with one substitution | 248 | 3 | 210 | 61% | 7% |

The same three families come out under both settings: the rectos of the Great Santiago, Great St Petersburg, and Small St Petersburg tablets; the versos of the same three; and the Small Santiago recto with the Small London tablet, which the fuzzy setting extends to London's verso. Recto and verso families never cross, so H, P, and Q each carry two texts copied as a set. The longest single shared run is 15 signs between Hr3 and Qr3.

Everything else is nearly isolated. Tahua, Aruku Kurenga, Mamari, the Santiago Staff, and Keiti's recto share no run of five with any other object, and under the fuzzy setting their coverage stays below five percent. Keiti's recto instead has a strong internal refrain, the run 40, 40, 300.28, 4.430, 22, 203, which recurs on Er1, Er2, Er3, and Er6. Mamari's internal repeats on Ca7 and Ca8 are its calendar section.

> **Caveat.** These families are known to specialists; Pozdniakov and Horley catalogued the H, P, Q group and the G, K relation by hand alignment. Rediscovering them from scratch is a check on the data and method, not a new result. The isolation of the other texts holds only at the granularity tested; looser alignments may connect them.

## 3. Two plates: what Keiti shares

Keiti's verso has two external parallels of substance, both verified against Barthel's drawings glyph for glyph.

### Ev4 and Gr5: two consecutive list entries

Ev4 opens with two entries separated by the 380.1 delimiter: an oval, a stroke, a forked sign, a stroke; then the turtle sign 280 twice, each followed by a stroke. Gr5, on the Small Santiago tablet, carries the same two entries in the same order as its fourth and fifth of six, with the delimiter written 380.1.3. The Small Santiago version adds sign 521 after each turtle's stroke and a third turtle; Keiti stacks sign 61 onto the last stroke of the first entry.

Gr5 from unit 16, Barthel's tracing:

![Gr5, shared segment](docs/img/gr5_shared.png)

`380.1.3 · 88 · 1 · 47 · 1 · 380.1.3 · 280 · 1 · 521 · 280 · 1 · 521 · 1 · 22.61 · 280 · 380.1.3 · 1`

Ev4 from unit 1, Barthel's tracing:

![Ev4, shared segment](docs/img/ev4_shared.png)

`380.1 · 88 · 1 · 47 · 1.61 · 380.1 · 280 · 1 · 280 · 2 · 1 · 380.1 …`

The two full lines, for context. Gr5:

![Gr5, full line](docs/img/gr5_line.png)

Ev4:

![Ev4, full line](docs/img/ev4_line.png)

Entry by entry, with `|` marking the delimiter:

```
Gr5  62x.7 1 | 216s 20 7 320.70 600 | 290.20 79 280 2 280 30a | 88 1 47 1    | 280 1 521 280 1 521 1 22.61 280 | 1
Ev4                                                            | 88 1 47 1.61 | 280 1 280 2 1                   | 1f 57 1 1f 163 200 1.62 522fy | 607 607 650y | 200.70.3 | 376s 1 1V | 405s 522f 405s 22f 10.700 10.53 430 430 407 405 407
```

### Ev6, Hv12, Ra5: an eight-sign formula on three tablets

The run 27, 77, 34, 4, 522, 700, 600, 59 appears on Keiti, on the last line of the Great Santiago verso, and on the fifth line of the Small Washington tablet, three objects in three countries. Fish 700 is followed by frigatebird 600 every time, so the pair is a slot in a formula, not a description of animals. Keiti writes the first four signs as two ligatures, 27.6 and 77.34, where the others write them separately. What precedes the run differs on each tablet, so it is a reusable unit placed in different surroundings.

Ev6:

![Ev6 shared run](docs/img/ev6_shared.png)

`244s · 27.6 · 77.34 · 4 · 522fy · 700 · 600 · 59f · 324 · 4.4`

Hv12:

![Hv12 shared run](docs/img/hv12_shared.png)

`254.71 · 27 · 77 · 34 · 4 · 522y · 700 · 600 · 59f · 220.4.64 · 220.132`

Ra5. The Commons tracing of tablet R is small and the enlargement blurred:

![Ra5 shared run](docs/img/ra5_shared.png)

`illegible · 27? · 77? · 34 · 4 · 522 · 700 · 600 · 59f · 4.64 · 6:700`

```
Ev6   244s      | 27.6  77.34   4  522fy  700  600  59f | 324        4.4
Hv12  254.71    | 27    77  34  4  522y   700  600  59f | 220.4.64   220.132
Ra5   illegible | 27?   77? 34  4  522    700  600  59f | 4.64       6:700
```

## 4. The 380.1 lists

The compound 380.1, a seated figure with an attached stroke, is a list delimiter on six tablets: Small Santiago 30 occurrences, Keiti 22, Small London 22, Mamari 20, Small Vienna 7, Great Washington 4. Cutting every stretch between two consecutive delimiters gives 93 entries.

| Measure | Value | Reading |
|---|---|---|
| Entries of 1 to 5 units | 82 of 93 | Word or name length |
| Entries repeated exactly on another tablet | 6 clusters, all G and K | London copies Santiago in order, differing only in ligatures |
| Entries in a family sharing a sign pair | 31, in 12 families | Keiti's only cross-tablet matches are with Small Santiago |
| Unique entries | 62 | Two thirds of content is not shared anywhere |
| Entries ending in stroke 1 | 16 | Commonest final sign; strokes fall last more often than first |
| Mamari Ca3 entries opening with sign 22 | all | A list built as "22 plus item", a different shape from Keiti's |

The format is formulaic and the content mostly is not. That is what lists of distinct names or items look like, a genealogy for example, rather than a liturgy repeated across tablets. Keiti's borrowed entries from Small Santiago are a fragment inside an otherwise unique list, which strengthens the reading of those entries as fixed items.

## 5. Alternating series

A series is a run X a X b X c with the same head sign at every second position and one unit between. With at least three heads, and bare strokes excluded as heads, the corpus holds 61 such series on 14 objects. Classifying by what fills the gaps splits them into two devices.

| Kind | Series | Fillers | Examples |
|---|---|---|---|
| Affix-like | 35 | Simple signs below 100, mostly strokes | Fish 700 on H with 20, 1, 90. Fish 710 on Q with 20, 1, 90. Sign 92 on Keiti with 1, 9, 5, 22, 90. Sign 62.6 on H and P with a stroke six times. |
| List-like | 26 | Complex signs, each rare in the corpus | The 380.1 lists. The hand 73.6 on G and K with 206, 200, 222, 451, identical on both tablets. Sign 22 on Tahua with five 500-series figures. |

The affix-like fillers form a small shared set. Stroke 1 follows ten different head signs on eight objects; signs 20 and 90 each follow four heads and are five and three times more frequent in these slots than in the corpus overall. The H and Q fish series share their fillers because H and Q copy each other, so Keiti's Ev7 is the only independent witness to the set.

## 6. The affix test

If the small signs are suffixes they should select their host on one side and be indifferent on the other. For each candidate the distribution of the sign before it and after it was compared with the corpus background by Kullback-Leibler divergence in bits, with contexts on the copying tablets down-weighted so a passage counts once. Content signs served as controls.

| Sign | Left choosiness | Right choosiness | Difference | Distinct left neighbours |
|---|---|---|---|---|
| 1 | 0.98 | 1.18 | -0.19 | 127 |
| 2 | 0.90 | 0.98 | -0.08 | 119 |
| 4 | 1.91 | 1.68 | +0.22 | 86 |
| 20 | 2.61 | 2.57 | +0.04 | 38 |
| 90 | 2.23 | 2.55 | -0.32 | 43 |
| fish 700, control | 1.27 | 1.36 | -0.09 | 81 |
| frigatebird 600, control | 1.19 | 1.16 | +0.03 | 99 |

**The free-standing strokes fail.** No candidate shows the one-sided pattern. Strokes 1 and 2 are the least choosy signs in the corpus on both sides, which is how a very common syllable or a general particle behaves, not a host-selective affix. Signs 20 and 90 are choosy toward specific partners, the fish signs and sign 80, which is the alternating passages again rather than a general rule.

**Two things survive.** When strokes stand side by side their order is fixed: 2 before 1 in 18 cases against 8, 4 before 2 in 17 against 7, 1 before 9 in 10 against none, 2 before 3 in 5 against none. That gives a chain 4, 2, 1, 9, which is what affix chains and numeral systems both produce. And the fused components are host-selective in exactly the way free strokes are not: sign 3 is bound in 404 of 433 occurrences, sign 9 in 142 of 194, and bound stroke 1 attaches to sign 380 in 107 of 430 cases. If anything here is an affix, it is the small sign fused into a larger one.

## 7. Allographs and how copies differ

The fuzzy parallel runs align copies with one sign swapped. Each swap is a pair of signs in the same slot of the same passage, and recurring pairs are candidate allographs, variant spellings of one sign. This is the mechanism by which Pozdniakov reduced Barthel's inventory.

The layer is thin. The runs contain 48 substitutions in 42 distinct pairs; only three recur in separate passages, 8 with 551, 316 with 356, and 400 with 430, and 17 one-off pairs sit in the same Barthel series and are plausible look-alikes. Merging was tested by rerunning the strict parallel map: the three recurring pairs raise shared runs from 134 to 145; adding the 17 look-alikes raises them to 165 and lifts Great Santiago's covered share from 42 to 46 percent. The families do not change and no isolated text connects to anything.

**Copies vary in attachments, not in head signs.** Scribes kept the main sign and changed what was fused to it. Sign 22 stands bare on one tablet and carries 380 on another eight times; sign 200 carries 50 in one copy and 132 in the other six times. Components 10, 50, 132, 380, 1, and 430 come and go most. Barthel's compound notation is recording a layer that copyists treated as optional.

> **Caveat.** Copied passages are too few and too faithful for empirical allograph reduction to reach anywhere near 52 signs. Pozdniakov's reduction rests mainly on visual similarity, which section 9 tests directly.

## 8. The inventory

Three inventories were counted with one witness per family, so copies do not inflate the numbers: head signs, the first component of every unit; attached components, everything fused onto a head; and whole units as written.

| Inventory | Tokens | Distinct | Once only | Signs for 50% | 90% | 99% | Zipf slope |
|---|---|---|---|---|---|---|---|
| Head signs | 8,688 | 649 | 30% | 34 | 223 | 563 | 1.36 |
| Attached components | 3,088 | 224 | 35% | 9 | 66 | 194 | 1.42 |
| Whole units | 8,688 | 2,067 | 63% | 80 | 1,199 | 1,981 | 0.93 |

**Head signs, as Barthel numbered them, are not a syllabary.** Rapa Nui has about 55 syllables. The 55 most frequent head signs cover about 62 percent of the text and the next 600 carry the remaining third. For a reduction to roughly 52 basic signs to hold, some 600 of Barthel's numbers must be compounds or variants of those 52, and they account for over a third of all tokens.

**Attached components are a compact set.** Nine cover half of all attachments; one sign, 76, is nearly a fifth of them, followed by 3, 1, 10, and 6. A small closed set attached to a large open one is the shape of a grammatical layer on a lexical one, and it is the same set the affix test singled out.

**Whole units have the statistics of words.** A natural-language text of about 9,000 tokens typically has around 2,000 distinct words, more than half occurring once, with a Zipf slope near one. Units come out at 2,067 distinct, 63 percent once only, slope 0.93. Neither head signs nor components separately fit that profile; the units do.

Barthel's series confirm the split: the geometric signs below 100 are 139 distinct signs and 54 percent of the text, while each pictorial series, human figures, birds, fish, holds between 4 and 10 percent. The script is mostly abstract marks with pictorial signs through it, not a picture script with a few marks.

> **Caveat.** Barthel's catalogue splits what may be one sign into several numbers, so 649 is an upper bound and the tail is shorter than it looks. The word-like statistics of units are suggestive, not probative, because an over-split catalogue also inflates the unit count.

## 9. Shape similarity of the signs

Barthel's catalogue drawings, 601 signs and 713 drawings including the variants he drew for 112 of them, were fetched from kohaumotu and compared by shape. Each drawing is normalised to a 40 pixel square and described by a lightly blurred silhouette and by gradient-orientation histograms over a five by five grid; similarity is the cosine of the descriptors, best of direct and mirrored, penalised for aspect-ratio mismatch.

Barthel's own variant pairs are the ground truth. The threshold was set where only one unrelated pair in 200 passes, and at that setting it recovers 22 percent of the genuine variant pairs. Classes are cliques: a sign joins only if it passes against every current member. A first attempt with single linkage chained the whole catalogue into one class, which is a warning about how continuous the shape space is.

The closest pairs, from the contact sheet the script writes:

![Closest sign pairs](docs/img/sign_pairs.png)

| Inventory, one witness per family | Distinct | Signs for 50% | 90% | 99% |
|---|---|---|---|---|
| Barthel head signs | 649 | 34 | 223 | 563 |
| After shape merging, strict | 485 | 25 | 151 | 399 |

- **113 look-alike classes absorb 171 signs.** The closest pairs are real: the figures 212 and 216, the ovals 22 and 24, the birds 622 and 624, the fish 700 and 710, the fork signs 90 and 91.
- **Shape merging does not get near 52.** Even the over-merged single-linkage pass only reached 380 classes. Pozdniakov's reduction cannot be a look-alike merge; it has to treat most of Barthel's numbers as compounds of a few dozen elements, which is a different claim and one this method does not test.
- **The copy-derived allograph pairs split by shape.** Same-series pairs from the copied passages score high, 254 with 256 at 0.83, 316 with 356 at 0.69, 630 with 631 at 0.68, against a median of 0.34 for random pairs. But 400 with 430, seen in two passages, scores 0.30, and 8 with 551 scores 0.55. Those are genuine substitutions in copying, not spelling variants.

> **Caveat.** The descriptor is crude and the recall figure says so: most of Barthel's own variant pairs fall below the strict threshold, so the merge is conservative. A few classes remain doubtful, such as the ovals 22 to 24 grouped with the fish 700, whose drawing is an elongated oval. This measures similarity of Barthel's type drawings, not of the signs as carved, which vary more.

## 10. Genre by vocabulary, and entropy

Copying groups texts that share passages. A second grouping asks which texts share a vocabulary, whether or not they share passages. Each side with at least 40 units is profiled by the head signs it favours relative to the corpus, tf-idf weighted, and sides are compared by cosine similarity. Thirty-one sides qualify.

![Sides mapped by the signs they favour](docs/img/genre_map.png)

- **The copied families are also vocabulary families**, which is a sanity check: Hr with Qr at 0.84, Hv with Pv at 0.75, Gr with Kv at 0.67.
- **Keiti's verso keeps company with the other list tablets.** Its nearest neighbours by vocabulary are Small Vienna side a and Great Washington side a, with Small London verso close behind, none of which copy it. The 380.1 lists share a vocabulary as well as a format.
- **Keiti's recto belongs elsewhere.** Its nearest neighbour is the recto of Aruku Kurenga, and its own verso ranks only fourth. Small Santiago and Small Vienna have sides even less alike, at ranks 19 and 25 of 30, so several objects carry two texts of different kinds. Tahua, Mamari, and Great Santiago have sides that resemble each other.
- **The Santiago Staff and the Honolulu tablet stand apart together.** Their vocabularies resemble each other at 0.53 and nothing else above 0.38. That matches Fischer's grouping of the two, made on other grounds.

Entropy asks how much a sign is predicted by the sign before it. For each layer the unigram entropy and the conditional entropy given the previous token are computed one witness per family, and the same for the tokens shuffled, which keeps the frequencies and destroys the order. The difference is the information carried by adjacency.

| Layer | Tokens | H1 | H2 as written | H2 shuffled | Adjacency gain, bits |
|---|---|---|---|---|---|
| Head signs | 8,569 | 7.49 | 4.60 | 4.89 | 0.29 |
| Whole units | 8,569 | 9.10 | 3.49 | 3.74 | 0.25 |
| Components | 11,666 | 7.29 | 4.75 | 5.20 | 0.45 |

![How much the previous sign predicts the next](docs/img/entropy_curve.png)

Adjacency carries a consistent quarter to half a bit per token at every vocabulary size tested, so the order of signs is not random. The gain is modest, which fits texts dominated by lists of distinct items, where the previous item says little about the next. Components show the largest gain because a compound's parts follow each other in a fixed way, which is the ligature layer again.

> **Caveat.** Conditional entropy on a finite sample sits below the unigram entropy even for random order, because rare pairs are never observed. The shuffled column is the fair baseline, not H1. Published entropy comparisons across scripts use varied conventions, so these values should be compared with others only after matching the method.

## 11. Charts

All charts are produced by `scripts/charts.py` from the tables in `out/`.

![Three inventories, three shapes](docs/img/rank_frequency.png)

![How much of each text is found elsewhere](docs/img/parallel_coverage.png)

![No stroke sign behaves like a suffix](docs/img/affix_test.png)

![Adjacent strokes keep a fixed order](docs/img/stroke_order.png)

## 12. What it means and what it does not

Nothing here reads a sign. Fish 700 appears five times on Keiti's verso, always inside a formula or a list slot; the verso's commonest signs are strokes, the delimiter, and sign 22, none of them pictures of anything. A rendering into English sentences would be invention.

What the evidence supports is a genre-level and layer-level description. The texts are recited formulaic material: copied sets on H, P, and Q, a condensed copy on K, delimited lists whose items are mostly unique, refrains and alternating series. Within a text, three layers behave differently. The head sign is the open, content-bearing class. The attached component is a small closed class that copyists treated as optional and that carries whatever host selectivity exists. The compound unit is the word-sized thing. This picture is consistent with the mixed logo-syllabic reading most specialists favour, and it argues against both the picture-reading and the pure-cipher framings.

What is probably known already: the families, the 380.1 lists, and the size of Barthel's inventory. What is worth checking against the literature: the negative affix result for free strokes, the fixed stacking order 4, 2, 1, 9, the finding that copies vary in attachments rather than head signs, the word-like statistics of whole units, and the result that shape merging alone cannot reach a syllabary-sized inventory.

### Open questions and next tests

- **Are units words?** Compare the distribution of unit length in components with Rapa Nui word length in syllables, and the most frequent units with Rapa Nui's frequent particles. Nineteenth-century chants and genealogies match the genre and are free to use.
- **What is the stacking order?** Chains of the small signs in the order 4, 2, 1, 9 could be a numeral system or an affix sequence. Counting how often each chain length occurs, and where in a list entry it falls, would separate the two.
- **What does 380.1 do?** It never repeats and it separates word-length items. Whether its own attachments, 3 on G and K, 52 on N, correlate with the entries around it is testable.
- **Are Keiti's refrains strophic?** The recto refrain on Er1, Er2, Er3, and Er6 and the Ev7 series both look like chant structure. Measuring the distance between refrains against the line lengths of documented Rapa Nui chants is a test that needs no reading.
- **Do compounds decompose?** If Pozdniakov is right, most of the 600 rare head signs are built from a few dozen elements. A shape decomposition that matches sub-parts of drawings against the frequent signs would test that directly.

## 13. Method, data, reproducibility

The data is the CEIPP numerical transliteration of the whole corpus, Thomas Barthel's numbering as extended by the Cercle d'Études sur l'Île de Pâques et la Polynésie, served at kohaumotu.org, and Barthel's sign catalogue drawings from the same site. Each unit is one compound as Barthel drew it; components are joined by dots, variant letters mark drawn variants, a question mark marks doubt, and 000 marks an illegible sign. Matching throughout strips variant letters and doubt marks, and most comparisons use only the first component so ligature differences do not break a match. Where copies would count the same evidence several times, the H, P, Q group and the G, K pair are down-weighted or reduced to one witness.

### Layout

```
data/html/          raw transliteration pages, one per object (A to Z)
data/corpus.json    parsed corpus: line id -> list of Barthel units
data/signs/         catalogue pages, row GIFs, rows.json (row -> five sign numbers)
docs/img/           line crops from Barthel's tracings used in this README
scripts/            one script per analysis, see below
out/                generated CSV and Markdown reports
```

### Run

```bash
python scripts/fetch_corpus.py                 # only to refresh data/html
python scripts/parse_corpus.py
python scripts/alternations.py
python scripts/lists_380.py
python scripts/affix_test.py
python scripts/parallels.py
python scripts/parallels.py --min-run 4 --mismatch 1 --suffix _fuzzy
python scripts/allographs.py
python scripts/parallels.py --merge out/allograph_merge.csv --suffix _merged
python scripts/inventory.py
python scripts/fetch_signs.py
python scripts/sign_shapes.py
python scripts/genre_entropy.py
python scripts/charts.py
```

Requires Python 3.10 or later with numpy, scipy, Pillow and matplotlib. The kohaumotu site serves plain http only and its TLS certificate has expired.

| Script | Produces |
|---|---|
| fetch_corpus.py, parse_corpus.py | data/html, data/corpus.json |
| alternations.py | Every alternating series, filler inventories, affix-like against list-like |
| lists_380.py | The 93 list entries, exact and ligature-tolerant clusters, families, entry shape |
| affix_test.py | Host selectivity, enrichment, fused hosts, stacking order |
| parallels.py | Shared runs, blocks, side matrix, families; options for run length, substitutions, merges |
| allographs.py | Substitution pairs, component swaps, merge tables |
| inventory.py | Three inventories with coverage thresholds and Zipf slopes |
| fetch_signs.py, sign_shapes.py | Catalogue drawings, similarity, look-alike classes, contact sheet |
| genre_entropy.py | Vocabulary similarity of sides, clusters, 2-D map coordinates; unigram and conditional entropy per layer |
| charts.py | The six charts in docs/img |

### Conventions

Line ids are Barthel's: object letter, side, line (Ev04 = Keiti verso line 4). A unit like `380.001.003` is one compound glyph; `522fy` carries Barthel variant letters; `?` marks an uncertain reading and `000!` an illegible sign. In prose the leading zeros are dropped, so 380.001 is written 380.1.

### Sources

- Barthel, T. S. 1958. *Grundlagen zur Entzifferung der Osterinselschrift.* Hamburg.
- Pozdniakov, K. 1996. Les bases du déchiffrement de l'écriture de l'île de Pâques. *Journal de la Société des Océanistes* 103.
- Horley, P. 2005. Allographic variations and statistical analysis of the rongorongo corpus. *Rapa Nui Journal* 19.
- Fischer, S. R. 1997. *Rongorongo: The Easter Island Script.* Oxford.
- CEIPP transliteration and Barthel sign catalogue: http://kohaumotu.org/rongorongo_org/
- Barthel tracings: Wikimedia Commons files Barthel_Ev.png, Barthel_Gr.png, Barthel_Hv.png, Barthel_Ra.jpg.
- Provenance and line counts of each object: the Wikipedia articles on the individual rongorongo texts.
