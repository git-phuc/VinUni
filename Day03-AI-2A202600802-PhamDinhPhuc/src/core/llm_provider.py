from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Supports OpenAI, Gemini, and Local models.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates content from the LLM.
        Returns:
            Dict containing:
                "text": str (the generated content)
                "latency": float (execution time in seconds)
                "prompt_tokens": int (input token usage)
                "completion_tokens": int (output token usage)
                "total_tokens": int (total token usage)
        """
        pass
