from app.dependencies import load_settings


def test_get_settings_reuses_cached_instance() -> None:
    load_settings.cache_clear()
    first = load_settings()
    second = load_settings()

    assert first is second
    load_settings.cache_clear()
