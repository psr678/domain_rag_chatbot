"""Generates architecture_diagram.png -- a vertical flowchart of the RAG pipeline."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

steps = [
    ("Upload PDF Document(s)", "app.py (Streamlit)"),
    ("Extract Text per Page", "document_loader.py"),
    ("Chunk Text\n(700-1000 chars, 100-150 overlap)", "vector_store.py"),
    ("Embed Chunks\n(pretrained MiniLM model)", "vector_store.py + fastembed"),
    ("Store in FAISS Vector Index", "vector_store.py"),
    ("User Asks a Question", "app.py"),
    ("Embed the Question", "vector_store.py"),
    ("Retrieve Top-K Similar Chunks", "vector_store.py (FAISS search)"),
    ("Check Relevance Threshold\n(refuse if too weak)", "prompt.py"),
    ("Build Grounded Prompt\n+ Call Gemini LLM", "rag_pipeline.py"),
    ("Display Answer\n+ Source Document & Page", "app.py"),
]

fig, ax = plt.subplots(figsize=(3.6, 11.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, len(steps) * 2 + 1)
ax.axis("off")

box_w, box_h = 8.6, 1.35
y = len(steps) * 2

colors = ["#dbe9f6"] * 5 + ["#fdeecb"] * 1 + ["#dbe9f6"] * 3 + ["#e8f5e9"] * 2

for i, ((title, tool), color) in enumerate(zip(steps, colors)):
    box = FancyBboxPatch((0.7, y - box_h), box_w, box_h,
                          boxstyle="round,pad=0.08,rounding_size=0.12",
                          linewidth=1.4, edgecolor="#2c5a7c", facecolor=color)
    ax.add_patch(box)
    ax.text(5, y - box_h * 0.38, title, ha="center", va="center", fontsize=8.6, fontweight="bold", wrap=True)
    ax.text(5, y - box_h * 0.82, tool, ha="center", va="center", fontsize=7.2, color="#555555", style="italic")

    if i < len(steps) - 1:
        arrow = FancyArrowPatch((5, y - box_h - 0.02), (5, y - 2 + 0.05),
                                 arrowstyle="-|>", mutation_scale=14, linewidth=1.3, color="#2c5a7c")
        ax.add_patch(arrow)
    y -= 2

plt.tight_layout()
plt.savefig("architecture_diagram.png", dpi=160, bbox_inches="tight")
print("Saved architecture_diagram.png")
