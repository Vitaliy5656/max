"""Debug RAG query to understand why no results"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from src.core.memory import memory
    from src.core.rag import rag
    from src.core.lm_client import lm_client
    
    await memory.initialize()
    await rag.initialize(memory._db)
    
    print("=== RAG DEBUG ===")
    
    # List documents
    docs = await rag.list_documents()
    print(f"\nDocuments: {len(docs)}")
    for d in docs:
        print(f"  - {d.filename} ({d.chunk_count} chunks)")
    
    # Check if chunks have embeddings
    async with memory._db.execute(
        "SELECT id, document_id, tokens, embedding IS NOT NULL as has_emb FROM document_chunks"
    ) as cursor:
        chunks = await cursor.fetchall()
    
    print(f"\nChunks in DB: {len(chunks)}")
    for c in chunks:
        print(f"  Chunk {c['id']}: tokens={c['tokens']}, has_embedding={c['has_emb']}")
    
    # Test query
    test_q = "DeepSeek Dual-Pipe GPU"
    print(f"\nQuery: '{test_q}'")
    
    # Get embedding for query
    q_emb = await lm_client.get_embedding(test_q)
    print(f"Query embedding: {len(q_emb)} dims")
    
    # Run query
    results = await rag.query(test_q, top_k=5)
    print(f"\nResults: {len(results)}")
    for r in results:
        print(f"  Score: {r.score:.4f} | {r.content[:80]}...")

if __name__ == "__main__":
    asyncio.run(main())
