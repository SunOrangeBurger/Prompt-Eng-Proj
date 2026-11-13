"""Independent repository: read an invoice inside the configured folder."""
from pathlib import Path


def read_invoice(root: str, filename: str) -> str:
    path = Path(root) / filename
    return path.read_text(encoding="utf-8")
