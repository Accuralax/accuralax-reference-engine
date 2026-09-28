from src.core.internationalization import Internationalization


def test_auto_switch_south_africa():
    i = Internationalization()
    ctx = i.resolve(headers={'Accept-Language':'en-ZA,en;q=0.9','X-Timezone':'Africa/Johannesburg'})
    assert ctx['country'] == 'ZA'
    assert ctx['currency'] == 'ZAR'
    assert ctx['language'] == 'en'
    assert ctx['timezone'] == 'Africa/Johannesburg'
    assert ctx['postal_field'] == 'postal_code'
    assert ctx['measurement_system'] == 'metric'


def test_explicit_profile_overrides_browser():
    i = Internationalization()
    ctx = i.resolve(
        user={'country':'DE','language':'de','currency':'EUR','timezone':'Europe/Berlin'},
        headers={'Accept-Language':'en-US,en;q=0.9','X-Timezone':'America/New_York'},
    )
    assert ctx['country'] == 'DE'
    assert ctx['language'] == 'de'
    assert ctx['currency'] == 'EUR'
    assert ctx['timezone'] == 'Europe/Berlin'
    assert ctx['text_direction'] == 'ltr'


def test_invalid_timezone_falls_back():
    i = Internationalization()
    ctx = i.resolve(headers={'Accept-Language':'en-US','X-Timezone':'Not/AZone'})
    assert ctx['timezone'] == i.default_timezone
