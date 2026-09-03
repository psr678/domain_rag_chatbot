"""
vector_store.py

Chunking + embeddings + FAISS vector store for the RAG chatbot.

Beginner approach, as specified in the project brief:
  - LangChain's RecursiveCharacterTextSplitter for chunking (chunk size
    700-1000 chars, overlap 100-150 chars).
  - Pretrained sentence-embedding model "sentence-transformers/all-MiniLM-L6-v2"
    (384-dim), the exact beginner embedding model named in the brief.
  - FAISS for the vector index (top-k cosine/inner-product similarity search).

Implementation note on the embedding runtime: the primary embedder loads
this model through the `fastembed` library (ONNX Runtime) rather than the
`sentence-transformers` / PyTorch package -- it is the *same* pretrained
model producing the same 384-dim embedding space, only the runtime differs
and the dependency footprint is much lighter (no PyTorch/CUDA required).
`fastembed` downloads the ONNX model files from huggingface.co on first use.

Offline fallback: if the pretrained model can't be downloaded (for example,
no internet access at that moment), this module automatically falls back
to a local TF-IDF embedder (`sklearn.feature_extraction.text.TfidfVectorizer`)
so the app keeps working instead of crashing. The fallback is deterministic
and clearly logged via a warning -- it is never a silent substitution.
Whenever `fastembed` can reach huggingface.co, the real MiniLM model is
used and the fallback never activates.
"""
import os
import pickle
import warnings
from dataclasses import dataclass, field

import numpy as np
import faiss
from langchain_text_splitters import RecursiveCharacterTextSplitter

from document_loader import PageRecord

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CHUNK_SIZE = 900
CHUNK_OVERLAP = 130
TOP_K = 4


class Embedder:
    """
    Wraps the pretrained MiniLM embedder (fastembed/ONNX) with an offline
    TF-IDF fallback. `self.backend` tells you which one is actually active
    ("pretrained-minilm" or "tfidf-fallback") -- always check/log this so
    the fallback is never mistaken for the real thing.
    """

    def __init__(self):
        self.backend = None
        self.dim = None
        self._model = None
        self._tfidf = None
        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
            self.backend = "pretrained-minilm"
            self.dim = EMBEDDING_DIM
        except Exception as exc:
            warnings.warn(
                f"Could not load pretrained embedding model '{EMBEDDING_MODEL_NAME}' "
                f"({exc}). Falling back to an offline TF-IDF embedder for this session."
            )
            self.backend = "tfidf-fallback"

    def fit_corpus(self, texts: list[str]) -> None:
        """Only needed for the TF-IDF fallback, which must be fit on the chunk corpus first."""
        if self.backend == "tfidf-fallback":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(
                max_features=4096, ngram_range=(1, 2), stop_words="english", sublinear_tf=True
            )
            self._tfidf.fit(texts)
            self.dim = len(self._tfidf.vocabulary_)

    def embed(self, texts: list[str]) -> np.ndarray:
        if self.backend == "pretrained-minilm":
            if self._model is None:  # re-loaded from disk; reconnect to the model
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
            return np.array(list(self._model.embed(texts)), dtype="float32")
        if self._tfidf is None:
            raise RuntimeError("TF-IDF fallback embedder was not fit yet -- call fit_corpus() first.")
        vecs = self._tfidf.transform(texts).toarray().astype("float32")
        return vecs

    def __getstate__(self):
        # Exclude the (non-picklable) ONNX model session; it is lazily
        # reconnected on first use after unpickling. The TF-IDF vectorizer
        # (if any) pickles normally and is kept.
        state = self.__dict__.copy()
        state["_model"] = None
        return state


@dataclass
class Chunk:
    text: str
    doc_name: str
    page_number: int
    chunk_id: int = 0


@dataclass
class VectorStore:
    index: "faiss.Index" = None
    chunks: list = field(default_factory=list)  # parallel list of Chunk, same order as index
    embedder: Embedder = None

    def build(self, page_records: list[PageRecord]) -> None:
        """Chunks every page record, embeds each chunk, and builds a fresh FAISS index."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks: list[Chunk] = []
        for rec in page_records:
            pieces = splitter.split_text(rec.text)
            for i, piece in enumerate(pieces):
                chunks.append(Chunk(text=piece, doc_name=rec.doc_name, page_number=rec.page_number, chunk_id=i))

        if not chunks:
            raise ValueError("No text chunks were produced from the uploaded documents.")

        self.embedder = Embedder()
        self.embedder.fit_corpus([c.text for c in chunks])
        vectors = self.embedder.embed([c.text for c in chunks])
        faiss.normalize_L2(vectors)  # so inner product == cosine similarity

        index = faiss.IndexFlatIP(self.embedder.dim)
        index.add(vectors)

        self.index = index
        self.chunks = chunks

    def search(self, query: str, top_k: int = TOP_K) -> list[tuple[Chunk, float]]:
        if self.index is None or not self.chunks:
            raise ValueError("Vector store is empty -- process documents before asking questions.")
        qvec = self.embedder.embed([query])
        faiss.normalize_L2(qvec)
        scores, ids = self.index.search(qvec, min(top_k, len(self.chunks)))
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "chunks.pkl"), "wb") as f:
            pickle.dump({"chunks": self.chunks, "embedder": self.embedder}, f)

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        index = faiss.read_index(os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "chunks.pkl"), "rb") as f:
            payload = pickle.load(f)
        return cls(index=index, chunks=payload["chunks"], embedder=payload["embedder"])


if __name__ == "__main__":
    import glob
    from document_loader import extract_pages

    all_records = []
    for path in sorted(glob.glob("documents/*.pdf")):
        with open(path, "rb") as f:
            data = f.read()
        all_records.extend(extract_pages(path.split("/")[-1], data))

    print(f"Loaded {len(all_records)} pages from {len(glob.glob('documents/*.pdf'))} PDFs.")
    store = VectorStore()
    store.build(all_records)
    print(f"Embedding backend in use: {store.embedder.backend}")
    print(f"Built {len(store.chunks)} chunks, FAISS index size: {store.index.ntotal}")

    for q in ["What is the leave policy?", "How is attendance calculated?", "Who is the company CEO?"]:
        print(f"\nQuery: {q}")
        for chunk, score in store.search(q, top_k=3):
            print(f"  score={score:.3f}  {chunk.doc_name} p.{chunk.page_number}  {chunk.text[:70]!r}")
