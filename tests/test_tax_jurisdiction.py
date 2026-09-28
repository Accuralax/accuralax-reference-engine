from src.core.tax_jurisdiction import TaxJurisdictionEngine

def test_tax_calculation_and_audit(tmp_path):
    e = TaxJurisdictionEngine(str(tmp_path / 'tax.sqlite3'))
    result = e.calculate('ZA', 1000)
    assert result['tax_amount'] == 150
    assert result['rate'] == 0.15
    assert result['audit_id'].startswith('TAX-')

def test_tax_rate_required_for_variable_jurisdiction(tmp_path):
    e = TaxJurisdictionEngine(str(tmp_path / 'tax.sqlite3'))
    try:
        e.calculate('US', 1000)
    except ValueError as exc:
        assert str(exc) == 'tax_rate_required'
    else:
        assert False
