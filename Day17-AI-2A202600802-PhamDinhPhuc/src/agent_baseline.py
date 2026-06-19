from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import answer_from_facts, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class SessionState:
    """Per-thread state. Nothing here is shared across threads, which is what
    makes the baseline forget the user as soon as a new thread starts."""

    messages: list[dict[str, str]] = field(default_factory=list)
    facts: dict[str, str] = field(default_factory=dict)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Agent A — within-session memory only.

    - Remembers facts inside the *current* thread.
    - Has no persistent `User.md`.
    - Therefore cannot recall anything in a fresh thread, which is the whole
      point of comparing it against the advanced agent.
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}
        self.langchain_agent = None
        if not self.force_offline and self.config.model.api_key:
            try:
                self._maybe_build_langchain_agent()
            except Exception:
                self.langchain_agent = None

    # -- public API ---------------------------------------------------------

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        session = self.sessions.setdefault(thread_id, SessionState())
        # Learn facts, but only within this thread's scope.
        session.facts.update(extract_profile_updates(message))

        if self._is_live():
            return self._reply_live(session, message)
        return self._reply_offline(session, message)

    def token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.token_usage if session else 0

    def prompt_token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.prompt_tokens_processed if session else 0

    def compaction_count(self, thread_id: str) -> int:
        # The baseline never compacts; it just keeps the full thread.
        return 0

    def reset_thread(self, thread_id: str) -> None:
        self.sessions.pop(thread_id, None)

    # -- internals ----------------------------------------------------------

    def _is_live(self) -> bool:
        return not self.force_offline and self.langchain_agent is not None

    def _reply_live(self, session: SessionState, message: str) -> dict[str, Any]:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        chat = [SystemMessage(content="You are a helpful assistant. You only remember the current conversation.")]
        for m in session.messages:
            chat.append(HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]))
        chat.append(HumanMessage(content=message))

        prompt_tokens = estimate_tokens("".join(m.content for m in chat))
        response_text = self.langchain_agent.invoke(chat).content
        return self._record(session, message, response_text, prompt_tokens)

    def _reply_offline(self, session: SessionState, message: str) -> dict[str, Any]:
        prompt_tokens = estimate_tokens("".join(m["content"] for m in session.messages) + message)
        response_text = self._answer(session, message)
        return self._record(session, message, response_text, prompt_tokens)

    def _answer(self, session: SessionState, message: str) -> str:
        if session.facts:
            answer = answer_from_facts(session.facts, message)
        else:
            answer = "Mình chưa có thông tin này vì cuộc trò chuyện mới bắt đầu."
        # A fresh thread never has facts, so recall questions honestly fail.
        return answer

    def _record(self, session: SessionState, message: str, response_text: str, prompt_tokens: int) -> dict[str, Any]:
        response_tokens = estimate_tokens(response_text)
        session.messages.append({"role": "user", "content": message})
        session.messages.append({"role": "assistant", "content": response_text})
        session.token_usage += response_tokens
        session.prompt_tokens_processed += prompt_tokens
        return {
            "response": response_text,
            "token_usage": response_tokens,
            "prompt_tokens_processed": prompt_tokens,
        }

    def _maybe_build_langchain_agent(self) -> None:
        self.langchain_agent = build_chat_model(self.config.model)
