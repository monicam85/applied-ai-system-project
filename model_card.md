# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeScorecard 1.0**: a small, explainable music recommender that scores every song against a listener's stated taste.

---

## 2. Goal, Intended Use and Non-Intended Use  

**Goal:** predict which songs a listener will like best. VibeScorecard suggests five songs from an 18-song catalog. It uses the listener's favorite genre, favorite mood, target energy (0 to 1) and how acoustic they want the music. Every suggestion comes with a plain-language list of the points it earned. A person can see exactly why it was chosen.

**Assumptions it makes about the listener:**

- They can describe their taste in one sitting, as a single genre, a single mood and a single energy number. There is no listening history and no "people like you" signal.
- Their taste is one consistent mood. Someone who wants calm songs on Monday and workout songs on Friday would need two separate profiles.
- They type genres and moods exactly as the catalog spells them (lowercase, such as "pop" or "happy").

**Intended use:** this is a classroom exploration. It shows how a content-based recommender turns song attributes into a ranked list. It is good for learning, for testing scoring ideas, and for explaining how recommendations work.

**Non-intended use:** do not use it for real listeners or real products. Do not use it to decide what music gets promoted, paid or hidden. Do not use it to judge anyone's taste. The songs are invented examples. The weights are my own hand-picked judgements, not learned from data. The catalog is too small and too lopsided to treat the results as fair for every kind of listener.

---

## 3. How the Model Works  

Think of it as a judge with a 10-point scorecard. The judge looks at every song in the catalog, one at a time, and asks how well it fits what the listener says they want. The songs with the most points are recommended.

**What the listener tells us:** their favorite genre, their favorite mood, how energetic they want the music (a number from 0 to 1), and how acoustic they want it, either as a yes/no ("likes acoustic") or as a number from 0 to 1. They can optionally add a few extras, such as how upbeat or how recent the music should be.

**How a song earns points:**

- **Energy (up to 3.5 points):** the closer the song's energy is to the listener's target, the more points. A near-perfect match earns almost all 3.5, and a song that is 0.5 or more away earns none.
- **Mood (up to 3 points):** full points if the mood is the same. A close cousin earns a share that depends on the pair: "intense" and "aggressive", or "sad" and "melancholic", earn 90%; "chill" and "relaxed" earn 70%; "happy" and "euphoric" earn 60%. Moods that are not on that hand-picked list fall back to a small taxonomy (`data/taxonomy.json`): two moods in the same group, such as "happy" and "confident" (both "upbeat"), earn 60%, and a few listed neighbours across groups earn 30%. Unrelated moods earn nothing.
- **Acoustic feel (up to 2 points):** closeness to the listener's acousticness target. A yes/no answer becomes a target of 0.8 (acoustic) or 0.2 (electronic); a number is used as given. An answer the system cannot read, such as "maybe", is rejected with an error instead of being guessed.
- **Genre (up to 1.5 points):** full points for the same genre, half points for a neighbor (for example rock and metal, or pop and indie pop). Genres that are not on that hand-picked list fall back to the taxonomy: two genres in the same family (for example hip-hop and reggae, both "groove") also earn half points. Everything else earns none.

Extras only count if the listener asked for them, and the final score is simply points earned divided by points available, so it always lands between 0 and 1. The songs are then sorted from highest to lowest and the top five are picked one at a time. Each pick lowers the score of later songs by the same artist (by 0.20) or from the same sound group (by 0.05), so one artist or one cluster of similar songs cannot take over the list. Each recommendation comes with a plain-language list of why it earned its points.

**Scoring modes:** the recipe above is the default, called "balanced". Three other modes change how many points each feature is worth: "genre-first", "mood-first" and "energy-focused". Only the weights change. The scoring steps are the same. You pick a mode when you run the program (`--mode`), or compare all four (`--compare`).

**Why mood counts for more than genre:** a genre label is a blunt tool, and most genres in this small catalog have only one song. Mood and energy describe how a song actually feels, so they get most of the points. A happy, high-energy song from a neighboring genre can therefore beat a same-genre song with the wrong vibe.

**Changes from the starter logic:** the starter only had empty placeholders. I added the point-based scorecard, a stricter closeness rule (a gap of 0.5 or more earns zero rather than half credit), and the "reasons" list so every recommendation is explainable. After testing I added graded credit for related moods, half credit for related genres, a numeric acousticness target with input checking, and the artist and cluster penalty. In the final stage I added a reliability layer (input repair, confidence rating, relaxation when nothing fits) and the genre and mood taxonomy. I tried and rejected two weight changes (see the README experiments): lowering the mood weight and doubling the energy weight.

---

## 4. Data  

The catalog is [data/songs.csv](data/songs.csv): 18 songs, each with a genre, a mood, and numbers for energy, tempo, valence, danceability, acousticness, instrumentalness, speechiness and release year (1972 to 2024).

**What is represented:** 15 genres and 14 moods, but thin. 13 of the 15 genres and 11 of the 14 moods have exactly one song; lofi (3 songs) and pop (2 songs) are the only genres with more than one. Energy is lopsided: 7 songs are below 0.45, only 3 are between 0.45 and 0.7, and 8 are at 0.75 or above. Mood and energy also move together, since every sad, chill, relaxed or focused song is low energy and every happy, intense, aggressive or euphoric song is high energy. Acousticness is similar, with only 1 song between 0.4 and 0.7.

**Did I add or remove data:** the starter file had 10 songs. I added 8 (ids 11 to 18: r&b, hip-hop, country, classical, metal, reggae, edm and folk) so that more genres and moods exist, and removed none.

**What is missing:** the songs are invented examples, not real recordings, and there is no listening history, language, artist popularity or lyrics. Whole areas of taste are absent or have one song each, such as Latin, K-pop, gospel and heavy electronic subgenres, and there are no mid-energy happy songs or high-energy sad ones.

---

## 5. Strengths  

- **It works well when a listener's tastes line up the way the catalog does.** Chill Lofi gets "Library Rain" (0.98), "Midnight Coding" and "Spacewalk Thoughts", all quiet, slow and acoustic. High-Energy Pop gets "Sunrise City" (0.97) first, a song that matches every one of its preferences. Both lists matched what I would have picked by hand.
- **The two ordinary profiles pull apart cleanly.** Pop and Lofi share no songs, which shows the scorecard really separates a loud, bright taste from a quiet, mellow one.
- **Near misses are treated sensibly.** Songs in neighboring moods and genres earn partial credit, so a lofi fan also sees a calm "focused" lofi track, a chill ambient track and a relaxed jazz track. After I gave each related mood pair its own credit, the Deep Intense Rock list put "Iron Tide" (metal, aggressive) ahead of "Gym Hero" (pop, intense), which matches how a rock fan would hear them.
- **Every recommendation is explainable.** Each result lists the points earned for energy, mood, acoustic feel and genre, which is how I found each of the weaknesses described in this card.
- **It fails safely on bad input.** Scores always stay between 0 and 1, an empty profile says "no preferences provided" rather than inventing a taste, and values it cannot read (such as `likes_acoustic = "maybe"`) are rejected with an error instead of being guessed. The word "no" is read correctly as "not acoustic".
- **The ranking avoids obvious repeats.** A song by an artist who already has a pick in the list, or one from the same sound group, is nudged down, so one artist does not fill the list.
- **It is tested.** Originally 12 automatic tests covered the scoring rules, the related genre and mood credit, the acousticness parsing and the diversity step. The final system has 98 tests plus an 80-check evaluation (see section 7 and section 10).

---

## 6. Limitations and Bias 

Energy and mood move together in my catalog: sad and chill songs are all low energy, and happy and intense songs are all high energy. A "sad but high-energy" listener shows the problem, because "Hollow Lantern" (energy 0.30) wins at 0.62 as the only sad song, even though it earns 0 of the 3.5 energy points. The system never says that nothing fits both wishes, and doubling the energy weight just made a rock song the winner instead. Listeners at the extremes also lose out, since an energy request of 0.1 earns credit from only 10 of 18 songs. The root cause is the tiny catalog, where five loud songs fill 28 of the 60 top-5 slots, so more songs would help more than better weights.

---

## 7. Evaluation  

### Which profiles I tested

I tested 14 listener profiles. I looked at the top 5 songs for each. 12 ran. 2 were refused on purpose.

- **Three ordinary tastes:** High-Energy Pop (pop, happy, energy 0.85, not acoustic). Chill Lofi (lofi, chill, energy 0.35, acoustic). Deep Intense Rock (rock, intense, energy 0.92, not acoustic).
- **Eleven tricky tastes:**
  - Sad but high-energy folk.
  - A metal fan who wants chill music.
  - An acoustic-loving EDM fan.
  - An empty profile.
  - "Pop" and "Happy" typed with capital letters.
  - `likes_acoustic = "no"` typed as a word.
  - A jazz fan with acousticness 0.5.
  - A profile that only names a genre (lofi).
  - Energy set to 1.5, which is off the scale.
  - `likes_acoustic = "maybe"`.
  - Energy typed as the word "high".
- The last two are refused with an error message. That is on purpose.

I also did these checks:

- I ran 12 automatic tests.
- I checked by hand that scores stay between 0 and 1.
- I checked that the points in each "why" list add up.
- I ran four experiments. Each changed one rule. The README has the details.
  1. A lower mood weight.
  2. Double energy and half genre.
  3. A higher flat credit for similar moods.
  4. A separate credit for each pair of similar moods. I kept this one.
- I compared four scoring modes side by side. Each mode flipped at least one result. For example, "genre-first" lifts "Gym Hero" to second place for Happy Pop fans, and "energy-focused" makes a rock song the top pick for the sad folk fan.

### Why "Gym Hero" keeps showing up for "Happy Pop" fans

Think of the recommender as a judge with a scorecard. A Happy Pop fan wants pop, happy, energetic, not acoustic. "Gym Hero" is a pop song. It is very energetic. It is not acoustic at all.

So it earns almost every point. It earns 2.9 points for energy. It earns 1.4 for not being acoustic. It earns 1.5 for being pop. It earns **0 of 3 mood points**. Its mood is "intense", not "happy".

Its total is 0.58 out of 1.00. That is only fourth place. "Sunrise City" scores 0.97. But the catalog has only 18 songs. Only two are pop. There are few other songs to fill the list.

The judge cannot hear the difference between a happy pop song and a workout pop song. It only sees labels and numbers. Loud, electronic songs match many tastes on the numbers. So "Gym Hero" also shows up for rock fans, EDM fans and the "metal fan who wants chill". It appeared in 6 of the 12 lists.

This makes sense for the scorecard. It is not what a real Happy Pop fan wants. A small catalog and number-only rules can repeat the same song.

### What surprised me

- **A few loud songs show up everywhere.** Five songs fill 28 of the 60 top-5 slots. I expected genre to cause this. But genre has the smallest main weight. The real cause is the small catalog.
- **A "sad but high-energy" listener gets a slow song first.** "Hollow Lantern" has energy 0.30. The listener asked for 0.9. It wins at 0.62 because it is the only sad song. Nothing says that no song fits both wishes.
- **Changing the weights barely helped.** A lower mood weight left almost every #1 song the same. A higher flat credit for similar moods did too. What fixed the rock list was a separate credit for each pair of similar moods.
- **Typing "Pop" instead of "pop" quietly breaks things.** The system still returns songs. It gives no warning. The genre and mood points are gone. The top score falls from 0.97 to 0.53.
- **One preference gives a perfect score.** A profile that only says "lofi" gives three songs a score of 1.00. That looks perfect. It only means the one thing I asked for matched.

### Comparing profiles, pair by pair

Every profile appears in at least one pair. In each pair, the profiles differ mostly in one way. So the change in the results shows what that preference controls.

1. **High-Energy Pop vs Chill Lofi.**
   - Pop gets "Sunrise City", "Rooftop Lights" and "Laser Cathedral". These are loud and bright.
   - Lofi gets "Library Rain", "Midnight Coding" and "Spacewalk Thoughts". These are quiet and acoustic.
   - The two lists share no songs.
   - This makes sense. Energy, mood and acoustic feel all point opposite ways. It is the clearest sign that the scorecard separates two tastes.
2. **High-Energy Pop vs Deep Intense Rock.**
   - Both want loud, non-acoustic music. Both lists come from the same pool of loud songs. "Gym Hero" and "Sunrise City" are in both.
   - The order changes. Pop puts the happy songs first. Rock puts the intense songs first: "Storm Runner" and "Iron Tide".
   - This is correct. The only real difference is mood and genre.
3. **Deep Intense Rock vs the `likes_acoustic = "no"` rock profile.**
   - These are meant to be the same taste. Energy is 0.92 and 0.90.
   - The lists are almost the same. "Storm Runner" is first at 0.95 in both. "Iron Tide" scores 0.80 and 0.78. "Gym Hero" scores 0.78 and 0.77.
   - This is what I wanted. The word "no" now means "not acoustic". It used to be read as "yes".
4. **Deep Intense Rock vs the metal fan who wants chill.**
   - Both want loud, non-acoustic music at about the same energy.
   - Rock tops out at 0.95 with "Storm Runner". The metal fan tops out at 0.64 with "Iron Tide". It matches the genre but not the mood.
   - This makes sense. No song is both very loud and chill. The system returns loud songs. The scores honestly drop.
5. **Chill Lofi vs the acoustic-loving EDM fan.**
   - Both say they like acoustic music. The results are opposite.
   - Lofi gets quiet acoustic songs. The EDM fan gets "Laser Cathedral" first. It is almost fully electronic. Its acousticness is 0.03.
   - Genre, mood and energy all match for the EDM fan. Acoustic feel is worth only 2 of 10 points.
   - So the acoustic wish is a weak voice. A real listener may not want that.
6. **The acoustic-loving EDM fan vs the "sad but high-energy" folk fan.**
   - Both want loud (0.9 to 0.95) and acoustic music. The EDM fan gets a loud song first. The folk fan gets a quiet one.
   - The cause is the catalog, not the wishes. EDM has a song that is loud and euphoric. The only sad song is slow.
   - The folk fan's wish for sad and loud cannot be met. This is the weakness in Section 6.
7. **Chill Lofi vs the jazz fan with acousticness 0.5.**
   - Both like mellow music. The jazz fan wants middle energy (0.5) and middle acoustic feel.
   - The jazz list moves to "Coffee Shop Stories" (jazz) and "Island Breeze" (reggae, middle energy). It adds a few lofi songs.
   - The best score is 0.75, not 0.98.
   - This makes sense. Few songs sit in the middle. A middle taste has fewer near-perfect matches than a taste at one end.
8. **High-Energy Pop vs the capital-letter "Pop" and "Happy" profile.**
   - This is the same taste. The capital letters cost all the genre and mood points. The system compares text exactly.
   - "Sunrise City" is still first. Its score falls from 0.97 to 0.53. "Concrete Verses" (hip-hop, confident) jumps to second.
   - This result is not valid for a real user. A real user expects "Pop" to mean pop. It is a weakness, not good behavior.
9. **High-Energy Pop vs the energy 1.5 profile.**
   - Same genre and mood. The only change is that 1.5 is beyond every song.
   - The first two songs stay the same: "Sunrise City" and "Rooftop Lights". Mood and genre still count.
   - The top score drops from 0.97 to 0.64. The rest of the list gets weaker.
   - The system falls back on the other wishes. That is sensible. But it never tells the user the energy request was impossible.
10. **The empty profile vs the lofi-only profile.**
    - With nothing to go on, every song scores 0.00. The list is just the first songs in the file. "Sunrise City" is first.
    - With only "lofi", three lofi songs score 1.00. The ambient and jazz songs get 0.50 for being neighbors of lofi.
    - This follows the rules. But it shows how little a score means when almost nothing was asked. A 1.00 here does not mean "perfect for you".

### What I trust and what I do not

I trust the system when a taste matches how the catalog is built. Loud and happy works. Quiet and chill works.

I do not trust it in three cases. The first is a taste that crosses the line between low-energy and high-energy moods. The second is a preference typed with different capital letters. The third is a profile with only one or two preferences. The score looks confident in all three.

I still have no accuracy number, because there are no real listener ratings to compare against. What I do have is automated checking of properties that should always hold: `python -m src.evaluate` runs 80 checks (scores stay within 0 to 1, the right number of results comes back, no artist repeats more than twice, results are deterministic, each profile earns the expected confidence level, and a model reply with bad JSON or an invented genre is handled), and 98 unit tests cover the rest. These show the system behaves safely and consistently. They do not show that the picks are the ones a listener would enjoy. That judgement still comes from comparing the results to what I would expect to hear.

### Reliability and beyond-accuracy results

**Summary:** 98 of 98 unit tests and 80 of 80 evaluation checks pass. Across the 13 profiles the scorer accepts, confidence was 7 HIGH, 5 MEDIUM, 0 LOW and 1 NONE, with a mean top score of 0.87 (lowest 0.62). The system struggled when context was missing or contradictory: the empty profile gets NONE, and the contradictory "metal fan who wants chill" profile still earns MEDIUM. The relax and NO STRONG MATCH paths never fire on the 14 built-in profiles (none scores LOW), so unit tests are the only thing exercising them. No human or peer evaluation has been done; all of these results are automated. The full parseable tables (per-profile checks, request-parsing cases, confidence summary and the metrics below) are in the README under "Testing summary" and are regenerated into `reports/evaluation_report.md` by `python -m src.evaluate`.

Beyond-accuracy metrics (12 profiles with usable preferences, top 5 each, diversity step on versus off):

| Metric | Diversity step ON | Diversity step OFF |
|---|---|---|
| Catalog coverage | 100% | 94% |
| Distinct genres per list (of 5) | 4.33 | 4.00 |
| Share of list slots taken by the 5 most-shown songs | 48% | 55% |
| Exposure Gini | 0.27 | 0.37 |
| Serendipity proxy (relevant picks outside the requested genre) | 62% (30 of 48) | not measured |

**Which of diversity, novelty, serendipity, coverage and popularity bias are worth testing here:** diversity and coverage directly (the system has a diversity penalty, and the original evaluation found five songs filling 28 of 60 slots). Popularity bias only as an analogue, *exposure concentration*, because the songs are invented and have no popularity data. Serendipity only as a proxy, because there is no listening history to say what a listener expected. Novelty not at all: it needs per-listener history or popularity, and with one song for 13 of 15 genres a genre-rarity stand-in would be meaningless. The serendipity figure is inflated by that same one-song-per-genre structure.

### Specialization: baseline vs specialized output

The baseline is the keyword parser. The specialized parser is the optional hybrid (keyword rules first, then embedding prototypes, one exemplar phrase set per mood, with similarity cut-offs tuned on half of a 36-request labelled benchmark). No model weights are trained; the specialization is exemplars plus tuning. "Both correct" means the mood and the energy band are both acceptable against the labels.

| Parser | Held-out half, both correct | Mood | Energy | All 36 requests |
|---|---|---|---|---|
| keywords | 67% | 72% | 78% | 58% |
| embeddings | 50% | 67% | 83% | 61% |
| hybrid | 83% | 83% | 100% | 83% |

Their outputs differ on 18 of 36 requests; the specialized parser fixes 9, breaks none, and still gets 4 wrong. A sample, including two it gets wrong (the full list is in `reports/parser_benchmark.md`):

| Request | Baseline (keywords) | Specialized (hybrid) | Baseline | Specialized |
|---|---|---|---|---|
| music to unwind after a long day | `{}` | `{"mood": "relaxed", "energy": 0.15}` | wrong | right |
| songs that make me want to dance all night | `{"energy": 0.85}` | `{"mood": "euphoric", "energy": 0.85}` | wrong | right |
| I'm heartbroken | `{}` | `{"mood": "sad"}` | wrong | right |
| wistful memories of my childhood | `{}` | `{"mood": "nostalgic"}` | wrong | right |
| fast and loud | `{}` | `{"mood": "intense", "energy": 0.93}` | wrong | right |
| feel-good summer vibes | `{}` | `{"mood": "chill", "energy": 0.8}` | wrong | wrong |
| slow and gentle | `{}` | `{"mood": "romantic", "energy": 0.3}` | wrong | wrong |

For reference, the live Claude parser scored 100% on the held-out half and 97% overall in one run (no tuning, no fallbacks); it is the most accurate option but needs a paid key, adds latency and varies between runs, so it is the optional front end, not the default.

Caveats: 36 requests is small; the benchmark was drafted by Claude Code before any model ran and its labels have one author; it is weighted toward paraphrases (14 of 36), which the keyword rules were never built for; and it measures request parsing, not whether listeners get better recommendations.

### Multi-source retrieval: before and after

Ranking draws on two sources, `songs.csv` and, as a fallback for pairs the hand-tuned tables do not list, `taxonomy.json`. Adding the second source changes the top 5 for 8 of the 14 profiles. Three examples (all are in `reports/evaluation_report.md`):

| Profile | Top 5 without the taxonomy | Top 5 with the taxonomy |
|---|---|---|
| High-Energy Pop | Sunrise City, Rooftop Lights, Laser Cathedral, Gym Hero, Velvet Hours | Sunrise City, Rooftop Lights, Laser Cathedral, Concrete Verses, Gym Hero |
| Deep Intense Rock | Storm Runner, Iron Tide, Gym Hero, Sunrise City, Laser Cathedral | Storm Runner, Iron Tide, Gym Hero, Night Drive Loop, Concrete Verses |
| Conflicted (sad but high-energy) | Hollow Lantern, Winter Nocturne, Rooftop Lights, Storm Runner, Dust Road Home | Hollow Lantern, Night Drive Loop, Winter Nocturne, Rooftop Lights, Dust Road Home |

This is a change in output, not a measured gain: there are no listener ratings to say whether the new results are better.

### How the taxonomy was checked

Turning the taxonomy on changes the top 5 for 8 of the 14 profiles (before-and-after lists are in `reports/evaluation_report.md`), so it needed more than a glance. I borrowed an idea from ontology evaluation, where a vocabulary is tested by whether it can answer a list of "competency questions" (Rashid, De Roure and McGuinness, "A Music Theory Ontology", SAAM 2018; that paper is about notes and chords, which this project does not use, but the testing approach carries over). Each question is a test in `tests/test_taxonomy.py`, for example: which genres share a family with a given genre, does every label sit in exactly one group, is similarity symmetric and below 1.0 unless the labels match, do opposite moods such as sad and euphoric earn nothing, and do the arousal and valence tags I gave each mood group agree with the measured energy and valence of the songs in it. The last one is the only check against data. The family and cluster groupings, and the credit values, are still my judgement.

---

## 8. Ideas for Improvement  

1. **Add many more songs.** Most problems I found come from having only 18 songs. Five loud songs fill 28 of 60 top-5 slots, and 13 of 15 genres have one song. Hundreds of songs, with some sad high-energy and happy mid-energy tracks, would help more than any weight change.
2. **Say so when nothing fits (done).** The reliability layer now rates confidence and prints NO STRONG MATCH, or relaxes the profile. Original note: if the best score is low, or the request conflicts (like "sad" with energy 0.9), the output should say "closest I could find". Right now it shows the same confident list.
3. **Accept messier input (done).** Input is now cleaned and out-of-range values are clamped with a note. Original note: ignore capital letters and extra spaces, so "Pop" means "pop". Reject energy values outside 0 to 1 with a clear message.

**Smaller ideas:** let a listener give an energy range or two moods. Use tempo and danceability, which are in the data but unused. Learn which moods and genres are similar from real listening data instead of my guesses. Add a one-sentence summary above the points list, such as "close on energy, but not the mood you asked for."

---

## 9. Personal Reflection  

### My biggest learning moment

The weights were not the lever. I wanted "Iron Tide" to rank above "Gym Hero" for a rock fan. I lowered the mood weight. I doubled the energy weight. I raised the flat credit for similar moods. None of it fixed the problem. When I worked out the points by hand, I saw why. An exact mood match is worth much more than a related one, and one global number cannot fix one pair without loosening all the others. Giving each pair of similar moods its own credit fixed it. The bigger lesson is that a recommender is a chain of judgement calls. Which features count, how much each is worth and which moods are neighbors are all my choices. The results are only as good as those choices and the catalog behind them.

### How AI tools helped, and when I had to double-check them

I used Claude Code through the whole project. It wrote the tricky test profiles and ran them. It ran each experiment in a scratch script, so my code stayed unchanged until I chose to keep something. It also checked that scores stay between 0 and 1 and helped write the docs. That saved a lot of time.

Its predictions were often wrong, so I checked each one against the real output. Here are four examples:

- It said a genre similarity map would fix "Gym Hero" over "Iron Tide". It did not.
- It said a mood credit of 0.75 would flip the rock list. The credit had to be about 0.9 or more.
- It guessed that a chill song might beat "Iron Tide" for the metal fan. It did not.
- Its first variety rule, a hard cap per cluster, pushed weak filler songs into many lists. I replaced it with a gentler penalty.

One automatic check also flagged two "failures" that were only rounding. I only trusted a claim after the run or the arithmetic agreed with it. When an experiment was not better, I reverted it and wrote down why.

### What surprised me about simple algorithms

Four simple rules were enough to feel like real recommendations. The Chill Lofi list looked like a playlist I would make myself. A score of 0.97 felt like the system understood me. The "why" list made it feel even more convincing. But the system only compares numbers and labels. It cannot tell a happy pop song from a workout pop song. That is why "Gym Hero" kept appearing. It also gave a sad, high-energy listener a slow song with no warning. A confident-looking list can hide how little the system knows.

### What I would try next

1. Add many more songs, with some sad high-energy and happy mid-energy tracks. Most of my problems came from having only 18.
2. Make the system say "closest I could find" when nothing fits a listener's taste. (Done in the final system: confidence rating, relaxation and NO STRONG MATCH.)
3. Ignore capital letters, so "Pop" means "pop". (Done: input is normalized.)
4. Learn which moods and genres are similar from real listening data. My 0.9 for intense and aggressive was tuned to one test, so I would check it on a second dataset.

---

## 10. Responsible AI Reflection (final system)

Sections 1 to 9 describe the original recommender and my first evaluation. This section covers the final system: the scorer plus the genre/mood taxonomy, the reliability layer, and the optional Claude natural-language front end.

### 10.1 Limitations and biases

- **A tiny, invented, lopsided catalog.** There are 18 made-up songs. 13 of 15 genres and 11 of 14 moods have one song, and in my original 12-profile evaluation the same five loud songs filled 28 of 60 top-5 slots. The system serves the tastes the catalog happens to contain; a listener who wants something it lacks gets a weak match.
- **Mood and energy move together in the data**, so a contradictory request (sad but high-energy, or a metal fan who wants "chill") has no good answer. The reliability layer lowers the confidence, but only partly: the rating depends only on the best song's score and how many preferences were given. The metal-fan-who-wants-chill profile still earns **MEDIUM** with the note "best match scored only 0.64", and the system never says that the request contradicts itself.
- **The taxonomy encodes my viewpoint, and a Western, English-language one.** I grouped 15 genres into 7 families and 14 moods into 5 clusters. Groupings such as putting reggae with hip-hop and r&b, or jazz with classical, are judgement calls, and whole traditions (Latin, K-pop, gospel, regional folk) are absent. Naming groups is also a value judgement: my first label for the jazz/classical family was "art", which implies other genres are not, so I renamed it "instrumental". The credit values (0.5, 0.6, 0.3) are guesses. I checked the mood clusters' arousal and valence tags against the catalog's measured energy and valence, but not against what listeners hear. One tag was wrong at first: I had tagged the "wistful" cluster (nostalgic, romantic) with mixed valence, but its songs measure 0.66 and 0.68 and a source I consulted (section 10.5) places nostalgia and tenderness at positive valence and low arousal, so I corrected it and linked the "relaxed" mood to "nostalgic" and "romantic" as neighbours.
- **Hand-picked weights.** Every scoring weight and similarity credit is my judgement, and one (intense/aggressive at 0.9) was tuned to a single test case.
- **The offline keyword parser is crude.** It never reads genre words. It knows only a few goal phrases ("cheer me up", "wake me up", "calm me down", "help me focus") and skips negated words ("not sad" gives no mood) instead of understanding them. It had a substring bug ("brunch" matched "run"), which I fixed with word-start matching.
- **The optional embedding parser is measured on a small, author-labelled benchmark.** On 36 hand-labelled requests the hybrid parser (rules first, embeddings fill gaps) scored 83% on the held-out half against 67% for the keyword rules, but the benchmark was drafted by Claude Code before any model ran, has one set of labels that no second person has reviewed, and is weighted toward paraphrases (14 of 36), which the keyword rules were never built to handle. It measures parsing, not recommendation quality. The embedding model also inherits whatever associations it learned from its training text, which I have not audited, and sentence embeddings cannot read goals or negation, which is why the rules stay in charge of those.
- **The lexicon cross-check is a small outside check, not proof.** The NRC-VAD ratings come from crowd workers rating English words, so they reflect that population's sense of how a word feels; the lexicon's authors note that such resources carry the biases of their raters. Only 12 of my 14 mood words are in it, and it validates the groupings, not the credit values.
- **Moods describe what a song conveys, but requests describe what a listener wants.** The music emotion recognition literature separates perceived emotion (what the music itself conveys) from induced emotion (what it provokes in the listener) (Han et al., 2022). Our catalog moods are perceived labels, while "cheer me up" names an induced state, so the request parsers translate goals into target moods, imperfectly. The same survey stresses that emotion is subjective, that one valence-arousal quadrant holds several distinct emotions, and that public datasets are small and skewed toward a few genres, all of which apply here. Our 14 moods also have no equivalent of the "amazement" and "solemnity" categories in the Geneva Emotional Music Scales, and the features include no key or mode.
- **The Claude path is measured only once, on a small benchmark.** In one live run on the 36-request benchmark it scored 97% overall and 100% on the held-out half, with no fallbacks. Its one miss was returning no preferences for "I'm heartbroken", on three tries out of three: a conservative reading of my prompt, which tells it to omit anything the request gives no evidence for, not an error. Its output varies between runs (one request gave energy targets of 0.30, 0.35 and 0.40), the benchmark is small, one-author and weighted toward paraphrases, and Claude's mapping from phrases to moods could carry biases I have not audited (what counts as "mellow", or who "study music" is for).
- **Plausible-looking explanations can create false trust.** The "why" list reads like understanding, but the system only compares numbers and labels; it knows nothing about lyrics, language, culture, popularity or listening history.
- **No fairness measure for artists.** The only exposure control is a per-list penalty that stops one artist or sound cluster dominating a single list. The artists are invented, so nothing here shows how it would treat real, unequally popular artists.
- **No accuracy measure.** There are no listener ratings. My 80 checks and 98 tests show the system behaves safely and consistently, not that its picks are good.

### 10.2 Could this AI be misused, and how could it be prevented?

It is a classroom-scale recommender, so the realistic harms are small, but the patterns carry over to real systems.

- **Abuse of the free-text `--ask` input.** Text goes to an LLM, so someone could try prompt injection or send huge inputs to run up cost. *What is in place:* the reply is only ever parsed as JSON, restricted to five known keys, clamped, and checked against the catalog's real genres and moods, so an injected instruction cannot change anything but those five values; the model has no tools; input is cut at 500 characters; calls time out after 20 seconds with one retry. *Not in place:* rate limiting, authentication and a spending cap. Before exposing this as a public service I would add all three.
- **Making a biased ranking look neutral.** Someone could tune the weights or the catalog to push particular songs or artists while the "why" list makes the result look objective. *Prevention:* keep the weights and taxonomy in plain, reviewable files, record changes in version control, report how a change shifts the rankings (the evaluation report's taxonomy section does this), and state in the model card that the weights are judgements.
- **False authority.** A confident-looking score could be used to justify decisions about people or about which music gets paid, promoted or hidden. *Prevention:* the confidence rating, the NO STRONG MATCH result, the intended-use and non-intended-use statements in section 2, and not using this on real listeners or products.
- **Supply chain for the optional model.** `--embeddings` downloads a model from Hugging Face on first use. The package version is pinned in `requirements-embeddings.txt`, but the model is requested by name, not by a fixed revision, so the file could change upstream. Before any real deployment I would pin an exact revision, and I would keep the option off by default as it is now. The model is not redistributed in this repository.
- **Privacy.** The log records each request's text (`logs/app.log`) along with the parsed preferences. The log is git-ignored and local, but a multi-user deployment would need redaction, a retention limit and notice to users. The API key is read from an environment variable, is never logged or written to a file, and `.env` is git-ignored.

### 10.3 What surprised me while testing reliability

- **The taxonomy's effect was bigger than I expected.** I described it as a small fallback for pairs my tables did not list, but it changed the top five for **8 of the 14 profiles**. That is why the evaluation report now lists the before-and-after results for each changed profile.
- **A perfect 76/76 hid real problems.** After every automated check passed, trying odd inputs by hand turned up three bugs: `--ask ""` silently ran the 14 default profiles, an unintelligible request printed an arbitrary ranking, and "brunch playlist" was read as high-energy. The checks only cover what I thought to test.
- **The confidence rating is easy to fool.** Because it looks only at the best score, one song that matches the energy exactly can carry a contradictory request to MEDIUM. I had assumed it would flag contradictions.
- **The first live API call found a bug no offline test could.** I had tested the Claude path only with a fake client. The real model's reply began with a "thinking" block that has no `.text`, so the parser crashed and quietly fell back to the keyword rules; everything still looked fine in the output. I fixed it (the parser reads the text blocks, with more token headroom) and added tests that use that exact reply shape. Going live also showed that the evaluator and some tests would have made real API calls whenever a key was set, so they now remove the key for their duration.
- **The original crashes were the easy part.** Turning `likes_acoustic="maybe"` and `energy="high"` into clear messages took little effort; making the system sound appropriately unsure was harder, and is still incomplete.
- **A basic setup mismatch.** `pyproject.toml` required Python 3.14 and declared no dependencies, while the README said 3.11 and `requirements.txt` listed two. I only found it by checking the setup from a clean copy.

### 10.4 My collaboration with AI

I used Claude Code throughout: it wrote and ran test profiles and experiments, built the reliability layer, the taxonomy and the evaluation harness, and drafted the documentation. The taxonomy's groupings and credit values were drafted by Claude and are checked only against the catalog data, not against listeners. As in section 9, I treated its claims as predictions to verify against real output.

**One suggestion I accepted: delete the out-of-date architecture diagram.** After the system gained the reliability layer, the taxonomy and the evaluator, Claude pointed out that `assets/architecture.png` was a screenshot of the original design (scorer only), that nothing in the README linked to it, and that a reader could mistake it for the current system. It proposed replacing it with a text-based diagram, `diagrams/architecture.mmd`, that shows the real components, the data flow and where humans and tests check the AI, and then deleting the stale image. I agreed because a wrong diagram is worse than none, and a Mermaid source file can be read, diffed and kept in sync with the code. Claude also checked the new diagram with Mermaid's own parser before I relied on it.

**One suggestion I did not adopt as written: building an ontology.** I shared an Oxford paper, "A Music Theory Ontology", and asked whether it could help. The fetch tool Claude used could not read the PDF and returned nothing usable, so it extracted and decoded the text itself and listed what might transfer. The full ontology route (an RDF/OWL class hierarchy with labels, queried and reasoned over with Semantic Web tools) was not a good fit, so I rejected it. The paper is about notes, scales and chords, and my catalog has none of those, only labels and a few numbers. A formal ontology would have been over-engineered and harder for a reader to follow than a small JSON file and a loader, and it would not have improved a single recommendation. I kept only the part that fit: testing the taxonomy with **competency questions**, each a plain pytest test, such as "does every label belong to exactly one group?" and "do opposite moods like sad and euphoric earn nothing?". I also did not add the paper's idea of alternative (synonym) labels, because the keyword parser's word lists already cover what I need.

**Where I had to check its work.** Beyond the examples in section 9, the keyword-parser bug above came from probing the parser with everyday phrases, not from the tests that already existed. When Claude fixed it, its first edit broke three existing checks because a regex escape was written incorrectly, and the failing tests and the evaluation run showed it immediately. I trusted the fix only once the full suite and the 76 checks passed again.

### 10.5 Sources consulted and how they were used

Two published sources were reviewed for whether they could improve the system. I used what the evidence supports and left the rest out.

| Source | What I took from it | What I did not use |
|---|---|---|
| Habibi & Damasio (2014), "Music, Feelings, and the Human Brain", *Psychomusicology* 24(1) | Moods sit on arousal and valence dimensions, and positive-valence, low-arousal music covers peacefulness, tenderness and nostalgia (Trost et al., 2012, as cited there). That led to the corrected "wistful" tag and the new relaxed/nostalgic and relaxed/romantic neighbours. Juslin (2000), as cited there, says sad music tends to be slow and fear-like music faster; the catalog agrees (sad and melancholic songs run 56 to 70 bpm, intense and aggressive ones 132 to 168), so a test now checks it. The review also notes that most studies used Western classical music and that familiarity and training change responses, which supports the Western-centric and no-listener-history limitations above. | The neuroscience (brain regions, dopamine, the feelings-versus-emotions distinction). It gives no mapping from song features to mood, so it cannot validate the weights or credit values. |
| Schäfer, Sedlmeier, Städtler & Huron (2013), "The psychological functions of music listening", *Frontiers in Psychology* 4:511 | In a survey of 834 people, arousal and mood regulation was the most-endorsed reason for listening (mean 3.78 of 6, against 3.59 for self-awareness and 2.01 for social relatedness). That supports giving mood and energy most of the points, and it motivated reading a request as the state the listener wants ("I'm sad, cheer me up" means happy) in both the Claude prompt and the keyword fallback. | Any claim that it predicts preference: it surveys motivations and analyzes no tempo, mode, energy or genre. The sample was mostly young and German-speaking, so I did not use it to personalize by age or gender. |

Neither source was used to change scoring weights. Tempo is still not part of the score; using it would change rankings and needs its own measured experiment.

Two further resources were used afterwards, one as a check and one as an option:


| Resource | What I used it for | Terms and limits |
|---|---|---|
| NRC Valence, Arousal, and Dominance Lexicon v2.1 (Saif M. Mohammad, National Research Council Canada) | An outside check on the mood taxonomy (`python -m src.lexicon_check`): cluster tags agree with the ratings on both axes, same-cluster moods are closer than different-cluster ones (0.79 vs 1.21), hand-credited close-mood pairs are closer than other pairs (0.61 vs 1.19), and the ratings rank moods like the catalog's songs (Spearman +0.76 for valence, +0.81 for arousal). | Free for non-commercial research and education; the data may not be redistributed, so it is not in the repository (git-ignored `data/external/`) and each user downloads it from the [NRC page](https://saifmohammad.com/WebPages/nrc-vad.html). Only aggregates are reported. Credit: this project makes use of the NRC VAD Lexicon, created by Saif M. Mohammad at the National Research Council Canada. |
| Sentence-Transformers `all-MiniLM-L6-v2` (optional) | The embedding half of the optional hybrid request parser. | Downloaded on demand and not redistributed; its license is stated on its Hugging Face page and should be checked before any redistribution. Adds about 1.2 GB of packages and a ~175 MB model. |
| Han, Kong, Han & Wang (2022), "A survey of music emotion recognition", *Frontiers of Computer Science* 16(6):166335 | (1) Russell's valence-arousal model is the most commonly used dimensional emotion model in the field, which matches our arousal and valence tags. (2) Our five clusters resemble the categories of the two music emotion models it describes: calm is like Hevner's "serene" and GEMS "calmness", upbeat like "happy" and "joyful activation", intense like "vigorous" and GEMS "power" and "tension", downcast like "sad" and "sadness", and wistful like GEMS "tenderness" and "nostalgia". This is a qualitative resemblance, not a test. (3) The perceived-versus-induced emotion distinction explains why requests such as "cheer me up" need separate handling from mood labels. (4) For scale only: audio-based mood classification in the MIREX competition has stayed at roughly 61% to 70% accuracy for a decade (its Table 13), on a different task and data, so my 83% on a 36-request parsing benchmark should not be compared with it or read as strong. | Its deep-learning, audio, lyric and EEG methods, because the catalog has no audio or lyrics. It reports no results for a setting like this one. It also points to what is missing here: GEMS categories for awe (amazement, solemnity), key and mode as features, and public datasets with valence-arousal annotations and audio (DEAM, AMG1608, MediaEval) that could replace the invented catalog or test the mood-to-valence-and-energy mapping in future work. I did not check those datasets' licenses. |

I considered but did not use a music-audio or music-text model (CLAP-style, MERT, Essentia classifiers): the catalog is invented and has no audio, so there is nothing for such a model to listen to. I also did not use word embeddings to compute mood similarity, because opposites such as "sad" and "happy" often sit close together in embedding space; the lexicon's explicit valence and arousal ratings are a better check.

### 10.6 Future improvements

In the order I would do them:

1. **Replace the invented catalog.** Eighteen made-up songs are the root of most limitations. Public datasets with audio and valence-arousal annotations exist (DEAM, AMG1608, MediaEval; I did not check their licenses). They would also let me test the mood-to-valence-and-energy mapping against real annotations instead of only the lexicon.
2. **Flag contradictory requests.** The confidence rating looks only at the best score, so "a metal fan who wants chill" earns MEDIUM. A check that notices when the stated moods and energies cannot co-occur in the catalog would say why, not just how sure.
3. **A second labeller and a larger benchmark** for the request parsers, so the 83% against 67% result can be trusted or corrected, plus repeated live runs of the Claude path (so far there is one run, and its output varies).
4. **Use more of the features.** Tempo (sad songs here run slower than intense ones) and key or mode are in or near the data but not in the score. Any change that alters rankings needs its own measured experiment.
5. **Grounded explanations** (a real retrieval-augmented step): have a model write each "why" sentence from the retrieved catalog row and taxonomy entry, with a validator that rejects claims not in those fields.
6. **Pin the optional embedding model to an exact revision** and add per-listener history so novelty and true serendipity can be measured rather than skipped.
