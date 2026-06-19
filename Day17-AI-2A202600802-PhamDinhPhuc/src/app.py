import json
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr

# Ensure the src folder is importable.
sys.path.append(str(Path(__file__).resolve().parent))

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config
from model_provider import build_chat_model

config = load_config(Path(__file__).resolve().parent.parent)

api_key_exists = bool(config.model.api_key)
force_offline_default = not api_key_exists

agents = {
    "baseline": BaselineAgent(config, force_offline=force_offline_default),
    "advanced": AdvancedAgent(config, force_offline=force_offline_default),
}


def _agent_for(agent_type: str):
    return agents["advanced"] if agent_type == "Advanced Agent" else agents["baseline"]


def update_agents_mode(offline_mode: bool) -> str:
    """Toggle offline/live for both agents, building the live model on demand."""
    if not offline_mode:
        if not api_key_exists:
            return "⚠️ No API key found — staying in **Offline (Rule-based)** mode."
        for agent in agents.values():
            agent.force_offline = False
            if agent.langchain_agent is None:
                try:
                    agent.langchain_agent = build_chat_model(config.model)
                except Exception as exc:  # pragma: no cover - depends on live creds
                    agent.force_offline = True
                    return f"⚠️ Could not start live model ({exc}). Staying **Offline**."
        return "Agents updated to: **Live (LLM-based)** mode."

    for agent in agents.values():
        agent.force_offline = True
    return "Agents updated to: **Offline (Rule-based)** mode."


def get_profile_content(user_id: str) -> str:
    path = agents["advanced"].profile_store.path_for(user_id)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "*No profile exists yet for this user. Send a message to extract facts!*"


def save_profile_content(user_id: str, content: str) -> str:
    if not user_id.strip():
        return "Error: User ID cannot be empty!"
    path = agents["advanced"].profile_store.write_text(user_id, content)
    return f"Successfully saved to {path.name}!"


def log_chat_message(user_id, thread_id, agent_type, mode, message, response, token_usage, prompt_tokens, compactions):
    log_dir = config.state_dir / "chat_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "thread_id": thread_id,
        "agent_type": agent_type,
        "mode": mode,
        "message": message,
        "response": response,
        "token_usage": token_usage,
        "prompt_tokens_processed": prompt_tokens,
        "compactions": compactions,
    }
    with open(log_dir / f"{user_id}_{thread_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _short_term_view(agent, agent_type: str, thread_id: str) -> str:
    summary = "None"
    recent = []
    if agent_type == "Advanced Agent":
        ctx = agent.compact_memory.context(thread_id)
        summary = ctx.get("summary") or "None"
        recent = [f"{m['role'].upper()}: {m['content']}" for m in ctx.get("messages", [])]
    else:
        session = agent.sessions.get(thread_id)
        if session:
            recent = [f"{m['role'].upper()}: {m['content']}" for m in session.messages]

    body = "\n".join(f"- {m}" for m in recent) if recent else "None"
    return f"### Summary of Older Messages:\n{summary}\n\n### Kept Short-Term Messages:\n{body}"


def chat_interface_fn(user_id, thread_id, agent_type, message, history):
    if not user_id.strip():
        return history, "Error: Please enter a User ID first!", "", 0, 0, 0, ""
    if not thread_id.strip():
        return history, "Error: Please enter a Thread ID first!", "", 0, 0, 0, ""

    agent = _agent_for(agent_type)
    if not message.strip():
        # Nothing to send — just refresh the inspector/stats for this thread.
        return (
            history, "", _short_term_view(agent, agent_type, thread_id),
            agent.token_usage(thread_id), agent.prompt_token_usage(thread_id),
            agent.compaction_count(thread_id), get_profile_content(user_id),
        )

    result = agent.reply(user_id, thread_id, message)
    reply_text = result.get("response", "")
    history = history + [(message, reply_text)]

    token_usage = agent.token_usage(thread_id)
    prompt_tokens = agent.prompt_token_usage(thread_id)
    compactions = agent.compaction_count(thread_id)

    mode = "offline" if agent.force_offline else "live"
    log_chat_message(user_id, thread_id, agent_type, mode, message, reply_text, token_usage, prompt_tokens, compactions)

    short_term = _short_term_view(agent, agent_type, thread_id)
    profile_summary = get_profile_content(user_id)
    return history, "", short_term, token_usage, prompt_tokens, compactions, profile_summary


def clear_thread(user_id, thread_id, agent_type):
    """Reset the chat AND the selected agent's short-term memory for this thread.
    Persistent `User.md` is intentionally left untouched."""
    agent = _agent_for(agent_type)
    if thread_id.strip():
        agent.reset_thread(thread_id)
    inspector = "*No messages in this session yet.*"
    return [], "", inspector, 0, 0, 0


def run_suite(suite_type):
    from benchmark import format_rows, load_conversations, run_agent_benchmark

    if suite_type == "Standard Benchmark":
        convs = load_conversations(config.data_dir / "conversations.json")
        title = "Standard Benchmark Results (10 sessions)"
    else:
        convs = load_conversations(config.data_dir / "advanced_long_context.json")
        title = "Long-Context Stress Benchmark Results"

    # Benchmarks always run offline so results are deterministic and free.
    b_row = run_agent_benchmark("Baseline Agent", BaselineAgent(config, force_offline=True), convs, config)
    a_row = run_agent_benchmark("Advanced Agent", AdvancedAgent(config, force_offline=True), convs, config)
    return f"### {title}\n\n{format_rows([b_row, a_row])}"


custom_css = """
body { background-color: #0b0f19; color: #e2e8f0; }
.gradio-container { font-family: 'Outfit', 'Inter', sans-serif !important; }
#title_panel {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 24px; border-radius: 12px; border: 1px solid #334155;
    margin-bottom: 24px; text-align: center;
}
#title_panel h1 { color: #38bdf8 !important; font-weight: 800; }
.stat-card {
    background-color: #1e293b; border: 1px solid #334155;
    padding: 16px; border-radius: 8px; text-align: center;
}
"""

with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    with gr.Row(elem_id="title_panel"):
        gr.Markdown(
            "# 🧠 Memory-Aware Agent Systems Playground (Day 17)\n"
            "Evaluate short-term, persistent, and compressed memory architectures."
        )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Mode Settings")
            offline_toggle = gr.Checkbox(label="Force Offline Mode (Rule-based)", value=force_offline_default)
            api_status = "Available" if api_key_exists else "Not Found (Using offline fallback)"
            gr.Markdown(f"**API Key:** {api_status}")
            status_text = gr.Markdown("Mode is currently initialized.")

        with gr.Column(scale=2):
            with gr.Row():
                user_id_input = gr.Textbox(label="User ID", value="dungct", placeholder="e.g. dungct")
                thread_id_input = gr.Textbox(label="Thread ID", value="session_01", placeholder="e.g. session_01")
                agent_select = gr.Radio(
                    choices=["Baseline Agent", "Advanced Agent"], label="Selected Agent", value="Advanced Agent"
                )

    with gr.Tabs():
        with gr.Tab("💬 Interactive Chat"):
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(label="Chat Console", height=450)
                    msg_input = gr.Textbox(
                        label="Message",
                        placeholder="Say hello, tell the agent some facts, or ask a recall question...",
                        container=False,
                    )
                    clear_btn = gr.Button("Clear Chat & Thread Memory")
                with gr.Column(scale=1):
                    gr.Markdown("### 📊 Live Statistics (Current Thread)")
                    with gr.Row():
                        stat_out_tokens = gr.Number(label="Output Tokens", value=0, interactive=False)
                        stat_prompt_tokens = gr.Number(label="Prompt Context Tokens", value=0, interactive=False)
                        stat_compactions = gr.Number(label="Compactions Triggered", value=0, interactive=False)
                    gr.Markdown("### 📜 Short-Term Memory Inspector")
                    st_inspector = gr.Markdown("*No messages in this session yet.*")

        with gr.Tab("📂 Persistent User Profile (User.md)"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 👤 User facts store (`User.md` contents)")
                    profile_viewer = gr.Markdown()
                    refresh_profile_btn = gr.Button("🔄 Refresh Profile")
                with gr.Column():
                    gr.Markdown("### ✏️ Edit Profile Directly")
                    profile_editor = gr.TextArea(label="Raw Markdown Profile Editor", lines=12)
                    save_profile_btn = gr.Button("💾 Save Edited Profile")
                    save_status = gr.Markdown()

        with gr.Tab("📈 Benchmarks Dashboard"):
            with gr.Row():
                benchmark_select = gr.Radio(
                    choices=["Standard Benchmark", "Long-Context Stress Benchmark"],
                    label="Select Benchmark Dataset",
                    value="Standard Benchmark",
                )
                run_btn = gr.Button("⚡ Run Offline Benchmark", variant="primary")
            with gr.Row():
                benchmark_results = gr.Markdown("Click run to execute the evaluation suite.")

    chat_outputs = [chatbot, msg_input, st_inspector, stat_out_tokens, stat_prompt_tokens, stat_compactions, profile_viewer]

    offline_toggle.change(update_agents_mode, inputs=[offline_toggle], outputs=[status_text])

    msg_input.submit(
        chat_interface_fn,
        inputs=[user_id_input, thread_id_input, agent_select, msg_input, chatbot],
        outputs=chat_outputs,
    )

    clear_btn.click(
        clear_thread,
        inputs=[user_id_input, thread_id_input, agent_select],
        outputs=[chatbot, msg_input, st_inspector, stat_out_tokens, stat_prompt_tokens, stat_compactions],
        queue=False,
    )

    refresh_profile_btn.click(get_profile_content, inputs=[user_id_input], outputs=[profile_viewer])
    save_profile_btn.click(save_profile_content, inputs=[user_id_input, profile_editor], outputs=[save_status])
    user_id_input.change(get_profile_content, inputs=[user_id_input], outputs=[profile_editor])
    run_btn.click(run_suite, inputs=[benchmark_select], outputs=[benchmark_results])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
