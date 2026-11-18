"""
Optional embedding-based request parser (experimental).

Instead of matching keywords, it embeds the request with a sentence-embedding
model and picks the nearest mood and energy "prototype" phrase. That lets it read
paraphrases the keyword list does not know ("music to unwind after a long day").

It is a gap-filler, not a replacement: rules still handle goals ("cheer me up")
and negation ("not sad"), which sentence embeddings are poor at, and anything the
rules find wins. The encoder is any object with encode(list_of_str) returning one
vector per string, so tests can use a tiny fake and the heavy model is only
loaded when someone asks for it. Install it with:  pip install -r requirements-embeddings.txt
"""

import math
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Similarity cut-offs chosen on the tuning half of data/nl_benchmark.json (see
# reports/parser_benchmark.md); the held-out half was not used to pick them.
TUNED_MOOD_THRESHOLD = 0.45
TUNED_ENERGY_THRESHOLD = 0.30

# Short descriptive phrases per catalog mood. Several phrases per mood make the
# match less dependent on one wording.
MOOD_PROTOTYPES: Dict[str, List[str]] = {
    "chill": ["chill and calm", "laid-back relaxing vibes"],
    "relaxed": ["relaxed, unwinding and peaceful", "soothing music to relax"],
    "laid-back": ["easygoing laid-back sunny vibe"],
    "focused": ["focused, concentrating on work or study"],
    "happy": ["happy, cheerful and joyful"],
    "euphoric": ["euphoric, ecstatic and thrilled", "dancing all night at a party"],
    "confident": ["confident, bold and powerful"],
    "intense": ["intense, driving and powerful"],
    "aggressive": ["angry, furious and aggressive"],
    "sad": ["sad, crying and heartbroken"],
    "melancholic": ["melancholic, gloomy and sorrowful"],
    "moody": ["moody, dark and brooding"],
    "nostalgic": ["nostalgic, remembering the past"],
    "romantic": ["romantic, loving and tender"],
}

# (energy value, description): the energy of the nearest description is returned.
ENERGY_PROTOTYPES: List[Tuple[float, str]] = [
    (0.15, "very quiet, slow, sleepy music"),
    (0.30, "calm, soft and mellow"),
    (0.55, "moderate, steady and easygoing"),
    (0.80, "upbeat, lively and energetic"),
    (0.93, "very loud, fast, high-energy and intense"),
]

# If the request contains a negator, an embedding-derived mood is not trusted:
# embeddings place "not sad" next to "sad".
NEGATOR = re.compile(r"(?<![a-z])(?:not|no|never|without|don'?t|doesn'?t|isn'?t|aren'?t|nothing|but)(?![a-z])")


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def default_encoder(model_name: str = DEFAULT_MODEL):
    """Loads a sentence-transformers model; raises a clear error if the package is missing."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("embedding parser needs sentence-transformers: "
                           "pip install -r requirements-embeddings.txt") from error
    model = SentenceTransformer(model_name)

    class _Encoder:
        def encode(self, texts: List[str]):
            return [[float(x) for x in vec] for vec in model.encode(texts, normalize_embeddings=True)]

    return _Encoder()


class EmbeddingParser:
    """Nearest-prototype mood and energy from a sentence embedding."""

    def __init__(self, encoder, mood_threshold: float = TUNED_MOOD_THRESHOLD,
                 energy_threshold: float = TUNED_ENERGY_THRESHOLD):
        self.encoder = encoder
        self.mood_threshold = mood_threshold
        self.energy_threshold = energy_threshold
        mood_texts = [(mood, phrase) for mood, phrases in MOOD_PROTOTYPES.items() for phrase in phrases]
        self._mood_labels = [m for m, _ in mood_texts]
        self._mood_vecs = encoder.encode([p for _, p in mood_texts])
        self._energy_values = [v for v, _ in ENERGY_PROTOTYPES]
        self._energy_vecs = encoder.encode([d for _, d in ENERGY_PROTOTYPES])

    def scores(self, text: str) -> Tuple[Tuple[str, float], Tuple[float, float]]:
        """((best mood, similarity), (best energy, similarity)) with no thresholding."""
        vec = self.encoder.encode([text])[0]
        mood = max(zip(self._mood_labels, (cosine(vec, v) for v in self._mood_vecs)), key=lambda t: t[1])
        energy = max(zip(self._energy_values, (cosine(vec, v) for v in self._energy_vecs)), key=lambda t: t[1])
        return mood, energy

    def parse(self, text: str) -> Dict:
        """Preferences from the nearest prototypes, each kept only if its similarity clears the threshold."""
        (mood, mood_sim), (energy, energy_sim) = self.scores(text)
        prefs: Dict = {}
        if mood_sim >= self.mood_threshold:
            prefs["mood"] = mood
        if energy_sim >= self.energy_threshold:
            prefs["energy"] = energy
        return prefs


def hybrid_parse(text: str, keyword_prefs: Dict, parser: EmbeddingParser) -> Dict:
    """
    Rules first, embeddings fill the gaps. Anything the keyword/goal rules found wins.
    An embedding-derived mood is dropped when the request contains a negator.
    """
    prefs = parser.parse(text)
    if "mood" in prefs and NEGATOR.search(text.lower()):
        del prefs["mood"]
    prefs.update(keyword_prefs)
    return prefs
