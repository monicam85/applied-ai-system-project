"""
Command line runner for the Music Recommender Simulation.

Run from the project root with either:
    python -m src.main
    python src/main.py

Options:
    --mode NAME   scoring strategy: balanced (default), genre-first,
                  mood-first or energy-focused
    --compare     show the top 3 of every mode side by side for each profile
    --ask TEXT    describe what you want in plain English, e.g. --ask "mellow study music"
    --embeddings  with --ask: read paraphrases with an optional embedding model
    --trace       print the decision chain (sanitize, rank, confidence, relax, decision) per result
"""

import argparse
import logging
from pathlib import Path

try:  # works for `python -m src.main`
    from .embed_parse import EmbeddingParser, default_encoder
    from .nl_query import parse_request
    from .recommender import MODES, load_songs, recommend_songs
    from .reliability import format_trace, recommend_with_checks
except ImportError:  # works for `python src/main.py`
    from embed_parse import EmbeddingParser, default_encoder
    from nl_query import parse_request
    from recommender import MODES, load_songs, recommend_songs
    from reliability import format_trace, recommend_with_checks

ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = ROOT / "data" / "songs.csv"
LOG_FILE = ROOT / "logs" / "app.log"


def setup_logging() -> None:
    """Logs everything to logs/app.log; only warnings and errors reach the terminal."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    root = logging.getLogger("vibescorecard")
    if root.handlers:  # already configured (e.g. main() called twice in tests)
        return
    root.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    root.addHandler(file_handler)
    root.addHandler(console)
WIDTH = 64


# Distinct taste profiles used to evaluate the scoring logic.
PROFILES = {
    "High-Energy Pop": {
        "genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False,
    },
    "Chill Lofi": {
        "genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False,
    },
    # Adversarial: sad mood but very high energy, which almost never go together.
    "Conflicted (sad but high-energy)": {
        "genre": "folk", "mood": "sad", "energy": 0.9, "likes_acoustic": True,
    },
    # Adversarial: genre and energy point to metal, but the mood is chill.
    "Adversarial: metal fan who wants chill": {
        "genre": "metal", "mood": "chill", "energy": 0.97, "likes_acoustic": False,
    },
    # Adversarial: acoustic taste contradicts an acoustic-free genre and energy.
    "Adversarial: acoustic-loving EDM fan": {
        "genre": "edm", "mood": "euphoric", "energy": 0.95, "likes_acoustic": True,
    },
    # Adversarial: no preferences at all.
    "Adversarial: empty profile": {},
    # Adversarial: wrong capitalisation, so exact matching never hits.
    "Adversarial: wrong-case genre and mood": {
        "genre": "Pop", "mood": "Happy", "energy": 0.8, "likes_acoustic": False,
    },
    # Adversarial: a string where a bool belongs. "no" used to be truthy; it is now parsed.
    "Adversarial: likes_acoustic='no'": {
        "genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": "no",
    },
    # Adversarial: an unparseable string; should be rejected, not guessed.
    "Adversarial: likes_acoustic='maybe'": {
        "genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": "maybe",
    },
    # Numeric acoustic target (middle of the road) instead of a yes/no switch.
    "Numeric acousticness=0.5": {
        "genre": "jazz", "mood": "relaxed", "energy": 0.5, "acousticness": 0.5,
    },
    # Adversarial: a single weak preference gets normalised to a full 0-1 range.
    "Adversarial: genre-only (lofi)": {"genre": "lofi"},
    # Adversarial: energy outside the 0-1 range.
    "Adversarial: energy out of range (1.5)": {
        "genre": "pop", "mood": "happy", "energy": 1.5, "likes_acoustic": False,
    },
    # Adversarial: wrong type for energy; expected to crash.
    "Adversarial: energy='high' (wrong type)": {
        "genre": "pop", "mood": "happy", "energy": "high", "likes_acoustic": False,
    },
}


def format_recommendations(name: str, user_prefs: dict, recommendations: list) -> str:
    """Builds a readable block: profile header, then one entry per song."""
    profile = ", ".join(f"{key}={value}" for key, value in user_prefs.items())
    lines = [
        "=" * WIDTH,
        f"TOP RECOMMENDATIONS: {name}".center(WIDTH),
        "=" * WIDTH,
        f"Profile: {profile}",
        "",
    ]
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        lines.append(f"{rank}. {song['title']} by {song['artist']}")
        lines.append(f"   Score: {score:.2f} / 1.00   [{song['genre']} | {song['mood']}]")
        lines.append("   Why:")
        lines.extend(f"     - {reason}" for reason in explanation.split("; "))
        lines.append("")
    lines.append("-" * WIDTH)
    return "\n".join(lines)


def present(label: str, result: dict) -> str:
    """Renders a guarded result. A no-strong-match result is NOT shown as a pick list."""
    confidence = result["confidence"]
    if result["error"]:
        return f"{label}: rejected input: {result['error']}"
    if result["no_strong_match"]:
        best = result["recommendations"][0][1] if result["recommendations"] else 0.0
        return (f"{label}: NO STRONG MATCH (best score {best:.2f}).\n"
                "  Nothing in the catalog fits this taste; try different preferences.")
    block = format_recommendations(label, result["prefs"], result["recommendations"])
    notes = result["warnings"] + confidence["reasons"]
    footer = [f"Confidence: {confidence['level'].upper()} (top score {confidence['top_score']:.2f})"]
    footer += [f"  note: {n}" for n in notes]
    return block + "\n" + "\n".join(footer)


def format_comparison(name: str, user_prefs: dict, songs: list, k: int = 3) -> str:
    """One block per profile: the top k songs of every scoring mode, one mode per line."""
    profile = ", ".join(f"{key}={value}" for key, value in user_prefs.items()) or "(empty)"
    lines = [f"{name}", f"  Profile: {profile}"]
    for mode_name in MODES:
        picks = recommend_songs(user_prefs, songs, k=k, mode=mode_name)
        cells = " > ".join(f"{song['title']} ({score:.2f})" for song, score, _ in picks)
        lines.append(f"  {mode_name:<15} {cells}")
    return "\n".join(lines)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument("--mode", choices=list(MODES), default="balanced",
                        help="scoring strategy (default: balanced)")
    parser.add_argument("--compare", action="store_true",
                        help="compare the top 3 of every mode for each profile")
    parser.add_argument("--ask", metavar="TEXT",
                        help="plain-English request; uses Claude if ANTHROPIC_API_KEY is set")
    parser.add_argument("--trace", action="store_true",
                        help="after each result, print the decision chain: what each step saw and decided")
    parser.add_argument("--embeddings", action="store_true",
                        help="with --ask and no API key, read paraphrases with a sentence-embedding "
                             "model (optional install: requirements-embeddings.txt)")
    args = parser.parse_args(argv)
    setup_logging()

    try:
        songs = load_songs(str(SONGS_CSV))
    except (OSError, ValueError) as error:
        logging.getLogger("vibescorecard").error("could not load catalog: %s", error)
        print(f"Cannot start: could not load the song catalog ({error}).")
        raise SystemExit(1)
    if args.ask is not None:
        embedder, embed_notes = None, []
        if args.embeddings:
            try:
                embedder = EmbeddingParser(default_encoder())
            except Exception as error:  # package missing, no network for the model, ...
                logging.getLogger("vibescorecard").error("embedding parser unavailable: %s", error)
                embed_notes.append(f"--embeddings unavailable ({error}); used keyword fallback")
        prefs, notes, source = parse_request(args.ask, songs, embedder=embedder)
        notes = embed_notes + notes
        if not prefs:  # nothing usable: say so rather than print an arbitrary ranking
            print("Could not find any music preferences in that request.")
            for line in notes:
                print(f"  note: {line}")
            print('Try something like: --ask "upbeat pop for a workout"')
            return
        result = recommend_with_checks(prefs, songs, k=5, mode=args.mode)
        shown = args.ask.strip()
        shown = shown if len(shown) <= 60 else shown[:57] + "..."
        print(present(f"Request: {shown}", result))
        if args.trace:
            interpret = {"step": "interpret", "detail": f"read {args.ask.strip()!r} via {source} -> {prefs!r}"
                         + (f"; notes: {'; '.join(notes)}" if notes else "")}
            print("\nDecision trace:\n" + format_trace([interpret] + result["trace"]))
        print(f"Interpreted via: {source}")
        for line in notes:
            print(f"  note: {line}")
        return

    if args.compare:
        print("Top 3 per scoring mode (score in brackets)")
        print("=" * WIDTH)
        for mode in MODES.values():
            print(f"  {mode.name:<15} {mode.description}")
        print("=" * WIDTH + "\n")
        for name, user_prefs in PROFILES.items():
            try:
                print(format_comparison(name, user_prefs, songs))
            except Exception as error:  # adversarial profiles may be invalid on purpose
                print(f"{name}: CRASHED with {type(error).__name__}: {error}")
            print()
        return

    for name, user_prefs in PROFILES.items():
        result = recommend_with_checks(user_prefs, songs, k=5, mode=args.mode)
        label = name if args.mode == "balanced" else f"{name} [{args.mode}]"
        print(present(label, result))
        if args.trace:
            print("\nDecision trace:\n" + format_trace(result["trace"]))
        print()


if __name__ == "__main__":
    main()
