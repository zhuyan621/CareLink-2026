from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parent.parent / "careguard_app.py"


def test_navigation_does_not_reset_synthetic_case_input():
    app = AppTest.from_file(str(APP_PATH)).run(timeout=15)
    note = app.text_area[0].value
    heart_rate = app.number_input[0].value
    assert note
    assert heart_rate == 112

    app.radio[0].set_value(app.radio[0].options[1]).run(timeout=15)
    app.radio[0].set_value(app.radio[0].options[0]).run(timeout=15)

    assert not app.exception
    assert app.text_area[0].value == note
    assert app.number_input[0].value == heart_rate


def test_homepage_explains_cases_system_and_limits():
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    content = "\n".join(block.value for block in app.markdown)

    assert "交接班不是一句“情况不好”" in content
    assert "?focus=workspace&amp;case=chest" in content
    assert "?focus=workspace&amp;case=stroke" in content
    assert "?focus=workspace&amp;case=change" in content
    assert "有刹车的协作链" in content
    assert "把“不知道”也设计进界面" in content
    assert "没有有效动态证据时，显示空结果" in content
