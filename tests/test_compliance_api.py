import json
from src.api_server import Handler

def test_compliance_module_imports():
    from src.api_server import compliance
    assert compliance.config["id"] == "CFS-BUSINESS-COMPLIANCE-MATRIX"
