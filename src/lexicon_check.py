"""
Cross-checks the mood taxonomy against an independent source: the NRC
Valence-Arousal-Dominance (NRC-VAD) Lexicon, in which people rated how positive
(valence) and how energetic (arousal) each English word feels, on a -1 to 1 scale.

It asks four questions, none of which uses the catalog to define the answer:
  1. Do the arousal/valence tags on each mood cluster agree with the word ratings?
  2. Are moods in the same cluster closer together in valence-arousal space than
     moods in different clusters (is the clustering coherent)?
  3. Do the hand-tuned "close mood" pairs sit closer together than other pairs?
  4. Do the word ratings rank the moods the way the catalog's measured song
     features do (valence vs song valence, arousal vs song energy)?

The lexicon is NOT part of this repository. Its terms allow free non-commercial
research and educational use but forbid redistribution, so each user downloads it
from the NRC home page (https://saifmohammad.com/WebPages/nrc-vad.html) into
data/external/ (git-ignored). The report prints only aggregates, never the
lexicon's per-word values.

    python -m src.lexicon_check [--lexicon PATH]    # writes reports/taxonomy_lexicon_check.md

This tool makes use of the NRC VAD Lexicon (v2.1), created by Saif M. Mohammad at
the National Research Council Canada.
"""

import argparse
import statistics
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from . import taxonomy
    from .main import SONGS_CSV
    from .recommender import MOOD_SIMILARITY, load_songs
except ImportError:
    import taxonomy
    from main import SONGS_CSV
    from recommender import MOOD_SIMILARITY, load_songs

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = (ROOT / "data" / "external" / "NRC-VAD-Lexicon-v2.1" / "Unigrams"
                   / "unigrams-NRC-VAD-Lexicon-v2.1.txt")
REPORT = ROOT / "reports" / "taxonomy_lexicon_check.md"
HOME_PAGE = "https://saifmohammad.com/WebPages/nrc-vad.html"

# Spellings tried, in order, when a mood word is not in the lexicon as written.
VARIANTS = {"laid-back": ["laid-back", "laid back", "laidback"]}


def load_lexicon(path: Path) -> Dict[str, Tuple[float, float]]:
    """Reads a tab-separated term, valence, arousal, dominance file into {term: (valence, arousal)}."""
    scores: Dict[str, Tuple[float, float]] = {}
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        if header[:3] != ["term", "valence", "arousal"]:
            raise ValueError(f"{path}: unexpected header {header}")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                scores[parts[0]] = (float(parts[1]), float(parts[2]))
    return scores


def mood_scores(moods: Sequence[str], lexicon: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    """(valence, arousal) for each mood found in the lexicon; moods it lacks are left out."""
    out = {}
    for mood in moods:
        for spelling in VARIANTS.get(mood, [mood]):
            if spelling in lexicon:
                out[mood] = lexicon[spelling]
                break
    return out


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _ranks(values: Sequence[float]) -> List[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1  # average rank for ties
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Spearman rank correlation; None if fewer than 3 points or no variation."""
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def cluster_tag_check(scores: Dict[str, Tuple[float, float]], clusters: Dict[str, dict]) -> List[Tuple[str, bool, str]]:
    """Question 1: do cluster arousal/valence tags order the clusters like the word ratings do?"""
    means = {}
    for name, cluster in clusters.items():
        pts = [scores[m] for m in cluster["members"] if m in scores]
        if pts:
            means[name] = (statistics.mean(p[0] for p in pts), statistics.mean(p[1] for p in pts))
    rows = []
    for axis, index, tags in (("arousal", 1, ("high", "low")), ("valence", 0, ("high", "low"))):
        top = [n for n, c in clusters.items() if c[axis] == tags[0] and n in means]
        bottom = [n for n, c in clusters.items() if c[axis] == tags[1] and n in means]
        if not top or not bottom:
            continue
        low_of_top = min(means[n][index] for n in top)
        high_of_bottom = max(means[n][index] for n in bottom)
        rows.append((f"every '{tags[0]}' {axis} cluster rates above every '{tags[1]}' one",
                     low_of_top > high_of_bottom,
                     f"lowest high-tagged mean {low_of_top:+.2f} vs highest low-tagged mean {high_of_bottom:+.2f}"))
    return rows


def coherence_check(scores: Dict[str, Tuple[float, float]], clusters: Dict[str, dict]) -> Tuple[float, float]:
    """Question 2: (mean distance within clusters, mean distance across clusters) in valence-arousal space."""
    owner = {m: n for n, c in clusters.items() for m in c["members"] if m in scores}
    within, across = [], []
    for a, b in combinations(sorted(owner), 2):
        (within if owner[a] == owner[b] else across).append(distance(scores[a], scores[b]))
    return statistics.mean(within), statistics.mean(across)


def similarity_pairs_check(scores: Dict[str, Tuple[float, float]],
                           credited: Dict[frozenset, float]) -> Tuple[float, float, int, int]:
    """Question 3: mean distance of hand-credited pairs vs all other pairs, with each count."""
    near, far = [], []
    for a, b in combinations(sorted(scores), 2):
        (near if frozenset((a, b)) in credited else far).append(distance(scores[a], scores[b]))
    return statistics.mean(near), statistics.mean(far), len(near), len(far)


def catalog_agreement(scores: Dict[str, Tuple[float, float]], songs: List[Dict]) -> Tuple[Optional[float], Optional[float], int]:
    """Question 4: Spearman of word valence vs song valence, and word arousal vs song energy, across moods."""
    per_mood: Dict[str, List[Dict]] = {}
    for song in songs:
        per_mood.setdefault(song["mood"], []).append(song)
    moods = [m for m in sorted(scores) if m in per_mood]
    word_v = [scores[m][0] for m in moods]
    word_a = [scores[m][1] for m in moods]
    song_v = [statistics.mean(float(s["valence"]) for s in per_mood[m]) for m in moods]
    song_e = [statistics.mean(float(s["energy"]) for s in per_mood[m]) for m in moods]
    return spearman(word_v, song_v), spearman(word_a, song_e), len(moods)


def build_report(lexicon: Dict[str, Tuple[float, float]], songs: List[Dict]) -> str:
    tax = taxonomy.load_taxonomy()
    clusters = tax["moods"]["clusters"]
    moods = sorted(m for c in clusters.values() for m in c["members"])
    scores = mood_scores(moods, lexicon)
    missing = [m for m in moods if m not in scores]

    lines = ["# Taxonomy check against the NRC-VAD lexicon", "",
             "This report makes use of the NRC VAD Lexicon (v2.1), created by Saif M. Mohammad at the "
             f"National Research Council Canada ({HOME_PAGE}). The lexicon is not distributed with this "
             "repository; only aggregate results appear below.", "",
             f"Moods found in the lexicon: {len(scores)} of {len(moods)}"
             + (f" (not found: {', '.join(missing)})" if missing else "") + ". "
             "Scores are on a -1 to 1 scale. Informational: a few moods and a rating scale from a "
             "different population cannot prove the taxonomy right or wrong.", "",
             "## 1. Do the cluster tags agree with the word ratings?", "",
             "| Question | Result | Detail |", "|---|---|---|"]
    for question, ok, detail in cluster_tag_check(scores, clusters):
        lines.append(f"| {question} | {'Agree' if ok else 'DISAGREE'} | {detail} |")

    within, across = coherence_check(scores, clusters)
    lines += ["", "## 2. Is the clustering coherent?", "",
              "| Measure | Value |", "|---|---|",
              f"| Mean valence-arousal distance, moods in the same cluster | {within:.2f} |",
              f"| Mean valence-arousal distance, moods in different clusters | {across:.2f} |",
              f"| Verdict | {'Coherent: same-cluster moods are closer' if within < across else 'NOT coherent'} |"]

    near, far, n_near, n_far = similarity_pairs_check(scores, MOOD_SIMILARITY)
    lines += ["", "## 3. Do the hand-tuned close-mood pairs sit close together?", "",
              "| Measure | Value |", "|---|---|",
              f"| Mean distance, the {n_near} hand-credited pairs | {near:.2f} |",
              f"| Mean distance, the other {n_far} pairs | {far:.2f} |",
              f"| Verdict | {'Credited pairs are closer' if near < far else 'Credited pairs are NOT closer'} |"]

    adjacent = {frozenset(pair): 1.0 for pair in tax["moods"]["adjacent"]}
    near2, far2, n_near2, n_far2 = similarity_pairs_check(scores, adjacent)
    lines += ["", "## 3b. Do the taxonomy's own cross-cluster neighbour pairs sit close together?", "",
              "| Measure | Value |", "|---|---|",
              f"| Mean distance, the {n_near2} listed neighbour pairs | {near2:.2f} |",
              f"| Mean distance, the other {n_far2} pairs | {far2:.2f} |",
              f"| Verdict | {'Neighbour pairs are closer' if near2 < far2 else 'Neighbour pairs are NOT closer'} |"]

    rho_v, rho_a, n = catalog_agreement(scores, songs)
    fmt = lambda r: "n/a" if r is None else f"{r:+.2f}"
    lines += ["", "## 4. Do word ratings rank moods like the catalog's measured songs do?", "",
              f"Spearman rank correlation across the {n} moods that have songs (1 = same order, 0 = unrelated).", "",
              "| Word rating vs measured song feature | Spearman |", "|---|---|",
              f"| Valence rating vs mean song valence | {fmt(rho_v)} |",
              f"| Arousal rating vs mean song energy | {fmt(rho_a)} |", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the mood taxonomy against the NRC-VAD lexicon")
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON,
                        help=f"unigrams file from NRC-VAD v2.1 (default: {DEFAULT_LEXICON.relative_to(ROOT)})")
    args = parser.parse_args(argv)
    if not args.lexicon.exists():
        print(f"Lexicon file not found: {args.lexicon}\n"
              f"Download NRC-VAD v2.1 from {HOME_PAGE} (free for non-commercial research and\n"
              "education; do not redistribute), unzip it, and pass the Unigrams file with --lexicon\n"
              "or place the unzipped folder in data/external/.", file=sys.stderr)
        return 1
    songs = load_songs(str(SONGS_CSV))
    report = build_report(load_lexicon(args.lexicon), songs)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
