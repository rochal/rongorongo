# A statistical decipherment attempt

The 40 most frequent head signs, 2593 adjacent pairs among them, assigned one-to-one to Rapa Nui syllables by simulated annealing (12 restarts of 40000 steps) to maximise bigram log-likelihood under a model built from 6003 syllables (Thomson recitations plus 1582 Metraux tokens; 47 syllable types with 3+ occurrences).

## Scores, log-likelihood per adjacent pair (higher is better)

| condition | score |
|---|---|
| real, Rapa Nui | -3.674 |
| reversed, Rapa Nui | -3.671 |
| shuffled, Rapa Nui, mean | -3.734 |
| shuffled, Rapa Nui, max | -3.722 |
| real, English letters (24 signs) | -3.453 |
| shuffled, English letters (24 signs), mean | -3.478 |
| real, Rapa Nui (24 signs) | -3.385 |
| shuffled, Rapa Nui (24 signs), mean | -3.416 |
| positive control: Apai syllables as unknown signs, searched | -3.438 |
| positive control: Apai under the true assignment | -3.642 |
| positive control: Apai shuffled, searched | -3.616 |
| Rapa Nui text under its own model | -3.040 |
| shuffled Rapa Nui text under its own model | -3.836 |

- Gain of the real sequence over its shuffles under Rapa Nui, 40 signs: **+0.061**
- Same on 24 signs, Rapa Nui: **+0.031**; English letters, the wrong language: **+0.025**
- Forward minus reversed under Rapa Nui: **-0.002**
- Positive control, a real Rapa Nui recitation treated as unknown signs: gain over its shuffle **+0.178**, 5% of 40 syllables recovered correctly, searched score -3.438 against -3.642 for the true assignment.

## The best assignment, for what it is worth

| sign | tokens | syllable |
|---|---|---|
| 001 | 432 | i |
| 002 | 361 | a |
| 004 | 291 | ko |
| 600 | 233 | ta |
| 022 | 219 | te |
| 700 | 215 | ra |
| 200 | 188 | e |
| 005 | 160 | ki |
| 006 | 150 | ma |
| 090 | 133 | to |
| 040 | 123 | no |
| 430 | 119 | o |
| 007 | 114 | u |
| 380 | 109 | ri |
| 070 | 98 | re |
| 280 | 94 | ka |
| 050 | 89 | na |
| 020 | 89 | ne |
| 300 | 87 | ro |
| 670 | 87 | mo |
| 071 | 82 | ha |
| 076 | 82 | nga |
| 008 | 79 | tu |
| 073 | 74 | mu |
| 011 | 73 | hi |