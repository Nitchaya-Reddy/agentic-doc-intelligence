from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def extract_text(filename: str, content_type: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()

    if suffix in {".txt", ".md", ".markdown", ".csv"} or content_type.startswith("text/"):
        return raw.decode("utf-8", errors="replace").strip()

    raise ValueError("Unsupported file type. Upload PDF, TXT, MD, or CSV.")
