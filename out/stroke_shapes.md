# A stroke-based descriptor

601 signs, 713 drawings, 130 variant pairs of one sign against 6000 random pairs.

## Calibration: five descriptors on the same test

| descriptor | within-sign median | random median | recall at 99.5th pct | at 99th | at 95th | rank AUC |
|---|---|---|---|---|---|---|
| pixel | 0.375 | 0.228 | 35% | 44% | 65% | 0.822 |
| stroke counts | 0.847 | 0.690 | 5% | 6% | 22% | 0.693 |
| skeleton image | 0.349 | 0.220 | 26% | 33% | 58% | 0.809 |
| shape context | 0.734 | 0.569 | 18% | 25% | 44% | 0.776 |
| pixel + skeleton | 0.358 | 0.224 | 31% | 43% | 65% | 0.818 |

Best at the strict threshold: **pixel**. Recall = share of Barthel's own variant pairs scoring above the threshold that only the stated share of random pairs exceed. AUC = probability that a variant pair outscores a random pair.

## Look-alike classes with the pixel descriptor at the 99.5th-percentile threshold

325 reciprocal-neighbour pairs, 115 classes absorbing 189 signs (section 9 with the pixel descriptor: 113 classes absorbing 171).

| class |
|---|
| 204 206 222 226 236 292 303 306 |
| 263 266 276 293 294 526 |
| 202 376 506 531 582 721 |
| 022 023 024 040 073 |
| 191 220 320 331 502 |
| 253 254 256 354 356 |
| 215 231 311 315 501 |
| 200 300 570 590 593 |
| 070 149 150 151 |
| 019 155 156 158 |
| 212 216 227 314 |
| 201 203 205 302 |
| 235 275 285 393 |
| 397 402 404 406 |
| 301 305 505 575 |
| 326 336 396 576 |
| 602 603 604 606 |
| 613 622 624 626 |
| 550 560 600 690 |
| 286 296 596 696 |
| 004 010 062 724 |
| 141 142 143 |
| 152 153 154 |
| 163 165 166 |
| 243 244 246 |
| 260 280 281 |
| 262 282 284 |
| 321 322 324 |
| 343 344 346 |
| 183 366 726 |

## Allograph candidates from copied passages, rescored

| a | b | similarity | passages | same series |
|---|---|---|---|---|
| 254 | 256 | 0.443 | 1 | yes |
| 409 | 609 | 0.434 | 1 |  |
| 316 | 356 | 0.432 | 2 | yes |
| 214 | 216 | 0.416 | 1 | yes |
| 630 | 631 | 0.416 | 1 | yes |
| 066 | 117 | 0.413 | 1 |  |
| 381 | 385 | 0.411 | 1 | yes |
| 066 | 074 | 0.407 | 1 | yes |
| 741 | 742 | 0.405 | 1 | yes |
| 001 | 066 | 0.405 | 1 | yes |
| 400 | 600 | 0.403 | 1 |  |
| 307 | 607 | 0.393 | 1 |  |
| 009 | 599 | 0.393 | 1 |  |
| 450 | 710 | 0.389 | 1 |  |
| 301 | 394 | 0.388 | 1 | yes |
| 056 | 084 | 0.384 | 1 | yes |
| 001 | 004 | 0.371 | 1 | yes |
| 280 | 290 | 0.360 | 1 | yes |
| 309 | 464 | 0.358 | 1 |  |
| 110 | 141 | 0.351 | 1 | yes |
| 008 | 081 | 0.346 | 1 | yes |
| 048 | 117 | 0.344 | 1 |  |
| 013 | 200 | 0.301 | 1 |  |
| 013 | 110 | 0.297 | 1 |  |
| 386 | 551 | 0.292 | 1 |  |

Threshold 0.401; random-pair median 0.228.

## Metoro's pairs of section 18

| a | b | similarity |
|---|---|---|
| 004 | 022 | 0.399 |
| 400 | 600 | 0.403 |
| 040 | 041 | 0.115 |
| 206 | 380 | 0.220 |