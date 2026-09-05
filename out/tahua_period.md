# Tahua's secondary period

Side a: 678 units on 8 lines of 84, 83, 75, 83, 85, 88, 92, 88 units. Side b: 659 units.

## Same-sign recurrence by distance, both sides

| distance | Aa matches | expected | z | Ab matches | expected | z |
|---|---|---|---|---|---|---|
| 18 | 14 | 7.8 | +2.3 | 14 | 13.9 | +0.0 |
| 19 | 13 | 7.9 | +1.9 | 15 | 14.3 | +0.2 |
| 20 | 8 | 7.6 | +0.1 | 17 | 14.0 | +0.9 |
| 21 | 18 | 7.7 | +3.8 | 19 | 14.1 | +1.3 |
| 22 | 17 | 8.0 | +3.0 | 16 | 14.0 | +0.6 |
| 23 | 10 | 7.4 | +1.0 | 11 | 14.0 | -0.9 |
| 24 | 22 | 7.5 | +5.4 | 15 | 14.1 | +0.2 |
| 25 | 12 | 7.3 | +1.8 | 12 | 13.8 | -0.5 |
| 26 | 9 | 7.9 | +0.4 | 27 | 13.3 | +3.7 |
| 27 | 10 | 7.3 | +1.1 | 12 | 13.9 | -0.6 |
| 28 | 14 | 7.4 | +2.6 | 19 | 13.7 | +1.5 |

## What carries the excess at 22 to 24 on side a

| distance | matches | expected | signs with the largest excess (matches, expected) |
|---|---|---|---|
| 22 | 17 | 8.6 | 080 (2, 0.1), 004 (3, 1.5), 025 (2, 0.7), 182 (1, 0.0), 539 (1, 0.0), 048 (1, 0.0) |
| 23 | 10 | 8.5 | 025 (3, 0.7), 600 (2, 0.5), 11 (1, 0.1), 020 (1, 0.2), 002 (2, 1.4), 001 (1, 1.0) |
| 24 | 22 | 8.5 | 002 (6, 1.4), 22 (2, 0.3), 004 (3, 1.5), 600 (2, 0.5), 114 (1, 0.0), 21 (1, 0.0) |

Driving signs, by excess summed over the three distances: 002 (+5.3), 025 (+3.9), 600 (+3.6), 004 (+3.1), 080 (+2.7), 22 (+2.4), 11 (+1.9), 745 (+1.9).

## Gaps between consecutive occurrences of the driving signs

| sign | occurrences on Aa | gaps | gaps of 18 to 28 |
|---|---|---|---|
| 002 | 31 | 27 5 49 8 16 3 18 3 2 28 7 73 37 14 10 1 6 1 6 12 1 11 1 36 6 53 2 4 17 7 | 3 of 30 |
| 025 | 22 | 11 6 247 10 6 9 14 1 11 10 1 8 21 5 3 5 20 5 3 15 13 | 2 of 21 |
| 600 | 18 | 4 2 11 1 3 2 4 1 50 55 15 24 13 49 71 123 76 | 1 of 17 |
| 004 | 32 | 68 4 17 28 3 6 5 4 9 6 2 19 30 8 3 7 62 15 3 44 7 12 12 10 12 4 6 6 28 36 6 | 3 of 31 |
| 080 | 10 | 4 48 17 206 7 12 12 10 12 | 0 of 9 |
| 22 | 14 | 2 2 2 2 2 3 3 2 8 49 13 30 24 | 1 of 13 |
| 11 | 6 | 8 7 4 5 18 | 1 of 5 |
| 745 | 6 | 8 49 1 24 22 | 2 of 5 |

## Groups of three signs returning at 18 to 28 positions: 8

| group | first at | returns at | gap | line, offset of first |
|---|---|---|---|---|
| 002 002 080 | 512 | 531 | 19 | line 7, +14 |
| 002 080 004 | 513 | 532 | 19 | line 7, +15 |
| 080 004 280 | 533 | 555 | 22 | line 7, +35 |
| 004 280 182 | 534 | 556 | 22 | line 7, +36 |
| 280 182 048 | 535 | 557 | 22 | line 7, +37 |
| 182 048 022 | 536 | 558 | 22 | line 7, +38 |
| 048 022 025 | 537 | 559 | 22 | line 7, +39 |
| 022 025 025 | 538 | 560 | 22 | line 7, +40 |

## Where the driving signs fall in their lines

- 002: line 3 +38, line 3 +65, line 3 +70, line 4 +44, line 4 +52, line 4 +68, line 4 +71, line 5 +6, line 5 +9, line 5 +11, line 5 +39, line 5 +46, line 6 +34, line 6 +71, line 6 +85, line 7 +7, line 7 +8, line 7 +14, line 7 +15, line 7 +21, line 7 +33, line 7 +34, line 7 +45, line 7 +46, line 7 +82, line 7 +88, line 8 +49, line 8 +51, line 8 +55, line 8 +72, line 8 +79
- 025: line 3 +69, line 4 +5, line 4 +11, line 7 +2, line 7 +12, line 7 +18, line 7 +27, line 7 +41, line 7 +42, line 7 +53, line 7 +63, line 7 +64, line 7 +72, line 8 +1, line 8 +6, line 8 +9, line 8 +14, line 8 +34, line 8 +39, line 8 +42, line 8 +57, line 8 +70
- 600: line 3 +0, line 3 +4, line 3 +6, line 3 +17, line 3 +18, line 3 +21, line 3 +23, line 3 +27, line 3 +28, line 4 +3, line 4 +58, line 4 +73, line 5 +14, line 5 +27, line 5 +76, line 6 +62, line 8 +5, line 8 +81
- 004: line 3 +5, line 3 +73, line 4 +2, line 4 +19, line 4 +47, line 4 +50, line 4 +56, line 4 +61, line 4 +65, line 4 +74, line 4 +80, line 4 +82, line 5 +18, line 5 +48, line 5 +56, line 5 +59, line 5 +66, line 6 +43, line 6 +58, line 6 +61, line 7 +17, line 7 +24, line 7 +36, line 7 +48, line 7 +58, line 7 +70, line 7 +74, line 7 +80, line 7 +86, line 8 +22, line 8 +58, line 8 +64