"""
app/rag_pipeline.py — GoGenie RAG Pipeline
PDF ingest → text extraction → chunking → Gemini embeddings → cosine retrieval → LLM answer.
"""

import io
import numpy as np
from typing import List, Tuple

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


# ── PDF Text Extraction ───────────────────────────────────────────────────────
def extract_text_from_pdfs(uploaded_files) -> str:
    """Extract and concatenate text from one or more uploaded PDF files."""
    all_text = []

    for f in uploaded_files:
        try:
            # PyMuPDF — best quality extraction
            import fitz
            pdf_bytes = f.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = [page.get_text("text") for page in doc]
            doc.close()
            f.seek(0)
            all_text.append(f"\n\n[Document: {f.name}]\n" + "\n".join(pages))

        except ImportError:
            # Fallback: pypdf
            try:
                import pypdf
                f.seek(0)
                reader = pypdf.PdfReader(f)
                pages  = [p.extract_text() or "" for p in reader.pages]
                f.seek(0)
                all_text.append(f"\n\n[Document: {f.name}]\n" + "\n".join(pages))
            except Exception as e2:
                all_text.append(f"[Could not read {f.name}: {e2}]")

        except Exception as e:
            all_text.append(f"[Error reading {getattr(f, 'name', 'file')}: {e}]")

    return "\n\n".join(all_text)


# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_SIZE,
    overlap:    int = config.CHUNK_OVERLAP
) -> List[str]:
    """Split text into overlapping fixed-size chunks."""
    chunks = []
    start  = 0
    while start < len(text):
        end   = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ── Gemini Embeddings ─────────────────────────────────────────────────────────
def _embed(text: str, task_type: str = "retrieval_document") -> List[float]:
    """Embed a single text string using Gemini."""
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    try:
        result = genai.embed_content(
            model=config.GEMINI_EMBED_MODEL,
            content=text,
            task_type=task_type
        )
        return result["embedding"]
    except Exception:
        return [0.0] * 768          # 768-dim for text-embedding-004


def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Embed all chunks. Returns list of embedding vectors."""
    embeddings = []
    for chunk in chunks:
        embeddings.append(_embed(chunk, "retrieval_document"))
    return embeddings


def embed_query(query: str) -> List[float]:
    """Embed a user query for retrieval."""
    return _embed(query, "retrieval_query")


# ── Similarity Retrieval ──────────────────────────────────────────────────────
def _cosine_sim(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    return float(np.dot(a_arr, b_arr) / denom) if denom > 0 else 0.0


def retrieve_top_k(
    query:      str,
    chunks:     List[str],
    embeddings: List[List[float]],
    top_k:      int = config.TOP_K_CHUNKS
) -> List[str]:
    """Return the top-k most relevant chunks for the query."""
    if not chunks or not embeddings:
        return []
    q_emb  = embed_query(query)
    scores = [_cosine_sim(q_emb, emb) for emb in embeddings]
    top_i  = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [chunks[i] for i in top_i]


# ── Full Ingest Pipeline ──────────────────────────────────────────────────────
def ingest_pdfs(uploaded_files) -> Tuple[List[str], List[List[float]]]:
    """
    End-to-end: PDF files → (chunks, embeddings).
    Store these in st.session_state for reuse.
    """
    text       = extract_text_from_pdfs(uploaded_files)
    if not text.strip():
        return [], []
    chunks     = chunk_text(text)
    embeddings = embed_chunks(chunks)
    return chunks, embeddings


# ── RAG Answer ────────────────────────────────────────────────────────────────
def answer_from_pdf(
    query:      str,
    chunks:     List[str],
    embeddings: List[List[float]]
) -> str:
    """
    Full RAG: retrieve relevant chunks → Gemini generates answer grounded in context.
    """
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)

    relevant = retrieve_top_k(query, chunks, embeddings)
    if not relevant:
        return "I couldn't find relevant information in the uploaded documents. Please check if the PDF was uploaded correctly."

    context = "\n\n---\n\n".join(relevant)
    model   = genai.GenerativeModel(config.GEMINI_MODEL)

    prompt = f"""You are Genie, a helpful AI travel assistant. A user has uploaded travel-related PDF documents and is asking a question about them.

Answer the question based ONLY on the context below from their documents. Be concise, accurate, and friendly. If the answer isn't in the context, say so clearly — don't make up information.

Context from uploaded documents:
\"\"\"
{context}
\"\"\"

User question: {query}

Answer:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Error generating answer: {e}"
