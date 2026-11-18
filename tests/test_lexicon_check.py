import pytest

from src import lexicon_check as lc

CLUSTERS = {
    "up": {"arousal": "high", "valence": "high", "members": ["a", "b"]},
    "down": {"arousal": "low", "valence": "low", "members": ["c", "d"]},
}
# (valence, arousal): a, b are happy and energetic; c, d unhappy and calm.
SCORES = {"a": (0.8, 0.7), "b": (0.9, 0.6), "c": (-0.7, -0.5), "d": (-0.6, -0.6)}


def test_spearman_basics():
    assert lc.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert lc.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert lc.spearman([1, 2], [1, 2]) is None            # too few points
    assert lc.spearman([1, 1, 1], [1, 2, 3]) is None       # no variation
    assert lc.spearman([1, 2, 2, 3], [1, 2, 2, 3]) == pytest.approx(1.0)  # ties


def test_cluster_tag_check_agrees_and_detects_disagreement():
    assert all(ok for _, ok, _ in lc.cluster_tag_check(SCORES, CLUSTERS))
    flipped = dict(SCORES, a=(-0.9, -0.9), b=(-0.9, -0.9))
    assert not all(ok for _, ok, _ in lc.cluster_tag_check(flipped, CLUSTERS))


def test_coherence_and_similarity_pairs():
    within, across = lc.coherence_check(SCORES, CLUSTERS)
    assert within < across
    near, far, n_near, n_far = lc.similarity_pairs_check(SCORES, {frozenset(("a", "b")): 1.0})
    assert (n_near, n_far) == (1, 5) and near < far


def test_mood_scores_skips_missing_and_tries_variants():
    lexicon = {"laid back": (0.3, -0.4), "happy": (0.9, 0.5)}
    found = lc.mood_scores(["happy", "laid-back", "focused"], lexicon)
    assert set(found) == {"happy", "laid-back"}


def test_load_lexicon_rejects_unexpected_header(tmp_path):
    bad = tmp_path / "lex.txt"
    bad.write_text("word\tscore\nhappy\t0.9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected header"):
        lc.load_lexicon(bad)


def test_main_explains_how_to_get_the_lexicon_when_missing(tmp_path, capsys):
    assert lc.main(["--lexicon", str(tmp_path / "nope.txt")]) == 1
    err = capsys.readouterr().err
    assert "saifmohammad.com" in err and "do not redistribute" in err.lower()
