# The automatic registration scored against hand-drawn boxes on Ev

269 glyphs on 7 hand-corrected lines (Ev02, Ev03, Ev04, Ev05, Ev06, Ev07, Ev08). Automatic boxes placed with the corrections ignored.

| glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median centre offset, px | offset over hand width |
|---|---|---|---|---|---|
| all: 269 | 0.45 | 49% | 29% | 12.1 | 0.28 |

## By position along the line

| where | glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| first fifth | 56 | 0.44 | 48% | 20% | 13.8 | 0.28 |
| middle | 157 | 0.45 | 48% | 31% | 9.8 | 0.25 |
| last fifth | 56 | 0.49 | 50% | 32% | 12.7 | 0.31 |

## Thin strokes against the rest

| glyphs | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| thin, under 0.4 of the line's median width | 18 | 0.49 | 50% | 22% | 6.1 | 0.58 |
| the rest | 251 | 0.45 | 49% | 29% | 12.3 | 0.25 |

## By the local match score the registration reported

| local score | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| below 0.2, flagged | 2 | 0.64 | 100% | 0% | 9.5 | 0.10 |
| 0.2 to 0.35 | 39 | 0.33 | 38% | 21% | 27.5 | 0.54 |
| above 0.35 | 228 | 0.49 | 50% | 30% | 8.8 | 0.22 |

## By line

| line | glyphs | median IoU | IoU at least 0.5 | median offset, px | median signed offset, px |
|---|---|---|---|---|---|
| Ev02 | 29 | 0.47 | 48% | 6.9 | -2.0 |
| Ev03 | 39 | 0.67 | 85% | 4.3 | +0.5 |
| Ev04 | 42 | 0.75 | 86% | 2.9 | +0.0 |
| Ev05 | 37 | 0.03 | 30% | 45.2 | -44.5 |
| Ev06 | 38 | 0.65 | 68% | 4.5 | +1.5 |
| Ev07 | 43 | 0.03 | 23% | 38.5 | -29.5 |
| Ev08 | 41 | 0.00 | 2% | 89.1 | +53.5 |

## Widths

Correlation of relative ink width, automatic against hand boxes, per line medians: **0.60** over all glyphs, **0.57** without the thin strokes.