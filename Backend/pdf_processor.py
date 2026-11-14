
import fitz


def extract_text_from_pdf(file_path):
    """Extract text and page numbers from a PDF."""
    document = fitz.open(file_path)
    pages = []

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text")
            pages.append({
                "page": page_number,
                "text": text.strip()
            })
    finally:
        document.close()

    return pages
