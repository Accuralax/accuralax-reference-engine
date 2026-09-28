from src.core.mcp_tool_fabric import MCPToolFabric, ToolSpec


def test_read_tool_registration_discovery_and_execution():
    fabric = MCPToolFabric()
    fabric.register(ToolSpec("github.search", "github", "search", "read",
                             handler=lambda query: {"matches": [query]}))
    assert fabric.discover("github")[0]["tool_id"] == "github.search"
    result = fabric.execute("github.search", {"query": "repo"}, actor="agent", scope="github:read")
    assert result["allowed"]
    assert result["verified"]
    assert result["credentials_exposed"] is False


def test_side_effect_requires_approval_and_policy():
    fabric = MCPToolFabric()
    fabric.register(ToolSpec("mail.send", "email", "send", "external_side_effect",
                             handler=lambda to: {"sent": to}))
    blocked = fabric.execute("mail.send", {"to": "x"}, actor="agent", scope="email:send")
    assert blocked["reason"] == "approval_required"
    blocked2 = fabric.execute("mail.send", {"to": "x"}, actor="agent", scope="email:send", approved=True)
    assert blocked2["reason"] == "policy_check_required"
    ok = fabric.execute("mail.send", {"to": "x"}, actor="agent", scope="email:send",
                        approved=True, policy_checked=True)
    assert ok["allowed"]


def test_credentials_are_rejected():
    fabric = MCPToolFabric()
    fabric.register(ToolSpec("x.read", "x", "read", "read", handler=lambda **x: x))
    result = fabric.execute("x.read", {"api_key": "secret"}, actor="agent", scope="x:read")
    assert result["reason"] == "credential_argument_rejected"
