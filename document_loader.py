"""
document_loader.py

Handles PDF validation and text extraction for the RAG chatbot.
Beginner approach: pypdf for extraction, one entry per non-empty page with
(document name, page number) kept as metadata so answers can always cite
their source.
"""
from dataclasses import dataclass
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_FILE_SIZE_MB = 20
ALLOWED_EXTENSIONS = (".pdf",)


class DocumentLoadError(Exception):
    """Raised when a file cannot be validated or read as a PDF."""


@dataclass
class PageRecord:
    doc_name: str
    page_number: int  # 1-indexed, matches what a human would see in a PDF viewer
    text: str


def validate_file(filename: str, file_size_bytes: int) -> None:
    lower = filename.lower()
    if not lower.endswith(ALLOWED_EXTENSIONS):
        raise DocumentLoadError(f"Unsupported file type: '{filename}'. Only PDF files are accepted.")
    size_mb = file_size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise DocumentLoadError(
            f"'{filename}' is {size_mb:.1f} MB, which exceeds the {MAX_FILE_SIZE_MB} MB limit."
        )


def extract_pages(filename: str, file_bytes: bytes) -> list[PageRecord]:
    """
    Extracts text from every page of a PDF, skipping empty pages safely.
    Returns a list of PageRecord (one per non-empty page), each carrying the
    original filename and 1-indexed page number as metadata.
    """
    try:
        reader = PdfReader(__import__("io").BytesIO(file_bytes))
    except PdfReadError as exc:
        raise DocumentLoadError(f"Could not read '{filename}' as a PDF: {exc}") from exc

    if reader.is_encrypted:
        raise DocumentLoadError(f"'{filename}' is password-protected and cannot be processed.")

    records: list[PageRecord] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        if not text:
            # Skip empty / scanned-image pages safely (OCR is an optional
            # extension, intentionally not implemented in this submission).
            continue
        records.append(PageRecord(doc_name=filename, page_number=i, text=text))

    if not records:
        raise DocumentLoadError(
            f"No extractable text found in '{filename}'. It may be a scanned/image-only PDF "
            "(OCR is not implemented in this beginner version)."
        )
    return records


def extract_multiple(files: list[tuple[str, bytes]]) -> list[PageRecord]:
    """files: list of (filename, file_bytes) tuples. Returns combined page records."""
    all_records: list[PageRecord] = []
    for filename, file_bytes in files:
        validate_file(filename, len(file_bytes))
        all_records.extend(extract_pages(filename, file_bytes))
    return all_records


if __name__ == "__main__":
    import glob
    for path in glob.glob("documents/*.pdf"):
        with open(path, "rb") as f:
            data = f.read()
        recs = extract_pages(path.split("/")[-1], data)
        print(f"{path}: {len(recs)} non-empty pages, first page preview: {recs[0].text[:60]!r}")
