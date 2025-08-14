from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation

def parse_date(s: str) -> datetime:
    """
    Acepta ISO 8601: 'YYYY-MM-DDTHH:MM:SSZ' o con offset '+00:00'.
    Valida que no sea futura.
    """
    if not s or not s.strip():
        raise ValueError("Fecha/hora vacía o nula.")

    txt = s.strip()
    # Normaliza sufijo Z a +00:00 para fromisoformat
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        # fallback a formatos comunes
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(txt, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Fecha inválida: {s}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if dt > datetime.now(tz=timezone.utc):
        raise ValueError(f"hire_date futura no permitida: {dt.isoformat()}")

    return dt

def parse_decimal(s: str) -> Decimal:
    """
    Convierte la cadena en Decimal con 2 decimales.
    Lanza ValueError si el valor no es numérico.
    """
    if s is None or s == "":
        raise ValueError("Valor decimal vacío.")
    try:
        return Decimal(str(s)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Decimal inválido: {s}") from e

