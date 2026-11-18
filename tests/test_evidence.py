from src import evidence as ev


def test_sanitize_paths_removes_plain_and_escaped_project_path():
    root = str(ev.ROOT)
    escaped = root.replace(chr(92), chr(92) * 2)
    text = f"no such file: {root}/data/x.csv and repr {escaped}/data/y.csv"
    out = ev.sanitize_paths(text)
    assert root not in out and escaped not in out and "<project>" in out


def test_trim_keeps_header_first_songs_and_footer():
    block = "\n\n".join(["HEADER"] + [f"{i}. Song {i}\n   Score: 0.5" for i in range(1, 6)])
    block = block + "\n\n" + "-" * 64 + "\nConfidence: HIGH"
    out = ev.trim(block, 2)
    assert "1. Song 1" in out and "2. Song 2" in out and "3. Song 3" not in out
    assert "... (3 more)" in out and out.endswith("Confidence: HIGH")
    assert ev.trim("no result block here", 2) == "no result block here"


def test_block_shows_command_and_output():
    text = ev.block("python -m src.main", "hello")
    assert "$ python -m src.main" in text and "hello" in text


def test_evaluation_never_touches_a_live_model_even_when_a_key_is_set(monkeypatch):
    import pytest
    anthropic = pytest.importorskip("anthropic")
    from src import evaluate

    def boom(*args, **kwargs):
        raise AssertionError("evaluation tried to build a live Anthropic client")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(anthropic, "Anthropic", boom)
    _, passed, total = evaluate.run()
    assert passed == total
    import os
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-not-real"  # restored afterwards
