# Taxonomy check against the NRC-VAD lexicon

This report makes use of the NRC VAD Lexicon (v2.1), created by Saif M. Mohammad at the National Research Council Canada (https://saifmohammad.com/WebPages/nrc-vad.html). The lexicon is not distributed with this repository; only aggregate results appear below.

Moods found in the lexicon: 12 of 14 (not found: focused, laid-back). Scores are on a -1 to 1 scale. Informational: a few moods and a rating scale from a different population cannot prove the taxonomy right or wrong.

## 1. Do the cluster tags agree with the word ratings?

| Question | Result | Detail |
|---|---|---|
| every 'high' arousal cluster rates above every 'low' one | Agree | lowest high-tagged mean +0.31 vs highest low-tagged mean -0.03 |
| every 'high' valence cluster rates above every 'low' one | Agree | lowest high-tagged mean +0.39 vs highest low-tagged mean -0.28 |

## 2. Is the clustering coherent?

| Measure | Value |
|---|---|
| Mean valence-arousal distance, moods in the same cluster | 0.79 |
| Mean valence-arousal distance, moods in different clusters | 1.21 |
| Verdict | Coherent: same-cluster moods are closer |

## 3. Do the hand-tuned close-mood pairs sit close together?

| Measure | Value |
|---|---|
| Mean distance, the 5 hand-credited pairs | 0.61 |
| Mean distance, the other 61 pairs | 1.19 |
| Verdict | Credited pairs are closer |

## 3b. Do the taxonomy's own cross-cluster neighbour pairs sit close together?

| Measure | Value |
|---|---|
| Mean distance, the 6 listed neighbour pairs | 0.77 |
| Mean distance, the other 60 pairs | 1.19 |
| Verdict | Neighbour pairs are closer |

## 4. Do word ratings rank moods like the catalog's measured songs do?

Spearman rank correlation across the 12 moods that have songs (1 = same order, 0 = unrelated).

| Word rating vs measured song feature | Spearman |
|---|---|
| Valence rating vs mean song valence | +0.76 |
| Arousal rating vs mean song energy | +0.81 |
