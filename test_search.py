import asyncio
from qdrant_client import QdrantClient
import httpx

async def test():
    # Generate embedding using Ollama
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": "What are the main security findings?"
            }
        )
        embedding = response.json()["embedding"]
        print(f"Query embedding size: {len(embedding)}")
    
    # Search Qdrant
    qdrant_client = QdrantClient(host="localhost", port=6333)
    results = qdrant_client.search(
        collection_name="analysis_results",
        query_vector=embedding,
        limit=5
    )
    
    print(f"\nSearch returned {len(results)} results:")
    for i, r in enumerate(results):
        chunk_type = r.payload.get("chunk_type", "unknown")
        score = r.score
        content = r.payload.get("content", "")[:150]
        print(f"\n{i+1}. Score: {score:.4f}, Type: {chunk_type}")
        print(f"   Content: {content}...")

asyncio.run(test())
