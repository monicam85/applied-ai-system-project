"""
Evaluation harness: runs every profile and natural-language case through the full
pipeline and checks properties that should always hold. Writes a pass/fail report.

Run from the project root:
    python -m src.evaluate            # prints a summary, writes reports/evaluation_report.md
"""

import json
import os
from pathlib import Path
from typing import Callable, Dict, List, Tuple

try:
    from . import metrics
    from . import recommender as _rec_module
    from .main import PROFILES, SONGS_CSV, setup_logging
    from .nl_query import parse_request
    from .recommender import load_songs, recommend_songs
    from .reliability import recommend_with_checks
except ImportError:
    import metrics
    import recommender as _rec_module
    from main import PROFILES, SONGS_CSV, setup_logging
    from nl_query import parse_request
    from recommender import load_songs, recommend_songs
    from reliability import recommend_with_checks

REPORT = Path(__file__).resolve().parent.parent / "reports" / "evaluation_report.md"
K = 5

# What confidence each profile should earn. Ordinary tastes must be trusted;
# self-contradictory or empty ones must not be rated "high".
EXPECTED_LEVELS = {
    "High-Energy Pop": {"high"},
    "Chill Lofi": {"high"},
    "Deep Intense Rock": {"high"},
    "Conflicted (sad but high-energy)": {"medium", "low"},
    "Adversarial: metal fan who wants chill": {"medium", "low"},
    "Adversarial: acoustic-loving EDM fan": {"medium", "low"},
    "Adversarial: empty profile": {"none"},
    "Adversarial: wrong-case genre and mood": {"medium", "low", "high"},
    "Adversarial: likes_acoustic='no'": {"high"},
    "Adversarial: likes_acoustic='maybe'": {"none"},
    "Numeric acousticness=0.5": {"medium", "low", "high"},
    "Adversarial: genre-only (lofi)": {"medium"},
    "Adversarial: energy out of range (1.5)": {"medium", "low", "high"},
    "Adversarial: energy='high' (wrong type)": {"medium", "low", "high"},
}


class _FakeClient:
    """Stands in for the Anthropic client so LLM-path tests run offline."""

    def __init__(self, reply: str):
        self.messages = self
        self._reply = reply

    def create(self, **_kwargs):
        class _Block:
            text = self._reply
        class _Reply:
            content = [_Block()]
        return _Reply()


# (name, request text, client or None, predicate on the parsed prefs)
NL_CASES: List[Tuple[str, str, object, Callable[[Dict], bool]]] = [
    ("keywords: study music", "something mellow for studying", None,
     lambda p: p.get("energy", 1) <= 0.4),
    ("keywords: workout", "pump-up music for the gym", None,
     lambda p: p.get("energy", 0) >= 0.8),
    ("keywords: gibberish", "asdf qwerty", None, lambda p: p == {}),
    ("keywords: goal beats current mood", "I'm sad, cheer me up", None,
     lambda p: p.get("mood") == "happy"),
    ("keywords: wake-me-up goal", "wake me up", None, lambda p: p.get("energy", 0) >= 0.8),
    ("keywords: negation skipped", "I am not sad", None, lambda p: "mood" not in p),
    ("keywords: word not substring", "brunch playlist", None, lambda p: p == {}),
    ("llm: well-formed JSON", "x", _FakeClient('{"genre": "lofi", "energy": 0.3}'),
     lambda p: p == {"genre": "lofi", "energy": 0.3}),
    ("llm: JSON wrapped in prose", "x", _FakeClient('Sure! {"mood": "happy"} Enjoy.'),
     lambda p: p == {"mood": "happy"}),
    ("llm: malformed JSON falls back", "chill beats", _FakeClient("not json at all"),
     lambda p: p.get("mood") == "chill"),
    ("llm: hallucinated genre dropped", "x", _FakeClient('{"genre": "vaporwave", "energy": 0.4}'),
     lambda p: "genre" not in p and p.get("energy") == 0.4),
    ("llm: out-of-range energy clamped", "x", _FakeClient('{"energy": 7}'),
     lambda p: p.get("energy") == 1.0),
    ("llm: unexpected keys ignored", "x", _FakeClient('{"mood": "sad", "tempo": 999}'),
     lambda p: p == {"mood": "sad"}),
]


def check_profile(name: str, prefs: Dict, songs: List[Dict]) -> List[Tuple[str, bool, str]]:
    """Runs the property checks for one profile; returns (check, passed, detail) rows."""
    rows: List[Tuple[str, bool, str]] = []
    result = recommend_with_checks(prefs, songs, k=K)
    recs, level = result["recommendations"], result["confidence"]["level"]

    if result["error"]:
        rows.append(("rejects bad input cleanly", True, result["error"]))
    else:
        scores = [score for _, score, _ in recs]
        rows.append(("returns k results", len(recs) == min(K, len(songs)), f"{len(recs)} returned"))
        rows.append(("scores within 0-1", all(0 <= s <= 1 for s in scores), f"{scores}"))
        artists = [song["artist"] for song, _, _ in recs]
        worst = max((artists.count(a) for a in set(artists)), default=0)
        rows.append(("no artist repeats more than twice", worst <= 2, f"max repeats {worst}"))
        again = recommend_with_checks(prefs, songs, k=K)["recommendations"]
        rows.append(("deterministic", [s["id"] for s, _, _ in again] == [s["id"] for s, _, _ in recs], ""))
    expected = EXPECTED_LEVELS.get(name)
    if expected:
        rows.append(("confidence level as expected", level in expected,
                     f"got {level}, expected one of {sorted(expected)}"))
    return rows


def taxonomy_impact(songs: List[Dict]) -> Tuple[List[str], int]:
    """
    Ranks every profile with and without the taxonomy fallback and lists the
    profiles whose top-K changed. Returns (markdown lines, profiles changed).
    """
    tax = _rec_module.taxonomy
    originals = tax.genre_similarity, tax.mood_similarity

    def top_ids(prefs: Dict) -> List[int]:
        return [song["id"] for song, _, _ in recommend_with_checks(prefs, songs, k=K)["recommendations"]]

    with_tax = {name: top_ids(prefs) for name, prefs in PROFILES.items()}
    tax.genre_similarity = tax.mood_similarity = lambda a, b: 1.0 if a == b else 0.0
    try:
        without = {name: top_ids(prefs) for name, prefs in PROFILES.items()}
    finally:
        tax.genre_similarity, tax.mood_similarity = originals

    title = {song["id"]: song["title"] for song in songs}
    lines = ["| Profile | Top-%d without taxonomy | Top-%d with taxonomy |" % (K, K), "|---|---|---|"]
    changed = 0
    for name in PROFILES:
        if with_tax[name] != without[name]:
            changed += 1
            lines.append(f"| {name} | {', '.join(title[i] for i in without[name])} "
                         f"| {', '.join(title[i] for i in with_tax[name])} |")
    if not changed:
        lines.append("| (no profile changed) | | |")
    return lines, changed


def _profile_results(songs: List[Dict]) -> Dict[str, Dict]:
    """The guarded result for every profile the scorer accepts (rejected ones are skipped)."""
    results = {name: recommend_with_checks(prefs, songs, k=K) for name, prefs in PROFILES.items()}
    return {name: r for name, r in results.items() if not r["error"] and r["recommendations"]}


def confidence_summary(results: Dict[str, Dict]) -> List[str]:
    """Markdown: how confident the system was across profiles, and how often it relaxed or refused."""
    levels = [r["confidence"]["level"] for r in results.values()]
    # A profile with no usable preferences has no meaningful score, so leave it out of the averages.
    tops = [r["confidence"]["top_score"] for r in results.values() if r["confidence"]["level"] != "none"]
    lines = ["| Measure | Value |", "|---|---|",
             f"| Profiles scored | {len(results)} of {len(PROFILES)} (the rest were rejected as invalid) |"]
    for level in ("high", "medium", "low", "none"):
        lines.append(f"| Confidence {level.upper()} | {levels.count(level)} |")
    lines += [f"| Mean top score (excluding NONE) | {metrics.mean(tops):.2f} |",
              f"| Lowest top score (excluding NONE) | {min(tops):.2f} |",
              f"| Profiles relaxed automatically | {sum(1 for r in results.values() if r['relaxed_dropped'])} |",
              f"| Profiles flagged NO STRONG MATCH | {sum(1 for r in results.values() if r['no_strong_match'])} |"]
    return lines


def beyond_accuracy(songs: List[Dict], results: Dict[str, Dict]) -> Tuple[List[str], Dict[str, float]]:
    """
    Diversity, coverage, exposure concentration and a serendipity proxy across all
    scored profiles, with the diversity step on versus off. Returns (markdown, numbers).
    """
    on = {name: [song for song, _, _ in r["recommendations"]] for name, r in results.items()}
    off = {name: [song for song, _, _ in recommend_songs(r["prefs"], songs, k=K, diversify=False)]
           for name, r in results.items()}
    on_lists, off_lists = list(on.values()), list(off.values())

    def avg_diversity(lists):
        return metrics.mean([metrics.intra_list_diversity(songs_) for songs_ in lists])

    def avg_artists(lists):
        return metrics.mean([len({s["artist"] for s in songs_}) for songs_ in lists])

    def avg_genres(lists):
        return metrics.mean([len({s["genre"] for s in songs_}) for songs_ in lists])

    counts_on, counts_off = metrics.exposure_counts(on_lists), metrics.exposure_counts(off_lists)
    exposure_on = [counts_on.get(s["id"], 0) for s in songs]
    exposure_off = [counts_off.get(s["id"], 0) for s in songs]
    catalog_energy = metrics.mean([float(s["energy"]) for s in songs])
    rec_energy = metrics.mean([float(s["energy"]) for lst in on_lists for s in lst])

    serendip, relevant = 0, 0
    for r in results.values():
        hit, rel = metrics.serendipity_counts(r["recommendations"], r["prefs"].get("genre"))
        serendip, relevant = serendip + hit, relevant + rel

    numbers = {
        "coverage_on": metrics.catalog_coverage(on_lists, len(songs)),
        "coverage_off": metrics.catalog_coverage(off_lists, len(songs)),
        "diversity_on": avg_diversity(on_lists), "diversity_off": avg_diversity(off_lists),
        "artists_on": avg_artists(on_lists), "artists_off": avg_artists(off_lists),
        "top5_on": metrics.top_share(counts_on, 5), "top5_off": metrics.top_share(counts_off, 5),
    }
    lines = [
        "| Metric | Diversity step ON (default) | Diversity step OFF | What it shows |",
        "|---|---|---|---|",
        f"| Catalog coverage (songs shown in any list) | {numbers['coverage_on']:.0%} | {numbers['coverage_off']:.0%} "
        f"| Higher = more of the catalog gets a chance |",
        f"| Genre coverage | {metrics.genre_coverage(on_lists, songs):.0%} | {metrics.genre_coverage(off_lists, songs):.0%} "
        f"| Genres that ever appear |",
        f"| Intra-list diversity (0-1, sound distance) | {numbers['diversity_on']:.3f} | {numbers['diversity_off']:.3f} "
        f"| Higher = songs in one list sound less alike |",
        f"| Distinct artists per list (of {K}) | {numbers['artists_on']:.2f} | {numbers['artists_off']:.2f} "
        f"| Higher = fewer repeat artists |",
        f"| Distinct genres per list (of {K}) | {avg_genres(on_lists):.2f} | {avg_genres(off_lists):.2f} "
        f"| Higher = broader lists |",
        f"| Exposure share of the 5 most-shown songs | {numbers['top5_on']:.0%} | {numbers['top5_off']:.0%} "
        f"| Lower = less \"popularity\" concentration |",
        f"| Exposure Gini (0 = even, 1 = one song takes all) | {metrics.gini(exposure_on):.2f} | {metrics.gini(exposure_off):.2f} "
        f"| Lower = more even exposure |",
        f"| Mean energy of recommended songs vs catalog | {rec_energy:.2f} vs {catalog_energy:.2f} | "
        f"{metrics.mean([float(s['energy']) for lst in off_lists for s in lst]):.2f} vs {catalog_energy:.2f} "
        f"| Gap = lists skew toward loud or quiet songs |",
        f"| Serendipity proxy (relevant picks outside the requested genre) | "
        f"{serendip} of {relevant} ({(serendip / relevant if relevant else 0):.0%}) | n/a "
        f"| Relevant = score >= {metrics.RELEVANT_SCORE}; proxy only |",
    ]
    top = metrics.exposure_counts(on_lists).most_common(5)
    title = {s["id"]: s["title"] for s in songs}
    lines += ["", "Most-shown songs (slots across all profiles): "
              + ", ".join(f"{title[i]} ({c})" for i, c in top)
              + f". Never shown: {sum(1 for c in exposure_on if c == 0)} of {len(songs)} songs."]
    return lines, numbers


def run() -> Tuple[str, int, int]:
    """
    Runs everything. Returns (markdown report, checks passed, checks total).

    ANTHROPIC_API_KEY is removed for the duration, so the offline cases never reach a live model and
    the results are the same with or without a key set.
    """
    previous = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        return _run()
    finally:
        if previous is not None:
            os.environ["ANTHROPIC_API_KEY"] = previous


def _run() -> Tuple[str, int, int]:
    """The evaluation itself; call run(), which makes it hermetic."""
    songs = load_songs(str(SONGS_CSV))
    lines = ["# Evaluation report", "",
             f"Catalog: {len(songs)} songs. Top-k: {K}.", "",
             "## Profile checks", "", "| Profile | Check | Result | Detail |", "|---|---|---|---|"]
    passed = total = 0
    for name, prefs in PROFILES.items():
        for check, ok, detail in check_profile(name, prefs, songs):
            total += 1
            passed += ok
            lines.append(f"| {name} | {check} | {'PASS' if ok else 'FAIL'} | {detail[:70]} |")

    lines += ["", "## Natural-language parsing checks", "",
              "| Case | Result | Parsed prefs | Source |", "|---|---|---|---|"]
    for name, text, client, predicate in NL_CASES:
        prefs, _notes, source = parse_request(text, songs, client=client)
        ok = predicate(prefs)
        total += 1
        passed += ok
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | `{json.dumps(prefs)}` | {source} |")

    impact, changed = taxonomy_impact(songs)
    lines += ["", "## Taxonomy impact", "",
              "Profiles whose top results change when genre/mood taxonomy credit is enabled "
              f"({changed} of {len(PROFILES)}). Full-credit and hand-tuned pair values are unaffected.", ""]
    lines += impact

    results = _profile_results(songs)
    lines += ["", "## Confidence summary", ""] + confidence_summary(results)
    meaningful = {n: r for n, r in results.items() if r["confidence"]["level"] != "none"}
    beyond_lines, _numbers = beyond_accuracy(songs, meaningful)
    lines += ["", "## Beyond-accuracy metrics", "",
              f"Computed over the {len(meaningful)} profiles with usable preferences, top-{K} each "
              "(the empty profile is excluded: its list is arbitrary). "
              "These are informational, not pass/fail. Novelty is not measured (see README).", ""] + beyond_lines

    lines += ["", f"**Total: {passed}/{total} checks passed.**", ""]
    return "\n".join(lines), passed, total


def main() -> None:
    setup_logging()
    report, passed, total = run()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to {REPORT}")
    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
