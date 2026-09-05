# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 13758 syllables (Thomson recitations plus 6123 Metraux tokens; 48 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -3.670 |
| reversed, Rapa Nui | -3.678 |
| shuffled, Rapa Nui, mean | -3.739 |
| shuffled, Rapa Nui, max | -3.729 |
| real, English letters (24 signs) | -3.434 |
| shuffled, English letters (24 signs), mean | -3.473 |
| real, Rapa Nui (24 signs) | -3.341 |
| shuffled, Rapa Nui (24 signs), mean | -3.361 |
| positive control: Apai syllables as unknown signs, searched | -3.441 |
| positive control: Apai under the true assignment | -3.599 |
| positive control: Apai shuffled, searched | -3.555 |
| Rapa Nui text under its own model | -3.039 |
| shuffled Rapa Nui text under its own model | -3.787 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.068**
- Same on 24 signs, Rapa Nui: **+0.021**; English letters, the wrong language: **+0.039**
- Forward minus reversed under Rapa Nui: **+0.007**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.114**, 8% of 40 syllables recovered correctly, searched score -3.441 against -3.599 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | i |
| 002 | 361 | he |
| 004 | 291 | to |
| 600 | 233 | a |
| 022 | 219 | o |
| 700 | 215 | te |
| 200 | 188 | re |
| 005 | 160 | ka |
| 006 | 150 | e |
| 090 | 133 | ko |
| 040 | 123 | ru |
| 430 | 119 | ra |
| 007 | 114 | ki |
| 380 | 109 | ri |
| 070 | 98 | pe |
| 280 | 94 | ma |
| 050 | 89 | ha |
| 020 | 89 | pa |
| 300 | 87 | ro |
| 670 | 87 | hi |
| 071 | 82 | mo |
| 076 | 82 | ta |
| 008 | 79 | ti |
| 073 | 74 | ngo |
| 011 | 73 | na |