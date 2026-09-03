"""
app.py -- Streamlit interface for the Domain-Specific RAG Chatbot.

Upload one or more PDFs (or use the bundled sample HR documents), click
"Process Documents", then ask questions in the chat box. Every answer is
grounded only in the uploaded documents and cites its source document +
page number.
"""
import os
import glob

import streamlit as st
from dotenv import load_dotenv

from rag_pipeline import RAGPipeline
from prompt import REFUSAL_MESSAGE

load_dotenv()

st.set_page_config(page_title="Domain-Specific RAG Chatbot", page_icon="\U0001F4C4", layout="wide")

st.title("\U0001F4C4 Domain-Specific RAG Chatbot")
st.caption("Ask questions about your uploaded PDF documents. Answers are grounded only in what you upload.")

with st.expander("ℹ️ Responsible AI notes -- please read", expanded=False):
    st.markdown(
        "- This chatbot answers **only** from the documents you upload -- it will not use outside "
        "knowledge to fill gaps.\n"
        "- If the answer isn't in your documents, it will say so instead of guessing.\n"
        "- **Verify high-stakes information** (legal, medical, financial, HR-policy decisions) with "
        "the original source document or a qualified person before acting on it.\n"
        "- Do not upload confidential or sensitive documents you don't have permission to share.\n"
        "- Any instructions found *inside* an uploaded document are treated as plain text, not as "
        "commands to the assistant.\n"
        "- Uploaded files are processed in memory for this session only."
    )

if "pipeline" not in st.session_state:
    st.session_state.pipeline = RAGPipeline()
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role", "content", "sources"}
if "docs_processed" not in st.session_state:
    st.session_state.docs_processed = False

pipeline: RAGPipeline = st.session_state.pipeline

# ---------------------------------------------------------------------------
# Sidebar: document upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("1. Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload one or more PDF files", type=["pdf"], accept_multiple_files=True
    )

    use_samples = st.checkbox(
        "Use the bundled sample HR documents instead",
        value=not uploaded_files,
        help="4 fictional 'Solstice Retail Pvt Ltd' HR policy PDFs bundled with this project (documents/).",
    )

    process_clicked = st.button("⚙️ Process Documents", type="primary")

    if process_clicked:
        files_to_process = []
        if use_samples:
            for path in sorted(glob.glob("documents/*.pdf")):
                with open(path, "rb") as f:
                    files_to_process.append((os.path.basename(path), f.read()))
        elif uploaded_files:
            for uf in uploaded_files:
                files_to_process.append((uf.name, uf.getvalue()))

        if not files_to_process:
            st.warning("Please upload at least one PDF, or check the sample-documents box.")
        else:
            with st.spinner("Extracting text, chunking, and building the vector index..."):
                try:
                    n_chunks = pipeline.process_documents(files_to_process)
                    st.session_state.docs_processed = True
                    st.session_state.messages = []
                    st.success(
                        f"Processed {len(files_to_process)} document(s) into {n_chunks} chunks. "
                        f"Embedding backend: `{pipeline.embedding_backend}`."
                    )
                except Exception as exc:
                    st.session_state.docs_processed = False
                    st.error(f"Could not process documents: {exc}")

    if st.session_state.docs_processed:
        st.markdown("**Currently indexed:**")
        for name in pipeline.processed_files:
            st.markdown(f"- {name}")

    st.divider()
    if st.button("\U0001F5D1️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    if not os.environ.get("GOOGLE_API_KEY"):
        st.warning("No GOOGLE_API_KEY found in your environment. Add one to `.env` (see `.env.example`) "
                    "to enable answer generation.", icon="⚠️")

# ---------------------------------------------------------------------------
# Main: chat interface
# ---------------------------------------------------------------------------
if not st.session_state.docs_processed:
    st.info("\U0001F448 Upload PDFs (or use the sample documents) in the sidebar and click "
            "**Process Documents** to get started.")
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("\U0001F4CE Sources"):
                for s in msg["sources"]:
                    st.markdown(f"- **{s.doc_name}**, page {s.page_number} (relevance {s.score:.2f})")

question = st.chat_input("Ask a question about your documents...")
if question:
    st.session_state.messages.append({"role": "user", "content": question, "sources": None})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving relevant passages and generating an answer..."):
            try:
                answer = pipeline.ask(question)
                st.markdown(answer.text)
                if answer.sources:
                    with st.expander("\U0001F4CE Sources"):
                        for s in answer.sources:
                            st.markdown(f"- **{s.doc_name}**, page {s.page_number} (relevance {s.score:.2f})")
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer.text, "sources": answer.sources}
                )
            except RuntimeError as exc:
                st.error(str(exc))
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Error: {exc}", "sources": None}
                )
