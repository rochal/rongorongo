# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 2783535 syllables (Thomson recitations plus 1582 Metraux tokens plus 1434243 maori tokens; 50 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -3.762 |
| reversed, Rapa Nui | -3.758 |
| shuffled, Rapa Nui, mean | -3.826 |
| shuffled, Rapa Nui, max | -3.806 |
| real, English letters (24 signs) | -3.439 |
| shuffled, English letters (24 signs), mean | -3.468 |
| real, Rapa Nui (24 signs) | -3.355 |
| shuffled, Rapa Nui (24 signs), mean | -3.394 |
| positive control: Apai syllables as unknown signs, searched | -3.397 |
| positive control: Apai under the true assignment | -3.561 |
| positive control: Apai shuffled, searched | -3.605 |
| Rapa Nui text under its own model | -2.956 |
| shuffled Rapa Nui text under its own model | -3.775 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.065**
- Same on 24 signs, Rapa Nui: **+0.038**; English letters, the wrong language: **+0.029**
- Forward minus reversed under Rapa Nui: **-0.004**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.208**, 12% of 40 syllables recovered correctly, searched score -3.397 against -3.561 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | a |
| 002 | 361 | i |
| 004 | 291 | te |
| 600 | 233 | ta |
| 022 | 219 | ha |
| 700 | 215 | ka |
| 200 | 188 | e |
| 005 | 160 | ki |
| 006 | 150 | ra |
| 090 | 133 | na |
| 040 | 123 | pa |
| 430 | 119 | o |
| 007 | 114 | ma |
| 380 | 109 | no |
| 070 | 98 | ko |
| 280 | 94 | tu |
| 050 | 89 | he |
| 020 | 89 | ti |
| 300 | 87 | ri |
| 670 | 87 | hu |
| 071 | 82 | u |
| 076 | 82 | to |
| 008 | 79 | nga |
| 073 | 74 | re |
| 011 | 73 | mo |