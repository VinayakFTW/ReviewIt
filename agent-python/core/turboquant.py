import torch
from transformers.cache_utils import Cache
from typing import Dict, Any, Tuple

class TurboQuantCache(Cache):
    def __init__(self, config, compression_bits=4):
        super().__init__()
        self.compression_bits = compression_bits
        
        # Safely extract head_dim from Qwen config
        if hasattr(config, "head_dim"):
            self.head_dim = config.head_dim
        else:
            self.head_dim = config.hidden_size // config.num_attention_heads
            
        # Storage for compressed states dictionaries
        # Format: layer_idx -> (q_x, scale, min_val, qjl_sign, qjl_scale)
        self.key_cache = {}
        self.value_cache = {}

        # These will be initialized dynamically to match device/dtype of the first tensor
        self.rotation_matrix = None
        self.inverse_rotation = None

    def _init_matrices(self, device, dtype):
        """Initializes the rotation matrices on the correct device and dtype."""
        if self.rotation_matrix is None:
            # 1. Generate the random orthogonal rotation matrix to spread outliers
            random_matrix = torch.randn(self.head_dim, self.head_dim, device=device, dtype=torch.float32)
            q, _ = torch.linalg.qr(random_matrix)
            self.rotation_matrix = q.to(dtype=dtype, device=device)
            self.inverse_rotation = self.rotation_matrix.T

    def _compress(self, x: torch.Tensor):
        """Encodes a full precision tensor into quantized state tuples."""
        # x shape: [batch, num_heads, seq_len, head_dim]
        rotated_x = torch.matmul(x, self.rotation_matrix)
        
        # --- Base Quantization (4-bit Uniform) ---
        min_val = rotated_x.amin(dim=-1, keepdim=True)
        max_val = rotated_x.amax(dim=-1, keepdim=True)
        
        # Calculate step scale for target bits
        scale = (max_val - min_val) / ((1 << self.compression_bits) - 1)
        scale = scale.clamp(min=1e-5) # Prevent division by zero
        
        # Quantize to int8
        q_x = torch.round((rotated_x - min_val) / scale).to(torch.int8)
        
        # --- Residual QJL (1-bit) ---
        # Calculate what the error currently is
        dequantized_base = (q_x.to(x.dtype) * scale) + min_val
        residual = rotated_x - dequantized_base
        
        # Extract sign (1-bit) and the magnitude scale of the residual
        qjl_sign = torch.sign(residual).to(torch.int8)
        qjl_scale = residual.abs().mean(dim=-1, keepdim=True) 
        
        return q_x, scale, min_val, qjl_sign, qjl_scale

    def _decompress(self, compressed_state) -> torch.Tensor:
        """Decodes state tuples back into a full precision tensor."""
        q_x, scale, min_val, qjl_sign, qjl_scale = compressed_state
        dtype = scale.dtype
        
        # Reconstruct base + scaled residual
        base = (q_x.to(dtype) * scale) + min_val
        res = qjl_sign.to(dtype) * qjl_scale
        reconstructed_rotated = base + res
        
        # Inverse rotation back to original basis
        reconstructed = torch.matmul(reconstructed_rotated, self.inverse_rotation)
        return reconstructed

    def _concat_states(self, past_state, new_state):
        """Concatenates new compressed tokens to the history along the sequence dimension."""
        # Dim -2 is the sequence length dimension in [batch, heads, seq, head_dim]
        return tuple(torch.cat([s1, s2], dim=-2) for s1, s2 in zip(past_state, new_state))

    def update(
        self,
        key_states: torch.Tensor,
        value_states: torch.Tensor,
        layer_idx: int,
        cache_kwargs: Dict[str, Any] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        
        # Ensure matrices match the current layer's tensors
        self._init_matrices(key_states.device, key_states.dtype)

        # 1. Compress the incoming new tokens
        new_compressed_k = self._compress(key_states)
        new_compressed_v = self._compress(value_states)

        # 2. Append to persistent cache
        if layer_idx not in self.key_cache:
            # First token (prompt processing)
            self.key_cache[layer_idx] = new_compressed_k
            self.value_cache[layer_idx] = new_compressed_v
        else:
            # Subsequent tokens (autoregressive generation)
            self.key_cache[layer_idx] = self._concat_states(self.key_cache[layer_idx], new_compressed_k)
            self.value_cache[layer_idx] = self._concat_states(self.value_cache[layer_idx], new_compressed_v)

        # 3. Decompress the *entire* sequence to return to standard Attention
        full_k = self._decompress(self.key_cache[layer_idx])
        full_v = self._decompress(self.value_cache[layer_idx])

        return full_k, full_v

    def get_seq_length(self, layer_idx: int = 0) -> int:
        if layer_idx not in self.key_cache:
            return 0
        # q_x is at index 0 of the state tuple. Its shape is [batch, heads, seq_len, head_dim]
        return self.key_cache[layer_idx][0].shape[-2]
        
    def get_max_length(self) -> int:
        # Hugging Face internal safety check fallback
        return 4096