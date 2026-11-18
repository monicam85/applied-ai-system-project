"""
Compares request parsers on the hand-labelled benchmark in data/nl_benchmark.json.

Methods: keywords (the current fallback), embeddings (nearest prototype only) and
hybrid (rules first, embeddings fill gaps). The two embedding thresholds are
chosen on the tuning split (even-numbered cases) and every method is reported on
the held-out test split (odd-numbered cases) as well as overall, so a threshold
cannot be tuned to the numbers that are reported. With only 36 cases the
differences are suggestive, not statistically strong.

    python -m src.benchmark_parsers      # writes reports/parser_benchmark.md

The embedding rows need sentence-transformers; without it only keywords run.
"""

import json
from collections import defaultdict
from itertools import product
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    from .embed_parse import EmbeddingParser, default_encoder, hybrid_parse
    from .nl_query import keyword_parse
except ImportError:
    from embed_parse import EmbeddingParser, default_encoder, hybrid_parse
    from nl_query import keyword_parse

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "data" / "nl_benchmark.json"
REPORT = ROOT / "reports" / "parser_benchmark.md"
GRID = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def band(energy: Optional[float]) -> str:
    if energy is None:
        return "none"
    return "low" if energy <= 0.45 else "high" if energy >= 0.7 else "mid"


def judge(case: Dict, prefs: Dict) -> Tuple[bool, bool]:
    """(mood acceptable, energy acceptable) for one parsed result."""
    mood = prefs.get("mood", "")
    if "forbid" in case:
        mood_ok = mood not in case["forbid"]
    else:
        mood_ok = mood in case["ok"]
    wanted = case["energy"]
    energy_ok = wanted == "any" or band(prefs.get("energy")) == wanted
    return mood_ok, energy_ok


def accuracy(cases: List[Dict], parse: Callable[[str], Dict]) -> Tuple[float, float, float]:
    """(mood accuracy, energy accuracy, both-correct accuracy)."""
    results = [judge(case, parse(case["text"])) for case in cases]
    n = len(results) or 1
    return (sum(m for m, _ in results) / n, sum(e for _, e in results) / n,
            sum(m and e for m, e in results) / n)


def split(cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    return cases[0::2], cases[1::2]


def tune(cases: List[Dict], make_parse: Callable[[float, float], Callable[[str], Dict]]) -> Tuple[float, float]:
    """Threshold pair with the best both-correct accuracy on `cases` (ties go to the higher thresholds)."""
    best, best_score = (GRID[0], GRID[0]), -1.0
    for mood_t, energy_t in product(GRID, GRID):
        score = accuracy(cases, make_parse(mood_t, energy_t))[2]
        if score >= best_score:
            best, best_score = (mood_t, energy_t), score
    return best


def by_kind(cases: List[Dict], parse: Callable[[str], Dict]) -> Dict[str, Tuple[int, int]]:
    out: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for case in cases:
        mood_ok, energy_ok = judge(case, parse(case["text"]))
        out[case["kind"]][0] += mood_ok and energy_ok
        out[case["kind"]][1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def main() -> int:
    cases = json.loads(BENCHMARK.read_text(encoding="utf-8"))["cases"]
    dev, test = split(cases)
    methods: Dict[str, Callable[[str], Dict]] = {"keywords": keyword_parse}
    notes: List[str] = []
    try:
        from_encoder = default_encoder()
        make_emb = lambda m, e: EmbeddingParser(from_encoder, m, e).parse
        make_hyb = lambda m, e: (lambda t, p=EmbeddingParser(from_encoder, m, e): hybrid_parse(t, keyword_parse(t), p))
        m_t, e_t = tune(dev, make_emb)
        methods["embeddings"] = make_emb(m_t, e_t)
        notes.append(f"embeddings thresholds chosen on the tuning split: mood {m_t}, energy {e_t}")
        m_h, e_h = tune(dev, make_hyb)
        methods["hybrid"] = make_hyb(m_h, e_h)
        notes.append(f"hybrid thresholds chosen on the tuning split: mood {m_h}, energy {e_h}")
    except RuntimeError as error:
        notes.append(f"embedding rows skipped: {error}")

    lines = ["# Request-parser benchmark", "",
             f"{len(cases)} hand-labelled requests ({len(dev)} tuning, {len(test)} held-out test) from "
             "`data/nl_benchmark.json`. Both-correct = mood acceptable AND energy band acceptable. "
             "Small sample: treat gaps of a few points as noise.", ""]
    lines += [f"- {n}" for n in notes] + ["",
              "| Method | Held-out test: both correct | Test mood | Test energy | Overall both correct |",
              "|---|---|---|---|---|"]
    for name, parse in methods.items():
        tm, te, tb = accuracy(test, parse)
        _, _, ob = accuracy(cases, parse)
        lines.append(f"| {name} | {tb:.0%} | {tm:.0%} | {te:.0%} | {ob:.0%} |")
    kinds = sorted({c["kind"] for c in cases})
    lines += ["", "Both-correct by request type (all 36 cases; correct / total):", "",
              "| Method | " + " | ".join(kinds) + " |", "|---|" + "---|" * len(kinds)]
    for name, parse in methods.items():
        counts = by_kind(cases, parse)
        lines.append(f"| {name} | " + " | ".join(f"{counts[k][0]}/{counts[k][1]}" for k in kinds) + " |")
    lines += ["", "Cases each method gets wrong:", ""]
    for name, parse in methods.items():
        wrong = [c["text"] for c in cases if not all(judge(c, parse(c["text"])))]
        lines.append(f"- **{name}** ({len(wrong)}): " + "; ".join(f'"{t}"' for t in wrong))
    if "hybrid" in methods:
        lines += ["", "## Where the specialized parser (hybrid) differs from the baseline (keywords)", "",
                  "Every benchmark request where the two outputs differ. Judged against the labels in "
                  "`data/nl_benchmark.json` (mood acceptable and energy band acceptable).", "",
                  "| Request | Baseline output | Specialized output | Baseline | Specialized |",
                  "|---|---|---|---|---|"]
        verdict = lambda c, prefs: "right" if all(judge(c, prefs)) else "wrong"
        differing = better = worse = 0
        for case in cases:
            base, spec = methods["keywords"](case["text"]), methods["hybrid"](case["text"])
            if base == spec:
                continue
            differing += 1
            b, sp = verdict(case, base), verdict(case, spec)
            better += (b, sp) == ("wrong", "right")
            worse += (b, sp) == ("right", "wrong")
            lines.append(f"| {case['text']} | `{json.dumps(base)}` | `{json.dumps(spec)}` | {b} | {sp} |")
        lines += ["", f"Outputs differ on {differing} of {len(cases)} requests: the specialized parser fixes "
                  f"{better}, breaks {worse}, and the rest are different but equally right or equally wrong."]
    text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
