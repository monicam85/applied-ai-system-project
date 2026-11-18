import sys

import pytest

from src import embed_parse as ep
from src import main as app
from src.main import SONGS_CSV
from src.nl_query import parse_request
from src.recommender import load_songs

SONGS = load_songs(str(SONGS_CSV))


class BagOfWordsEncoder:
    """Tiny deterministic stand-in for a sentence-embedding model: word-count vectors."""

    def __init__(self):
        words = {w.strip(",.") for phrases in ep.MOOD_PROTOTYPES.values() for p in phrases for w in p.split()}
        words |= {w.strip(",.") for _, d in ep.ENERGY_PROTOTYPES for w in d.split()}
        self.vocab = sorted(words)

    def encode(self, texts):
        return [[float(t.lower().replace(",", " ").split().count(w)) for w in self.vocab] for t in texts]


@pytest.fixture
def parser():
    return ep.EmbeddingParser(BagOfWordsEncoder(), mood_threshold=0.3, energy_threshold=0.3)


def test_cosine_basics():
    assert ep.cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert ep.cosine([1, 0], [0, 1]) == 0.0
    assert ep.cosine([0, 0], [1, 1]) == 0.0


def test_nearest_prototype_wins(parser):
    assert parser.parse("feeling angry and furious")["mood"] == "aggressive"
    assert parser.parse("calm, soft and mellow")["energy"] == 0.30


def test_below_threshold_returns_nothing(parser):
    assert parser.parse("zzzz qqqq") == {}


def test_hybrid_rules_win_over_embeddings(parser):
    out = ep.hybrid_parse("sad and heartbroken", {"mood": "happy"}, parser)
    assert out["mood"] == "happy"


def test_hybrid_drops_embedding_mood_when_negated(parser):
    assert "mood" not in ep.hybrid_parse("not sad and crying and heartbroken", {}, parser)
    assert ep.hybrid_parse("sad crying heartbroken", {}, parser)["mood"] == "sad"


def test_parse_request_uses_embedder_when_no_llm(parser, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    prefs, notes, source = parse_request("happy cheerful and joyful", SONGS, embedder=parser)
    assert source == "embeddings+keywords" and prefs["mood"] == "happy"


def test_broken_embedder_falls_back_to_keywords(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class Broken:
        def parse(self, text):
            raise RuntimeError("model exploded")

    prefs, notes, source = parse_request("something mellow for studying", SONGS, embedder=Broken())
    assert source == "keywords" and prefs.get("mood") == "chill"
    assert any("embedding parse failed" in n for n in notes)


def test_default_encoder_explains_missing_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(RuntimeError, match="requirements-embeddings.txt"):
        ep.default_encoder()


def test_cli_flag_degrades_when_model_unavailable(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(app, "default_encoder", lambda: (_ for _ in ()).throw(RuntimeError("no model")))
    app.main(["--ask", "mellow music for studying", "--embeddings"])
    out = capsys.readouterr().out
    assert "--embeddings unavailable" in out and "TOP RECOMMENDATIONS" in out


def test_embedding_note_does_not_claim_keyword_fallback(parser, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, notes, source = parse_request("happy cheerful and joyful", SONGS, embedder=parser)
    assert source == "embeddings+keywords"
    assert not any("used keyword fallback" in n for n in notes)
