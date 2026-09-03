import os, requests, chromadb
from pypdf import PdfReader

LIBRARY = os.path.expanduser("~/emergency-library")
DB_PATH = os.path.expanduser("~/emergency-db")
OLLAMA = "http://localhost:11434"
CHUNK_SIZE = 900
OVERLAP = 150

def read_document(path):
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if path.lower().endswith(".txt"):
        with open(path, "r", errors="ignore") as f:
            return f.read()
    return None

def chunk_text(text):
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        cut = text.rfind("\n", start + CHUNK_SIZE - 200, end)
        if cut == -1 or cut <= start:
            cut = end
        chunk = text[start:cut].strip()
        if len(chunk) > 100:
            chunks.append(chunk)
        start = max(cut - OVERLAP, start + 1)
    return chunks

def embed(texts):
    r = requests.post(f"{OLLAMA}/api/embed",
                      json={"model": "nomic-embed-text", "input": texts})
    r.raise_for_status()
    return r.json()["embeddings"]

client = chromadb.PersistentClient(path=DB_PATH)
try:
    client.delete_collection("emergency")
except Exception:
    pass
col = client.create_collection("emergency")

total = 0
for fname in sorted(os.listdir(LIBRARY)):
    path = os.path.join(LIBRARY, fname)
    if not os.path.isfile(path):
        continue
    text = read_document(path)
    if not text or len(text) < 500:
        print(f"SKIP {fname} (no usable text)")
        continue
    chunks = chunk_text(text)
    if "IFRC" not in fname:
        import re as _re
        _blk = _re.compile(r"make (him|her|the person|a person) vomit|induce vomiting|ipecac|to cause vomiting when|loosen the (tie|tourniquet) for a moment|let the blood circulate|heel of your lower hand on (his|her|the) belly", _re.I)
        kept = [c for c in chunks if not _blk.search(c)]
        if len(kept) != len(chunks):
            print(f"  BLOCKED {len(chunks)-len(kept)} obsolete-emesis chunks from {fname}")
        chunks = kept
    print(f"{fname}: {len(chunks)} chunks, embedding...")
    for i in range(0, len(chunks), 16):
        batch = chunks[i:i+16]
        vectors = embed(batch)
        ids = [f"{fname}-{i+j}" for j in range(len(batch))]
        metas = [{"source": fname} for _ in batch]
        col.add(ids=ids, embeddings=vectors, documents=batch, metadatas=metas)
        print(f"  {min(i+16, len(chunks))}/{len(chunks)}")
    total += len(chunks)

print(f"\nDone. {total} chunks indexed into {DB_PATH}")
