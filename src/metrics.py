"""
Beyond-accuracy metrics for recommendation lists.

Accuracy alone (did the right song rank first?) hides problems that matter in a
recommender: lists full of near-identical songs, a few songs hogging every list,
or most of the catalog never being shown. These small, pure functions measure
that. They take lists of song dicts so they are easy to test.

Which metrics apply here, and which do not, is explained in the README
("Which beyond-accuracy metrics apply"): diversity, coverage and exposure
concentration are measured directly; serendipity is measured as a proxy;
novelty and true popularity bias need data this project does not have.
"""

from collections import Counter
from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Numeric song features on a 0-1 scale, used to judge how different two songs sound.
DIVERSITY_FEATURES = ("energy", "valence", "danceability", "acousticness")

# A pick counts as "relevant" for the serendipity proxy at or above this score.
RELEVANT_SCORE = 0.5


def song_distance(a: Dict, b: Dict) -> float:
    """Mean absolute difference over DIVERSITY_FEATURES: 0 = identical sound, 1 = opposite."""
    return sum(abs(float(a[f]) - float(b[f])) for f in DIVERSITY_FEATURES) / len(DIVERSITY_FEATURES)


def intra_list_diversity(songs: Sequence[Dict]) -> float:
    """Average pairwise song_distance within one list (0 for fewer than two songs)."""
    pairs = list(combinations(songs, 2))
    if not pairs:
        return 0.0
    return sum(song_distance(a, b) for a, b in pairs) / len(pairs)


def catalog_coverage(lists: Iterable[Sequence[Dict]], catalog_size: int) -> float:
    """Share of the catalog that appears in at least one list."""
    shown = {song["id"] for songs in lists for song in songs}
    return len(shown) / catalog_size if catalog_size else 0.0


def genre_coverage(lists: Iterable[Sequence[Dict]], catalog: Sequence[Dict]) -> float:
    """Share of the catalog's genres that appear in at least one list."""
    genres = {song["genre"] for song in catalog}
    shown = {song["genre"] for songs in lists for song in songs}
    return len(shown & genres) / len(genres) if genres else 0.0


def exposure_counts(lists: Iterable[Sequence[Dict]]) -> Counter:
    """How many list slots each song id received."""
    return Counter(song["id"] for songs in lists for song in songs)


def top_share(counts: Counter, n: int) -> float:
    """Share of all list slots taken by the n most-shown songs (1.0 = a few songs get everything)."""
    total = sum(counts.values())
    return sum(c for _, c in counts.most_common(n)) / total if total else 0.0


def gini(values: Sequence[float]) -> float:
    """Inequality of exposure: 0 = every song shown equally often, near 1 = one song takes all."""
    values = sorted(values)
    n, total = len(values), sum(values)
    if n == 0 or total == 0:
        return 0.0
    weighted = sum((i + 1) * v for i, v in enumerate(values))
    return (2 * weighted) / (n * total) - (n + 1) / n


def serendipity_counts(recs: Sequence[Tuple[Dict, float, str]],
                       wanted_genre: Optional[str]) -> Tuple[int, int]:
    """
    Serendipity PROXY for one list: (relevant picks outside the requested genre, relevant picks).

    A pick is relevant if its score is at least RELEVANT_SCORE. True serendipity
    needs to know what the listener already expected or has heard, which this
    project does not have, so "good but outside the genre they named" stands in.
    Returns (0, 0) when no genre was requested.
    """
    if not wanted_genre:
        return 0, 0
    relevant = [song for song, score, _ in recs if score >= RELEVANT_SCORE]
    return sum(1 for song in relevant if song["genre"] != wanted_genre), len(relevant)


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0
