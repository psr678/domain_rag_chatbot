"""
app.py -- Streamlit interface for the Domain-Specific RAG Chatbot.

Upload one or more PDFs (or use the bundled sample HR documents), click
"Process Documents", then ask questions in the chat box. Every answer is
grounded only in the uploaded documents and cites its source document +
page number.
"""
import os
import glob
import threading
import time
import uuid

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx

from rag_pipeline import RAGPipeline
from prompt import REFUSAL_MESSAGE
from feedback import log_feedback
from evaluate_qa import run_evaluation, write_report, QUESTIONS_PATH, REPORT_PATH

load_dotenv()

st.set_page_config(page_title="Domain-Specific RAG Chatbot", page_icon="\U0001F4C4", layout="wide")

st.title("\U0001F4C4 Domain-Specific RAG Chatbot")
st.caption("Ask questions about your uploaded PDF documents. Answers are grounded only in what you upload -- "
           "follow-up questions in the same session are understood in context.")

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
        "- Uploaded files are processed in memory for this session only.\n"
        "- Follow-up questions are understood using this session's chat history; click **Clear Chat** "
        "or process new documents to start a fresh conversation.\n"
        "- Clicking a 👍/👎 button below an answer logs that question, answer, and your rating to a "
        "local `feedback_log.csv` file (never sent anywhere) -- entirely optional."
    )

if "pipeline" not in st.session_state:
    st.session_state.pipeline = RAGPipeline()
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role", "content", "sources"}
if "docs_processed" not in st.session_state:
    st.session_state.docs_processed = False
if "processed_file_bytes" not in st.session_state:
    st.session_state.processed_file_bytes = []  # snapshot used to build an independent eval pipeline
if "eval_running" not in st.session_state:
    st.session_state.eval_running = False
if "eval_confirm_pending" not in st.session_state:
    st.session_state.eval_confirm_pending = False
if "eval_progress" not in st.session_state:
    st.session_state.eval_progress = {"current": 0, "total": 0, "last_question": ""}
if "eval_error" not in st.session_state:
    st.session_state.eval_error = None
if "eval_partial" not in st.session_state:
    st.session_state.eval_partial = []

pipeline: RAGPipeline = st.session_state.pipeline


def _run_evaluation_background(files: list, google_api_key: str) -> None:
    """
    Runs in a background thread (see add_script_run_ctx below) so the main
    chat UI stays fully usable while it works through all 20 questions.
    Uses its OWN RAGPipeline instance (built from a snapshot of the
    processed document bytes) rather than the shared `pipeline` object, so
    it never fights the main thread over conversation state if the user
    keeps chatting while the evaluation runs.
    """
    print("[evaluate_qa] Starting background evaluation...", flush=True)
    try:
        eval_pipeline = RAGPipeline(google_api_key=google_api_key)
        n_chunks = eval_pipeline.process_documents(files)
        print(f"[evaluate_qa] Indexed {n_chunks} chunks from {len(files)} document(s). "
              f"Embedding backend: {eval_pipeline.embedding_backend}", flush=True)

        def on_progress(i, total, result):
            st.session_state.eval_progress = {
                "current": i, "total": total, "last_question": result["question"],
            }
            st.session_state.eval_partial.append(result)
            print(f"[evaluate_qa] [{i}/{total}] {result['correct']}  "
                  f"({result['latency_seconds']}s)  {result['question']}", flush=True)

        results = run_evaluation(eval_pipeline, progress_callback=on_progress)
        write_report(results)
        st.session_state.eval_results = results
        st.session_state.eval_error = None
        n_pass = sum(1 for r in results if r["correct"] == "PASS")
        print(f"[evaluate_qa] Done: {n_pass}/{len(results)} passed. Report written to {REPORT_PATH}", flush=True)
    except Exception as exc:
        st.session_state.eval_results = st.session_state.eval_partial or None
        st.session_state.eval_error = str(exc)
        print(f"[evaluate_qa] Stopped early after {len(st.session_state.eval_partial)} question(s): {exc}",
              flush=True)
    finally:
        st.session_state.eval_running = False


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
                    st.session_state.processed_file_bytes = files_to_process
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
        pipeline.reset_conversation()
        st.rerun()

    st.divider()
    st.header("2. Evaluate (optional)")
    st.caption(f"Runs all 20 questions in `{QUESTIONS_PATH}` through the live pipeline "
               "(retrieval + Gemini generation) and scores the results. Runs in the background "
               "-- you can keep using the chat while it works.")

    if st.session_state.eval_running:
        prog = st.session_state.eval_progress
        if prog["total"]:
            st.progress(prog["current"] / prog["total"],
                        text=f"[{prog['current']}/{prog['total']}] {prog['last_question']}")
        else:
            st.progress(0.0, text="Starting evaluation...")
        st.caption("Running in the background -- feel free to keep chatting; this will keep going "
                   "and the results will appear below when it's done.")
    elif st.session_state.eval_confirm_pending:
        st.warning(
            "This calls the Gemini API once per question (20 calls total). Depending on API "
            "response times -- and any automatic retries on temporary high-demand errors -- this "
            "can take anywhere from under a minute to several minutes. It runs in the background, "
            "so you can keep using the chat while it works.",
            icon="⏳",
        )
        col_yes, col_no = st.columns(2)
        if col_yes.button("✅ Yes, start", type="primary", use_container_width=True):
            if not os.environ.get("GOOGLE_API_KEY"):
                st.error("No GOOGLE_API_KEY found -- add one to `.env` first (see `.env.example`).")
            else:
                st.session_state.eval_running = True
                st.session_state.eval_confirm_pending = False
                st.session_state.eval_progress = {"current": 0, "total": 0, "last_question": ""}
                st.session_state.eval_partial = []
                thread = threading.Thread(
                    target=_run_evaluation_background,
                    args=(st.session_state.processed_file_bytes, os.environ.get("GOOGLE_API_KEY")),
                    daemon=True,
                )
                add_script_run_ctx(thread)  # lets the background thread safely touch st.session_state
                thread.start()
                st.rerun()
        if col_no.button("Cancel", use_container_width=True):
            st.session_state.eval_confirm_pending = False
            st.rerun()
    else:
        if st.button("\U0001F4CA Run Evaluation (20 questions)", disabled=not st.session_state.docs_processed):
            st.session_state.eval_confirm_pending = True
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

if st.session_state.eval_running:
    st.info("\U0001F4CA An evaluation is running in the background (see the sidebar for progress) -- "
            "the chat below still works normally while it finishes.", icon="⏳")

if st.session_state.eval_error and not st.session_state.eval_running:
    st.error(f"The last evaluation stopped early: {st.session_state.eval_error}")

if st.session_state.get("eval_results") and not st.session_state.eval_running:
    with st.expander("\U0001F4CA Latest Evaluation Results", expanded=True):
        results = st.session_state.eval_results
        n_pass = sum(1 for r in results if r["correct"] == "PASS")
        col1, col2 = st.columns(2)
        col1.metric("Passed", f"{n_pass} / {len(results)}")
        col2.metric("Accuracy", f"{n_pass / len(results):.0%}")
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        if os.path.exists(REPORT_PATH):
            with open(REPORT_PATH, "rb") as f:
                st.download_button("Download evaluation_report.csv", f, file_name="evaluation_report.csv")

def render_message(msg: dict) -> None:
    """Renders one message bubble. Assistant messages (that aren't errors) get a
    Sources expander and a 👍/👎 feedback widget."""
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("\U0001F4CE Sources"):
                for s in msg["sources"]:
                    st.markdown(f"- **{s.doc_name}**, page {s.page_number} (relevance {s.score:.2f})")

        if msg["role"] == "assistant" and not msg.get("is_error"):
            fb_key = f"fb_{msg['id']}"
            selected = st.feedback("thumbs", key=fb_key)
            if selected is not None and msg.get("feedback_logged") != selected:
                label = "useful" if selected == 1 else "incorrect"
                log_feedback(msg.get("question", ""), msg["content"], msg.get("sources"), label)
                msg["feedback_logged"] = selected


for msg in st.session_state.messages:
    render_message(msg)

question = st.chat_input("Ask a question about your documents...")
if question:
    st.session_state.messages.append({"role": "user", "content": question, "sources": None})
    with st.chat_message("user"):
        st.markdown(question)

    with st.spinner("Retrieving relevant passages and generating an answer..."):
        try:
            answer = pipeline.ask(question)
            new_msg = {
                "role": "assistant", "content": answer.text, "sources": answer.sources,
                "question": question, "id": uuid.uuid4().hex, "feedback_logged": None,
            }
        except RuntimeError as exc:
            new_msg = {
                "role": "assistant", "content": f"Error: {exc}", "sources": None,
                "question": question, "id": uuid.uuid4().hex, "is_error": True,
            }
    st.session_state.messages.append(new_msg)
    render_message(new_msg)

if st.session_state.eval_running:
    # Lightweight polling refresh so the sidebar progress bar keeps moving
    # even if the user isn't otherwise interacting with the page. The
    # evaluation itself runs independently in its own thread, so this
    # rerun never interrupts it -- unlike the earlier (fixed) approach
    # where the evaluation ran inline in the main script thread.
    time.sleep(2)
    st.rerun()
