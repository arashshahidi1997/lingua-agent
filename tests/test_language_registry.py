from lingua_agent.languages import LanguagePair, get_language, list_languages
from lingua_agent.languages.scripts import detect_dominant_script


def test_seed_languages_present():
    codes = {lang.code for lang in list_languages()}
    assert codes == {"en", "fa", "it", "ru", "de", "nl"}


def test_german_and_dutch_are_ltr_latin():
    for code in ("de", "nl"):
        lang = get_language(code)
        assert lang.script.value == "latin"
        assert lang.direction.value == "ltr"
        assert lang.transliteration_supported is False


def test_persian_is_rtl():
    fa = get_language("fa")
    assert fa.direction.value == "rtl"
    assert fa.script.value == "arabic"
    assert fa.transliteration_supported is True


def test_italian_is_ltr_latin():
    it = get_language("it")
    assert it.direction.value == "ltr"
    assert it.script.value == "latin"


def test_russian_cyrillic():
    ru = get_language("ru")
    assert ru.script.value == "cyrillic"
    assert ru.direction.value == "ltr"


def test_language_pair_validates_distinct():
    pair = LanguagePair.from_codes("en", "fa", "en")
    assert pair.is_rtl_target() is True
    assert pair.key == "en->fa"
    import pytest
    with pytest.raises(ValueError):
        LanguagePair.from_codes("en", "en")


def test_script_detection():
    assert detect_dominant_script("hello world") == "latin"
    assert detect_dominant_script("سلام دنیا") == "arabic"
    assert detect_dominant_script("Привет мир") == "cyrillic"
    assert detect_dominant_script("12345 ...") is None
