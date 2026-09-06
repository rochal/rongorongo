# The automatic registration scored against hand-drawn boxes on Ev

269 glyphs on 7 hand-corrected lines (Ev02, Ev03, Ev04, Ev05, Ev06, Ev07, Ev08). Automatic boxes placed with the corrections ignored.

| glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median centre offset, px | offset over hand width |
|---|---|---|---|---|---|
| all: 269 | 0.45 | 47% | 8% | 10.0 | 0.24 |

## By position along the line

| where | glyphs | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| first fifth | 56 | 0.39 | 39% | 4% | 16.6 | 0.38 |
| middle | 157 | 0.48 | 49% | 8% | 8.7 | 0.18 |
| last fifth | 56 | 0.47 | 48% | 14% | 7.2 | 0.26 |

## Thin strokes against the rest

| glyphs | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| thin, under 0.4 of the line's median width | 18 | 0.29 | 33% | 0% | 9.2 | 0.62 |
| the rest | 251 | 0.46 | 48% | 9% | 11.0 | 0.23 |

## By the local match score the registration reported

| local score | count | median IoU | IoU at least 0.5 | at least 0.7 | median offset, px | offset over width |
|---|---|---|---|---|---|---|
| below 0.2, flagged | 3 | 0.44 | 0% | 0% | 17.0 | 0.13 |
| 0.2 to 0.35 | 37 | 0.29 | 38% | 0% | 22.2 | 0.49 |
| above 0.35 | 229 | 0.48 | 49% | 10% | 9.5 | 0.22 |

## Widths

Correlation of relative ink width, automatic against hand boxes, per line medians: **0.63** over all glyphs, **0.61** without the thin strokes.