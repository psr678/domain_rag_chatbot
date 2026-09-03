"""
run_pipeline_test.py

End-to-end sanity test against tests/test_questions.csv.

This checks the parts of the pipeline that are fully testable offline,
without a live LLM call: PDF extraction, chunking, embedding, FAISS
retrieval, and the relevance-threshold refusal logic. For each question it
verifies:
  1. Retrieval accuracy -- does the top retrieved chunk come from the
     expected source document (for answerable questions)?
  2. Refusal correctness -- does the relevance threshold correctly flag
     "not available" questions as not answerable?

Live LLM answer generation (the final wording of the answer) requires a
GOOGLE_API_KEY and is exercised separately -- see README.md "Testing" section
and tests/evaluation_notes.md for how to run that check locally.
"""
import csv
import glob

from rag_pipeline import RAGPipeline
from prompt import is_context_relevant_enough

pipeline = RAGPipeline()
files = []
for path in sorted(glob.glob("documents/*.pdf")):
    with open(path, "rb") as f:
        files.append((path.split("/")[-1], f.read()))

n_chunks = pipeline.process_documents(files)
print(f"Indexed {n_chunks} chunks from {len(files)} documents.")
print(f"Embedding backend: {pipeline.embedding_backend}")
if pipeline.embedding_backend == "tfidf-fallback":
    print("NOTE: running with the offline TF-IDF fallback embedder -- see vector_store.py docstring.\n")

with open("tests/test_questions.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

results = []
n_correct = 0
for row in rows:
    question = row["question"]
    expected_available = row["expected_available"].strip().lower() == "yes"
    expected_source = row["expected_source"]

    retrieved = pipeline.store.search(question, top_k=4)
    relevant = is_context_relevant_enough(retrieved)
    top_chunk, top_score = retrieved[0]

    if expected_available:
        actual_doc = f"{top_chunk.doc_name}, page {top_chunk.page_number}"
        expected_doc_name = expected_source.split(",")[0].strip()
        retrieval_ok = (top_chunk.doc_name == expected_doc_name) and relevant
        correct = retrieval_ok
        retrieved_str = actual_doc if relevant else "(below relevance threshold -- would refuse)"
    else:
        correct = not relevant  # correctly refuses to answer
        retrieved_str = "correctly refused" if correct else f"{top_chunk.doc_name}, page {top_chunk.page_number} (should have refused)"

    n_correct += int(correct)
    actual_doc_page = f"{top_chunk.doc_name}, page {top_chunk.page_number}"
    results.append((question, expected_source, retrieved_str, "PASS" if correct else "FAIL", top_score, actual_doc_page))

print(f"{'Question':<55} {'Expected':<28} {'Result':<6} {'Score':>6}  {'Actual top hit'}")
print("-" * 130)
for question, expected, retrieved_str, status, score, actual in results:
    q_disp = (question[:52] + "...") if len(question) > 55 else question
    print(f"{q_disp:<55} {expected:<28} {status:<6} {score:>6.3f}  {actual}")

print(f"\nResult: {n_correct}/{len(rows)} test cases passed.")
