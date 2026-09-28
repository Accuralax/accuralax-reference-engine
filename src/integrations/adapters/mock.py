from __future__ import annotations

from .base import MockBusinessAdapter


def build_mock_adapters() -> dict[str, MockBusinessAdapter]:
    systems = {
        "whatsapp": {"read_messages", "send_message", "create_handoff"},
        "make": {"trigger_webhook", "read_scenario_status"},
        "hubspot": {"search_contact", "search_company", "search_deal", "create_contact", "create_company", "create_deal", "update_contact", "update_deal", "create_task"},
        "website": {"read_form_submission", "create_lead", "update_lead"},
        "social": {"read_messages", "publish_post", "create_lead"},
        "qx": {"read_account", "read_reports"},
        "wolas": {"read_agent_status", "create_task", "read_usage"},
    }
    return {name: MockBusinessAdapter(name, actions) for name, actions in systems.items()}
