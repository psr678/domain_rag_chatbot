"""
feedback.py

Logs user feedback (👍/👎) on chatbot answers to a local CSV file, so the
project owner can review which answers were marked useful or incorrect.
Fully offline -- no external service involved. This is opt-in: nothing is
logged unless the user clicks a feedback button in the UI.
"""
import csv
import os
from datetime import datetime

FEEDBACK_LOG_PATH = "feedback_log.csv"


def log_feedback(question: str, answer_text: str, sources: list, feedback_label: str) -> None:
    """
    feedback_label: a short string like "useful" or "incorrect".
    sources: list of SourceRef (from rag_pipeline.py) or None.
    """
    is_new_file = not os.path.exists(FEEDBACK_LOG_PATH)
    source_str = "; ".join(f"{s.doc_name} p.{s.page_number}" for s in (sources or []))
    with open(FEEDBACK_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["timestamp", "question", "answer", "sources", "feedback"])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            question,
            answer_text,
            source_str,
            feedback_label,
        ])


if __name__ == "__main__":
    # Quick manual check.
    log_feedback("What is the leave policy?", "Employees get 12 days of Casual Leave...", [], "useful")
    print(f"Wrote a test row to {FEEDBACK_LOG_PATH}")
