
import json
import sys
import traceback
import uuid
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import fitz
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

UPLOAD_FOLDER = BASE_DIR / "uploads"
DATA_FOLDER = BASE_DIR / "document_data"
UPLOAD_FOLDER.mkdir(exist_ok=True)
DATA_FOLDER.mkdir(exist_ok=True)

ERROR_LOG = BASE_DIR / "error_log.txt"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"


def ask_ollama(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )
    response.raise_for_status()

    answer = response.json().get("response", "").strip()

    if not answer:
        raise ValueError("The AI returned an empty response.")

    return answer


def extract_pdf(file_path):
    document = fitz.open(file_path)

    try:
        return [
            {"page": number, "text": page.get_text("text").strip()}
            for number, page in enumerate(document, start=1)
        ]
    finally:
        document.close()


def read_uploaded_pdf(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Please select a PDF file.")

    if not uploaded_file.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are allowed.")

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        raise ValueError("Invalid PDF filename.")

    temp_path = UPLOAD_FOLDER / f"{uuid.uuid4().hex}_{filename}"

    try:
        uploaded_file.save(temp_path)
        pages = extract_pdf(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    text = "\n\n".join(
        f"Page {page['page']}:\n{page['text']}"
        for page in pages
    )

    if not text.strip():
        raise ValueError(
            f"No selectable text found in {filename}. "
            "Scanned PDFs need OCR support."
        )

    return filename, pages, text


def generate_summary(text):
    prompt = (
        "You are DocuMind AI. Summarize only the supplied document. "
        "Do not invent facts. Use headings: Overview, Key Points, "
        "Important Dates and Names, and Conclusion. "
        "Mention absent information.\n\n"
        "DOCUMENT:\n" + text[:30000]
    )

    return ask_ollama(prompt)


def extract_keywords(text):
    prompt = (
        "You are DocuMind AI, an intelligent document analyst.\n"
        "Extract 10 to 15 important keywords or short phrases "
        "from the supplied document.\n"
        "Prioritize names, organizations, dates, technical terms, "
        "important concepts, amounts, and legal or business terms.\n"
        "Return a numbered list. Give a short explanation for each "
        "keyword. Use only information from the document. "
        "Do not invent details.\n\n"
        "DOCUMENT:\n" + text[:20000]
    )

    return ask_ollama(prompt)


def answer_question(text, question, chat_history=None):
    previous_chat = ""

    if chat_history:
        previous_chat = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join(
            f"User: {item['question']}\nAI: {item['answer']}"
            for item in chat_history[-6:]
        )

    prompt = (
        "You are DocuMind AI. Answer using only the PDF text. "
        "Use previous conversation for follow-up questions. If the answer "
        "is not in the document, say so. Do not invent facts. "
        "Use simple English.\n\n"
        "DOCUMENT:\n" + text[:25000] +
        previous_chat +
        "\n\nQUESTION:\n" + question[:1000] +
        "\n\nANSWER:"
    )

    return ask_ollama(prompt)


def compare_pdfs(text1, text2, filename1, filename2):
    prompt = (
        "Compare these two documents using only their supplied text. "
        "Do not invent facts. Clearly distinguish the documents.\n\n"
        "COMMON INFORMATION\n"
        "List key facts found in both documents.\n\n"
        "DIFFERENCES\n"
        "List meaningful differences and identify the source. "
        "If a detail is absent, say 'not stated'.\n\n"
        "AI COMPARISON REPORT\n"
        "Provide an overall comparison and conclusion.\n\n"
        f"DOCUMENT 1: {filename1}\n{text1[:10000]}\n\n"
        f"DOCUMENT 2: {filename2}\n{text2[:10000]}"
    )

    return ask_ollama(prompt)


def split_comparison_report(ai_result):
    sections = {
        "common": [],
        "differences": [],
        "report": []
    }

    heading_map = {
        "COMMON INFORMATION": "common",
        "DIFFERENCES": "differences",
        "AI COMPARISON REPORT": "report"
    }

    current = None

    for line in ai_result.splitlines():
        heading = (
            line.strip()
            .lstrip("#")
            .strip()
            .strip("*")
            .strip()
            .rstrip(":")
            .upper()
        )

        if heading in heading_map:
            current = heading_map[heading]
        elif current:
            sections[current].append(line)

    common = "\n".join(sections["common"]).strip()
    differences = "\n".join(sections["differences"]).strip()
    report = "\n".join(sections["report"]).strip()

    if not (common or differences or report):
        return (
            "See the AI Comparison Report below.",
            "See the AI Comparison Report below.",
            ai_result
        )

    return (
        common or "No common information was identified.",
        differences or "No differences were identified.",
        report or ai_result
    )


def save_document(document_id, data):
    (DATA_FOLDER / f"{document_id}.json").write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )


def load_document(document_id):
    try:
        safe_id = str(uuid.UUID(document_id))
    except (ValueError, TypeError, AttributeError):
        return None

    path = DATA_FOLDER / f"{safe_id}.json"

    if not path.is_file():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def log_error():
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as log:
            log.write("\n\n--- NEW ERROR ---\n")
            log.write(traceback.format_exc())
    except Exception:
        pass


def friendly_error(exc):
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Cannot connect to Ollama. Make sure Ollama is running."

    if isinstance(exc, requests.exceptions.Timeout):
        return "The AI took too long to respond. Please try again."

    if isinstance(exc, requests.exceptions.HTTPError):
        return "Ollama returned an error. Check that llama3.2:3b is installed."

    if isinstance(exc, ValueError):
        return str(exc)

    return (
        "Operation failed (" + type(exc).__name__ +
        "). Check error_log.txt for details."
    )


def search_pdf_pages(pages, query):
    matches = []
    query_lower = query.casefold()

    for page in pages:
        page_text = page.get("text", "")
        lower_text = page_text.casefold()
        start = 0

        while True:
            position = lower_text.find(query_lower, start)

            if position == -1:
                break

            left = max(0, position - 100)
            right = min(
                len(page_text),
                position + len(query) + 100
            )

            matches.append({
                "page": page["page"],
                "context": page_text[left:right],
                "match": query
            })

            start = position + max(1, len(query))

            if len(matches) >= 100:
                return matches

    return matches


@app.route("/", methods=["GET", "POST"])
def home():
    results = []
    comparison = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "upload")

        try:
            if action == "ask":
                document_id = request.form.get("document_id", "")
                question = request.form.get("question", "").strip()

                if not question:
                    raise ValueError("Please type a question.")

                if len(question) > 1000:
                    raise ValueError(
                        "Keep your question under 1000 characters."
                    )

                data = load_document(document_id)

                if not data:
                    raise ValueError(
                        "Document not found. Please upload it again."
                    )

                history = data.setdefault("chat_history", [])

                answer = answer_question(
                    data["text"],
                    question,
                    history
                )

                history.append({
                    "question": question,
                    "answer": answer
                })

                save_document(document_id, data)
                results.append(data)

            elif action == "search":
                document_id = request.form.get("document_id", "")
                query = request.form.get("search_query", "").strip()

                if not query:
                    raise ValueError(
                        "Please enter a word or phrase to search."
                    )

                if len(query) > 200:
                    raise ValueError(
                        "Keep your search under 200 characters."
                    )

                data = load_document(document_id)

                if not data:
                    raise ValueError(
                        "Document not found. Please upload it again."
                    )

                data["search_query"] = query
                data["search_results"] = search_pdf_pages(
                    data.get("pages", []),
                    query
                )

                results.append(data)

            elif action == "compare":
                file1 = request.files.get("pdf1")
                file2 = request.files.get("pdf2")

                if not file1 or not file1.filename:
                    raise ValueError("Please upload the first PDF.")

                if not file2 or not file2.filename:
                    raise ValueError("Please upload the second PDF.")

                filename1, pages1, text1 = read_uploaded_pdf(file1)
                filename2, pages2, text2 = read_uploaded_pdf(file2)

                ai_result = compare_pdfs(
                    text1,
                    text2,
                    filename1,
                    filename2
                )

                common, differences, report = split_comparison_report(
                    ai_result
                )

                comparison = {
                    "filename1": filename1,
                    "filename2": filename2,
                    "common": common,
                    "differences": differences,
                    "report": report
                }

            else:
                files = [
                    f for f in request.files.getlist("documents")
                    if f and f.filename
                ]

                if not files:
                    raise ValueError("Please select at least one PDF.")

                for uploaded_file in files:
                    filename, pages, text = read_uploaded_pdf(
                        uploaded_file
                    )

                    summary = generate_summary(text)
                    keywords = extract_keywords(text)
                    document_id = str(uuid.uuid4())

                    data = {
                        "document_id": document_id,
                        "filename": filename,
                        "pages": pages,
                        "page_count": len(pages),
                        "text_length": len(text),
                        "summary": summary,
                        "keywords": keywords,
                        "text": text,
                        "chat_history": []
                    }

                    save_document(document_id, data)
                    results.append(data)

        except Exception as exc:
            log_error()
            results = []
            comparison = None
            error = friendly_error(exc)

    return render_template(
        "index.html",
        results=results,
        comparison=comparison,
        error=error
    )


@app.route("/download/<document_id>/<file_type>")
def download_summary(document_id, file_type):
    data = load_document(document_id)

    if not data:
        return "Document not found. Please upload the PDF again.", 404

    if file_type not in ("txt", "pdf"):
        return "Unsupported download format.", 400

    summary = data.get("summary", "")
    filename = Path(data.get("filename", "document")).stem

    if file_type == "txt":
        return send_file(
            BytesIO(summary.encode("utf-8")),
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name=f"{filename}_summary.txt"
        )

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer
        )
        from reportlab.lib.units import inch

        buffer = BytesIO()

        pdf = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.7 * inch,
            leftMargin=0.7 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch
        )

        styles = getSampleStyleSheet()

        story = [
            Paragraph(
                "DocuMind AI - Document Summary",
                styles["Title"]
            ),
            Spacer(1, 12),
            Paragraph(
                "Document: " + escape(data.get("filename", "")),
                styles["Normal"]
            ),
            Spacer(1, 16)
        ]

        for line in summary.splitlines():
            if line.strip():
                story.append(
                    Paragraph(escape(line.strip()), styles["BodyText"])
                )
                story.append(Spacer(1, 6))

        pdf.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{filename}_summary.pdf"
        )

    except ImportError:
        return (
            "ReportLab is not installed. Run: "
            ".\\venv\\Scripts\\python.exe -m pip install reportlab",
            500
        )


@app.errorhandler(413)
def file_too_large(exc):
    return "File too large. Maximum upload size is 15 MB.", 413


if __name__ == "__main__":
    app.run(debug=True)
