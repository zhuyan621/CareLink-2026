"""The novice quick-start must stay aligned with the shipped launcher and model names."""

from pathlib import Path

from package_competition import ROOT


def test_new_colleague_guides_match_shipped_entrypoints():
    quick = (ROOT / "打开网页_新同事先看这个.txt").read_text(encoding="utf-8")
    detailed = (ROOT / "START_HERE_新同事打开网页.md").read_text(encoding="utf-8")
    for text in (quick, detailed):
        assert "start_demo.py --check" in text
        assert "start_demo.py" in text
        assert "http://127.0.0.1:8511/" in text
        assert "llama3:8b" in text
        assert "nomic-embed-text" in text
        assert "original_engine_package" in text
    assert (ROOT / "start_demo.py").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "careguard_web" / "index.html").is_file()
