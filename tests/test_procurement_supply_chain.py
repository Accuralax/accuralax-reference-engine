from src.core.procurement_supply_chain import ProcurementSupplyChain


def test_procurement_health():
    p = ProcurementSupplyChain()
    assert p.health()["status"] == "ok"
    assert p.health()["credentials_exposed"] is False


def test_supplier_review_and_purchase_approval():
    p = ProcurementSupplyChain()
    supplier = p.create_supplier("CyberFusion Supplier")
    blocked_supplier = p.assess_supplier(supplier["supplier_id"], "medium")
    assert blocked_supplier["allowed"] is False
    active = p.assess_supplier(supplier["supplier_id"], "medium", reviewed=True)
    assert active["allowed"] is True

    request = p.create_purchase_request("operator", supplier["supplier_id"], 5000, "Hardware")
    blocked = p.approve_purchase_request(request["request_id"])
    assert blocked["allowed"] is False
    approved = p.approve_purchase_request(request["request_id"], approved=True)
    assert approved["allowed"] is True

    blocked_po = p.create_purchase_order(request["request_id"])
    assert blocked_po["allowed"] is False
    po = p.create_purchase_order(request["request_id"], approved=True)
    assert po["status"] == "approved"


def test_contract_inventory_and_shipment():
    p = ProcurementSupplyChain()
    supplier = p.create_supplier("Supplier")
    p.assess_supplier(supplier["supplier_id"], "low", reviewed=True)
    blocked = p.create_contract(supplier["supplier_id"], "Supply Agreement")
    assert blocked["allowed"] is False
    contract = p.create_contract(supplier["supplier_id"], "Supply Agreement", approved=True)
    assert contract["status"] == "active"

    shipment = p.record_shipment("PO-1", "planned")
    inventory = p.register_inventory("SKU-001", 25)
    assert shipment["status"] == "planned"
    assert inventory["quantity"] == 25
