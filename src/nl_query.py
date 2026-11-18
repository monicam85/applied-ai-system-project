"""
Natural-language front end: turns a sentence like "something mellow for studying"
into the preferences dict the scorer understands.

An LLM does the interpretation (when ANTHROPIC_API_KEY is set); the existing
deterministic scorer still does all ranking, so every pick stays explainable.
The LLM's answer is treated as untrusted: it is parsed as JSON, restricted to the
known keys, and then cleaned by reliability.sanitize_prefs. With no API key, or
if the call or the JSON fails, a keyword parser takes over so the feature degrades
instead of breaking.
"""

import json
import logging
import os
import re
from typing import Callable, Dict, List, Optional, Tuple

try:
    from .embed_parse import hybrid_parse
    from .reliability import catalog_vocabulary, sanitize_prefs
except ImportError:
    from embed_parse import hybrid_parse
    from reliability import catalog_vocabulary, sanitize_prefs

log = logging.getLogger("vibescorecard.nl_query")

MODEL = "claude-haiku-5-5"
MAX_REQUEST_CHARS = 500  # longer text is cut before it reaches the LLM
TIMEOUT_SECONDS = 20.0  # a hung network call must not hang the app
MAX_TOKENS = 1024  # headroom: the reply may include thinking tokens before the JSON
ALLOWED_KEYS = {"genre", "mood", "energy", "likes_acoustic", "valence"}

# Everyday words mapped to catalog moods / energy levels for the offline fallback.
MOOD_WORDS = {
    "chill": "chill", "calm": "chill", "mellow": "chill", "relax": "relaxed",
    "study": "focused", "focus": "focused", "happy": "happy",
    "upbeat": "happy", "sad": "sad", "melanchol": "melancholic", "angry": "aggressive",
    "aggressive": "aggressive", "intense": "intense", "party": "euphoric",
    "euphoric": "euphoric", "romantic": "romantic", "nostalg": "nostalgic",
    "moody": "moody", "confident": "confident",
}
ENERGY_WORDS = {
    "workout": 0.9, "gym": 0.9, "run": 0.85, "party": 0.9, "dance": 0.85,
    "high-energy": 0.9, "energetic": 0.85, "mellow": 0.3, "chill": 0.3,
    "calm": 0.25, "sleep": 0.15, "study": 0.35, "relax": 0.3, "quiet": 0.2,
}


def _system_prompt(songs: List[Dict]) -> str:
    vocab = catalog_vocabulary(songs)
    return (
        "You convert a listener's request into JSON preferences for a music "
        "recommender. Reply with ONE JSON object and nothing else. Allowed keys: "
        f"genre (one of {sorted(vocab['genre'])}), mood (one of {sorted(vocab['mood'])}), "
        "energy (number 0-1), valence (number 0-1, how positive), likes_acoustic "
        "(true or false). Omit any key the request gives no evidence for. "
        "Never invent preferences. Describe the state the listener WANTS the music to "
        "put them in, not the state they are in: \"I'm sad, cheer me up\" means mood "
        "happy. Ignore negated preferences: \"not sad\" gives no mood."
    )


def _extract_json(text: str) -> Dict:
    """Pulls the first {...} block out of a model reply and parses it."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model reply")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model reply was not a JSON object")
    return data


# Requests often name the state the listener WANTS, not the one they are in
# ("I'm sad, cheer me up" wants happy music). People mainly use music to regulate
# their mood and arousal (Schaefer et al., 2013, Frontiers in Psychology), so these
# goal phrases are checked first and take precedence over single mood words.
GOAL_PHRASES = [
    (r"cheer(?:s|ed)? me up|cheer up|lift my (?:mood|spirits)|make me (?:feel )?happy", {"mood": "happy"}),
    (r"wake me up|get me going|pump me up|energi[sz]e me|make me (?:more )?alert|keep me awake", {"energy": 0.85}),
    (r"calm me|calm down|help me relax|relax me|wind down|help me sleep", {"mood": "chill", "energy": 0.25}),
    (r"help me (?:focus|concentrate)|keep me focused", {"mood": "focused", "energy": 0.35}),
]

# A negator within a few words before a keyword cancels it: "not sad" is not "sad".
NEGATION = re.compile(r"(?<![a-z])(?:not|no|never|without|don'?t|doesn'?t|isn'?t|aren'?t|nothing)\s+(?:\w+\s+){0,2}$")


def _find_word(word: str, text: str) -> bool:
    """
    True if `word` starts a word in text and is not negated. 'run' matches 'running'
    but not 'brunch'; 'sad' in 'not sad' does not count.
    """
    for match in re.finditer(r"(?<![a-z])" + re.escape(word), text):
        if not NEGATION.search(text[:match.start()]):
            return True
    return False


def keyword_parse(text: str) -> Dict:
    """
    Offline fallback: guesses mood, energy and acoustic feel from simple keywords.

    Goal phrases ("cheer me up", "wake me up") are read first as the state the
    listener wants. Negated words ("not sad") are skipped rather than flipped to
    their opposite. Known limit: it never reads genre words.
    """
    lowered = text.lower()
    prefs: Dict = {}
    for pattern, goal in GOAL_PHRASES:
        if re.search(r"(?<![a-z])(?:" + pattern + ")", lowered):
            for key, value in goal.items():
                prefs.setdefault(key, value)
    if "mood" not in prefs:
        for word, mood in MOOD_WORDS.items():
            if _find_word(word, lowered):
                prefs["mood"] = mood
                break
    if "energy" not in prefs:
        for word, energy in ENERGY_WORDS.items():
            if _find_word(word, lowered):
                prefs["energy"] = energy
                break
    if re.search(r"(?<![a-z])(acoustic|unplugged|guitar)", lowered) and not NEGATION.search(
            lowered[:re.search(r"(?<![a-z])(acoustic|unplugged|guitar)", lowered).start()]):
        prefs["likes_acoustic"] = True
    return prefs


def _reply_text(reply) -> str:
    """
    Joins the text blocks of a model reply. A reply can begin with a "thinking" block
    that has no .text, so reading content[0].text is wrong; blocks without text are skipped.
    """
    texts = [block.text for block in reply.content
             if getattr(block, "type", "text") == "text" and hasattr(block, "text")]
    if not texts:
        raise ValueError("model reply had no text block")
    return "\n".join(texts)


def _llm_parse(text: str, songs: List[Dict], client) -> Dict:
    reply = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=_system_prompt(songs),
        messages=[{"role": "user", "content": text}],
    )
    return _extract_json(_reply_text(reply))


def parse_request(text: str, songs: List[Dict], client=None, embedder=None) -> Tuple[Dict, List[str], str]:
    """
    Returns (prefs, notes, source) where source is "llm", "embeddings+keywords" or "keywords".

    `client` is any object with an Anthropic-style messages.create; when None one is
    built from ANTHROPIC_API_KEY if that variable is set. `embedder` is an optional
    embed_parse.EmbeddingParser used instead of the plain keyword fallback when the
    LLM is unavailable: rules still win, embeddings fill the gaps. notes lists every repair
    and fallback so the caller can show the user what happened.
    """
    notes: List[str] = []
    raw: Optional[Dict] = None
    source = "keywords"

    text = (text or "").strip()
    if not text:
        log.warning("empty request")
        return {}, ["empty request; nothing to interpret"], source
    if len(text) > MAX_REQUEST_CHARS:
        log.warning("request truncated from %d to %d chars", len(text), MAX_REQUEST_CHARS)
        notes.append(f"request was longer than {MAX_REQUEST_CHARS} characters; the rest was ignored")
        text = text[:MAX_REQUEST_CHARS]

    if client is None and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS, max_retries=1)

    if client is not None:
        try:
            raw = _llm_parse(text, songs, client)
            source = "llm"
            log.info("LLM parsed %r -> %s", text, raw)
        except Exception as error:  # network, auth, bad JSON: all fall back
            log.error("LLM parse failed for %r: %s: %s", text, type(error).__name__, error)
            notes.append(f"LLM parse failed ({type(error).__name__}); used keyword fallback")
    else:
        log.warning("no ANTHROPIC_API_KEY; using keyword fallback")
        notes.append("no ANTHROPIC_API_KEY; used keyword fallback")

    if raw is None and embedder is not None:
        try:
            raw = hybrid_parse(text, keyword_parse(text), embedder)
            source = "embeddings+keywords"
            notes = [n.replace("used keyword fallback", "used the embedding parser") for n in notes]
            log.info("embedding parser read %r -> %s", text, raw)
        except Exception as error:  # a broken model must not break the app
            log.error("embedding parse failed for %r: %s: %s", text, type(error).__name__, error)
            notes.append(f"embedding parse failed ({type(error).__name__}); used keyword fallback")
    if raw is None:
        raw = keyword_parse(text)

    unknown = set(raw) - ALLOWED_KEYS
    if unknown:
        notes.append(f"ignored unexpected keys: {sorted(unknown)}")
    raw = {k: v for k, v in raw.items() if k in ALLOWED_KEYS}

    prefs, warnings = sanitize_prefs(raw, songs)
    return prefs, notes + warnings, source
