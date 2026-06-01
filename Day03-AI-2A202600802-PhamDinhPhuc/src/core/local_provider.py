import time
import os
from typing import Dict, Any, Optional
from llama_cpp import Llama
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class LocalProvider(LLMProvider):
    """
    LLM Provider for local models using llama-cpp-python.
    Optimized for CPU usage with GGUF models.
    """
    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        super().__init__(model_name=os.path.basename(model_path))
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Please download it first.")
            
        # Initialize the Llama model
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # Prepare GGUF prompt structure
        full_prompt = ""
        if system_prompt:
            full_prompt += f"<|system|>\n{system_prompt}\n"
        full_prompt += f"<|user|>\n{prompt}\n<|assistant|>\n"
        
        try:
            response = self.llm(
                full_prompt,
                max_tokens=2048,
                temperature=0.1
            )
            latency = time.time() - start_time
            
            content = response["choices"][0]["text"] or ""
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            completion_tokens = usage.get("completion_tokens", len(content) // 4)
            total_tokens = prompt_tokens + completion_tokens
            
            # Structured telemetry logging
            logger.log_llm_metric(
                provider="Local",
                model=self.model_name,
                latency=latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
            return {
                "text": content,
                "latency": latency,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        except Exception as exc:
            latency = time.time() - start_time
            logger.log_event("LLM_ERROR", f"Local LLM call failed: {str(exc)}", {"latency": latency})
            raise
