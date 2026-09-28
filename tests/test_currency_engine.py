from src.core.currency_engine import CurrencyEngine

def test_currency_metadata_and_conversion_audit(tmp_path):
    e = CurrencyEngine(str(tmp_path / 'finance.sqlite3'))
    assert e.metadata('ZAR')['minor_unit'] == 2
    result = e.convert(100, 'ZAR', 'USD', 0.055, 'test-rate-source')
    assert result['converted_amount'] == 5.5
    assert result['source_currency'] == 'ZAR'

def test_exchange_rate_requires_source(tmp_path):
    e = CurrencyEngine(str(tmp_path / 'finance.sqlite3'))
    try:
        e.set_rate('ZAR', 'USD', 0.05, '')
    except ValueError as exc:
        assert str(exc) == 'invalid_exchange_rate'
    else:
        assert False
