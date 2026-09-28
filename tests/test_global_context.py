from src.core.global_context import GlobalContext


def test_preferences_persist_and_override_browser(tmp_path):
    g = GlobalContext(db_path=str(tmp_path / "global.sqlite3"))
    g.set_preferences("tenant-1","workspace-1","user","user-1",{
        "country":"DE","language":"de","currency":"EUR","timezone":"Europe/Berlin"
    },"tester")
    ctx = g.resolve("tenant-1","workspace-1","user-1",{"Accept-Language":"en-US","X-Timezone":"America/New_York"})
    assert ctx["country"] == "DE"
    assert ctx["language"] == "de"
    assert ctx["currency"] == "EUR"
    assert ctx["timezone"] == "Europe/Berlin"


def test_invalid_global_preferences_rejected(tmp_path):
    g = GlobalContext(db_path=str(tmp_path / "global.sqlite3"))
    try:
        g.set_preferences("t","w","user","u",{"country":"ZZ"})
        assert False
    except ValueError as exc:
        assert str(exc) == "unsupported_country"
