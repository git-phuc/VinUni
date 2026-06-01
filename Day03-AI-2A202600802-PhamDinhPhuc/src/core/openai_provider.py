import time
import json
import urllib.error
import urllib.request
from typing import Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            request = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(
                    {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            latency = time.time() - start_time
            
            content = payload.get("choices", [{}])[0].get("message", {}).get("content") or ""
            usage = payload.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
            total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
            
            # Structured telemetry logging
            logger.log_llm_metric(
                provider="OpenAI",
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
        except urllib.error.HTTPError as exc:
            latency = time.time() - start_time
            error_text = exc.read().decode("utf-8", errors="replace")
            logger.log_event("LLM_ERROR", f"OpenAI call failed: {error_text[:500]}", {"latency": latency})
            raise
        except Exception as exc:
            latency = time.time() - start_time
            logger.log_event("LLM_ERROR", f"OpenAI call failed: {str(exc)}", {"latency": latency})
            raise
