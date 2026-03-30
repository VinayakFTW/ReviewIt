import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Global references to keep the model in memory
_worker_model = None
_worker_tokenizer = None
_orchestrator_model = None
_orchestrator_tokenizer = None

def load_worker_model():
    global _worker_model, _worker_tokenizer
    if _worker_model is None:
        print("[ModelManager] Loading qwen2.5-coder:0.5b into PyTorch...")
        _worker_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
        _worker_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            device_map="auto",
            torch_dtype=torch.float16,
        )
    return _worker_model, _worker_tokenizer

def unload_workers():
    global _worker_model, _worker_tokenizer
    print("[ModelManager] Evicting worker model from VRAM...")
    del _worker_model
    del _worker_tokenizer
    _worker_model = None
    _worker_tokenizer = None
    torch.cuda.empty_cache()
    print("[ModelManager] Done.")
    return True

def load_orchestrator_model():
    global _orchestrator_model, _orchestrator_tokenizer
    if _orchestrator_model is None:
        print("[ModelManager] Loading qwen2.5-coder:14b into PyTorch...")
        # Make sure workers are unloaded to free VRAM!
        unload_workers() 
        
        _orchestrator_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-14B-Instruct")
        _orchestrator_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-Coder-14B-Instruct",
            device_map="auto",
            torch_dtype=torch.float16,
        )
    return _orchestrator_model, _orchestrator_tokenizer

def unload_orchestrator():
    global _orchestrator_model, _orchestrator_tokenizer
    print("[ModelManager] Evicting 14B model from VRAM...")
    del _orchestrator_model
    del _orchestrator_tokenizer
    _orchestrator_model = None
    _orchestrator_tokenizer = None
    torch.cuda.empty_cache()
    print("[ModelManager] Done.")
    return True