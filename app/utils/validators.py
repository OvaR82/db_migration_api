from datetime import datetime, timezone

def parse_date(s: str) -> datetime:
    """
    Accepts ISO 8601: 'YYYY-MM-DDTHH:MM:SSZ' or with an offset like '+00:00'.
    Rejects future dates.
    """
    if not s or not s.strip():
        raise ValueError("Empty or null datetime.")

    txt = s.strip()
    # Normalize the Z suffix to +00:00 for fromisoformat
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        # Fall back to common formats
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(txt, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Invalid date: {s}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if dt > datetime.now(tz=timezone.utc):
        raise ValueError(f"Future hire_date is not allowed: {dt.isoformat()}")

    return dt
