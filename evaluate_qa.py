"""
evaluate_qa.py

Optional advanced feature: full live evaluation against a prepared
question-answer dataset (tests/test_questions.csv). Unlike
run_pipeline_test.py (which only exercises the offline retrieval +
refusal-threshold logic), this runs the *complete* pipeline for every
question -- retrieval AND live Gemini answer generation.

`run_evaluation()` is the reusable core (imported by app.py for the
sidebar "Run Evaluation" button). Running this file directly does the
same thing from the command line and writes tests/evaluation_report.csv.

Requires GOOGLE_API_KEY to be set (see .env.example). Each question is
evaluated independently: conversation memory is reset before every
question so results aren't influenced by earlier questions in the run.

Usage:
    python evaluate_qa.py
"""
import csv
import glob
import sys
import time

REPORT_PATH = "tests/evaluation_report.csv"
QUESTIONS_PATH = "tests/test_questions.csv"
FIELDNAMES = ["question", "expected_source", "generated_answer", "cited_sources", "correct", "latency_seconds"]


def run_evaluation(pipeline, questions_path: str = QUESTIONS_PATH, progress_callback=None) -> list[dict]:
    """
    Runs the live pipeline (retrieval + Gemini generation) against every
    question in `questions_path`. `pipeline` must already have documents
    processed (pipeline.is_ready). Returns a list of result dicts (see
    FIELDNAMES). If provided, `progress_callback(i, total, result)` is
    called after each question -- used by app.py to update a progress bar.
    """
    with open(questions_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []
    for i, row in enumerate(rows, start=1):
        question = row["question"]
        expected_available = row["expected_available"].strip().lower() == "yes"
        expected_source = row["expected_source"]
        expected_doc = expected_source.split(",")[0].strip()

        pipeline.reset_conversation()  # keep each question independent
        start = time.monotonic()
        try:
            answer = pipeline.ask(question)
            error = None
        except RuntimeError as exc:
            answer = None
            error = str(exc)
        elapsed = time.monotonic() - start

        if error:
            correct = False
            cited = ""
            answer_text = f"ERROR: {error}"
        else:
            cited = "; ".join(f"{s.doc_name} p.{s.page_number}" for s in answer.sources)
            answer_text = answer.text
            if expected_available:
                correct = (not answer.refused) and any(s.doc_name == expected_doc for s in answer.sources)
            else:
                correct = answer.refused

        result = {
            "question": question,
            "expected_source": expected_source,
            "generated_answer": answer_text,
            "cited_sources": cited,
            "correct": "PASS" if correct else "FAIL",
            "latency_seconds": f"{elapsed:.2f}",
        }
        results.append(result)
        if progress_callback:
            progress_callback(i, len(rows), result)

    return results


def write_report(results: list[dict], report_path: str = REPORT_PATH) -> None:
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(results)


def main():
    from dotenv import load_dotenv
    from rag_pipeline import RAGPipeline

    load_dotenv()
    pipeline = RAGPipeline()
    if not pipeline.google_api_key:
        print("No GOOGLE_API_KEY found. Add one to .env (see .env.example) before running this "
              "live evaluation -- it needs a real Gemini API call per question.")
        sys.exit(1)

    files = []
    for path in sorted(glob.glob("documents/*.pdf")):
        with open(path, "rb") as f:
            files.append((path.split("/")[-1], f.read()))
    n_chunks = pipeline.process_documents(files)
    print(f"Indexed {n_chunks} chunks from {len(files)} documents. "
          f"Embedding backend: {pipeline.embedding_backend}\n")

    def report_progress(i, total, result):
        print(f"[{i}/{total}] {result['correct']}  ({result['latency_seconds']}s)  {result['question']}")

    results = run_evaluation(pipeline, progress_callback=report_progress)
    write_report(results)

    n_correct = sum(1 for r in results if r["correct"] == "PASS")
    print(f"\nResult: {n_correct}/{len(results)} passed. Full report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
