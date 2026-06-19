import io
import logging


logger = logging.getLogger("genifi.pdf")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""

    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF parsing requires pypdf or PyPDF2. Install backend requirements first."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Text extraction failed on page %s: %s", page_number, exc)
                page_text = ""
            if page_text.strip():
                pages.append(page_text.strip())
        return "\n\n".join(pages).strip()
    except Exception as exc:
        raise RuntimeError("The uploaded file is not a readable PDF.") from exc
