import re
from pathlib import Path
from typing import List, Tuple, Dict

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pdfplumber = None

try:
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None
    pytesseract = None

WEIGHT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(kg|g|kilogram(?:s)?|gram(?:s)?|lb|pound(?:s)?)\b", re.I)
DIMENSION_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch(?:es)?)"
    r"(?:\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch(?:es)?))?"
    r"(?:\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch(?:es)?))?",
    re.I,
)


def extract_text(path: str) -> str:
    """Return the textual content of ``path``.

    ``path`` may reference a PDF, an image or a plain text file.  Optional
    dependencies are used for PDF and image support.  If the required
    libraries are not installed, an informative error is raised.
    """

    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        if not pdfplumber:
            raise ImportError("pdfplumber is required to extract text from PDFs")
        text_parts: List[str] = []
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        if not (Image and pytesseract):
            raise ImportError("Pillow and pytesseract are required for OCR support")
        img = Image.open(p)
        return pytesseract.image_to_string(img)
    return p.read_text(errors="ignore")


def find_weights_and_dimensions(text: str) -> Dict[str, List[str]]:
    """Return weights and dimensions found in ``text``.

    Weight matches are returned as ``<value> <unit>`` strings.  Dimension
    matches are returned using ``x`` separators (e.g. ``10 mm x 20 mm``).
    """

    weights = [f"{value} {unit}" for value, unit in WEIGHT_RE.findall(text)]

    dimensions: List[str] = []
    for match in DIMENSION_RE.findall(text):
        parts = []
        for value, unit in zip(match[::2], match[1::2]):
            if value:
                parts.append(f"{value} {unit}")
        if parts:
            dimensions.append(" x ".join(parts))
    return {"weights": weights, "dimensions": dimensions}


def scan_document(path: str) -> Dict[str, List[str]]:
    """Extract weights and dimensions from a document or drawing."""

    text = extract_text(path)
    return find_weights_and_dimensions(text)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Extract weights and dimensions from technical documents or drawings"
    )
    parser.add_argument("path", help="Path to document (PDF, image or text file)")
    args = parser.parse_args()

    result = scan_document(args.path)
    print(json.dumps(result, indent=2))
