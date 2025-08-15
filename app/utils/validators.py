from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation

def parse_date(s: str) -> datetime:
    """
    Accepts ISO 8601: 'YYYY-MM-DDTHH:MM:SSZ' or with offset '+00:00'.
    Validates that the date is not in the future.
    """
    if not s or not s.strip():
        raise ValueError("Empty or null datetime.")

    txt = s.strip()
    # Normalize Z suffix to +00:00 for fromisoformat
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        # Fallback to common formats
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

def parse_decimal(s: str) -> Decimal:
    """
    Converts the string into a Decimal with 2 decimal places.
    Raises ValueError if the input is not numeric.
    """
    if s is None or s == "":
        raise ValueError("Empty decimal value.")
    try:
        return Decimal(str(s)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid decimal: {s}") from e
