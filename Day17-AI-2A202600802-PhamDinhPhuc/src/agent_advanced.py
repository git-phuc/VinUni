from __future__ import annotations

from typing import Any

from config import LabConfig, load_config
from memory_store import (
    CompactMemoryManager,
    UserProfileStore,
    answer_from_facts,
    estimate_tokens,
    extract_profile_updates,
    is_question,
)
from model_provider import build_chat_model


class AdvancedAgent:
    """Agent B — three memory layers working together:

    1. within-session memory (recent turns of the thread)
    2. persistent memory in `User.md` (survives across threads/sessions)
    3. compact memory that compresses older turns once a thread gets long
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

        self.langchain_agent = None
        if not self.force_offline and self.config.model.api_key:
            try:
                self._maybe_build_langchain_agent()
            except Exception:
                self.langchain_agent = None

    # -- public API ---------------------------------------------------------

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        # 1. Persist any stable facts to long-term memory (skipped for questions).
        updates = extract_profile_updates(message)
        if updates:
            facts = self.profile_store.get_facts(user_id)
            facts.update(updates)
            self.profile_store.save_facts(user_id, facts)

        # 2. Record the turn in compact (short-term) memory.
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)

        # 3. Generate the response.
        if self._is_live():
            response_text = self._reply_live(user_id, thread_id, message)
        else:
            response_text = self._offline_response(user_id, message)

        self.compact_memory.append(thread_id, "assistant", response_text)
        return self._record(thread_id, response_text, prompt_tokens)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def reset_thread(self, thread_id: str) -> None:
        """Drop short-term memory for a thread. `User.md` stays untouched."""
        self.compact_memory.state.pop(thread_id, None)
        self.thread_tokens.pop(thread_id, None)
        self.thread_prompt_tokens.pop(thread_id, None)

    # -- internals ----------------------------------------------------------

    def _is_live(self) -> bool:
        return not self.force_offline and self.langchain_agent is not None

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> str:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        ctx = self.compact_memory.context(thread_id)
        summary = ctx.get("summary", "")
        system_prompt = (
            "You are an advanced AI assistant with long-term memory about the user "
            "plus a compressed short-term context.\n\n"
            f"=== USER PROFILE ===\n{self.profile_store.read_text(user_id) or '(empty)'}\n\n"
            f"=== OLDER HISTORY SUMMARY ===\n{summary or 'No summary yet.'}\n\n"
            "Answer using the profile and history above. Be concise."
        )

        chat: list[Any] = [SystemMessage(content=system_prompt)]
        for m in ctx.get("messages", [])[:-1]:  # exclude the just-appended user turn
            chat.append(HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]))
        chat.append(HumanMessage(content=message))

        return self.langchain_agent.invoke(chat).content

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Context the agent carries each turn: profile + summary + kept turns.

        Compaction keeps this bounded, which is exactly what should make the
        advanced agent cheaper than the baseline on long threads."""
        ctx = self.compact_memory.context(thread_id)
        parts = [self.profile_store.read_text(user_id), ctx.get("summary", "")]
        parts += [f"{m['role']}: {m['content']}" for m in ctx.get("messages", [])]
        return estimate_tokens("\n".join(parts))

    def _offline_response(self, user_id: str, message: str) -> str:
        facts = self.profile_store.get_facts(user_id)
        if is_question(message):
            return answer_from_facts(facts, message)
        if facts:
            return "Mình đã ghi nhận và cập nhật hồ sơ dài hạn của bạn."
        return "Chào bạn, mình là Advanced Agent. Mình sẽ ghi nhớ các thông tin ổn định bạn chia sẻ."

    def _record(self, thread_id: str, response_text: str, prompt_tokens: int) -> dict[str, Any]:
        response_tokens = estimate_tokens(response_text)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        return {
            "response": response_text,
            "token_usage": response_tokens,
            "prompt_tokens_processed": prompt_tokens,
        }

    def _maybe_build_langchain_agent(self) -> None:
        self.langchain_agent = build_chat_model(self.config.model)
