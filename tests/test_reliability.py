import pytest

from src.main import SONGS_CSV
from src.nl_query import keyword_parse, parse_request
from src.recommender import load_songs, recommend_songs
from src.reliability import assess_confidence, recommend_with_checks, sanitize_prefs

SONGS = load_songs(str(SONGS_CSV))


def test_sanitize_normalises_case_and_clamps():
    clean, warnings = sanitize_prefs({"genre": " Pop ", "energy": 1.5}, SONGS)
    assert clean == {"genre": "pop", "energy": 1.0}
    assert len(warnings) == 2


def test_sanitize_drops_unknown_genre_and_wrong_types():
    clean, warnings = sanitize_prefs({"genre": "vaporwave", "energy": "high"}, SONGS)
    assert clean == {}
    assert len(warnings) == 2


def test_empty_profile_has_no_confidence():
    result = recommend_with_checks({}, SONGS)
    assert result["confidence"]["level"] == "none"


def test_ordinary_profile_is_high_and_contradictory_is_not():
    good = recommend_with_checks({"genre": "pop", "mood": "happy", "energy": 0.85,
                                  "likes_acoustic": False}, SONGS)
    bad = recommend_with_checks({"genre": "folk", "mood": "sad", "energy": 0.9,
                                 "likes_acoustic": True}, SONGS)
    assert good["confidence"]["level"] == "high"
    assert bad["confidence"]["level"] != "high"


def test_invalid_acoustic_string_returns_error_not_exception():
    result = recommend_with_checks({"genre": "rock", "likes_acoustic": "maybe"}, SONGS)
    assert result["error"] and result["recommendations"] == []


def test_keyword_parse_and_fallback_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    prefs, notes, source = parse_request("calm study session", SONGS)
    assert source == "keywords" and prefs["mood"] in {"chill", "focused"}
    assert any("fallback" in n for n in notes)


def test_llm_reply_is_validated():
    class Client:
        messages = None
        def __init__(self):
            self.messages = self
        def create(self, **_):
            class B: text = '{"genre": "vaporwave", "energy": 3, "mood": "sad"}'
            class R: content = [B()]
            return R()
    prefs, _, source = parse_request("anything", SONGS, client=Client())
    assert source == "llm"
    assert prefs == {"energy": 1.0, "mood": "sad"}


def test_low_confidence_relaxes_the_conflicting_preference():
    result = recommend_with_checks({"genre": "metal", "mood": "romantic", "energy": 0.05,
                                    "likes_acoustic": False}, SONGS)
    assert result["relaxed_dropped"] == "energy"
    assert result["confidence"]["level"] in ("medium", "high")
    assert not result["no_strong_match"]


def test_unfixable_profile_is_flagged_not_presented_as_a_match():
    result = recommend_with_checks({"genre": "metal", "mood": "romantic", "energy": 0.0, "valence": 0.0, "acousticness": 1.0}, SONGS)
    assert result["no_strong_match"] is True


def test_relaxation_never_reduces_to_fewer_than_two_preferences():
    result = recommend_with_checks({"genre": "metal", "mood": "romantic"}, SONGS)
    assert result["relaxed_dropped"] is None  # only 2 prefs: nothing is dropped
    assert len(result["prefs"]) == 2


def test_present_withholds_pick_list_on_no_strong_match():
    from src.main import present
    result = recommend_with_checks({"genre": "metal", "mood": "romantic", "energy": 0.0, "valence": 0.0, "acousticness": 1.0}, SONGS)
    text = present("Test", result)
    assert "NO STRONG MATCH" in text and "Score:" not in text


def test_logging_writes_to_file(tmp_path):
    import logging
    handler = logging.FileHandler(tmp_path / "t.log")
    logger = logging.getLogger("vibescorecard")
    logger.addHandler(handler); logger.setLevel(logging.INFO)
    try:
        recommend_with_checks({"genre": "Pop"}, SONGS)
        handler.flush()
    finally:
        logger.removeHandler(handler); handler.close()
    assert "confidence=" in (tmp_path / "t.log").read_text()


def test_workout_is_not_misread_as_a_focus_mood():
    prefs = keyword_parse("gym workout")
    assert "mood" not in prefs and prefs["energy"] >= 0.8


def test_keyword_parser_matches_words_not_substrings():
    assert keyword_parse("brunch playlist") == {}          # 'run' is inside 'brunch'
    assert keyword_parse("music for running")["energy"] == 0.85
    assert keyword_parse("melancholy evening")["mood"] == "melancholic"


def test_goal_phrases_describe_the_wanted_state_not_the_current_one():
    assert keyword_parse("I'm sad, cheer me up")["mood"] == "happy"
    assert keyword_parse("cheer me up") == {"mood": "happy"}
    assert keyword_parse("wake me up") == {"energy": 0.85}
    assert keyword_parse("calm me down")["mood"] == "chill"
    assert keyword_parse("I feel sad")["mood"] == "sad"  # no goal phrase: state words still count


def test_negated_words_are_skipped_not_flipped():
    assert keyword_parse("I am not sad") == {}
    assert keyword_parse("nothing too calm please").get("mood") is None
    assert "likes_acoustic" not in keyword_parse("no acoustic please")
    assert keyword_parse("acoustic guitar")["likes_acoustic"] is True


def test_llm_prompt_tells_the_model_to_read_the_wanted_state():
    from src.nl_query import _system_prompt
    prompt = _system_prompt(SONGS)
    assert "WANTS" in prompt and "cheer me up" in prompt and "not sad" in prompt


class _Block:
    def __init__(self, type_, text=None):
        self.type = type_
        if text is not None:
            self.text = text


def _client_returning(*blocks):
    class Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                class Reply:
                    content = list(blocks)
                return Reply()
    return Client()


def test_reply_that_starts_with_a_thinking_block_is_parsed():
    # Seen from the live API: content[0] is a thinking block with no .text, content[1] holds the JSON.
    client = _client_returning(_Block("thinking"), _Block("text", '{"mood": "focused", "energy": 0.35}'))
    prefs, notes, source = parse_request("anything", SONGS, client=client)
    assert source == "llm" and prefs == {"mood": "focused", "energy": 0.35}
    assert not any("failed" in n for n in notes)


def test_reply_with_no_text_block_falls_back_cleanly():
    client = _client_returning(_Block("thinking"))
    prefs, notes, source = parse_request("something mellow for studying", SONGS, client=client)
    assert source == "keywords" and prefs.get("mood") == "chill"
    assert any("LLM parse failed" in n for n in notes)


def test_multiple_text_blocks_are_joined():
    client = _client_returning(_Block("text", "Here you go: "), _Block("text", '{"mood": "happy"}'))
    prefs, _, source = parse_request("anything", SONGS, client=client)
    assert source == "llm" and prefs == {"mood": "happy"}
