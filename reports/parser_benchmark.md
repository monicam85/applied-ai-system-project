# Request-parser benchmark

36 hand-labelled requests (18 tuning, 18 held-out test) from `data/nl_benchmark.json`. Both-correct = mood acceptable AND energy band acceptable. Small sample: treat gaps of a few points as noise.

- embeddings thresholds chosen on the tuning split: mood 0.45, energy 0.3
- hybrid thresholds chosen on the tuning split: mood 0.45, energy 0.3
- claude row: live calls to the Claude parser in src/nl_query.py (not tuned on this benchmark)

| Method | Held-out test: both correct | Test mood | Test energy | Overall both correct |
|---|---|---|---|---|
| keywords | 67% | 72% | 78% | 58% |
| embeddings | 50% | 67% | 83% | 61% |
| hybrid | 83% | 83% | 100% | 83% |
| claude | 100% | 100% | 100% | 97% |

Both-correct by request type (all 36 cases; correct / total):

| Method | energy-only | goal | keyword-friendly | negation | no-information | paraphrase |
|---|---|---|---|---|---|---|
| keywords | 1/4 | 6/6 | 5/5 | 2/3 | 4/4 | 3/14 |
| embeddings | 3/4 | 2/6 | 4/5 | 1/3 | 4/4 | 8/14 |
| hybrid | 3/4 | 6/6 | 5/5 | 3/3 | 4/4 | 9/14 |
| claude | 4/4 | 6/6 | 5/5 | 3/3 | 4/4 | 13/14 |

Cases each method gets wrong:

- **keywords** (15): "music to unwind after a long day"; "something for a rainy Sunday morning"; "songs that make me want to dance all night"; "soundtrack for a late night drive"; "music to fall asleep to"; "I'm heartbroken"; "feeling pumped and fired up"; "something to get lost in while I code"; "furious, I need to scream along to something"; "feel-good summer vibes"; "wistful memories of my childhood"; "not too intense please, something gentle"; "very high energy"; "fast and loud"; "slow and gentle"
- **embeddings** (14): "pump-up music for the gym"; "something for a rainy Sunday morning"; "songs that make me want to dance all night"; "soundtrack for a late night drive"; "feeling pumped and fired up"; "something to get lost in while I code"; "feel-good summer vibes"; "I'm sad, cheer me up"; "cheer me up"; "wake me up"; "help me focus on my essay"; "I don't want anything sad"; "nothing aggressive"; "slow and gentle"
- **hybrid** (6): "something for a rainy Sunday morning"; "soundtrack for a late night drive"; "feeling pumped and fired up"; "something to get lost in while I code"; "feel-good summer vibes"; "slow and gentle"
- **claude** (1): "I'm heartbroken"

## Where the specialized parser (hybrid) differs from the baseline (keywords)

Every benchmark request where the two outputs differ. Judged against the labels in `data/nl_benchmark.json` (mood acceptable and energy band acceptable).

| Request | Baseline output | Specialized output | Baseline | Specialized |
|---|---|---|---|---|
| a sad song | `{"mood": "sad"}` | `{"mood": "sad", "energy": 0.15}` | right | right |
| happy upbeat music | `{"mood": "happy"}` | `{"mood": "happy", "energy": 0.8}` | right | right |
| music to unwind after a long day | `{}` | `{"mood": "relaxed", "energy": 0.15}` | wrong | right |
| songs that make me want to dance all night | `{"energy": 0.85}` | `{"mood": "euphoric", "energy": 0.85}` | wrong | right |
| soundtrack for a late night drive | `{}` | `{"energy": 0.15}` | wrong | wrong |
| music to fall asleep to | `{}` | `{"mood": "relaxed", "energy": 0.15}` | wrong | right |
| I'm heartbroken | `{}` | `{"mood": "sad"}` | wrong | right |
| feeling pumped and fired up | `{}` | `{"energy": 0.8}` | wrong | wrong |
| a romantic dinner playlist | `{"mood": "romantic"}` | `{"mood": "romantic", "energy": 0.8}` | right | right |
| furious, I need to scream along to something | `{}` | `{"mood": "aggressive", "energy": 0.93}` | wrong | right |
| feel-good summer vibes | `{}` | `{"mood": "chill", "energy": 0.8}` | wrong | wrong |
| wistful memories of my childhood | `{}` | `{"mood": "nostalgic"}` | wrong | right |
| not too intense please, something gentle | `{}` | `{"energy": 0.3}` | wrong | right |
| nothing aggressive | `{}` | `{"energy": 0.3}` | right | right |
| very high energy | `{}` | `{"mood": "intense", "energy": 0.93}` | wrong | right |
| quiet background music | `{"energy": 0.2}` | `{"mood": "relaxed", "energy": 0.2}` | right | right |
| fast and loud | `{}` | `{"mood": "intense", "energy": 0.93}` | wrong | right |
| slow and gentle | `{}` | `{"mood": "romantic", "energy": 0.3}` | wrong | wrong |

Outputs differ on 18 of 36 requests: the specialized parser fixes 9, breaks 0, and the rest are different but equally right or equally wrong.

## Claude parser notes

Live results from the Claude model named in `src/nl_query.py`. Model output can vary from run to run, so these numbers describe this run, not a guarantee.

- Requests where the live call failed and the keyword fallback answered instead: 0 of 36
