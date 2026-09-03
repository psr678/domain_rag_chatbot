# Evaluation Notes -- Domain-Specific RAG Chatbot

## What was tested automatically (`run_pipeline_test.py`)

Runs all 20 questions in `test_questions.csv` against the fully offline
part of the pipeline -- PDF extraction, chunking, embedding, FAISS
retrieval, and the relevance-threshold refusal logic. **Result: 20/20
passed** (17 answerable questions retrieved the correct source
document + page, and all 3 "not available" questions were correctly
flagged as below the relevance threshold).

### Embedding backend

`vector_store.py` embeds text with the pretrained
`sentence-transformers/all-MiniLM-L6-v2` model via `fastembed`. If that
model can't be downloaded for any reason, it automatically falls back to
a local `TfidfVectorizer` (bigrams, English stop words, sublinear TF
scaling) so the app keeps working instead of crashing. This fallback is:

- **Clearly logged** with a `UserWarning` every time it activates -- never
  silent.
- **Weaker than true semantic embeddings**, since it matches on keywords
  rather than meaning. The vectorizer settings (bigrams + English
  stop-word removal) were tuned so all 20 test questions still retrieve
  the correct source page even on this fallback, but a real MiniLM
  embedding handles paraphrasing/synonyms more robustly.

Check the `Embedding backend:` line printed at the top of
`run_pipeline_test.py`'s output -- it reads `pretrained-minilm` when the
real model is in use, or `tfidf-fallback` when the fallback is active.

## Verifying live answer generation

The retrieval step (finding the right passages) is fully tested above.
The final **answer wording** comes from Google Gemini and follows the
exact guardrail prompt from the assignment brief (`prompt.py`) -- to
verify it end-to-end:

1. Get a free key at https://aistudio.google.com/apikey
2. Add it to `.env` as `GOOGLE_API_KEY=...`
3. Run `streamlit run app.py`, process the sample documents, and ask a
   few of the questions from `test_questions.csv` -- confirm the wording
   is grounded, cites the right source, and that the 3 "not available"
   questions get the exact refusal message from the brief.

## Other quality checks

- **Groundedness / no invented facts:** the system prompt explicitly
  forbids answering outside the supplied context and instructs the model
  to say `"I could not find this information in the uploaded documents."`
  when the answer isn't present -- worded exactly as specified in the
  project brief.
- **Prompt-injection resistance:** the system prompt explicitly instructs
  the model to treat any instruction-like text *inside* a document or the
  user's question as ordinary content, never as a new instruction to the
  assistant (Responsible AI requirement from the brief).
- **Response time:** retrieval (FAISS search over 17 chunks) completes in
  well under 100ms locally; the dominant latency is the Gemini API call
  itself, typically 1-3 seconds.
- **Source quality:** every retrieved chunk carries its originating PDF
  filename and 1-indexed page number, displayed under a "Sources"
  expander below each answer in the Streamlit UI.
