import time
import google.generativeai as genai
from typing import Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt
            
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1
                ),
                **config
            )
            latency = time.time() - start_time
            
            content = response.text or ""
            
            # Approximate token counts for Gemini (1 token ~ 4 chars) or count using SDK
            try:
                prompt_tokens = self.model.count_tokens(prompt).total_tokens
                completion_tokens = self.model.count_tokens(content).total_tokens
                total_tokens = prompt_tokens + completion_tokens
            except Exception:
                prompt_tokens = len(prompt) // 4
                completion_tokens = len(content) // 4
                total_tokens = prompt_tokens + completion_tokens

            # Structured telemetry logging
            logger.log_llm_metric(
                provider="Gemini",
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
            logger.log_event("LLM_ERROR", f"Gemini call failed: {str(exc)}", {"latency": latency})
            raise
