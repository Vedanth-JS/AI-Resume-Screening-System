import chromadb
from chromadb.utils import embedding_functions
import os
from typing import List, Dict, Any

# Configure ChromaDB
CHROMA_DATA_PATH = "vector_db"
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
default_ef = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="candidates", 
    embedding_function=default_ef
)

class CandidateChatbot:
    @staticmethod
    def add_candidate(candidate_id: int, text: str, metadata: Dict[str, Any]):
        collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(candidate_id)]
        )

    @staticmethod
    def query_candidates(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        # Parse results into clean list
        output = []
        for i in range(len(results['ids'][0])):
            output.append({
                "id": results['ids'][0][i],
                "document": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i]
            })
        return output
