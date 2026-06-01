const els = {
  modelBadge: document.querySelector("#modelBadge"),
  keyBadge: document.querySelector("#keyBadge"),
  toggleSidebarBtn: document.querySelector("#toggleSidebarBtn"),
  modeButtons: Array.from(document.querySelectorAll(".mode-card")),
  sessionList: document.querySelector("#sessionList"),
  newSessionBtn: document.querySelector("#newSessionBtn"),
  sessionTitle: document.querySelector("#sessionTitle"),
  rawNote: document.querySelector("#rawNote"),
  runModeBtn: document.querySelector("#runModeBtn"),
  errorBox: document.querySelector("#errorBox"),
  modeKicker: document.querySelector("#modeKicker"),
  modeTitle: document.querySelector("#modeTitle"),
  modeStatusBadge: document.querySelector("#modeStatusBadge"),
  outputDetails: document.querySelector("#outputDetails"),
  chatbotView: document.querySelector("#chatbotView"),
  agentView: document.querySelector("#agentView"),
  mixView: document.querySelector("#mixView"),
  chatbotMeta: document.querySelector("#chatbotMeta"),
  chatbotResult: document.querySelector("#chatbotResult"),
  chatbotScore: document.querySelector("#chatbotScore"),
  agentMeta: document.querySelector("#agentMeta"),
  agentResult: document.querySelector("#agentResult"),
  agentScore: document.querySelector("#agentScore"),
  winnerBadge: document.querySelector("#winnerBadge"),
  comparisonBox: document.querySelector("#comparisonBox"),
  mixChatbotResult: document.querySelector("#mixChatbotResult"),
  mixAgentResult: document.querySelector("#mixAgentResult"),
  mixChatbotScore: document.querySelector("#mixChatbotScore"),
  mixAgentScore: document.querySelector("#mixAgentScore"),
  chatMessages: document.querySelector("#chatMessages"),
  doctorMessage: document.querySelector("#doctorMessage"),
  sendDoctorMessageBtn: document.querySelector("#sendDoctorMessageBtn"),
  finalDraft: document.querySelector("#finalDraft"),
  saveFinalBtn: document.querySelector("#saveFinalBtn"),
};

const modeConfig = {
  chatbot: {
    label: "Chatbot",
    kicker: "Chatbot baseline",
    title: "Chuyển raw note thành bản nháp SOAP",
    actionLabel: "Chạy Chatbot",
  },
  agent: {
    label: "Agent",
    kicker: "ReAct agent",
    title: "Agent kiểm tra dữ kiện, safety và tạo bản nháp",
    actionLabel: "Chạy Agent",
  },
  mix: {
    label: "Mix",
    kicker: "Mixed comparison",
    title: "So sánh Chatbot và Agent trên cùng raw note",
    actionLabel: "Chạy Mix",
  },
};

let activeMode = "chatbot";
let sessions = [];
let currentSession = null;
let latestFinalDraft = null;
const SIDEBAR_KEY = "day03.sidebar.collapsed";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function showError(error) {
  els.errorBox.hidden = false;
  els.errorBox.textContent = error.message || String(error);
}

function clearError() {
  els.errorBox.hidden = true;
  els.errorBox.textContent = "";
}

function setBusy(isBusy, label = "Đang chạy...") {
  els.runModeBtn.disabled = isBusy;
  els.sendDoctorMessageBtn.disabled = isBusy;
  els.saveFinalBtn.disabled = isBusy;
  els.runModeBtn.classList.toggle("is-loading", isBusy);
  els.runModeBtn.textContent = isBusy ? label : modeConfig[activeMode].actionLabel;
  els.modeStatusBadge.textContent = isBusy ? "Running" : "Ready";
  els.modeStatusBadge.className = isBusy ? "badge badge--warn" : "badge";
}

function selectMode(mode) {
  activeMode = mode;
  const config = modeConfig[mode];
  els.modeButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.mode === mode));
  els.modeKicker.textContent = config.kicker;
  els.modeTitle.textContent = config.title;
  els.runModeBtn.textContent = config.actionLabel;
  els.chatbotView.hidden = mode !== "chatbot";
  els.agentView.hidden = mode !== "agent";
  els.mixView.hidden = mode !== "mix";
  clearError();
}

function resetOutputs() {
  els.chatbotScore.textContent = "Score: -";
  els.agentScore.textContent = "Steps: -";
  els.mixChatbotScore.textContent = "Score: -";
  els.mixAgentScore.textContent = "Score: -";
  els.winnerBadge.textContent = "Winner: -";
  els.winnerBadge.className = "badge";
  els.chatbotMeta.innerHTML = "";
  els.agentMeta.innerHTML = "";
  els.chatbotResult.className = "result-box empty";
  els.chatbotResult.textContent = "Chưa chạy chatbot.";
  els.agentResult.className = "result-box empty";
  els.agentResult.textContent = "Chưa chạy agent.";
  els.mixChatbotResult.className = "result-box compact empty";
  els.mixChatbotResult.textContent = "Chưa có output.";
  els.mixAgentResult.className = "result-box compact empty";
  els.mixAgentResult.textContent = "Chưa có output.";
  els.comparisonBox.className = "comparison-box empty";
  els.comparisonBox.textContent = "Chưa có kết quả compare.";
}

function renderClinicalResult(container, payload, compact = false) {
  const result = payload.result || payload;
  const warnings = Array.isArray(result.warnings) ? result.warnings : [];
  container.className = compact ? "result-box compact" : "result-box";
  container.innerHTML = `
    <div class="soap-grid">
      ${soapItem("S", result.soap?.subjective)}
      ${soapItem("O", result.soap?.objective)}
      ${soapItem("A", result.soap?.assessment)}
      ${soapItem("P", result.soap?.plan)}
    </div>
    <div class="result-item">
      <strong>Câu hỏi còn thiếu</strong>
      <p>${escapeHtml((result.missing_questions || []).join("; ") || "Không có.")}</p>
    </div>
    <div class="result-item">
      <strong>Final answer</strong>
      <p>${escapeHtml(result.final_answer || "Không có.")}</p>
    </div>
    ${warnings.map(renderWarning).join("") || '<div class="warning-item"><strong>Warnings</strong><p>Không có.</p></div>'}
  `;
}

function renderResultMeta(container, payload, label) {
  const result = payload.result || payload;
  const traceCount = Array.isArray(payload.trace) ? payload.trace.length : 0;
  const escalationClass = result.human_escalation_required ? "meta-pill meta-pill--bad" : "meta-pill meta-pill--ok";
  container.innerHTML = `
    <span class="meta-pill">${escapeHtml(label)}</span>
    <span class="meta-pill meta-pill--ok">Doctor review: ${result.doctor_review_required ? "yes" : "no"}</span>
    <span class="${escalationClass}">Escalation: ${result.human_escalation_required ? "yes" : "no"}</span>
    ${traceCount ? `<span class="meta-pill">Steps: ${traceCount}</span>` : ""}
  `;
}

function soapItem(label, value) {
  return `
    <div class="soap-item">
      <strong>${escapeHtml(label)}</strong>
      <p>${escapeHtml(value || "Không có dữ kiện.")}</p>
    </div>
  `;
}

function renderWarning(warning) {
  const critical = warning.severity === "safety-critical" ? " warning-item--critical" : "";
  const major = warning.severity === "major" ? " warning-item--major" : "";
  return `
    <div class="warning-item${critical}${major}">
      <strong>${escapeHtml(warning.severity || "warning")} · ${escapeHtml(warning.type || "uncertain")}</strong>
      <p>${escapeHtml(warning.message || "")}</p>
    </div>
  `;
}

function renderComparison(payload) {
  els.winnerBadge.textContent = `Winner: ${payload.actual_winner}`;
  els.winnerBadge.className = payload.actual_matches_expected ? "badge badge--ok" : "badge badge--warn";
  els.mixChatbotScore.textContent = `Score: ${payload.chatbot.score.total}`;
  els.mixAgentScore.textContent = `Score: ${payload.agent.score.total}`;
  els.comparisonBox.className = "comparison-box";
  els.comparisonBox.innerHTML = `
    ${metric("Expected", payload.expected_winner)}
    ${metric("Actual", payload.actual_winner)}
    ${metric("Match", payload.actual_matches_expected ? "yes" : "no")}
    ${metric("Chatbot", payload.chatbot.score.total)}
    ${metric("Agent", payload.agent.score.total)}
    ${metric("Agent steps", (payload.agent.trace || []).length)}
  `;
  renderClinicalResult(els.mixChatbotResult, payload.chatbot, true);
  renderClinicalResult(els.mixAgentResult, payload.agent, true);
}

function metric(label, value) {
  return `
    <div class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

async function refreshSessions() {
  const payload = await api("/api/day03/sessions");
  sessions = payload.sessions || [];
  renderSessions();
}

function renderSessions() {
  if (!sessions.length) {
    els.sessionList.innerHTML = '<div class="history-empty">Chưa có phiên nào trong database.</div>';
    return;
  }
  els.sessionList.innerHTML = sessions
    .map((session) => {
      const isActive = currentSession?.id === session.id ? " is-active" : "";
      const date = new Date(session.updated_at);
      return `
        <button class="history-item${isActive}" type="button" data-session-id="${escapeHtml(session.id)}">
          <strong>${escapeHtml(session.title)}</strong>
          <span>${escapeHtml(session.last_mode || session.status || "draft")}</span>
          <time>${escapeHtml(date.toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }))}</time>
        </button>
      `;
    })
    .join("");
}

async function createBlankSession() {
  clearError();
  resetOutputs();
  latestFinalDraft = null;
  renderFinalDraft(null);
  const payload = await api("/api/day03/sessions", {
    method: "POST",
    body: JSON.stringify({ title: "Phiên làm việc mới" }),
  });
  setSession(payload.session);
  await refreshSessions();
}

function setSession(session) {
  currentSession = session;
  latestFinalDraft = null;
  els.sessionTitle.value = session?.title || "";
  els.rawNote.value = session?.raw_note || "";
  renderChatMessages(session?.messages || []);
  renderLatestRun(session);
  renderFinalNotes(session);
  renderSessions();
}

async function loadSession(sessionId) {
  clearError();
  const payload = await api(`/api/day03/sessions/${sessionId}`);
  setSession(payload.session);
}

function renderLatestRun(session) {
  resetOutputs();
  const run = session?.runs?.[0];
  if (!run) return;
  selectMode(run.mode);
  const payload = run.result;
  if (run.mode === "chatbot") {
    renderClinicalResult(els.chatbotResult, payload);
    renderResultMeta(els.chatbotMeta, payload, "1 LLM call");
    els.chatbotScore.textContent = `Score: ${payload.score?.total ?? run.score?.total ?? "-"}`;
  } else if (run.mode === "agent") {
    renderClinicalResult(els.agentResult, payload);
    renderResultMeta(els.agentMeta, payload, "ReAct loop");
    els.agentScore.textContent = `Steps: ${(payload.trace || run.trace || []).length}`;
  } else if (run.mode === "mix") {
    renderComparison(payload);
  }
}

function renderChatMessages(messages) {
  if (!messages.length) {
    els.chatMessages.innerHTML = '<div class="history-empty">Chưa có trao đổi. Sau khi chạy chatbot/agent, bác sĩ có thể hỏi hoặc yêu cầu chỉnh bản nháp ở đây.</div>';
    return;
  }
  els.chatMessages.innerHTML = messages
    .map((message) => `
      <div class="chat-bubble chat-bubble--${escapeHtml(message.role)}">
        <strong>${escapeHtml(roleLabel(message.role))}</strong>
        <p>${escapeHtml(displayMessageContent(message))}</p>
      </div>
    `)
    .join("");
  els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
}

function roleLabel(role) {
  if (role === "doctor") return "Bác sĩ/chuyên gia";
  if (role === "assistant") return "Agent";
  if (role === "user") return "Raw note";
  return role || "System";
}

function displayMessageContent(message) {
  const content = String(message.content || "").trim();
  if (message.role !== "assistant" || !content.startsWith("{")) return content;
  try {
    const parsed = normalizeFinalDraft(JSON.parse(content));
    const questions = parsed.questions_for_doctor || [];
    const warnings = parsed.safety_warnings || parsed.warnings || [];
    const parts = ["Mình đã cập nhật bản nháp SOAP ở khung bên phải."];
    if (questions.length) parts.push(`Còn ${questions.length} điểm cần bác sĩ xác nhận.`);
    if (warnings.length) parts.push(`Có ${warnings.length} cảnh báo/điểm cần kiểm tra.`);
    parts.push("Bản này vẫn cần bác sĩ/chuyên gia duyệt trước khi dùng.");
    return parts.join(" ");
  } catch {
    return content;
  }
}

function renderFinalNotes(session) {
  const latest = session?.final_notes?.[0];
  if (latest) {
    latestFinalDraft = latest.content;
    renderFinalDraft(latest.content, true);
  } else if (!latestFinalDraft) {
    renderFinalDraft(null);
  }
}

function renderFinalDraft(draft, approved = false) {
  if (!draft) {
    els.finalDraft.className = "final-draft empty";
    els.finalDraft.textContent = "Chưa có bản nháp cuối. Hãy chat với agent sau khi chạy chatbot/agent.";
    return;
  }

  const normalized = normalizeFinalDraft(draft);
  latestFinalDraft = normalized;
  const note = normalized.final_note_draft || {};
  const questions = normalized.questions_for_doctor || [];
  const warnings = normalized.safety_warnings || normalized.warnings || [];
  const cannotDecide = normalized.cannot_decide || [];
  els.finalDraft.className = "final-draft";
  els.finalDraft.innerHTML = `
    <div class="final-status ${approved ? "final-status--approved" : ""}">
      ${escapeHtml(approved ? "Đã lưu bản duyệt" : statusLabel(normalized.status))}
    </div>
    <div class="soap-grid">
      ${soapItem("S", note.subjective)}
      ${soapItem("O", note.objective)}
      ${soapItem("A", note.assessment)}
      ${soapItem("P", note.plan)}
    </div>
    ${finalList("Cần bác sĩ xác nhận", questions)}
    ${finalList("Cảnh báo an toàn", warnings)}
    ${finalList("Agent không tự chốt", cannotDecide)}
  `;
}

function normalizeFinalDraft(draft) {
  const normalized = draft?.content ? { ...draft.content } : { ...(draft || {}) };
  if (!normalized.final_note_draft && normalized.draft) {
    normalized.final_note_draft = normalized.draft;
  }
  if (!normalized.final_note_draft) {
    normalized.final_note_draft = {};
  }
  normalized.questions_for_doctor ||= [];
  normalized.safety_warnings ||= [];
  normalized.cannot_decide ||= [];
  normalized.status ||= "draft_pending_doctor_approval";
  return normalized;
}

function statusLabel(status) {
  if (status === "approved_by_doctor") return "Bác sĩ đã duyệt";
  if (status === "ready_for_doctor_review") return "Sẵn sàng để bác sĩ review";
  return "Bản nháp, chưa duyệt";
}

function finalList(title, items) {
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!list.length) return "";
  return `
    <div class="result-item">
      <strong>${escapeHtml(title)}</strong>
      <ul>
        ${list.map((item) => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`).join("")}
      </ul>
    </div>
  `;
}

async function ensureSession() {
  if (currentSession) return currentSession;
  const payload = await api("/api/day03/sessions", {
    method: "POST",
    body: JSON.stringify({
      title: els.sessionTitle.value || "Phiên làm việc mới",
      raw_note: els.rawNote.value,
    }),
  });
  currentSession = payload.session;
  await refreshSessions();
  return currentSession;
}

async function runCurrentMode() {
  clearError();
  const rawNote = els.rawNote.value.trim();
  if (!rawNote) {
    showError(new Error("Bạn cần nhập raw clinical note trước khi chạy."));
    return;
  }
  setBusy(true);
  try {
    const session = await ensureSession();
    const response = await api(`/api/day03/sessions/${session.id}/run`, {
      method: "POST",
      body: JSON.stringify({
        mode: activeMode,
        raw_note: rawNote,
      }),
    });
    setSession(response.session);
    els.outputDetails.open = true;
    await refreshSessions();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

async function sendDoctorMessage() {
  clearError();
  const message = els.doctorMessage.value.trim();
  if (!message) return;
  setBusy(true, "Đang chat...");
  try {
    const session = await ensureSession();
    const response = await api(`/api/day03/sessions/${session.id}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    latestFinalDraft = normalizeFinalDraft(response.payload.result);
    els.doctorMessage.value = "";
    setSession(response.session);
    renderFinalDraft(latestFinalDraft);
    await refreshSessions();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

async function saveFinalNote() {
  clearError();
  try {
    const session = await ensureSession();
    const content = latestFinalDraft || {};
    if (!Object.keys(content).length) {
      showError(new Error("Chưa có bản nháp cuối để lưu."));
      return;
    }
    const response = await api(`/api/day03/sessions/${session.id}/finalize`, {
      method: "POST",
      body: JSON.stringify({
        content,
        approved_by: "doctor_or_expert",
      }),
    });
    setSession(response.session);
    await refreshSessions();
  } catch (error) {
    showError(error);
  }
}

async function init() {
  selectMode("chatbot");
  resetOutputs();
  setSidebarCollapsed(localStorage.getItem(SIDEBAR_KEY) === "true");

  els.modeButtons.forEach((button) => {
    button.addEventListener("click", () => selectMode(button.dataset.mode));
  });
  els.runModeBtn.addEventListener("click", runCurrentMode);
  els.toggleSidebarBtn.addEventListener("click", () => {
    setSidebarCollapsed(!document.body.classList.contains("sidebar-collapsed"));
  });
  els.newSessionBtn.addEventListener("click", createBlankSession);
  els.rawNote.addEventListener("input", clearError);
  els.sendDoctorMessageBtn.addEventListener("click", sendDoctorMessage);
  els.saveFinalBtn.addEventListener("click", saveFinalNote);
  els.sessionList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-session-id]");
    if (button) loadSession(button.dataset.sessionId).catch(showError);
  });

  try {
    const health = await api("/api/day03/health");
    els.modelBadge.textContent = `Model: ${health.model}`;
    els.keyBadge.textContent = health.has_api_key ? "API key: ready" : "API key: missing";
    els.keyBadge.className = health.has_api_key ? "badge badge--ok" : "badge badge--bad";
  } catch (error) {
    showError(error);
  }

  await refreshSessions();
}

function setSidebarCollapsed(collapsed) {
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  els.toggleSidebarBtn.textContent = collapsed ? "Hiện panel" : "Thu panel";
  localStorage.setItem(SIDEBAR_KEY, String(collapsed));
}

init().catch(showError);
