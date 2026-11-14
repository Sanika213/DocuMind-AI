# DocuMind AI – Intelligent Document Investigator

## Project Overview
DocuMind AI is an AI-powered document analysis application that helps users upload, understand, search, and compare PDF documents. It uses Python, Flask, and a locally running Ollama LLM to provide intelligent document insights.

## Key Features

- **PDF Upload:** Upload and process PDF documents.
- **AI-Powered Summary:** Generate summaries with Overview, Key Points, Important Dates and Names, and Conclusion.
- **Keyword Extraction:** Identify important keywords from uploaded documents.
- **Smart Search:** Search for specific information and find matching page numbers.
- **Ask AI Questions:** Ask questions about uploaded PDF documents and receive AI-generated answers.
- **PDF Comparison:** Compare two PDF documents and identify common information and differences.
- **Download Reports:** Download document summaries and comparison reports.
- **Text Extraction:** Extract and display text page by page.
- **File Validation:** Validate file types and handle empty uploads.

## Technologies Used

| Category | Technology |
|---|---|
| Programming Language | Python |
| Backend Framework | Flask |
| Frontend | HTML, CSS, JavaScript |
| AI / LLM | Ollama |
| AI Model | Llama 3.2 (3B) |
| PDF Processing | PyMuPDF |
| HTTP Requests | Requests |

## Project Structure

```text
DocuMind_AI/
│
├── Backend/
│   ├── app.py
│   └── pdf_processor.py
│
├── templates/
│   └── index.html
│
├── static/
│   └── style.css
│
├── uploads/
├── document_data/
├── reports/
├── venv/
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd DocuMind_AI
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Install Dependencies

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Install and Start Ollama

Download Ollama from:

https://ollama.com/

Pull the AI model:

```bash
ollama pull llama3.2:3b
```

Start the model:

```bash
ollama run llama3.2:3b
```

### 5. Run the Flask Application

Open another terminal and execute:

```bash
python Backend/app.py
```

### 6. Open in Browser

```text
http://127.0.0.1:5000
```

## Application Workflow

1. Upload a PDF document.
2. Extract text from the document.
3. Generate an AI-powered summary.
4. Extract important keywords.
5. Search for information within the PDF.
6. Ask questions and receive AI-generated answers.
7. Upload two PDFs to compare their content.
8. Download the generated reports.

## Future Enhancements

- Support for additional document formats.
- Advanced document analytics.
- Multi-language document support.
- Improved AI-based information retrieval.
- User authentication and document management.

## Project Status

**Completed – Core features implemented and tested.**

## Author

**Sanika Nitin Kamble**

Computer Science and Engineering Graduate

AI | Python | Web Development | Generative AI
