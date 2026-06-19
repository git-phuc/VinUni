from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    """Build an isolated config for tests."""
    from config import LabConfig
    from model_provider import ProviderConfig

    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=tmp_path / "state",
        compact_threshold_tokens=50,
        compact_keep_messages=2,
        model=ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.0),
        judge_model=ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.0)
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Verify `User.md` can be created, updated, and edited."""
    from memory_store import UserProfileStore
    store = UserProfileStore(tmp_path / "profiles")
    user_id = "test_user"
    
    # Test Write
    content = "# User Profile: test_user\n- Tên: John Doe\n"
    path = store.write_text(user_id, content)
    assert path.exists()
    
    # Test Read
    read_content = store.read_text(user_id)
    assert "John Doe" in read_content
    
    # Test Edit
    edited = store.edit_text(user_id, "John Doe", "Jane Doe")
    assert edited
    assert "Jane Doe" in store.read_text(user_id)
    assert "John Doe" not in store.read_text(user_id)
    
    # Test File Size
    assert store.file_size(user_id) > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Verify long threads trigger compaction."""
    from memory_store import CompactMemoryManager
    manager = CompactMemoryManager(threshold_tokens=20, keep_messages=2)
    thread_id = "thread_1"
    
    manager.append(thread_id, "user", "Hello")
    manager.append(thread_id, "assistant", "Hi there")
    assert manager.compaction_count(thread_id) == 0
    
    manager.append(thread_id, "user", "This is a very long message that will definitely exceed the token threshold and trigger compaction since it is way over eighty characters long.")
    
    ctx = manager.context(thread_id)
    assert manager.compaction_count(thread_id) > 0
    assert len(ctx["messages"]) == 2
    assert ctx["summary"] != ""


def test_cross_session_recall(tmp_path: Path) -> None:
    """Verify advanced remembers across sessions and baseline does not."""
    config = make_config(tmp_path)
    
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    user_id = "user_abc"
    
    baseline.reply(user_id, "session_1", "Tên mình là DũngCT")
    advanced.reply(user_id, "session_1", "Tên mình là DũngCT")
    
    res_base = baseline.reply(user_id, "session_2", "Mình tên gì?")
    res_adv = advanced.reply(user_id, "session_2", "Mình tên gì?")
    
    assert "DũngCT" not in res_base["response"]
    assert "DũngCT" in res_adv["response"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Compare prompt load of baseline vs advanced on a long thread."""
    config = make_config(tmp_path)
    
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    user_id = "user_xyz"
    thread_id = "long_thread"
    
    for i in range(10):
        baseline.reply(user_id, thread_id, f"Đây là tin nhắn thứ {i} chứa rất nhiều nội dung để tăng số lượng token nhanh chóng.")
        advanced.reply(user_id, thread_id, f"Đây là tin nhắn thứ {i} chứa rất nhiều nội dung để tăng số lượng token nhanh chóng.")
        
    res_base = baseline.reply(user_id, thread_id, "Nêu style trả lời của mình.")
    res_adv = advanced.reply(user_id, thread_id, "Nêu style trả lời của mình.")
    
    assert res_adv["prompt_tokens_processed"] < res_base["prompt_tokens_processed"]

