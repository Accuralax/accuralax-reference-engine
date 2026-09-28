from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class NormalizedResponse:
    ok: bool
    status: str
    data: dict[str,Any]
    error_code: str|None=None
    retryable: bool=False
    provider: str=""

def normalize(provider: str, result: Any) -> NormalizedResponse:
    if hasattr(result,"ok"):
        if result.ok:
            return NormalizedResponse(True,"completed",dict(result.data or {}),provider=provider)
        error=result.error or "provider_operation_failed"
        return NormalizedResponse(False,"failed",{},_error_code(error),_retryable(error),provider)
    if isinstance(result,dict):
        if result.get("ok") is False:
            error=str(result.get("error") or "provider_operation_failed")
            return NormalizedResponse(False,"failed",{},_error_code(error),_retryable(error),provider)
        return NormalizedResponse(True,"completed",dict(result),provider=provider)
    return NormalizedResponse(True,"completed",{"value":result},provider=provider)

def _error_code(error: str) -> str:
    return error.split(":",1)[0].strip().lower().replace(" ","_")

def _retryable(error: str) -> bool:
    e=error.lower()
    return any(x in e for x in ("timeout","temporar","rate","429","connection","unavailable"))
