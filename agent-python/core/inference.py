import torch
from core.turboquant import TurboQuantCache

@torch.inference_mode()
def generate_with_turboquant(prompt: str, model, tokenizer, max_new_tokens=512, temperature=0.1) -> str:
    # Format prompt for Qwen Instruct
    messages = [
        {"role": "system", "content": "You are a senior software engineer."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    # Initialize the compressed cache
    tq_cache = TurboQuantCache(model.config)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        past_key_values=tq_cache, # <--- TurboQuant injection
        use_cache=True,
        temperature=temperature,
        do_sample=(temperature > 0)
    )
    
    # Strip the input prompt from the generated output
    generated_ids = outputs[0][len(inputs.input_ids[0]):]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()