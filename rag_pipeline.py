"""
rag_pipeline.py

Orchestrates the full RAG workflow:
  load PDFs -> extract text -> chunk -> embed -> store in FAISS
  -> (on each question) retrieve top-k chunks -> build grounded prompt
  -> call the LLM (Google Gemini) -> return answer + cited sources.

The project brief lists Groq, Gemini, OpenAI, Hugging Face, or a local
model as acceptable LLM choices -- this project uses Google Gemini via
the `google-genai` SDK.

Model choice / 503 handling: this project tries "gemini-3.6-flash-lite"
first (Google's lighter, cheaper, typically less congested free-tier
model -- plenty capable for short grounded Q&A) and falls back to the
full "gemini-3.6-flash" if the lite model isn't available for your key.
Each candidate is retried with exponential backoff on transient 503
"UNAVAILABLE / high demand" errors before moving to the next candidate,
since those errors are about temporary server load, not a bad model
choice. Override the model list with the GEMINI_MODEL env var (comma
-separated) if you want to pin a specific model.

Conversation memory (optional advanced feature): questions are sent
through a `google.genai` Chat session rather than a stateless
`generate_content` call, so Gemini can see prior turns in the same
session and resolve follow-up questions like "what about maternity
leave?" after an earlier leave-policy question. Retrieval for each turn
still runs on the latest question only (a beginner-level simplification
-- see README "Limitations"). Call `reset_conversation()` to start fresh.
"""
import os
import time
from dataclasses import dataclass, field

from document_loader import extract_multiple, DocumentLoadError
from vector_store import VectorStore
from prompt import SYSTEM_PROMPT, REFUSAL_MESSAGE, build_user_prompt, is_context_relevant_enough

_default_models = ["gemini-3.6-flash-lite", "gemini-3.6-flash"]
GEMINI_MODEL_CANDIDATES = (
    [m.strip() for m in os.environ.get("GEMINI_MODEL", "").split(",") if m.strip()]
    or _default_models
)
MAX_RETRIES_PER_MODEL = 3
RETRY_BASE_DELAY_SECONDS = 2


@dataclass
class SourceRef:
    doc_name: str
    page_number: int
    score: float


@dataclass
class Answer:
    text: str
    sources: list = field(default_factory=list)  # list[SourceRef]
    refused: bool = False


class RAGPipeline:
    def __init__(self, google_api_key: str | None = None):
        self.store = VectorStore()
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY")
        self._client = None
        self._chat = None
        self._chat_model = None
        self.processed_files: list[str] = []

    def reset_conversation(self) -> None:
        """Clears conversation memory. Call this alongside clearing the UI chat history."""
        self._chat = None
        self._chat_model = None

    # ---- Document ingestion -------------------------------------------------
    def process_documents(self, files: list[tuple[str, bytes]]) -> int:
        """files: list of (filename, file_bytes). Returns number of chunks indexed."""
        page_records = extract_multiple(files)
        self.store.build(page_records)
        self.processed_files = [f[0] for f in files]
        self.reset_conversation()  # new documents -> old chat history no longer applies
        return len(self.store.chunks)

    @property
    def is_ready(self) -> bool:
        return self.store.index is not None and len(self.store.chunks) > 0

    @property
    def embedding_backend(self) -> str:
        return self.store.embedder.backend if self.store.embedder else "not built yet"

    # ---- Question answering --------------------------------------------------
    def _get_client(self):
        if self._client is None:
            if not self.google_api_key:
                raise RuntimeError(
                    "No GOOGLE_API_KEY found. Add it to your .env file (see .env.example) "
                    "to enable answer generation."
                )
            from google import genai
            self._client = genai.Client(api_key=self.google_api_key)
        return self._client

    def _get_chat(self, client, model: str):
        """Returns the active Chat session for `model`, creating one if needed.
        Reusing the same Chat object across turns is what gives the assistant
        conversation memory -- Gemini sees every prior user/model turn sent
        through it."""
        if self._chat is None or self._chat_model != model:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=500,
                # This project never passes tools/functions to Gemini, so automatic
                # function calling (AFC) is irrelevant here -- disabling it explicitly
                # silences the SDK's generic "use AFC in Chat.send_message instead" notice.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )
            self._chat = client.chats.create(model=model, config=config)
            self._chat_model = model
        return self._chat

    def _call_gemini_with_retry_and_fallback(self, client, user_prompt: str):
        """
        Tries each model in GEMINI_MODEL_CANDIDATES in order, sending the
        message through a persistent Chat session (see _get_chat) so
        conversation history carries across turns. For each model, retries
        up to MAX_RETRIES_PER_MODEL times with exponential backoff on
        transient 503 "UNAVAILABLE / high demand" errors before moving on to
        the next model. A 404 "model not found" error skips straight to the
        next candidate (retrying won't fix a wrong model name). Falling back
        to a different model starts a fresh chat (conversation memory does
        not carry across a model switch).
        """
        last_exc = None
        for model in GEMINI_MODEL_CANDIDATES:
            for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                try:
                    chat = self._get_chat(client, model)
                    return chat.send_message(user_prompt)
                except Exception as exc:
                    last_exc = exc
                    msg = str(exc)
                    if "NOT_FOUND" in msg or "404" in msg:
                        self.reset_conversation()
                        break  # this model doesn't exist for this key -- try the next one, don't retry
                    if ("UNAVAILABLE" in msg or "503" in msg) and attempt < MAX_RETRIES_PER_MODEL:
                        time.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))  # 2s, 4s, ...
                        continue
                    self.reset_conversation()
                    break  # non-retryable error, or retries exhausted for this model -- try next model

        raise RuntimeError(
            f"Gemini did not respond after trying {GEMINI_MODEL_CANDIDATES} "
            f"(each with up to {MAX_RETRIES_PER_MODEL} attempts). Last error: {last_exc}. "
            "This is often temporary high demand on Google's free tier -- wait a bit and "
            "try again, or check https://ai.google.dev/gemini-api/docs/models for other "
            "available model names to set via the GEMINI_MODEL env var."
        ) from last_exc

    def ask(self, question: str, top_k: int = 4) -> Answer:
        if not self.is_ready:
            raise RuntimeError("No documents have been processed yet. Upload and process PDFs first.")

        retrieved = self.store.search(question, top_k=top_k)

        if not is_context_relevant_enough(retrieved):
            return Answer(text=REFUSAL_MESSAGE, sources=[], refused=True)

        user_prompt = build_user_prompt(question, retrieved)
        client = self._get_client()
        response = self._call_gemini_with_retry_and_fallback(client, user_prompt)
        answer_text = (response.text or "").strip()

        sources = [
            SourceRef(doc_name=c.doc_name, page_number=c.page_number, score=s)
            for c, s in retrieved
        ]
        refused = REFUSAL_MESSAGE.lower() in answer_text.lower()
        return Answer(text=answer_text, sources=sources, refused=refused)


if __name__ == "__main__":
    import glob

    files = []
    for path in sorted(glob.glob("documents/*.pdf")):
        with open(path, "rb") as f:
            files.append((path.split("/")[-1], f.read()))

    pipeline = RAGPipeline()
    n_chunks = pipeline.process_documents(files)
    print(f"Indexed {n_chunks} chunks from {len(files)} documents. Embedding backend: {pipeline.embedding_backend}")

    if not pipeline.google_api_key:
        print("\nNo GOOGLE_API_KEY set -- skipping live LLM calls.")
        print("Retrieval-only check (no generation):")
        for q in ["What is the leave policy?", "How is attendance calculated?", "Who is the company CEO?"]:
            retrieved = pipeline.store.search(q, top_k=3)
            relevant = is_context_relevant_enough(retrieved)
            print(f"  Q: {q}")
            print(f"     top score={retrieved[0][1]:.3f}  relevant={relevant}  "
                  f"would_answer_from={retrieved[0][0].doc_name} p.{retrieved[0][0].page_number}")
    else:
        for q in ["What is the leave policy?", "How is attendance calculated?", "Who is the company CEO?"]:
            ans = pipeline.ask(q)
            print(f"\nQ: {q}")
            print(f"A: {ans.text}")
            print(f"Sources: {[(s.doc_name, s.page_number) for s in ans.sources]}")
