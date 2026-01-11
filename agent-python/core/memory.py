import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

#CONFIGURATION
PERSIST_DIRECTORY = "./chroma_db"
EMBEDDING_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"

class MemoryManager:
    def __init__(self):
        print("Initializing Memory Manager...")
        
        self.embedding_fn = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME,model_kwargs={'device': 'cpu','trust_remote_code': True})
        
        if not os.path.exists(PERSIST_DIRECTORY):
            raise FileNotFoundError(f"Database not found at {PERSIST_DIRECTORY}.\nDid you run ingest.py?")
            
        self.vector_db = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=self.embedding_fn,
            collection_name="codebase_memory"
        )
        print("Memory loaded successfully.")

    def retrieve_context(self, query: str, k: int = 4) -> list:
        """
        Searches the memory for code chunks relevant to the query.
        
        Args:
            query: The natural language question (e.g., "Where is the login logic?")
            k: Number of chunks to retrieve (default 4)
            
        Returns:
            List of strings (the actual code code snippets)
        """
        print(f"Searching memory for: '{query}'")
        
        results = self.vector_db.similarity_search(query, k=k)
        
        context_snippets = [doc.page_content for doc in results]
        
        return context_snippets

def querydb(__req: str):
    memory = MemoryManager()
    results = memory.retrieve_context(__req)

    return results


# if __name__ == "__main__":
#     try:
#         memory = MemoryManager()
#         test_query = input("Enter a search query about your codebase: ")
#         results = memory.retrieve_context(test_query)
        
#         print(f"\nFound {len(results)} relevant code blocks:\n")
#         for i, snippet in enumerate(results):
#             print(f"--- Result {i+1} ---")
#             print(snippet[:200] + "...\n") #Print first 200 chars only
#     except Exception as e:
#         print(f"Error: {e}")