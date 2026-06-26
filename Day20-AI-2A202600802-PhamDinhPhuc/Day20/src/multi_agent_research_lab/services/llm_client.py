"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass



import logging
from openai import OpenAI
from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client using OpenAI."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.openai_api_key
        self.model = self.settings.openai_model

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        Uses the configured OpenAI API key and model, tracks token usage, and
        calculates estimated API usage costs.
        """
        if not self.api_key or "your_openai_api_key" in self.api_key or not self.api_key.strip():
            raise ValueError(
                "OPENAI_API_KEY is not set or is still a placeholder in your .env file. "
                "Please configure a valid API key to proceed."
            )

        client = OpenAI(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0

            # Cost calculation based on model type
            if "gpt-4o-mini" in self.model:
                cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
            elif "gpt-4o" in self.model:
                cost = (prompt_tokens * 5.00 + completion_tokens * 15.00) / 1_000_000
            else:
                cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000

            return LLMResponse(
                content=content,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_usd=cost,
            )
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

