from huggingface_hub import snapshot_download
import os

local_dir = os.path.join(os.getcwd(), "offline_model")
os.makedirs(local_dir, exist_ok=True)

print("Downloading jina-code-embeddings-1.5b")
snapshot_download(
    repo_id="jinaai/jina-code-embeddings-1.5b", 
    local_dir=local_dir,
    ignore_patterns=["*.msgpack", "*.h5", "rust_model.ot", "*.onnx"] 
)
print(f"Done! Model saved to {local_dir}")