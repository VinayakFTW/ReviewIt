from huggingface_hub import snapshot_download
import os

def pre_download_qwen_models():
    print("========================================================")
    print("      Downloading Qwen Models to Local HF Cache         ")
    print("========================================================\n")
    
    models = [
        "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "Qwen/Qwen2.5-Coder-14B-Instruct"
    ]
    
    # We ignore formats we don't need (like Flax/TensorFlow) to save disk space
    ignore_patterns = ["*.msgpack", "*.h5", "*.ot", "*.ckpt"]
    
    for model_id in models:
        print(f"Fetching: {model_id}")
        try:
            local_dir = os.path.join(os.getcwd(), "agent-python/offline_model/" + model_id.replace("/", "_"))
            os.makedirs(local_dir, exist_ok=True)
            
            cache_dir = snapshot_download(
                repo_id=model_id, 
                ignore_patterns=ignore_patterns,
                local_dir=local_dir,
                local_files_only=False 
            )
            print(f"[SUCCESS] Cached at: {cache_dir}\n")
        except Exception as e:
            print(f"[ERROR] Failed to download {model_id}: {e}\n")
    print("==============================================================")
    print("      Downloading jina-code-embeddings-1.5b to Local HF Cache ")
    print("==============================================================\n")   
    local_dir = os.path.join(os.getcwd(), "agent-python/offline_model/" + "jinaai_jina-code-embeddings-1.5b")
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(
        repo_id="jinaai/jina-code-embeddings-1.5b", 
        local_dir=local_dir,
        ignore_patterns=["*.msgpack", "*.h5", "rust_model.ot", "*.onnx"] 
    )
    print(f"Done! Model saved to {local_dir}")

if __name__ == "__main__":
    pre_download_qwen_models()