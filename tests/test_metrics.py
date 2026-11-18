import pytest

from src import metrics as mx

LOUD = {"id": 1, "artist": "A", "genre": "rock", "energy": 1.0, "valence": 1.0, "danceability": 1.0, "acousticness": 1.0}
QUIET = {"id": 2, "artist": "B", "genre": "folk", "energy": 0.0, "valence": 0.0, "danceability": 0.0, "acousticness": 0.0}
COPY = dict(LOUD, id=3)


def test_song_distance_bounds():
    assert mx.song_distance(LOUD, LOUD) == 0.0
    assert mx.song_distance(LOUD, QUIET) == 1.0


def test_intra_list_diversity():
    assert mx.intra_list_diversity([LOUD]) == 0.0
    assert mx.intra_list_diversity([LOUD, COPY]) == 0.0
    assert mx.intra_list_diversity([LOUD, QUIET]) == 1.0
    assert mx.intra_list_diversity([LOUD, COPY, QUIET]) == pytest.approx(2 / 3)


def test_coverage_counts_distinct_songs_and_genres():
    lists = [[LOUD, QUIET], [LOUD]]
    assert mx.catalog_coverage(lists, 4) == 0.5
    assert mx.genre_coverage(lists, [LOUD, QUIET, COPY]) == 1.0
    assert mx.catalog_coverage([], 0) == 0.0


def test_exposure_concentration():
    counts = mx.exposure_counts([[LOUD, QUIET], [LOUD, COPY], [LOUD]])
    assert counts[1] == 3 and sum(counts.values()) == 5
    assert mx.top_share(counts, 1) == 0.6
    assert mx.top_share(counts, 3) == 1.0


def test_gini_extremes():
    assert mx.gini([2, 2, 2, 2]) == 0.0
    assert mx.gini([0, 0, 0, 8]) == pytest.approx(0.75)
    assert mx.gini([]) == 0.0 and mx.gini([0, 0]) == 0.0


def test_serendipity_proxy_counts_only_relevant_off_genre_picks():
    recs = [(LOUD, 0.9, ""), (QUIET, 0.7, ""), (COPY, 0.2, "")]
    assert mx.serendipity_counts(recs, "rock") == (1, 2)   # folk is relevant and off-genre; COPY is not relevant
    assert mx.serendipity_counts(recs, None) == (0, 0)
