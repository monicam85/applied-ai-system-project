"""Genre and mood taxonomy loaded from data/taxonomy.json.

Two levels: label -> family (genres) or cluster (moods). Gives a fallback
similarity for label pairs the recommender's hand-tuned tables don't cover.
recommender.score_song uses it as a fallback after its own tables.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("vibescorecard.taxonomy")

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "taxonomy.json"


_EMPTY = {
    "genres": {"families": {}, "adjacent": []},
    "moods": {"clusters": {}, "adjacent": []},
    "credit": {"same_family": 0.0, "adjacent": 0.0, "same_cluster": 0.0, "adjacent_cluster_pair": 0.0},
}


@lru_cache(maxsize=1)
def load_taxonomy(path: Optional[str] = None) -> dict:
    """
    Reads the taxonomy file. A missing, unreadable or malformed file is logged and
    replaced by an empty taxonomy, so scoring degrades to exact matches plus the
    recommender's own hand-tuned tables instead of crashing.
    """
    try:
        with open(path or TAXONOMY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for section, keys in (("genres", ("families", "adjacent")), ("moods", ("clusters", "adjacent")),
                              ("credit", tuple(_EMPTY["credit"]))):
            for key in keys:
                data[section][key]
        _invert(data["genres"]["families"])
        _invert(data["moods"]["clusters"])
        return data
    except (OSError, ValueError, KeyError, TypeError) as error:
        log.error("taxonomy unusable (%s: %s); falling back to exact matches only",
                  type(error).__name__, error)
        return _EMPTY


def _invert(groups: Dict[str, dict]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, group in groups.items():
        for label in group["members"]:
            if label in out:
                raise ValueError(f"{label!r} appears in both {out[label]!r} and {name!r}")
            out[label] = name
    return out


@lru_cache(maxsize=1)
def _genre_lookup() -> Dict[str, str]:
    return _invert(load_taxonomy()["genres"]["families"])


@lru_cache(maxsize=1)
def _mood_lookup() -> Dict[str, str]:
    return _invert(load_taxonomy()["moods"]["clusters"])


@lru_cache(maxsize=1)
def _adjacent_pairs() -> Dict[str, set]:
    t = load_taxonomy()
    return {kind: {frozenset(p) for p in t[kind]["adjacent"]} for kind in ("genres", "moods")}


def genre_family(genre: str) -> Optional[str]:
    return _genre_lookup().get(genre)


def mood_cluster(mood: str) -> Optional[str]:
    return _mood_lookup().get(mood)


def _similarity(a: str, b: str, group_of, adjacent, same_credit: float, adj_credit: float) -> float:
    if a == b:
        return 1.0
    if frozenset((a, b)) in adjacent:
        return adj_credit
    ga, gb = group_of(a), group_of(b)
    return same_credit if ga is not None and ga == gb else 0.0


def genre_similarity(a: str, b: str) -> float:
    """1.0 same genre, adjacent credit for listed neighbours, family credit within a family, else 0."""
    t = load_taxonomy()
    return _similarity(a, b, genre_family, _adjacent_pairs()["genres"],
                       t["credit"]["same_family"], t["credit"]["adjacent"])


def mood_similarity(a: str, b: str) -> float:
    """1.0 same mood, small credit for listed neighbours, cluster credit within a cluster, else 0."""
    t = load_taxonomy()
    return _similarity(a, b, mood_cluster, _adjacent_pairs()["moods"],
                       t["credit"]["same_cluster"], t["credit"]["adjacent_cluster_pair"])
