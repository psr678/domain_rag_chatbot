from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image, ListFlowable, ListItem, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleC', fontSize=19, leading=23, spaceAfter=4, textColor=colors.HexColor('#1a3d5c')))
styles.add(ParagraphStyle(name='SubInfo', fontSize=10, leading=14, textColor=colors.HexColor('#444444'), spaceAfter=10))
styles.add(ParagraphStyle(name='H2s', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#2c5a7c'), spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle(name='Bodys', parent=styles['Normal'], fontSize=9.8, leading=13.5, spaceAfter=7))
styles.add(ParagraphStyle(name='Caption', parent=styles['Normal'], fontSize=8.5, alignment=1, textColor=colors.HexColor('#555555'), spaceAfter=10))
styles.add(ParagraphStyle(name='CellHead', parent=styles['Normal'], fontSize=8.6, leading=10.5, textColor=colors.white, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle(name='CellBody', parent=styles['Normal'], fontSize=8.4, leading=10.5))
styles.add(ParagraphStyle(name='CellBodyCenter', parent=styles['Normal'], fontSize=8.4, leading=10.5, alignment=1))
styles.add(ParagraphStyle(name='HighlightHead', parent=styles['Normal'], fontSize=11, leading=14, textColor=colors.HexColor('#1a3d5c'), fontName='Helvetica-Bold', spaceAfter=4))
styles.add(ParagraphStyle(name='HighlightBody', parent=styles['Normal'], fontSize=9.2, leading=12.8, spaceAfter=5))
styles.add(ParagraphStyle(name='CellLink', parent=styles['Normal'], fontSize=8.4, leading=10.5, textColor=colors.HexColor('#1a56db')))

def cell(text, style=None):
    return Paragraph(text, style or styles['CellBody'])

story = []

story.append(Paragraph("Domain-Specific RAG Chatbot for PDF Question Answering", styles['TitleC']))
story.append(Paragraph("Major Project Report", styles['SubInfo']))

info_table = Table([
    ["Student:", "Raju_P_S", "Batch:", "AIML Batch", "Date:", "3 September 2026"],
], colWidths=[0.5*inch, 1.3*inch, 0.5*inch, 1.3*inch, 0.45*inch, 1.3*inch])
info_table.setStyle(TableStyle([
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
    ('FONTNAME', (4,0), (4,-1), 'Helvetica-Bold'),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story.append(info_table)
story.append(Spacer(1, 4))

REPO = "https://github.com/psr678/domain_rag_chatbot"

def link_cell(text, url, style=None):
    return Paragraph(f'<link href="{url}"><u>{text}</u></link>', style or styles['CellLink'])

story.append(Paragraph("Submission Deliverables &amp; GitHub Repository Links", styles['H2s']))
story.append(Paragraph(
    f'All source code, documents, and supporting files referenced below are in the public GitHub '
    f'repository: <link href="{REPO}"><u>{REPO}</u></link>. This report is self-contained -- every '
    f'deliverable required by the assignment brief is listed here with a direct link to its exact '
    f'location, so this PDF alone is sufficient for submission and review.', styles['Bodys']))

deliverables = [
    ["1", "Working Streamlit application", link_cell("app.py", f"{REPO}/blob/main/app.py")],
    ["2", "Complete source code", link_cell("repository root (all .py modules)", f"{REPO}")],
    ["3", "Sample PDF documents", link_cell("documents/ (4 fictional HR policy PDFs)", f"{REPO}/tree/main/documents")],
    ["4", "requirements.txt", link_cell("requirements.txt", f"{REPO}/blob/main/requirements.txt")],
    ["5", "README (setup &amp; usage instructions)", link_cell("README.md", f"{REPO}/blob/main/README.md")],
    ["6", "Architecture / workflow diagram", link_cell("architecture_diagram.png", f"{REPO}/blob/main/architecture_diagram.png")],
    ["7", "Testing sheet (20 questions, min. 15 required)", link_cell("tests/test_questions.csv", f"{REPO}/tree/main/tests")],
    ["8", "GitHub repository", link_cell(REPO.replace("https://", ""), REPO)],
    ["9", "Project report &amp; demonstration video", Paragraph(
        'This PDF report (self-contained). Demonstration video: '
        f'<link href="{REPO}/blob/main/demo_video.mp4"><u>demo_video.mp4</u></link>', styles['CellBody'])],
]
deliv_rows = [[cell("#", styles['CellHead']), cell("Deliverable", styles['CellHead']), cell("Location / Link", styles['CellHead'])]]
for num, name, loc in deliverables:
    loc_cell = loc if isinstance(loc, Paragraph) else cell(loc)
    deliv_rows.append([cell(num, styles['CellBodyCenter']), cell(name), loc_cell])

dt = Table(deliv_rows, colWidths=[0.3*inch, 2.35*inch, 3.05*inch])
dt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a3d5c')),
    ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#cccccc')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f2f6f9')]),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(dt)
story.append(Spacer(1, 8))

story.append(PageBreak())

story.append(Paragraph("1. Project Objective", styles['H2s']))
story.append(Paragraph(
    "Build a Retrieval-Augmented Generation (RAG) chatbot that answers questions from user-uploaded "
    "PDF documents. The chatbot retrieves the most relevant passages from the uploaded documents and "
    "generates an answer based only on those passages, citing the source document and page number.", styles['Bodys']))

story.append(Paragraph("2. Problem Statement", styles['H2s']))
story.append(Paragraph(
    "Large documents (policies, manuals, handbooks) are tedious to search manually -- a user may need "
    "to read many pages to find one answer. This project solves that by letting users upload documents "
    "and ask questions in natural language, getting a grounded, cited answer instead.", styles['Bodys']))

story.append(Paragraph("3. Approach Used", styles['H2s']))
story.append(Paragraph(
    "The <b>beginner approach</b> specified in the project brief: <b>pypdf</b> for PDF text extraction "
    "with page-level metadata, LangChain's <b>RecursiveCharacterTextSplitter</b> for chunking (900 "
    "characters, 130-character overlap), the pretrained <b>sentence-transformers/all-MiniLM-L6-v2</b> "
    "embedding model, and <b>FAISS</b> (IndexFlatIP / cosine similarity) for the vector store. "
    "Retrieved chunks are passed to <b>Google Gemini (gemini-3.6-flash)</b> with a strict "
    "context-only prompt, and a relevance-threshold check makes the chatbot refuse to answer rather "
    "than guess when nothing relevant is found.", styles['Bodys']))
story.append(Paragraph(
    "<b>Embedding runtime note:</b> the MiniLM model is loaded via the <b>fastembed</b> library (ONNX "
    "Runtime) rather than PyTorch, for a much lighter dependency footprint -- same pretrained model, "
    "same 384-dimension embedding space. If the model can't be downloaded from huggingface.co for any "
    "reason, vector_store.py automatically falls back to an offline TF-IDF embedder with a clear warning "
    "logged every time, so the app degrades gracefully instead of crashing. See tests/evaluation_notes.md "
    "for full details on this fallback.", styles['Bodys']))

story.append(Paragraph("4. Architecture / Workflow", styles['H2s']))
story.append(Image('architecture_diagram.png', width=3.0*inch, height=7.6*inch))
story.append(Paragraph("Pipeline: Upload -> Extract -> Chunk -> Embed -> Store (FAISS) -> Question -> Retrieve -> Relevance Check -> Generate (Gemini) -> Display with Sources.", styles['Caption']))

story.append(PageBreak())

story.append(Paragraph("5. Sample Document Set", styles['H2s']))
story.append(Paragraph(
    "The submission uses 4 fictional HR policy documents for a fictional company, <b>Solstice Retail "
    "Pvt Ltd</b> (created for this project -- not copied from any real company): Employee_Handbook.pdf "
    "(5 pages), Leave_Policy.pdf (4 pages), Attendance_Policy.pdf (3 pages), and Code_of_Conduct.pdf "
    "(5 pages) -- 17 pages / 17 text chunks in total. Users can also upload their own PDFs from any "
    "domain (manuals, legal documents, course notes) via the sidebar uploader.", styles['Bodys']))

story.append(Paragraph("6. Testing Results", styles['H2s']))
story.append(Paragraph(
    "20 test questions (tests/test_questions.csv) were run against the fully offline part of the "
    "pipeline -- retrieval and the relevance-threshold refusal logic -- via run_pipeline_test.py: "
    "17 answerable questions covering all 4 documents, plus 3 deliberately unanswerable questions "
    "(mirroring the brief's own example, 'Who is the company CEO?').", styles['Bodys']))

test_summary = [
    [cell("Category", styles['CellHead']), cell("Count", styles['CellHead']), cell("Result", styles['CellHead'])],
    [cell("Answerable questions (correct source + page retrieved)"), cell("17", styles['CellBodyCenter']), cell("17/17 correct", styles['CellBodyCenter'])],
    [cell("Unanswerable questions (correctly refused)"), cell("3", styles['CellBodyCenter']), cell("3/3 correct", styles['CellBodyCenter'])],
    [cell("Total"), cell("20", styles['CellBodyCenter']), cell("20/20 passed", styles['CellBodyCenter'])],
]
tt = Table(test_summary, colWidths=[3.6*inch, 1.0*inch, 2.0*inch])
tt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a3d5c')),
    ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#cccccc')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f2f6f9')]),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(tt)
story.append(Spacer(1, 6))
story.append(Paragraph(
    "<b>Result: 20/20 test cases passed.</b> Live answer generation (final wording from Gemini) "
    "requires a GOOGLE_API_KEY, set locally via .env (never stored in the repo). See "
    "tests/evaluation_notes.md for exact steps to verify live generation, and for the embedding-backend "
    "caveat noted above.", styles['Bodys']))

story.append(Paragraph("7. Responsible AI and Security Rules Applied", styles['H2s']))
rules = [
    "Answers only from retrieved context; explicitly refuses (with the brief's exact wording) rather than inventing facts.",
    "Every non-refusal answer cites its source document and page number.",
    "The app displays a Responsible AI notice asking users to verify high-stakes information.",
    "The system prompt instructs the model to ignore instruction-like text found inside documents or the user's question -- prompt-injection resistance.",
    "Uploaded resumes/documents are processed in memory only for the current session; nothing is written to disk unless explicitly saved.",
    "No API keys are stored in code or committed to GitHub (.env is gitignored; .env.example is a template).",
    "Uploaded files are validated for PDF type and a 20 MB size limit before processing.",
]
story.append(ListFlowable([ListItem(Paragraph(r, styles['Bodys']), bulletColor=colors.HexColor('#2c5a7c')) for r in rules], bulletType='bullet', leftIndent=14))

story.append(Paragraph("8. Optional Advanced Features Implemented", styles['H2s']))
story.append(Paragraph(
    "The assignment brief lists several optional advanced upgrades beyond the minimum requirement. "
    "<b>Four of these were implemented</b> in this submission:", styles['Bodys']))

adv_features = [
    ("&#10003; Conversation Memory for Follow-Up Questions", "rag_pipeline.py",
     "Questions are sent through a google.genai Chat session instead of a stateless call, so Gemini "
     "can resolve follow-ups (e.g. \"what about maternity leave?\") using earlier turns in the same "
     "session. Reset via the sidebar's Clear Chat button or by processing new documents."),
    ("&#10003; Feedback Buttons", "feedback.py",
     "A thumbs up / down widget under every answer logs the question, answer, sources, and rating to "
     "a local feedback_log.csv for review -- fully opt-in and offline."),
    ("&#10003; Docker Deployment", "Dockerfile, docker-compose.yml",
     "Containerizes the Streamlit app for one-command build and run (docker compose up --build)."),
    ("&#10003; Evaluation Using a Prepared Question-Answer Dataset", "evaluate_qa.py",
     "Runs the complete live pipeline (retrieval + Gemini generation) against all 20 questions in "
     "tests/test_questions.csv and writes a scored tests/evaluation_report.csv, going beyond "
     "run_pipeline_test.py's offline-only retrieval check. Runnable from the command line or via a "
     "Run Evaluation button in the app's sidebar, which shows pass/fail, accuracy, and a results "
     "table with a CSV download."),
]

adv_flat_rows = []
for title, filename, desc in adv_features:
    combined = Paragraph(
        f'{title} &mdash; <font name="Helvetica-Oblique">{filename}</font><br/>'
        f'<font size="9.2">{desc}</font>', styles['HighlightBody'])
    adv_flat_rows.append([combined])

adv_box = Table(adv_flat_rows, colWidths=[6.7*inch])
adv_box.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eef7ee')),
    ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor('#2e7d32')),
    ('LINEBELOW', (0,0), (-1,-2), 0.6, colors.HexColor('#bfe0bf')),
    ('LEFTPADDING', (0,0), (-1,-1), 10),
    ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ('TOPPADDING', (0,0), (-1,-1), 7),
    ('BOTTOMPADDING', (0,0), (-1,-1), 7),
]))
story.append(adv_box)
story.append(Spacer(1, 4))
story.append(Paragraph(
    "These were implemented in addition to the required minimum feature set to demonstrate extra "
    "depth; none are needed to satisfy the core assignment.", styles['Caption']))

story.append(Paragraph("9. Limitations & Future Improvements", styles['H2s']))
story.append(Paragraph(
    "Retrieval quality depends on the embedding backend in use -- the offline TF-IDF fallback "
    "(only triggered when the pretrained model can't be downloaded) is keyword-based and less robust "
    "to paraphrasing than the real MiniLM embeddings. No OCR is implemented, so scanned/image-only "
    "PDFs raise a clear error rather than returning empty text. Conversation memory carries the full "
    "chat history to Gemini but does not rewrite the retrieval query using that history, and isn't "
    "trimmed for very long sessions. A RAG chatbot can still be wrong even when grounded, if retrieval "
    "misses the most relevant passage. Further improvements: OCR support, multiple document "
    "collections, and a FastAPI backend (see project brief's Optional Advanced Features).", styles['Bodys']))

story.append(Paragraph("10. Conclusion", styles['H2s']))
story.append(Paragraph(
    "This project delivers a complete, working RAG pipeline covering every required module: PDF "
    "upload, text extraction with page metadata, chunking, pretrained-model embeddings, FAISS vector "
    "search, a relevance-threshold refusal guardrail, grounded answer generation via Google Gemini, and an "
    "interactive Streamlit chat interface with source citations. Four optional advanced features were "
    "added on top: conversation memory, feedback buttons, Docker deployment, and a live evaluation "
    "harness. All 20 offline-testable cases passed, and the codebase follows the Responsible AI and "
    "Security rules specified in the project brief throughout.", styles['Bodys']))

doc = SimpleDocTemplate(
    "Raju_P_S_RAG_Chatbot_Project_Report.pdf",
    pagesize=letter,
    topMargin=0.55*inch, bottomMargin=0.55*inch,
    leftMargin=0.65*inch, rightMargin=0.65*inch,
    title="Domain-Specific RAG Chatbot - Project Report - Raju_P_S",
    author="Raju_P_S", creator="Raju_P_S",
)
doc.build(story)

from pypdf import PdfReader, PdfWriter
reader = PdfReader("Raju_P_S_RAG_Chatbot_Project_Report.pdf")
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)
writer.add_metadata({
    "/Author": "Raju_P_S", "/Creator": "Raju_P_S", "/Producer": "Raju_P_S",
    "/Title": "Domain-Specific RAG Chatbot - Project Report - Raju_P_S",
})
with open("Raju_P_S_RAG_Chatbot_Project_Report.pdf", "wb") as f:
    writer.write(f)

print("PDF built.")
