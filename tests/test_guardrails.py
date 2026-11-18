import json
import logging

import pytest

from src import main as app
from src import taxonomy
from src.main import SONGS_CSV
from src.nl_query import MAX_REQUEST_CHARS, parse_request
from src.recommender import load_songs

SONGS = load_songs(str(SONGS_CSV))
HEADER = "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"


def _csv(tmp_path, body, header=HEADER):
    path = tmp_path / "songs.csv"
    path.write_text(header + body, encoding="utf-8")
    return str(path)


def test_load_songs_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_songs(str(tmp_path / "nope.csv"))


def test_load_songs_names_bad_value(tmp_path):
    path = _csv(tmp_path, "1,A,B,pop,happy,loud,100,0.5,0.5,0.5\n")
    with pytest.raises(ValueError, match="line 2: energy must be a number"):
        load_songs(path)


def test_load_songs_missing_column_and_empty(tmp_path):
    with pytest.raises(ValueError, match="missing required column"):
        load_songs(_csv(tmp_path, "", header="id,title\n"))
    with pytest.raises(ValueError, match="no songs"):
        load_songs(_csv(tmp_path, ""))


def test_main_exits_cleanly_when_catalog_missing(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(app, "SONGS_CSV", tmp_path / "missing.csv")
    with pytest.raises(SystemExit) as exit_info:
        app.main([])
    assert exit_info.value.code == 1
    assert "Cannot start" in capsys.readouterr().out


@pytest.mark.parametrize("text", ["", "   ", None])
def test_blank_request_is_reported_not_guessed(text):
    prefs, notes, _ = parse_request(text, SONGS)
    assert prefs == {} and any("empty request" in n for n in notes)


def test_blank_ask_does_not_run_default_profiles(capsys):
    app.main(["--ask", ""])
    out = capsys.readouterr().out
    assert "empty request" in out and "High-Energy Pop" not in out
    assert "TOP RECOMMENDATIONS" not in out


def test_gibberish_ask_prints_message_not_arbitrary_ranking(capsys):
    app.main(["--ask", "asdf qwerty"])
    out = capsys.readouterr().out
    assert "Could not find any music preferences" in out
    assert "TOP RECOMMENDATIONS" not in out


def test_long_request_is_truncated_before_llm():
    seen = {}

    class Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                seen["text"] = kwargs["messages"][0]["content"]
                raise RuntimeError("stop here")

    _, notes, _ = parse_request("calm " * 1000, SONGS, client=Client)
    assert len(seen["text"]) <= MAX_REQUEST_CHARS
    assert any("longer than" in n for n in notes)


def test_corrupt_taxonomy_degrades_instead_of_crashing(tmp_path, caplog):
    bad = tmp_path / "taxonomy.json"
    bad.write_text("{not json", encoding="utf-8")
    taxonomy.load_taxonomy.cache_clear()
    with caplog.at_level(logging.ERROR, logger="vibescorecard.taxonomy"):
        data = taxonomy.load_taxonomy(str(bad))
    assert data["genres"]["families"] == {}
    assert "taxonomy unusable" in caplog.text
    taxonomy.load_taxonomy.cache_clear()


def test_taxonomy_with_missing_keys_or_duplicate_label_is_rejected(tmp_path):
    for content in ({"genres": {}}, json.loads(open(taxonomy.TAXONOMY_PATH, encoding="utf-8").read())):
        if "families" in content.get("genres", {}):
            content["genres"]["families"]["extra"] = {"members": ["pop"]}  # pop is already in 'pop'
        path = tmp_path / "t.json"
        path.write_text(json.dumps(content), encoding="utf-8")
        taxonomy.load_taxonomy.cache_clear()
        assert taxonomy.load_taxonomy(str(path))["genres"]["families"] == {}
    taxonomy.load_taxonomy.cache_clear()
