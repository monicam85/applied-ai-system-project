# Evaluation report

Catalog: 18 songs. Top-k: 5.

## Profile checks

| Profile | Check | Result | Detail |
|---|---|---|---|
| High-Energy Pop | returns k results | PASS | 5 returned |
| High-Energy Pop | scores within 0-1 | PASS | [0.9710000000000001, 0.8019999999999999, 0.667, 0.649, 0.584] |
| High-Energy Pop | no artist repeats more than twice | PASS | max repeats 1 |
| High-Energy Pop | deterministic | PASS |  |
| High-Energy Pop | confidence level as expected | PASS | got high, expected one of ['high'] |
| Chill Lofi | returns k results | PASS | 5 returned |
| Chill Lofi | scores within 0-1 | PASS | [0.976, 0.9149999999999998, 0.8280000000000001, 0.7849999999999999, 0. |
| Chill Lofi | no artist repeats more than twice | PASS | max repeats 2 |
| Chill Lofi | deterministic | PASS |  |
| Chill Lofi | confidence level as expected | PASS | got high, expected one of ['high'] |
| Deep Intense Rock | returns k results | PASS | 5 returned |
| Deep Intense Rock | scores within 0-1 | PASS | [0.953, 0.796, 0.783, 0.5129999999999999, 0.51] |
| Deep Intense Rock | no artist repeats more than twice | PASS | max repeats 1 |
| Deep Intense Rock | deterministic | PASS |  |
| Deep Intense Rock | confidence level as expected | PASS | got high, expected one of ['high'] |
| Conflicted (sad but high-energy) | returns k results | PASS | 5 returned |
| Conflicted (sad but high-energy) | scores within 0-1 | PASS | [0.618, 0.425, 0.402, 0.347, 0.356] |
| Conflicted (sad but high-energy) | no artist repeats more than twice | PASS | max repeats 1 |
| Conflicted (sad but high-energy) | deterministic | PASS |  |
| Conflicted (sad but high-energy) | confidence level as expected | PASS | got medium, expected one of ['low', 'medium'] |
| Adversarial: metal fan who wants chill | returns k results | PASS | 5 returned |
| Adversarial: metal fan who wants chill | scores within 0-1 | PASS | [0.6359999999999999, 0.543, 0.46799999999999997, 0.357, 0.462000000000 |
| Adversarial: metal fan who wants chill | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: metal fan who wants chill | deterministic | PASS |  |
| Adversarial: metal fan who wants chill | confidence level as expected | PASS | got medium, expected one of ['low', 'medium'] |
| Adversarial: acoustic-loving EDM fan | returns k results | PASS | 5 returned |
| Adversarial: acoustic-loving EDM fan | scores within 0-1 | PASS | [0.8, 0.514, 0.417, 0.41100000000000014, 0.24600000000000005] |
| Adversarial: acoustic-loving EDM fan | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: acoustic-loving EDM fan | deterministic | PASS |  |
| Adversarial: acoustic-loving EDM fan | confidence level as expected | PASS | got medium, expected one of ['low', 'medium'] |
| Adversarial: empty profile | returns k results | PASS | 5 returned |
| Adversarial: empty profile | scores within 0-1 | PASS | [0.0, 0.0, 0.0, 0.0, 0.0] |
| Adversarial: empty profile | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: empty profile | deterministic | PASS |  |
| Adversarial: empty profile | confidence level as expected | PASS | got none, expected one of ['none'] |
| Adversarial: wrong-case genre and mood | returns k results | PASS | 5 returned |
| Adversarial: wrong-case genre and mood | scores within 0-1 | PASS | [0.9780000000000001, 0.837, 0.6839999999999999, 0.632, 0.404] |
| Adversarial: wrong-case genre and mood | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: wrong-case genre and mood | deterministic | PASS |  |
| Adversarial: wrong-case genre and mood | confidence level as expected | PASS | got high, expected one of ['high', 'low', 'medium'] |
| Adversarial: likes_acoustic='no' | returns k results | PASS | 5 returned |
| Adversarial: likes_acoustic='no' | scores within 0-1 | PASS | [0.953, 0.782, 0.7689999999999999, 0.5269999999999999, 0.524] |
| Adversarial: likes_acoustic='no' | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: likes_acoustic='no' | deterministic | PASS |  |
| Adversarial: likes_acoustic='no' | confidence level as expected | PASS | got high, expected one of ['high'] |
| Adversarial: likes_acoustic='maybe' | rejects bad input cleanly | PASS | likes_acoustic must be a bool or yes/no, got 'maybe' |
| Adversarial: likes_acoustic='maybe' | confidence level as expected | PASS | got none, expected one of ['none'] |
| Numeric acousticness=0.5 | returns k results | PASS | 5 returned |
| Numeric acousticness=0.5 | scores within 0-1 | PASS | [0.7529999999999999, 0.6839999999999999, 0.695, 0.546, 0.586] |
| Numeric acousticness=0.5 | no artist repeats more than twice | PASS | max repeats 1 |
| Numeric acousticness=0.5 | deterministic | PASS |  |
| Numeric acousticness=0.5 | confidence level as expected | PASS | got medium, expected one of ['high', 'low', 'medium'] |
| Adversarial: genre-only (lofi) | returns k results | PASS | 5 returned |
| Adversarial: genre-only (lofi) | scores within 0-1 | PASS | [1.0, 1.0, 1.0, 0.5, 0.5] |
| Adversarial: genre-only (lofi) | no artist repeats more than twice | PASS | max repeats 2 |
| Adversarial: genre-only (lofi) | deterministic | PASS |  |
| Adversarial: genre-only (lofi) | confidence level as expected | PASS | got medium, expected one of ['medium'] |
| Adversarial: energy out of range (1.5) | returns k results | PASS | 5 returned |
| Adversarial: energy out of range (1.5) | scores within 0-1 | PASS | [0.866, 0.702, 0.6970000000000001, 0.591, 0.5439999999999999] |
| Adversarial: energy out of range (1.5) | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: energy out of range (1.5) | deterministic | PASS |  |
| Adversarial: energy out of range (1.5) | confidence level as expected | PASS | got high, expected one of ['high', 'low', 'medium'] |
| Adversarial: energy='high' (wrong type) | returns k results | PASS | 5 returned |
| Adversarial: energy='high' (wrong type) | scores within 0-1 | PASS | [0.9876923076923076, 0.7923076923076924, 0.5953846153846153, 0.5353846 |
| Adversarial: energy='high' (wrong type) | no artist repeats more than twice | PASS | max repeats 1 |
| Adversarial: energy='high' (wrong type) | deterministic | PASS |  |
| Adversarial: energy='high' (wrong type) | confidence level as expected | PASS | got high, expected one of ['high', 'low', 'medium'] |

## Natural-language parsing checks

| Case | Result | Parsed prefs | Source |
|---|---|---|---|
| keywords: study music | PASS | `{"mood": "chill", "energy": 0.3}` | keywords |
| keywords: workout | PASS | `{"energy": 0.9}` | keywords |
| keywords: gibberish | PASS | `{}` | keywords |
| keywords: goal beats current mood | PASS | `{"mood": "happy"}` | keywords |
| keywords: wake-me-up goal | PASS | `{"energy": 0.85}` | keywords |
| keywords: negation skipped | PASS | `{}` | keywords |
| keywords: word not substring | PASS | `{}` | keywords |
| llm: well-formed JSON | PASS | `{"genre": "lofi", "energy": 0.3}` | llm |
| llm: JSON wrapped in prose | PASS | `{"mood": "happy"}` | llm |
| llm: malformed JSON falls back | PASS | `{"mood": "chill", "energy": 0.3}` | keywords |
| llm: hallucinated genre dropped | PASS | `{"energy": 0.4}` | llm |
| llm: out-of-range energy clamped | PASS | `{"energy": 1.0}` | llm |
| llm: unexpected keys ignored | PASS | `{"mood": "sad"}` | llm |

## Taxonomy impact

Profiles whose top results change when genre/mood taxonomy credit is enabled (8 of 14). Full-credit and hand-tuned pair values are unaffected.

| Profile | Top-5 without taxonomy | Top-5 with taxonomy |
|---|---|---|
| High-Energy Pop | Sunrise City, Rooftop Lights, Laser Cathedral, Gym Hero, Velvet Hours | Sunrise City, Rooftop Lights, Laser Cathedral, Concrete Verses, Gym Hero |
| Deep Intense Rock | Storm Runner, Iron Tide, Gym Hero, Sunrise City, Laser Cathedral | Storm Runner, Iron Tide, Gym Hero, Night Drive Loop, Concrete Verses |
| Conflicted (sad but high-energy) | Hollow Lantern, Winter Nocturne, Rooftop Lights, Storm Runner, Dust Road Home | Hollow Lantern, Night Drive Loop, Winter Nocturne, Rooftop Lights, Dust Road Home |
| Adversarial: wrong-case genre and mood | Sunrise City, Rooftop Lights, Laser Cathedral, Gym Hero, Velvet Hours | Sunrise City, Rooftop Lights, Concrete Verses, Laser Cathedral, Velvet Hours |
| Adversarial: likes_acoustic='no' | Storm Runner, Iron Tide, Gym Hero, Sunrise City, Laser Cathedral | Storm Runner, Iron Tide, Gym Hero, Night Drive Loop, Concrete Verses |
| Numeric acousticness=0.5 | Coffee Shop Stories, Island Breeze, Midnight Coding, Library Rain, Velvet Hours | Coffee Shop Stories, Island Breeze, Midnight Coding, Velvet Hours, Library Rain |
| Adversarial: energy out of range (1.5) | Sunrise City, Laser Cathedral, Rooftop Lights, Gym Hero, Iron Tide | Sunrise City, Laser Cathedral, Rooftop Lights, Gym Hero, Concrete Verses |
| Adversarial: energy='high' (wrong type) | Sunrise City, Rooftop Lights, Laser Cathedral, Gym Hero, Velvet Hours | Sunrise City, Rooftop Lights, Laser Cathedral, Concrete Verses, Velvet Hours |

## Confidence summary

| Measure | Value |
|---|---|
| Profiles scored | 13 of 14 (the rest were rejected as invalid) |
| Confidence HIGH | 7 |
| Confidence MEDIUM | 5 |
| Confidence LOW | 0 |
| Confidence NONE | 1 |
| Mean top score (excluding NONE) | 0.87 |
| Lowest top score (excluding NONE) | 0.62 |
| Profiles relaxed automatically | 0 |
| Profiles flagged NO STRONG MATCH | 0 |

## Beyond-accuracy metrics

Computed over the 12 profiles with usable preferences, top-5 each (the empty profile is excluded: its list is arbitrary). These are informational, not pass/fail. Novelty is not measured (see README).

| Metric | Diversity step ON (default) | Diversity step OFF | What it shows |
|---|---|---|---|
| Catalog coverage (songs shown in any list) | 100% | 94% | Higher = more of the catalog gets a chance |
| Genre coverage | 100% | 93% | Genres that ever appear |
| Intra-list diversity (0-1, sound distance) | 0.161 | 0.141 | Higher = songs in one list sound less alike |
| Distinct artists per list (of 5) | 4.83 | 4.75 | Higher = fewer repeat artists |
| Distinct genres per list (of 5) | 4.33 | 4.00 | Higher = broader lists |
| Exposure share of the 5 most-shown songs | 48% | 55% | Lower = less "popularity" concentration |
| Exposure Gini (0 = even, 1 = one song takes all) | 0.27 | 0.37 | Lower = more even exposure |
| Mean energy of recommended songs vs catalog | 0.69 vs 0.60 | 0.71 vs 0.60 | Gap = lists skew toward loud or quiet songs |
| Serendipity proxy (relevant picks outside the requested genre) | 30 of 48 (62%) | n/a | Relevant = score >= 0.5; proxy only |

Most-shown songs (slots across all profiles): Rooftop Lights (6), Laser Cathedral (6), Concrete Verses (6), Gym Hero (6), Sunrise City (5). Never shown: 0 of 18 songs.

**Total: 80/80 checks passed.**
