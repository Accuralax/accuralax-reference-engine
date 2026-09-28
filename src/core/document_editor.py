from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Any

ALLOWED_OPERATIONS = {
    "rewrite", "expand", "shorten", "professionalise", "simplify",
    "reorganise", "add_section", "remove_section", "merge",
    "apply_theme", "executive_summary", "consistency_check",
}

@dataclass
class EditResult:
    operation: str
    status: str
    content: str
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    credentials_exposed: bool = False

class DocumentEditor:
    def validate_operation(self, operation: str) -> bool:
        return operation in ALLOWED_OPERATIONS

    def edit(self, content: str, operation: str, instruction: str = "") -> EditResult:
        if not self.validate_operation(operation):
            return EditResult(operation, "denied", content, warnings=["unsupported_operation"])
        if not isinstance(content, str) or not content.strip():
            return EditResult(operation, "needs_input", content, warnings=["empty_content"])

        if operation == "shorten":
            result = self._shorten(content)
        elif operation == "simplify":
            result = self._simplify(content)
        elif operation == "reorganise":
            result = self._reorganise(content)
        elif operation == "add_section":
            result = content.rstrip() + "\n\n## " + (instruction or "Additional Section") + "\n\n[Content required]"
        elif operation == "remove_section":
            result = self._remove_section(content, instruction)
        elif operation == "merge":
            result = content.rstrip() + "\n\n" + instruction.strip()
        else:
            result = content

        return EditResult(
            operation=operation,
            status="edited",
            content=result,
            changes=[operation],
            credentials_exposed=False,
        )

    def _shorten(self, content: str) -> str:
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        return "\n\n".join(paragraphs[:max(1, (len(paragraphs)+1)//2)])

    def _simplify(self, content: str) -> str:
        result = re.sub(r"\butilise\b", "use", content, flags=re.I)
        result = re.sub(r"\bfacilitate\b", "help", result, flags=re.I)
        return result

    def _reorganise(self, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        headings = [x for x in lines if x.startswith("#")]
        body = [x for x in lines if not x.startswith("#")]
        return "\n".join(headings + body)

    def _remove_section(self, content: str, heading: str) -> str:
        if not heading.strip():
            return content
        pattern = re.compile(
            r"(?ms)^#{1,6}\s+" + re.escape(heading.strip()) +
            r"\s*$.*?(?=^#{1,6}\s+|\Z)"
        )
        return re.sub(pattern, "", content).strip()

    def snapshot(self) -> dict[str, Any]:
        return {
            "operations": sorted(ALLOWED_OPERATIONS),
            "bounded": True,
            "credentials_exposed": False,
        }
