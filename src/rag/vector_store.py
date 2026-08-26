import os
import joblib
import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

from src.rag.sample_documents import SAMPLE_CLINICAL_DOCUMENTS, seed_clinical_documents

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "vector_store")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "chunks_metadata.joblib")

class ClinicalVectorStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.encoder = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.index = None
        self.chunks_metadata = []

    def _get_encoder(self):
        if HAS_SENTENCE_TRANSFORMERS and self.encoder is None:
            print("[VectorStore] Loading SentenceTransformer model...", flush=True)
            self.encoder = SentenceTransformer(self.model_name)
        return self.encoder

    def chunk_documents(self):
        """Chunk sample documents into structured passages."""
        seed_clinical_documents()
        chunks = []
        
        for doc in SAMPLE_CLINICAL_DOCUMENTS:
            filename = doc["filename"]
            doc_type = doc["document_type"]
            paragraphs = [p.strip() for p in doc["content"].split("\n\n") if p.strip()]
            
            for para in paragraphs:
                lines = [l.strip() for ll in para.split("\n") for l in [ll] if l.strip()]
                title = lines[0] if lines else "General Guidelines"
                body = " ".join(lines[1:]) if len(lines) > 1 else lines[0]
                
                chunks.append({
                    "filename": filename,
                    "document_type": doc_type,
                    "section_title": title,
                    "content": f"{title}\n{body}"
                })

        self.chunks_metadata = chunks
        return chunks

    def build_index(self):
        """Generate embeddings and store vector index."""
        chunks = self.chunk_documents()
        texts = [c["content"] for c in chunks]

        if HAS_SENTENCE_TRANSFORMERS:
            encoder = self._get_encoder()
            print(f"[VectorStore] Generating SentenceTransformer embeddings for {len(texts)} chunks...", flush=True)
            embeddings = encoder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            
            dim = embeddings.shape[1]
            faiss.normalize_L2(embeddings)
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)

            faiss.write_index(self.index, INDEX_PATH)
            joblib.dump(self.chunks_metadata, METADATA_PATH)
            print(f"[VectorStore] FAISS Index saved with {self.index.ntotal} vectors!", flush=True)
        else:
            print(f"[VectorStore] Using TF-IDF fallback vectorizer for {len(texts)} chunks...", flush=True)
            self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            joblib.dump(self.chunks_metadata, METADATA_PATH)
            print(f"[VectorStore] TF-IDF Vectorizer initialized with {len(texts)} document chunks!", flush=True)

    def load_index(self):
        """Load index from disk if available, else build."""
        if HAS_SENTENCE_TRANSFORMERS and os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            self.chunks_metadata = joblib.load(METADATA_PATH)
        else:
            self.build_index()

    def search(self, query, top_k=3):
        """Retrieve top-K relevant clinical passages with citations."""
        if not self.chunks_metadata:
            self.load_index()

        if HAS_SENTENCE_TRANSFORMERS and self.index is not None:
            encoder = self._get_encoder()
            q_emb = encoder.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(q_emb)

            scores, indices = self.index.search(q_emb, min(top_k, self.index.ntotal))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.chunks_metadata):
                    chunk = self.chunks_metadata[idx]
                    results.append({
                        "score": round(float(score), 4),
                        "filename": chunk["filename"],
                        "document_type": chunk["document_type"],
                        "section_title": chunk["section_title"],
                        "content": chunk["content"]
                    })
            return results
        else:
            if self.tfidf_matrix is None:
                texts = [c["content"] for c in self.chunks_metadata]
                self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
                self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

            q_vec = self.tfidf_vectorizer.transform([query])
            sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]
            top_indices = np.argsort(sims)[::-1][:top_k]

            results = []
            for idx in top_indices:
                chunk = self.chunks_metadata[idx]
                results.append({
                    "score": round(float(sims[idx]), 4),
                    "filename": chunk["filename"],
                    "document_type": chunk["document_type"],
                    "section_title": chunk["section_title"],
                    "content": chunk["content"]
                })
            return results

# Global store singleton
_vector_store_instance = None

def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = ClinicalVectorStore()
    return _vector_store_instance

if __name__ == "__main__":
    store = ClinicalVectorStore()
    store.build_index()
    res = store.search("What is the diagnostic threshold for HbA1c in diabetes?")
    print("Search Result sample:", res[0] if res else "No match")
