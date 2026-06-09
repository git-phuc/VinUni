"""Shared LLM factory for all agents."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client using OpenAI."""
    load_dotenv()
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
    )
