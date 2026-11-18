from src import main as app
from src import traces
from src.main import PROFILES, SONGS_CSV
from src.recommender import load_songs
from src.reliability import format_trace, recommend_with_checks

SONGS = load_songs(str(SONGS_CSV))


def steps(result):
    return [item["step"] for item in result["trace"]]


def test_normal_profile_trace_goes_straight_to_recommend():
    result = recommend_with_checks(PROFILES["Deep Intense Rock"], SONGS)
    assert steps(result) == ["sanitize", "rank", "confidence", "decision"]
    assert result["trace"][-1]["detail"].startswith("RECOMMEND")


def test_low_confidence_trace_records_each_relaxation_attempt():
    result = recommend_with_checks({"genre": "metal", "mood": "romantic", "energy": 0.05,
                                    "likes_acoustic": False}, SONGS)
    assert steps(result) == ["sanitize", "rank", "confidence", "relax", "decision"]
    relax = result["trace"][3]["detail"]
    for key in ("genre", "mood", "energy", "likes_acoustic"):
        assert f"without '{key}'" in relax
    assert result["trace"][-1]["detail"].startswith("RELAX: ignore 'energy'")


def test_no_strong_match_and_rejection_are_traced():
    unfixable = recommend_with_checks({"genre": "metal", "mood": "romantic", "energy": 0.0,
                                       "valence": 0.0, "acousticness": 1.0}, SONGS)
    assert unfixable["trace"][-1]["detail"].startswith("NO STRONG MATCH")
    rejected = recommend_with_checks(PROFILES["Adversarial: likes_acoustic='maybe'"], SONGS)
    assert steps(rejected)[-1] == "decision" and rejected["trace"][-1]["detail"].startswith("REJECT")


def test_repairs_appear_in_the_sanitize_step():
    result = recommend_with_checks({"genre": "Pop", "energy": 1.5}, SONGS)
    assert "clamped energy" in result["trace"][0]["detail"] and "normalised genre" in result["trace"][0]["detail"]


def test_format_trace_numbers_the_steps():
    text = format_trace([{"step": "a", "detail": "x"}, {"step": "b", "detail": "y"}])
    assert text == "1. [a] x\n2. [b] y"


def test_cli_trace_flag_prints_the_chain(capsys):
    app.main(["--ask", "mellow music for studying", "--trace"])
    out = capsys.readouterr().out
    assert "Decision trace:" in out and "[interpret]" in out and "[decision]" in out


def test_cli_without_flag_prints_no_trace(capsys):
    app.main(["--ask", "mellow music for studying"])
    assert "Decision trace" not in capsys.readouterr().out


def test_trace_document_covers_every_outcome_kind():
    text = traces.build()
    for needle in ("[interpret]", "RECOMMEND", "RELAX", "NO STRONG MATCH", "REJECT"):
        assert needle in text
    assert text == traces.build()  # deterministic, so the committed file only changes when the code does
