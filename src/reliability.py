"""
Reliability layer: checks inputs before scoring and judges how far to trust a result.

The scorer always returns a ranked list, even when nothing in the catalog fits.
This module adds the missing honesty:
  - sanitize_prefs  cleans a preferences dict and reports every fix it made
  - assess_confidence  rates a result list high / medium / low / none with reasons
"""

import logging
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("vibescorecard.reliability")

# Top-score cut-offs, picked from the 14 evaluation profiles: ordinary tastes land
# at 0.95+, contradictory ones at 0.4-0.65.
HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.60

NUMERIC_KEYS = ("energy", "valence", "acousticness", "instrumentalness", "speechiness")


def catalog_vocabulary(songs: List[Dict]) -> Dict[str, set]:
    """Returns the genres and moods that actually exist in the catalog."""
    return {
        "genre": {s["genre"] for s in songs},
        "mood": {s["mood"] for s in songs},
    }


def sanitize_prefs(prefs: Dict, songs: List[Dict]) -> Tuple[Dict, List[str]]:
    """
    Returns (clean_prefs, warnings). Never raises on bad values; it repairs or drops them.

    Repairs: genre/mood lower-cased and trimmed, numeric values clamped to 0-1.
    Drops: values of the wrong type, and genres/moods the catalog has no songs for
    (keeping them would just score 0 for every song and hide the real problem).
    """
    vocab = catalog_vocabulary(songs)
    clean: Dict = {}
    warnings: List[str] = []

    for key, value in prefs.items():
        if key in ("genre", "mood"):
            if not isinstance(value, str):
                warnings.append(f"dropped {key}: expected text, got {value!r}")
                continue
            norm = value.strip().lower()
            if norm != value:
                warnings.append(f"normalised {key} {value!r} -> {norm!r}")
            if norm not in vocab[key]:
                warnings.append(f"dropped {key} {norm!r}: no song in the catalog has it")
                continue
            clean[key] = norm
        elif key in NUMERIC_KEYS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                warnings.append(f"dropped {key}: expected a number, got {value!r}")
                continue
            if not 0 <= value <= 1:
                warnings.append(f"clamped {key} {value} into 0-1")
            clean[key] = min(1.0, max(0.0, float(value)))
        else:  # likes_acoustic, release_year, ...: the scorer validates these itself
            clean[key] = value
    return clean, warnings


def assess_confidence(prefs: Dict, recommendations: List[Tuple]) -> Dict:
    """
    Rates how much to trust a recommendation list.

    Returns {"level": "high"|"medium"|"low"|"none", "top_score": float, "reasons": [...]}.
    """
    scoring_keys = list(prefs)
    if not scoring_keys or not recommendations:
        return {"level": "none", "top_score": 0.0,
                "reasons": ["no usable preferences, so the ranking is arbitrary"]}

    best = max(score for _, score, _ in recommendations)
    reasons: List[str] = []
    if len(scoring_keys) == 1:
        reasons.append("only one preference given; scores are not comparable to richer profiles")

    if best >= HIGH_CONFIDENCE:
        level = "high"
    elif best >= MEDIUM_CONFIDENCE:
        level = "medium"
        reasons.append(f"best match scored only {best:.2f}")
    else:
        level = "low"
        reasons.append(f"best match scored only {best:.2f}: no song fits this taste well")

    if level == "high" and len(scoring_keys) == 1:
        level = "medium"
    return {"level": level, "top_score": round(best, 3), "reasons": reasons}


def _relax(clean: Dict, songs: List[Dict], k: int, mode,
           tried: Optional[List[Tuple[str, float]]] = None) -> Tuple[Dict, List[Tuple], str]:
    """
    Leave-one-out relaxation for a low-confidence profile: tries dropping each
    preference in turn and keeps the variant whose best match scores highest.
    Returns (prefs, recommendations, dropped_key), or ({}, [], "") if nothing helps.
    If `tried` is a list, each (dropped preference, best score without it) is appended
    so the caller can show why a preference was chosen.
    """
    from_here = _recommender()
    best: Tuple[float, Dict, List[Tuple], str] = (0.0, {}, [], "")
    if len(clean) < 3:  # relaxing must leave at least 2 preferences, or a lone match scores 1.0 trivially
        return best[1], best[2], best[3]
    for key in clean:
        trial = {k_: v for k_, v in clean.items() if k_ != key}
        try:
            recs = from_here(trial, songs, k=k, mode=mode)
        except ValueError:
            continue
        top = recs[0][1] if recs else 0.0
        if tried is not None:
            tried.append((key, top))
        if top > best[0]:
            best = (top, trial, recs, key)
    return best[1], best[2], best[3]


def _recommender():
    try:
        from .recommender import recommend_songs
    except ImportError:
        from recommender import recommend_songs
    return recommend_songs


def recommend_with_checks(prefs: Dict, songs: List[Dict], k: int = 5, mode="balanced") -> Dict:
    """
    The guarded recommendation pipeline. Never raises.

    1. sanitize prefs  2. recommend  3. rate confidence
    4. if confidence is LOW, relax the profile (drop the one preference that costs
       the most) and re-rank; if that still is not trustworthy, set
       no_strong_match so callers present the list as a weak fallback, not a pick.

    Every step also appends to a trace (a list of {"step", "detail"} dicts) that says
    what the step saw and what it decided, so the decision chain can be read back.

    Returns {"prefs", "recommendations", "confidence", "warnings", "error",
             "relaxed_dropped", "no_strong_match", "trace"}.
    """
    recommend_songs = _recommender()
    trace: List[Dict[str, str]] = []

    def note(step: str, detail: str) -> None:
        trace.append({"step": step, "detail": detail})

    clean, warnings = sanitize_prefs(prefs, songs)
    for warning in warnings:
        log.warning("input repaired: %s", warning)
    note("sanitize", f"received {prefs!r} -> kept {clean!r}"
         + (f"; repairs: {'; '.join(warnings)}" if warnings else "; no repairs needed"))

    result = {"prefs": clean, "recommendations": [], "warnings": warnings, "error": None,
              "relaxed_dropped": None, "no_strong_match": False, "trace": trace}
    try:
        recs = recommend_songs(clean, songs, k=k, mode=mode)
    except ValueError as error:
        log.error("scorer rejected input %s: %s", clean, error)
        note("rank", f"scorer rejected the profile: {error}")
        note("decision", "REJECT: report the error to the user instead of guessing")
        result.update(error=str(error), confidence=assess_confidence(clean, []))
        return result

    confidence = assess_confidence(clean, recs)
    log.info("prefs=%s mode=%s top=%.2f confidence=%s", clean, mode,
             confidence["top_score"], confidence["level"])
    note("rank", f"mode={mode}, scored {len(songs)} songs; top {len(recs)}: "
         + ", ".join(f"{song['title']} ({score:.2f})" for song, score, _ in recs[:3])
         + (" ..." if len(recs) > 3 else ""))
    note("confidence", f"{confidence['level'].upper()} (best score {max((sc for _, sc, _ in recs), default=0.0):.2f}; "
         f"HIGH needs >= {HIGH_CONFIDENCE}, MEDIUM >= {MEDIUM_CONFIDENCE})"
         + (f"; reasons: {'; '.join(confidence['reasons'])}" if confidence["reasons"] else ""))

    if confidence["level"] == "low":
        tried: List[Tuple[str, float]] = []
        relaxed, relaxed_recs, dropped = _relax(clean, songs, k, mode, tried)
        if tried:
            note("relax", "tried dropping each preference: "
                 + ", ".join(f"without {key!r} best score {top:.2f}" for key, top in tried))
        else:
            note("relax", "skipped: relaxing must leave at least 2 preferences")
        relaxed_conf = assess_confidence(relaxed, relaxed_recs) if relaxed_recs else None
        if relaxed_conf and relaxed_conf["level"] in ("medium", "high"):
            log.warning("low confidence; relaxed by dropping %r -> %s", dropped, relaxed_conf["level"])
            result["relaxed_dropped"] = dropped
            result["prefs"], recs, confidence = relaxed, relaxed_recs, relaxed_conf
            confidence["reasons"].append(f"relaxed: ignored your {dropped!r} preference, which no song fit")
            note("decision", f"RELAX: ignore {dropped!r}; re-ranked, confidence now "
                 f"{relaxed_conf['level'].upper()} (best score {max(sc for _, sc, _ in relaxed_recs):.2f})")
        else:
            log.warning("low confidence and relaxation did not help; flagging no strong match")
            result["no_strong_match"] = True
            note("decision", "NO STRONG MATCH: relaxing did not reach MEDIUM, so no ranked list is presented as a pick")
    else:
        note("decision", f"RECOMMEND: confidence {confidence['level'].upper()}, present the ranked list")

    result.update(recommendations=recs, confidence=confidence)
    return result


def format_trace(trace: List[Dict[str, str]]) -> str:
    """Numbered, human-readable lines for a trace returned by recommend_with_checks."""
    return "\n".join(f"{i}. [{item['step']}] {item['detail']}" for i, item in enumerate(trace, start=1))
