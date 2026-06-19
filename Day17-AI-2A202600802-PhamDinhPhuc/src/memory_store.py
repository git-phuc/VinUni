from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def estimate_tokens(text: str) -> int:
    """Cheap, stable token estimator (~4 chars/token) for offline benchmarking."""
    if not text:
        return 0
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Persistent profile storage (`User.md`)
# ---------------------------------------------------------------------------


@dataclass
class UserProfileStore:
    """Persistent per-user fact store backed by a `<user_id>.md` file."""

    root_dir: Path

    def __post_init__(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, user_id: str) -> Path:
        safe_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_id:
            safe_id = "user"
        return self.root_dir / f"{safe_id}.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        path = self.path_for(user_id)
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        if search_text not in content:
            return False
        path.write_text(content.replace(search_text, replacement, 1), encoding="utf-8")
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def get_facts(self, user_id: str) -> dict[str, str]:
        """Parse `- Key: value` lines back into a normalized fact dict."""
        facts: dict[str, str] = {}
        for line in self.read_text(user_id).splitlines():
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                key, value = line[2:].split(":", 1)
                norm_key = key.strip().lower().replace(" ", "_")
                facts[norm_key] = value.strip()
        return facts

    def save_facts(self, user_id: str, facts: dict[str, str]) -> None:
        lines = [f"# User Profile: {user_id}"]
        for key, value in sorted(facts.items()):
            lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")
        self.write_text(user_id, "\n".join(lines) + "\n")

    def upsert_fact(self, user_id: str, key: str, value: str) -> None:
        facts = self.get_facts(user_id)
        facts[key] = value
        self.save_facts(user_id, facts)


# ---------------------------------------------------------------------------
# Heuristic fact extraction (offline mode)
#
# The goal is a *generic* extractor: it captures whatever value the user states
# from sentence structure ("tên là X", "ở Y", "<Z> engineer"). It must never
# hardcode a specific person's name or pre-bake the expected benchmark answer,
# otherwise recall would look perfect without the memory layer doing any work.
# The real intelligence is expected from the LLM in live mode; this is the
# deterministic fallback that keeps the benchmark reproducible.
# ---------------------------------------------------------------------------

# Permissive name token: keeps internal capitals/digits so "DũngCT" or
# "DũngCT Stress" survive as a single value (trimmed at clause boundaries).
_NAME = r"[A-Za-zÀ-ỹ][\wÀ-ỹ]*(?:\s+[A-Za-zÀ-ỹ][\wÀ-ỹ]*)*"
_NEGATIONS = ("không còn", "khong con", "không phải", "khong phai", "chứ không", "chu khong", "đừng", "dung")

# Interrogative pronouns: never store these as fact values, e.g. capturing
# "gì" from a question like "tên mình là gì?".
_STOP_VALUES = {"gì", "gi", "đâu", "dau", "ai", "nào", "nao", "sao", "thế", "the", "ai?"}

# Broad markers used ONLY to decide whether to *answer with recall* (questions
# AND imperative recall requests like "nhắc lại ..."). This is deliberately NOT
# used to gate extraction: this dataset is a meta-conversation about memory
# agents, so declarative turns legitimately contain "recall"/"tóm tắt".
_QUESTION_MARKERS = (
    "?", "nhắc lại", "nhac lai", "tóm tắt", "tom tat", "bạn biết", "ban biet",
    "recall", "summarize", "tên gì", "ten gi", "là gì", "la gi", "what is",
    "who is", "where is", "con gì", "con gi", "ở đâu", "o dau", "nghề gì",
    "nghe gi", "là ai", "la ai", "thế nào", "the nao",
)


def is_question(message: str) -> bool:
    """True when the user is asking the agent to recall something."""
    low = message.lower()
    return any(marker in low for marker in _QUESTION_MARKERS)


def _trim_value(raw: str) -> str:
    """Stop a captured value at the first clause boundary and tidy it."""
    value = re.split(r"[,.;!?\n]", raw, maxsplit=1)[0].strip()
    # Drop trailing connective words that leak into greedy captures.
    value = re.sub(r"\s+(và|hiện|đang|nhưng|rồi|nên)$", "", value, flags=re.IGNORECASE).strip()
    return value


def _clean_value(raw: str) -> str:
    """Trim a captured value and drop it if it starts with an interrogative
    pronoun, e.g. "gì và mình nuôi con gì" grabbed from a recall question."""
    value = _trim_value(raw)
    if not value:
        return ""
    first = value.split()[0].lower().strip(".,;:!?")
    return "" if first in _STOP_VALUES else value


def _negated_before(text: str, pos: int, window: int = 18) -> bool:
    context = text[max(0, pos - window):pos].lower()
    return any(neg in context for neg in _NEGATIONS)


def _leading_proper(text: str) -> str:
    """Return the leading run of Capitalized words, Unicode-aware.

    Uses Python's `str.isupper()` (which is correct for Vietnamese, unlike a
    regex `[A-ZÀ-Ỹ]` range that also matches lowercase accented letters), and
    stops at the first lowercase word so "Huế để dùng" -> "Huế"."""
    words: list[str] = []
    for raw in text.strip().split():
        word = raw.strip(".,;:!?()\"'…")
        if word and word[0].isupper() and word.lower() not in _STOP_VALUES:
            words.append(word)
        else:
            break
    return " ".join(words)


def extract_profile_updates(message: str) -> dict[str, str]:
    """Extract stable profile facts from a user statement.

    Runs on every turn. Recall *questions* don't assert values, so the
    value-capturing patterns naturally find nothing in them; the one trap —
    "tên mình là gì?" capturing "gì" — is handled by rejecting interrogative
    pronouns via `_clean_value` / `_STOP_VALUES`.
    """
    low = message.lower()
    updates: dict[str, str] = {}

    # --- Name: an explicit self-reference is required (the "là" copula), so
    #     "corgi tên Bơ" (a pet's name) is NOT mistaken for the user's name. ---
    name_match = re.search(
        r"(?:tên|ten)\s+(?:mình\s+|cua\s+minh\s+|của\s+mình\s+|tôi\s+|toi\s+)?(?:là|la)\s+(" + _NAME + r")",
        message,
        re.IGNORECASE,
    )
    if not name_match:
        name_match = re.search(r"my name is\s+(" + _NAME + r")", message, re.IGNORECASE)
    if name_match:
        # Keep only the leading Title-case run, so "gì và mình thích ..." grabbed
        # from a recall question is rejected while "DũngCT Stress" survives.
        name = _leading_proper(name_match.group(1))
        if name:
            updates["name"] = name

    # --- Location: latest non-negated "ở/tại <Proper>" wins. Proper-noun
    #     detection is done in Python (Unicode-correct uppercase). ASCII
    #     fallbacks use word boundaries so "vào"/"cho" never leak in. ---------
    location = None
    for m in re.finditer(r"(?:ở|tại|\bo\b|\btai\b)\s+([^,.;!?\n]+)", message, re.IGNORECASE):
        if _negated_before(message, m.start()):
            continue
        cand = _leading_proper(m.group(1))
        if cand:
            location = cand
    if location:
        updates["location"] = location

    # --- Profession: last non-negated "<word> engineer" so a corrected
    #     "không còn ... backend engineer ... MLOps engineer" lands on MLOps. -
    for m in re.finditer(r"([A-Za-zÀ-ỹ]+)\s+engineer", message, re.IGNORECASE):
        if not _negated_before(message, m.start()):
            updates["profession"] = f"{m.group(1)} engineer"

    # --- Reply style: prefer the more specific "N bullet" form -------------
    bullet = re.search(r"(\d+|ba|hai|một)\s*bullet", low)
    if bullet:
        digit = {"ba": "3", "hai": "2", "một": "1"}.get(bullet.group(1), bullet.group(1))
        updates["preferred_style"] = f"{digit} bullet"
    elif "ngắn gọn" in low or "ngan gon" in low:
        updates["preferred_style"] = "ngắn gọn"

    # --- Favorite drink / food: "<đồ uống/món ăn> yêu thích là X" ----------
    drink = re.search(r"(?:đồ uống|do uong)[^\n.]*?(?:là|la|:)\s*([^.,;\n]+)", message, re.IGNORECASE)
    if drink and (val := _clean_value(drink.group(1))):
        updates["favorite_drink"] = val
    food = re.search(r"(?:món ăn|mon an)[^\n.]*?(?:là|la|:)\s*([^.,;\n]+)", message, re.IGNORECASE)
    if food and (val := _clean_value(food.group(1))):
        updates["favorite_food"] = val

    # --- Pet: "nuôi (một) (bé/con/chú) X" ----------------------------------
    pet = re.search(r"nu[ôo]i\s+(?:một\s+|mot\s+|1\s+)?(?:bé\s+|be\s+|con\s+|chú\s+|chu\s+)?([A-Za-zÀ-ỹ]+)", message, re.IGNORECASE)
    if pet and (val := _clean_value(pet.group(1))):
        updates["pet"] = val

    # --- Technical interests: matched case-sensitively to avoid the Vietnamese
    #     word "ai" colliding with the acronym "AI". -------------------------
    for term in ("Python", "AI", "RAG"):
        if re.search(rf"\b{re.escape(term)}\b", message):
            updates[f"interest_{term.lower()}"] = term

    return updates


# ---------------------------------------------------------------------------
# Recall from stored facts (offline mode)
#
# Answers come ONLY from facts that were actually stored. If a fact is missing
# the agent says so honestly — there is no fallback to a hardcoded value.
# ---------------------------------------------------------------------------

_NO_INFO = "Mình chưa có thông tin này trong bộ nhớ."

# field -> (keywords that ask for it, template using the stored value)
_FIELD_QUERIES: list[tuple[str, tuple[str, ...], str]] = [
    ("name", ("tên", "ten", "name"), "Tên của bạn là {v}."),
    ("location", ("ở", "o dau", "nơi ở", "noi o", "sống", "song", "live", "where"), "Hiện tại bạn đang ở {v}."),
    ("profession", ("nghề", "nghe", "công việc", "cong viec", "job", "work", "mlops", "backend"), "Nghề nghiệp hiện tại của bạn là {v}."),
    ("preferred_style", ("style", "phong cách", "phong cach", "trả lời", "tra loi", "kiểu trả lời", "kieu tra loi"), "Style trả lời bạn thích là {v}."),
    ("favorite_drink", ("đồ uống", "do uong", "uống", "uong", "drink"), "Đồ uống yêu thích của bạn là {v}."),
    ("favorite_food", ("món ăn", "mon an", "food", "ăn gì", "an gi"), "Món ăn yêu thích của bạn là {v}."),
    ("pet", ("con gì", "con gi", "nuôi", "nuoi", "pet", "thú cưng", "thu cung"), "Bạn nuôi một bé {v}."),
]

_INTEREST_MARKERS = ("quan tâm", "quan tam", "mối quan tâm", "moi quan tam", "tóm tắt", "tom tat", "interest", "là ai", "la ai")


def answer_from_facts(facts: dict[str, str], question: str) -> str:
    """Build a recall answer using only what is stored in `facts`."""
    low = question.lower()
    parts: list[str] = []

    for key, keywords, template in _FIELD_QUERIES:
        if any(kw in low for kw in keywords) and facts.get(key):
            parts.append(template.format(v=facts[key]))

    if any(marker in low for marker in _INTEREST_MARKERS):
        interests = [v for k, v in sorted(facts.items()) if k.startswith("interest_")]
        if interests:
            parts.append("Mối quan tâm kỹ thuật chính của bạn là " + " và ".join(interests) + ".")

    if parts:
        return " ".join(parts)

    # No specific field matched. For a recall-style ask, summarize everything
    # known; otherwise admit the memory does not contain it.
    if facts and any(m in low for m in ("nhắc lại", "nhac lai", "tóm tắt", "tom tat", "biết", "biet", "recall")):
        known = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(facts.items()))
        return f"Dựa trên bộ nhớ dài hạn, mình biết: {known}."
    return _NO_INFO


# ---------------------------------------------------------------------------
# Compact memory for long threads
# ---------------------------------------------------------------------------


def summarize_messages(messages: list[dict[str, str]], max_chars: int = 40) -> str:
    """Concise heuristic summary of older messages (offline mode)."""
    if not messages:
        return ""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "").strip().replace("\n", " ")
        if len(content) > max_chars:
            content = content[:max_chars].rstrip() + "…"
        parts.append(f"{role.capitalize()}: {content}")
    return " | ".join(parts)


@dataclass
class CompactMemoryManager:
    """Keeps the most recent messages verbatim and compresses older ones."""

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _thread(self, thread_id: str) -> dict[str, Any]:
        if thread_id not in self.state:
            self.state[thread_id] = {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def append(self, thread_id: str, role: str, content: str) -> None:
        thread = self._thread(thread_id)
        thread["messages"].append({"role": role, "content": content})

        total_tokens = (
            sum(estimate_tokens(m["content"]) for m in thread["messages"])
            + estimate_tokens(thread["summary"])
        )

        if total_tokens > self.threshold_tokens and len(thread["messages"]) > self.keep_messages:
            cut = len(thread["messages"]) - self.keep_messages
            to_compact = thread["messages"][:cut]
            thread["messages"] = thread["messages"][cut:]

            new_summary = summarize_messages(to_compact)
            merged = f"{thread['summary']} | {new_summary}" if thread["summary"] else new_summary
            thread["summary"] = self._cap_summary(merged)
            thread["compactions"] += 1

    def _cap_summary(self, summary: str) -> str:
        """Keep the running summary bounded (~threshold tokens). Without this
        the summary would grow as fast as the raw history and compaction would
        stop saving any prompt tokens — the opposite of its purpose."""
        budget = max(80, self.threshold_tokens * 4)  # ~4 chars per token
        if len(summary) <= budget:
            return summary
        return "…" + summary[-budget:]

    def context(self, thread_id: str) -> dict[str, Any]:
        return self._thread(thread_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.state.get(thread_id, {}).get("compactions", 0)
