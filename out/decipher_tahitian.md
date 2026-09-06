# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 2574466 syllables (Thomson recitations plus 1582 Metraux tokens plus 1326043 tahitian tokens; 49 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -4.069 |
| reversed, Rapa Nui | -4.052 |
| shuffled, Rapa Nui, mean | -4.133 |
| shuffled, Rapa Nui, max | -4.113 |
| real, English letters (24 signs) | -3.440 |
| shuffled, English letters (24 signs), mean | -3.464 |
| real, Rapa Nui (24 signs) | -3.370 |
| shuffled, Rapa Nui (24 signs), mean | -3.406 |
| positive control: Apai syllables as unknown signs, searched | -3.593 |
| positive control: Apai under the true assignment | -4.341 |
| positive control: Apai shuffled, searched | -3.783 |
| Rapa Nui text under its own model | -2.623 |
| shuffled Rapa Nui text under its own model | -3.337 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.064**
- Same on 24 signs, Rapa Nui: **+0.036**; English letters, the wrong language: **+0.024**
- Forward minus reversed under Rapa Nui: **-0.017**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.189**, 12% of 40 syllables recovered correctly, searched score -3.593 against -4.341 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | i |
| 002 | 361 | a |
| 004 | 291 | ra |
| 600 | 233 | u |
| 022 | 219 | ta |
| 700 | 215 | e |
| 200 | 188 | na |
| 005 | 160 | ma |
| 006 | 150 | o |
| 090 | 133 | ne |
| 040 | 123 | ru |
| 430 | 119 | hi |
| 007 | 114 | to |
| 380 | 109 | te |
| 070 | 98 | pe |
| 280 | 94 | ho |
| 050 | 89 | ri |
| 020 | 89 | re |
| 300 | 87 | pa |
| 670 | 87 | ha |
| 071 | 82 | ti |
| 076 | 82 | pi |
| 008 | 79 | tu |
| 073 | 74 | ka |
| 011 | 73 | mi |