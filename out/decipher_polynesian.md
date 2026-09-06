# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 5351998 syllables (Thomson recitations plus 1582 Metraux tokens plus 2760286 polynesian tokens; 50 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -3.768 |
| reversed, Rapa Nui | -3.751 |
| shuffled, Rapa Nui, mean | -3.820 |
| shuffled, Rapa Nui, max | -3.807 |
| real, English letters (24 signs) | -3.426 |
| shuffled, English letters (24 signs), mean | -3.470 |
| real, Rapa Nui (24 signs) | -3.301 |
| shuffled, Rapa Nui (24 signs), mean | -3.335 |
| positive control: Apai syllables as unknown signs, searched | -3.396 |
| positive control: Apai under the true assignment | -3.570 |
| positive control: Apai shuffled, searched | -3.569 |
| Rapa Nui text under its own model | -2.921 |
| shuffled Rapa Nui text under its own model | -3.587 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.052**
- Same on 24 signs, Rapa Nui: **+0.034**; English letters, the wrong language: **+0.043**
- Forward minus reversed under Rapa Nui: **-0.018**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.174**, 20% of 40 syllables recovered correctly, searched score -3.396 against -3.570 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | a |
| 002 | 361 | i |
| 004 | 291 | u |
| 600 | 233 | e |
| 022 | 219 | ra |
| 700 | 215 | o |
| 200 | 188 | na |
| 005 | 160 | te |
| 006 | 150 | ka |
| 090 | 133 | ko |
| 040 | 123 | ri |
| 430 | 119 | ta |
| 007 | 114 | ha |
| 380 | 109 | tu |
| 070 | 98 | nga |
| 280 | 94 | ki |
| 050 | 89 | ho |
| 020 | 89 | ti |
| 300 | 87 | ma |
| 670 | 87 | va |
| 071 | 82 | re |
| 076 | 82 | to |
| 008 | 79 | hi |
| 073 | 74 | he |
| 011 | 73 | ro |