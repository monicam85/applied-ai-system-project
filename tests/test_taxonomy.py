import csv
from pathlib import Path

from src import taxonomy as tx
from src import recommender as rec

SONGS = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def _catalog():
    with open(SONGS, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_every_catalog_label_is_classified():
    rows = _catalog()
    assert all(tx.genre_family(r["genre"]) for r in rows)
    assert all(tx.mood_cluster(r["mood"]) for r in rows)


def test_similarity_basics():
    assert tx.genre_similarity("rock", "rock") == 1.0
    assert tx.genre_similarity("rock", "metal") == 0.5
    assert tx.genre_similarity("rock", "jazz") == 0.0
    assert tx.mood_similarity("chill", "focused") == 0.6
    assert tx.mood_similarity("chill", "aggressive") == 0.0


def test_covers_existing_recommender_relations():
    for pair in rec.RELATED_GENRES:
        a, b = tuple(pair)
        assert tx.genre_similarity(a, b) > 0, pair
    for pair in rec.MOOD_SIMILARITY:
        a, b = tuple(pair)
        assert tx.mood_similarity(a, b) > 0, pair


def test_recommender_uses_taxonomy_for_unlisted_pairs():
    # hip-hop and reggae are in one family but not in RELATED_GENRES.
    assert frozenset(("hip-hop", "reggae")) not in rec.RELATED_GENRES
    base = {"genre": "hip-hop"}
    reggae = next(r for r in rec.load_songs(str(SONGS)) if r["genre"] == "reggae")
    score, reasons = rec.score_song(base, reggae)
    assert score > 0 and any("genre is close" in r for r in reasons)


def test_hand_tuned_value_wins_over_taxonomy():
    # chill/relaxed is hand-tuned at 0.7; the cluster fallback is 0.6.
    assert rec._mood_credit("chill", "relaxed") == 0.7


# --- Competency questions -----------------------------------------------------
# Borrowed from ontology evaluation (Rashid, De Roure & McGuinness, "A Music Theory
# Ontology", SAAM 2018): list the questions the taxonomy must be able to answer and
# test each one. Each test below is one such question.

import itertools
import statistics

CATALOG_GENRES = sorted({r["genre"] for r in _catalog()})
CATALOG_MOODS = sorted({r["mood"] for r in _catalog()})


def _members(section, group_key):
    return tx.load_taxonomy()[section][group_key]


def test_cq_which_genres_share_a_family_with_a_given_genre():
    family = lambda g: {x for x in CATALOG_GENRES if tx.genre_family(x) == tx.genre_family(g)} - {g}
    assert family("rock") == {"metal"}
    assert family("hip-hop") == {"r&b", "reggae"}
    assert family("country") == {"folk"}


def test_cq_does_every_label_belong_to_exactly_one_group():
    for section, key in (("genres", "families"), ("moods", "clusters")):
        seen = [m for g in _members(section, key).values() for m in g["members"]]
        assert len(seen) == len(set(seen)), f"a {section} label is in two groups"
    assert set(CATALOG_GENRES) <= {m for g in _members("genres", "families").values() for m in g["members"]}
    assert set(CATALOG_MOODS) <= {m for g in _members("moods", "clusters").values() for m in g["members"]}


def test_cq_is_similarity_symmetric_and_bounded():
    for fn, labels in ((tx.genre_similarity, CATALOG_GENRES), (tx.mood_similarity, CATALOG_MOODS)):
        for a, b in itertools.product(labels, repeat=2):
            assert fn(a, b) == fn(b, a)
            assert 0.0 <= fn(a, b) <= 1.0
            if a != b:
                assert fn(a, b) < 1.0, "only an exact match may earn full credit"


def test_cq_do_opposite_moods_earn_nothing():
    assert tx.mood_similarity("sad", "euphoric") == 0.0
    assert tx.mood_similarity("aggressive", "relaxed") == 0.0
    assert tx.genre_similarity("metal", "classical") == 0.0


def test_cq_do_adjacent_pairs_actually_cross_a_boundary():
    # An adjacent pair inside one group would be redundant with the group credit.
    for section, lookup in (("genres", tx.genre_family), ("moods", tx.mood_cluster)):
        for a, b in tx.load_taxonomy()[section]["adjacent"]:
            assert lookup(a) != lookup(b), f"{a}/{b} already share a group"
            assert lookup(a) and lookup(b), f"{a}/{b} has an unclassified label"


def test_cq_does_every_mood_cluster_describe_its_feel():
    for name, cluster in _members("moods", "clusters").items():
        assert cluster["arousal"] in {"low", "high"}, name
        assert cluster["valence"] in {"low", "high"}, name


def test_cq_do_cluster_labels_agree_with_the_catalog_data():
    # The arousal/valence tags are judgements; check they match the measured songs.
    by_cluster = {}
    for row in _catalog():
        by_cluster.setdefault(tx.mood_cluster(row["mood"]), []).append(row)
    mean = lambda name, col: statistics.mean(float(r[col]) for r in by_cluster[name])
    clusters = _members("moods", "clusters")
    high = [n for n, c in clusters.items() if c["arousal"] == "high"]
    low = [n for n, c in clusters.items() if c["arousal"] == "low"]
    assert min(mean(n, "energy") for n in high) > max(mean(n, "energy") for n in low)
    pos = [n for n, c in clusters.items() if c["valence"] == "high"]
    neg = [n for n, c in clusters.items() if c["valence"] == "low"]
    assert min(mean(n, "valence") for n in pos) > max(mean(n, "valence") for n in neg)


def test_cq_do_slow_and_fast_moods_differ_in_tempo():
    # Habibi & Damasio (2014), citing Juslin (2000): sad music tends to be slow, fear/tension music faster.
    tempo = lambda moods: statistics.mean(float(r["tempo_bpm"]) for r in _catalog() if r["mood"] in moods)
    assert tempo({"sad", "melancholic"}) < tempo({"intense", "aggressive"})
    clusters = _members("moods", "clusters")
    by_arousal = {"high": [], "low": []}
    for row in _catalog():
        by_arousal[clusters[tx.mood_cluster(row["mood"])]["arousal"]].append(float(row["tempo_bpm"]))
    assert statistics.mean(by_arousal["high"]) > statistics.mean(by_arousal["low"])


def test_cq_are_peaceful_and_tender_moods_neighbours():
    # Trost et al. (2012), cited by Habibi & Damasio: positive valence + low arousal covers
    # peacefulness, tenderness and nostalgia, so these moods should earn some credit.
    assert tx.mood_cluster("relaxed") != tx.mood_cluster("romantic")
    assert tx.mood_similarity("relaxed", "romantic") > 0
    assert tx.mood_similarity("relaxed", "nostalgic") > 0
    assert _members("moods", "clusters")["wistful"]["valence"] == "high"
