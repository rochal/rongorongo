# Genre clustering by sign vocabulary

31 sides with at least 40 units, profiled by tf-idf weighted head-sign frequencies, compared by cosine similarity. This measures shared vocabulary, not shared passages.

## Nearest neighbours

| side | units | nearest | sim | second | sim |
|---|---|---|---|---|---|
| Aa | 678 | Ab | 0.51 | Ra | 0.50 |
| Ab | 659 | Ra | 0.62 | Pr | 0.61 |
| Br | 437 | Er | 0.55 | Bv | 0.50 |
| Bv | 510 | Hr | 0.61 | Hv | 0.60 |
| Ca | 396 | Cb | 0.61 | Ra | 0.52 |
| Cb | 363 | Ca | 0.61 | Ev | 0.56 |
| Da | 106 | Hv | 0.49 | Ab | 0.46 |
| Db | 73 | Ab | 0.48 | Da | 0.44 |
| Er | 338 | Br | 0.55 | Hr | 0.48 |
| Ev | 309 | Na | 0.63 | Sa | 0.61 |
| Gr | 239 | Kv | 0.67 | Kr | 0.65 |
| Gv | 243 | Hv | 0.47 | Hr | 0.46 |
| Hr | 586 | Qr | 0.84 | Pr | 0.83 |
| Hv | 632 | Pv | 0.75 | Hr | 0.64 |
| Ia | 1619 | Ta | 0.53 | Hr | 0.38 |
| Kr | 82 | Gr | 0.65 | Kv | 0.56 |
| Kv | 62 | Gr | 0.67 | Ev | 0.60 |
| La | 44 | Hv | 0.16 | Hr | 0.15 |
| Ma | 48 | Oa | 0.42 | Bv | 0.39 |
| Na | 97 | Ev | 0.63 | Kv | 0.53 |
| Nb | 65 | Bv | 0.28 | Hv | 0.26 |
| Oa | 78 | Ab | 0.44 | Hr | 0.43 |
| Pr | 605 | Hr | 0.83 | Qr | 0.78 |
| Pv | 556 | Hv | 0.75 | Qv | 0.68 |
| Qr | 369 | Hr | 0.84 | Pr | 0.78 |
| Qv | 331 | Pv | 0.68 | Hv | 0.60 |
| Ra | 194 | Ab | 0.62 | Pr | 0.58 |
| Rb | 161 | Hr | 0.53 | Pr | 0.51 |
| Sa | 280 | Ev | 0.61 | Ab | 0.54 |
| Sb | 304 | Hr | 0.62 | Pr | 0.60 |
| Ta | 110 | Ia | 0.53 | Sb | 0.33 |

## Average-linkage clusters at distance 0.75

- Aa, Ab, Br, Bv, Ca, Cb, Da, Db, Er, Ev, Gr, Gv, Hr, Hv, Kr, Kv, Ma, Na, Oa, Pr, Pv, Qr, Qv, Ra, Rb, Sa, Sb
- Ia, Ta
- La
- Nb

Dendrogram order: La Nb Ia Ta Ma Oa Kr Gr Kv Sa Ev Na Da Db Gv Aa Br Er Rb Ca Cb Sb Ab Ra Bv Pr Hr Qr Qv Hv Pv

## Recto against verso of the same object

| object | sim(recto, verso) | rank of verso among recto's neighbours |
|---|---|---|
| A | 0.51 | 1 of 30 |
| B | 0.50 | 2 of 30 |
| C | 0.61 | 1 of 30 |
| D | 0.44 | 6 of 30 |
| E | 0.47 | 4 of 30 |
| G | 0.28 | 19 of 30 |
| H | 0.64 | 3 of 30 |
| K | 0.56 | 2 of 30 |
| N | 0.24 | 25 of 30 |
| P | 0.62 | 3 of 30 |
| Q | 0.56 | 4 of 30 |
| R | 0.50 | 10 of 30 |
| S | 0.52 | 6 of 30 |