# Sequence entropy

One witness per family (P, Q, K dropped). H1 = unigram entropy, H2 = conditional entropy of a token given the previous one, both in bits per token. Shuffled = same tokens in random order, which keeps H1 and removes all sequential structure, so H2 shuffled is the ceiling H2 could reach without any syntax. The gap between H2 and H2 shuffled is the information carried by adjacency.

| layer | tokens | H1 | H2 | H2/H1 | H2 shuffled | H2/H1 shuffled | adjacency gain, bits |
|---|---|---|---|---|---|---|---|
| heads | 8569 | 7.49 | 4.60 | 0.61 | 4.89 | 0.65 | 0.29 |
| units | 8569 | 9.10 | 3.49 | 0.38 | 3.74 | 0.41 | 0.25 |
| components | 11666 | 7.29 | 4.75 | 0.65 | 5.20 | 0.71 | 0.45 |

## Conditional entropy over the N most frequent tokens

| layer | N | tokens kept | H1 | H2 | H2 shuffled |
|---|---|---|---|---|---|
| heads | 20 | 3354 | 4.13 | 3.87 | 4.03 |
| heads | 30 | 4067 | 4.65 | 4.28 | 4.48 |
| heads | 50 | 5108 | 5.31 | 4.69 | 4.92 |
| heads | 75 | 5926 | 5.80 | 4.87 | 5.13 |
| heads | 100 | 6512 | 6.13 | 4.94 | 5.21 |
| heads | 150 | 7214 | 6.54 | 4.92 | 5.22 |
| heads | 200 | 7597 | 6.78 | 4.87 | 5.18 |
| heads | 300 | 8033 | 7.08 | 4.78 | 5.08 |
| units | 20 | 2319 | 4.13 | 3.81 | 4.00 |
| units | 30 | 2828 | 4.66 | 4.17 | 4.41 |
| units | 50 | 3565 | 5.32 | 4.49 | 4.80 |
| units | 75 | 4185 | 5.83 | 4.66 | 4.95 |
| units | 100 | 4642 | 6.17 | 4.68 | 4.99 |
| units | 150 | 5255 | 6.63 | 4.65 | 4.95 |
| units | 200 | 5640 | 6.92 | 4.57 | 4.88 |
| units | 300 | 6147 | 7.31 | 4.42 | 4.75 |
| components | 20 | 5062 | 4.11 | 3.72 | 4.06 |
| components | 30 | 6058 | 4.63 | 4.14 | 4.52 |
| components | 50 | 7411 | 5.26 | 4.60 | 5.00 |
| components | 75 | 8493 | 5.73 | 4.81 | 5.26 |
| components | 100 | 9198 | 6.03 | 4.91 | 5.36 |
| components | 150 | 10079 | 6.42 | 4.95 | 5.42 |
| components | 200 | 10552 | 6.65 | 4.93 | 5.40 |
| components | 300 | 11065 | 6.92 | 4.88 | 5.35 |

Note on the shuffled baseline: with a finite sample, conditional entropy of a random sequence sits below H1 because rare bigrams are never seen; the shuffled column is the fair comparison, not H1 itself.