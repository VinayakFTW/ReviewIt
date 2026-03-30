import torch
from core.turboquant import TurboQuantCache

@torch.inference_mode()
def precompute_system_prefix(system_prompt: str, model, tokenizer):
    """Encodes the system prompt once and returns its compressed KV cache."""
    # Format just the system portion
    messages = [{"role": "system", "content": system_prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False)
    
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    tq_cache = TurboQuantCache(model.config)
    
    # Run a forward pass to populate the cache (no token generation)
    model(**inputs, past_key_values=tq_cache, use_cache=True)
    
    return tq_cache, inputs.input_ids.shape[1]

@torch.inference_mode()
def generate_with_turboquant(user_query: str, base_cache: TurboQuantCache, model, tokenizer, max_new_tokens=2048, temperature=0.1) -> str:
    # Format prompt for Qwen Instruct
    messages = [{"role": "user", "content": user_query}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    req_cache = base_cache.clone()

    
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        past_key_values=req_cache, # <--- TurboQuant injection
        use_cache=True,
        temperature=temperature,
        do_sample=(temperature > 0)
    )
    
    # Strip the input prompt from the generated output
    generated_ids = outputs[0][len(inputs.input_ids[0]):]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()