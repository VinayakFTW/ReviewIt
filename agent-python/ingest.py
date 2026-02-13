import os
import shutil
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

#CONFIGURATION
PERSIST_DIRECTORY = "./chroma_db"
#files with specific extentions to look for
GLOB_PATTERN = "**/*.py" 

def load_documents(source_dir: str) -> List:
    print(f"Loading documents from {source_dir}...")
    loader = DirectoryLoader(
        source_dir, 
        glob=GLOB_PATTERN, 
        loader_cls=TextLoader,
        show_progress=True,
        use_multithreading=True
    )
    documents = loader.load()
    print(f"Loaded {len(documents)} documents.")
    return documents

def split_documents(documents: List) -> List:
    #RecursiveCharacterTextSplitter tries to split by paragraphs, then lines, etc. bade docs ke liye slow tho
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""] #seperate each code block
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks.")
    return chunks

#loads and ingests the codebase to chromadb using jina with a 32,768 token context window
def ingest_codebase(source_dir: str):
    documents = load_documents(source_dir)
    if not documents:
        print("No documents found. Check your path or glob pattern.")
        return

    chunks = split_documents(documents)

    print("Creating Embeddings")
    embedding_model = HuggingFaceEmbeddings(model_name="jinaai/jina-code-embeddings-1.5b",model_kwargs={'device': 'cuda','trust_remote_code': True})

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=PERSIST_DIRECTORY,
        collection_name="codebase_memory" 
    )
    
    print(f"Ingestion complete! Memory saved to {PERSIST_DIRECTORY}")

if __name__ == "__main__":
    #ABHI TESTING KE LIYE GIVE ANY EXISTING CODE DIRECTORY
    TARGET_DIRECTORY = "D:\\ReviewIt"
    
    if os.path.exists(TARGET_DIRECTORY):
        try:
            shutil.rmtree('chroma_db')
            print("Existing Memory Removed")
        except Exception as e:
            print(f"Error: {e}")
            pass
        ingest_codebase(TARGET_DIRECTORY)
    else:
        print("Invalid directory path.")