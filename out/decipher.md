# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 2903 syllables of the 1886 recitations (46 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -3.660 |
| reversed, Rapa Nui | -3.667 |
| shuffled, Rapa Nui, mean | -3.747 |
| shuffled, Rapa Nui, max | -3.736 |
| real, English letters (24 signs) | -3.431 |
| shuffled, English letters (24 signs), mean | -3.471 |
| real, Rapa Nui (24 signs) | -3.388 |
| shuffled, Rapa Nui (24 signs), mean | -3.459 |
| positive control: Apai syllables as unknown signs, searched | -3.523 |
| positive control: Apai under the true assignment | -3.782 |
| positive control: Apai shuffled, searched | -3.671 |
| Rapa Nui text under its own model | -2.856 |
| shuffled Rapa Nui text under its own model | -3.785 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.087**
- Same on 24 signs, Rapa Nui: **+0.071**; English letters, the wrong language: **+0.040**
- Forward minus reversed under Rapa Nui: **+0.008**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.148**, 5% of 39 syllables recovered correctly, searched score -3.523 against -3.782 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | a |
| 002 | 361 | e |
| 004 | 291 | to |
| 600 | 233 | te |
| 022 | 219 | ra |
| 700 | 215 | i |
| 200 | 188 | ri |
| 005 | 160 | ta |
| 006 | 150 | ka |
| 090 | 133 | no |
| 040 | 123 | pe |
| 430 | 119 | u |
| 007 | 114 | ma |
| 380 | 109 | ku |
| 070 | 98 | nga |
| 280 | 94 | tu |
| 050 | 89 | o |
| 020 | 89 | na |
| 300 | 87 | ro |
| 670 | 87 | ko |
| 071 | 82 | ki |
| 076 | 82 | ti |
| 008 | 79 | ru |
| 073 | 74 | mo |
| 011 | 73 | hi |