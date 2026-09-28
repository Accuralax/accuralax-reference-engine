from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def _parse(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone_required")
    return dt


def to_utc(value):
    return _parse(value).astimezone(timezone.utc)


def localize(value, tz_name):
    try:
        zone = ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError("invalid_timezone") from exc
    return to_utc(value).astimezone(zone)


def session_time_view(session, timezone_name):
    start = localize(session["scheduled_start"], timezone_name)
    end = localize(session["scheduled_end"], timezone_name)
    result = dict(session)
    result["scheduled_start_utc"] = to_utc(session["scheduled_start"]).isoformat()
    result["scheduled_end_utc"] = to_utc(session["scheduled_end"]).isoformat()
    result["scheduled_start_local"] = start.isoformat()
    result["scheduled_end_local"] = end.isoformat()
    result["display_timezone"] = timezone_name
    result["display_date"] = start.strftime("%Y-%m-%d")
    result["display_time"] = f"{start:%H:%M}–{end:%H:%M}"
    return result
