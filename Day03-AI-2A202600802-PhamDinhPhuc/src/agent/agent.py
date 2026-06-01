import json
import time
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.clinical_tools import (
    budget_check,
    clinical_stage_router,
    extract_clinical_facts,
    guardrail_review,
    needs_safety_review,
    retrieve_patient_memory,
    safety_review,
)
from src.shared.common import extract_json_object, normalize_output

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Implements core reasoning loop logic, guardrails, and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 4):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self, raw_note: str) -> str:
        """
        Builds the ReAct system prompt with available tools and format instructions.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""Bạn là hybrid ReAct + function-control agent hỗ trợ documentation lâm sàng tiếng Việt.

NHIỆM VỤ
- Nhận raw clinical note tiếng Việt.
- Không trả lời ngay như chatbot.
- Mỗi bước phải chọn action, nhận observation từ tool, rồi mới quyết định tiếp.
- Final output là SOAP draft + warnings + missing questions + doctor review flag.
- Có memory theo session/patient nếu backend cung cấp.
- Có budget/cost guardrail: không gọi tool/LLM quá mức để đoán dữ kiện thiếu.

SAFETY BOUNDARIES
- Không tự chẩn đoán.
- Không tự kê đơn.
- Không thay bác sĩ quyết định.
- Không bịa dữ kiện ngoài raw note hoặc observation từ tool.
- Luôn yêu cầu bác sĩ duyệt trước khi dùng note.
- Với red flag, thuốc nguy cơ cao, input mơ hồ, tool fail, hoặc thiếu dữ kiện safety-critical: ưu tiên human escalation.

STAGED HYBRID POLICY
- Stage 1 memory: gọi `retrieve_patient_memory` nếu có memory_context.
- Stage 2 budget: gọi `budget_check` để biết complexity và cost budget.
- Stage 3 facts: bắt buộc gọi `extract_clinical_facts`.
- Stage 4 routing: gọi `clinical_stage_router` để quyết định safety/long-horizon.
- Stage 5 safety: nếu router hoặc guardrail yêu cầu, gọi `safety_review`.
- Stage 6 final guardrail: trước khi final, output phải qua `guardrail_review`.
- Nếu tool fail hoặc budget hết, không cố đoán. Trả final theo hướng fallback/human escalation.
- Dừng sau tối đa {self.max_steps} iterations.

AVAILABLE TOOLS:
{tool_descriptions}

BẮT BUỘC TRẢ VỀ JSON FORMAT ĐÚNG MẪU:
{{
  "thought": "Giải thích chi tiết vì sao cần gọi tool này hoặc vì sao đã đủ dữ kiện để dừng và final.",
  "action": "retrieve_patient_memory | budget_check | clinical_stage_router | extract_clinical_facts | safety_review | guardrail_review | final",
  "action_args": {{}},
  "stop_condition": "continue | enough_evidence | needs_human_escalation | tool_fail | max_iterations"
}}

Nếu action là `final`, thì `action_args` PHẢI chứa SOAP kết quả hoàn chỉnh dưới dạng:
{{
  "mode": "react_agent",
  "soap": {{
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "..."
  }},
  "warnings": [
    {{
      "severity": "minor | major | safety-critical",
      "type": "missing_question | red_flag | medication_risk | uncertainty | contradiction | unsupported | tool_fail",
      "message": "..."
    }}
  ],
  "missing_questions": ["..."],
  "uncertainty": ["..."],
  "doctor_review_required": true,
  "human_escalation_required": false,
  "final_answer": "Tóm tắt ngắn gọn nhận định cho bác sĩ."
}}
""".strip()

    def run(self, raw_note: str, case_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the ReAct loop step-by-step.
        """
        trace: List[Dict[str, Any]] = []
        system_prompt = self.get_system_prompt(raw_note)
        
        self.history = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": "Start ReAct loop for this clinical note. Return one step JSON only.",
                        "case_meta": case_meta,
                        "raw_note": raw_note,
                    },
                    ensure_ascii=False,
                    indent=2
                )
            }
        ]
        
        memory_context = case_meta.get("memory_context") or {}
        budget_policy = case_meta.get("budget") or {
            "max_iterations": self.max_steps,
            "max_tool_calls": self.max_steps,
            "max_llm_calls": self.max_steps,
        }
        facts = []
        memory: Dict[str, Any] = {}
        budget_state: Dict[str, Any] = {}
        router_state: Dict[str, Any] = {}
        safety_state: Dict[str, Any] = {}
        has_extracted_facts = False
        has_safety_reviewed = False
        has_memory_loaded = False
        has_budget_checked = False
        has_routed = False
        llm_calls = 0
        tool_calls = 0
        
        for step in range(1, self.max_steps + 1):
            thought = ""
            action = ""
            action_args = {}
            stop_condition = "continue"
            
            try:
                # 1. Run LLM Provider
                llm_calls += 1
                logger.log_event("AGENT_THINK", f"Iteration {step} - Generating thought and action...", {"step": step})
                llm_response = self.llm.generate(
                    prompt=json.dumps(
                        {
                            "conversation_history": self.history[1:],
                            "instruction": "Return the next ReAct step as one strict JSON object only.",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    system_prompt=system_prompt
                )
                
                content = llm_response["text"]
                step_data = extract_json_object(content)
                
                thought = step_data.get("thought", "")
                action = step_data.get("action", "").strip()
                action_args = step_data.get("action_args") or {}
                stop_condition = step_data.get("stop_condition", "continue")
                action = self.enforce_next_action(
                    proposed_action=action,
                    memory_context=memory_context,
                    has_memory_loaded=has_memory_loaded,
                    has_budget_checked=has_budget_checked,
                    has_extracted_facts=has_extracted_facts,
                    has_routed=has_routed,
                    has_safety_reviewed=has_safety_reviewed,
                    router_state=router_state,
                    facts=facts,
                    raw_note=raw_note,
                    llm_calls=llm_calls,
                    tool_calls=tool_calls,
                    budget_state=budget_state,
                )
                
            except Exception as exc:
                # Safe fallback on LLM/JSON error
                logger.log_event("AGENT_ERROR", f"Iteration {step} - Parsing failed: {str(exc)}", {"step": step})
                trace_step = {
                    "iteration": step,
                    "thought": "LLM step không trả JSON hợp lệ hoặc API lỗi; agent dừng an toàn.",
                    "action": "final",
                    "action_args": {},
                    "observation": {"error": str(exc)},
                    "stop_condition": "tool_fail"
                }
                trace.append(trace_step)
                return {
                    "result": self.build_fallback_output("LLM/JSON error trong ReAct loop; cần bác sĩ review.", facts),
                    "trace": trace
                }

            trace_step = {
                "iteration": step,
                "thought": thought,
                "action": action,
                "action_args": action_args,
                "observation": None,
                "stop_condition": stop_condition
            }
            
            # Logger event for step thought & action
            logger.log_event(
                "AGENT_ACTION",
                f"Iteration {step} - Thought: '{thought[:100]}...' | Action: '{action}'",
                {"step": step, "action": action, "action_args": action_args, "stop_condition": stop_condition}
            )

            # 2. Tool Execution
            if action == "retrieve_patient_memory":
                tool_calls += 1
                observation = retrieve_patient_memory(memory_context)
                memory = observation
                has_memory_loaded = True
                trace_step["observation"] = observation
                trace_step["stop_condition"] = "continue"
                trace.append(trace_step)
                self.append_observation(step_data, "retrieve_patient_memory", observation)
                continue

            if action == "budget_check":
                tool_calls += 1
                observation = budget_check(raw_note, memory, budget_policy)
                budget_state = observation
                has_budget_checked = True
                trace_step["observation"] = observation
                trace_step["stop_condition"] = "continue"
                trace.append(trace_step)
                self.append_observation(step_data, "budget_check", observation)
                continue

            if action == "clinical_stage_router":
                tool_calls += 1
                observation = clinical_stage_router(raw_note, facts, memory)
                router_state = observation
                has_routed = True
                trace_step["observation"] = observation
                trace_step["stop_condition"] = "continue"
                trace.append(trace_step)
                self.append_observation(step_data, "clinical_stage_router", observation)
                continue

            if action == "extract_clinical_facts":
                tool_calls += 1
                try:
                    observation = extract_clinical_facts(raw_note)
                    facts = observation["facts"]
                    has_extracted_facts = True
                except Exception as exc:
                    observation = {"error": str(exc)}
                    stop_condition = "tool_fail"
                
                trace_step["observation"] = observation
                trace_step["stop_condition"] = stop_condition
                trace.append(trace_step)
                
                self.append_observation(step_data, "extract_clinical_facts", observation)
                continue

            elif action == "safety_review":
                tool_calls += 1
                try:
                    if case_meta.get("simulate_tool_failure"):
                        raise RuntimeError("Simulated safety_review timeout for edge-case testing")
                    observation = safety_review(raw_note, facts)
                    safety_state = observation
                    has_safety_reviewed = True
                    stop_condition = "needs_human_escalation" if observation.get("human_escalation_required") else "continue"
                except Exception as exc:
                    observation = {"error": str(exc)}
                    stop_condition = "tool_fail"
                    trace_step["observation"] = observation
                    trace_step["stop_condition"] = stop_condition
                    trace.append(trace_step)
                    return {
                        "result": self.build_fallback_output(f"safety_review fail hoặc timeout: {str(exc)}; cần human escalation.", facts),
                        "trace": trace
                    }
                
                trace_step["observation"] = observation
                trace_step["stop_condition"] = stop_condition
                trace.append(trace_step)
                
                self.append_observation(step_data, "safety_review", observation)
                continue

            elif action == "guardrail_review":
                tool_calls += 1
                candidate = action_args.get("candidate_output") if isinstance(action_args, dict) else {}
                observation = guardrail_review(raw_note, facts, safety_state, candidate)
                trace_step["observation"] = observation
                trace_step["stop_condition"] = "continue" if not observation.get("final_allowed") else "enough_evidence"
                trace.append(trace_step)
                self.append_observation(step_data, "guardrail_review", observation)
                continue

            elif action == "final":
                # Safety Guardrails checks
                safety_required = needs_safety_review(raw_note, facts)
                stage_gap = self.missing_required_stage(
                    memory_context=memory_context,
                    has_memory_loaded=has_memory_loaded,
                    has_budget_checked=has_budget_checked,
                    has_extracted_facts=has_extracted_facts,
                    has_routed=has_routed,
                    safety_required=safety_required or bool(router_state.get("safety_review_required")),
                    has_safety_reviewed=has_safety_reviewed,
                )
                if stage_gap:
                    reason = stage_gap
                elif not has_extracted_facts or (safety_required and not has_safety_reviewed):
                    reason = (
                        "extract_clinical_facts is required before final"
                        if not has_extracted_facts
                        else "safety_review is required before final for this note"
                    )
                else:
                    reason = ""
                if reason:
                    logger.log_event("GUARDRAIL_BLOCK", f"Iteration {step} - Final blocked: {reason}", {"step": step})
                    
                    trace_step["observation"] = {"final_blocked": reason}
                    trace_step["stop_condition"] = "continue"
                    trace.append(trace_step)
                    
                    self.history.append({"role": "assistant", "content": json.dumps(step_data, ensure_ascii=False)})
                    self.history.append({
                        "role": "user",
                        "content": json.dumps({
                            "controller_guardrail": reason,
                            "instruction": "Do not final yet. Return the required tool action as JSON."
                        }, ensure_ascii=False)
                    })
                    continue
                
                final_output = normalize_output(action_args, "react_agent")
                guardrail = guardrail_review(raw_note, facts, safety_state, final_output)
                if not guardrail.get("final_allowed"):
                    logger.log_event("GUARDRAIL_BLOCK", f"Iteration {step} - Final blocked by guardrail_review.", {"step": step})
                    trace_step["observation"] = guardrail
                    trace_step["stop_condition"] = "needs_human_escalation"
                    trace.append(trace_step)
                    return {
                        "result": self.build_fallback_output(
                            "Guardrail chặn final vì có unsupported claim hoặc vượt ranh giới clinical.",
                            facts,
                        ),
                        "trace": trace,
                        "memory": memory,
                        "budget": budget_state,
                        "stage_router": router_state,
                    }
                trace_step["observation"] = {"final_ready": True, "guardrail_review": guardrail}
                
                if final_output["human_escalation_required"]:
                    trace_step["stop_condition"] = "needs_human_escalation"
                elif trace_step["stop_condition"] not in {"enough_evidence", "needs_human_escalation"}:
                    trace_step["stop_condition"] = "enough_evidence"
                    
                trace.append(trace_step)
                logger.log_event("AGENT_SUCCESS", f"Iteration {step} - ReAct Agent completed successfully.", {"step": step})
                return {
                    "result": final_output,
                    "trace": trace,
                    "memory": memory,
                    "budget": budget_state,
                    "stage_router": router_state,
                }

            # If action is invalid
            observation = {"error": f"Unknown action: {action}"}
            stop_condition = "tool_fail"
            trace_step["observation"] = observation
            trace_step["stop_condition"] = stop_condition
            trace.append(trace_step)
            logger.log_event("AGENT_INVALID", f"Iteration {step} - Chosen action is invalid: {action}", {"step": step})
            return {
                "result": self.build_fallback_output(f"Agent chọn action không hợp lệ: {action}", facts),
                "trace": trace
            }

        # Exceeded iterations
        logger.log_event("AGENT_MAX_STEPS", f"ReAct Agent reached max iterations ({self.max_steps}). Falling back.", {})
        trace.append(
            {
                "iteration": self.max_steps,
                "thought": "Đạt MAX_ITERATIONS trước khi có final answer.",
                "action": "final",
                "action_args": {},
                "observation": {"max_iterations": self.max_steps},
                "stop_condition": "max_iterations"
            }
        )
        return {
            "result": self.build_fallback_output("Agent đạt MAX_ITERATIONS; cần bác sĩ review.", facts),
            "trace": trace,
            "memory": memory,
            "budget": budget_state,
            "stage_router": router_state,
        }

    def build_fallback_output(self, reason: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds a safe, structured fallback JSON when the agent fails.
        """
        return normalize_output(
            {
                "soap": {
                    "subjective": "; ".join(fact["fact"] for fact in facts) if facts else "Không có thông tin.",
                    "objective": "",
                    "assessment": "Chưa đủ cơ sở để hoàn tất nhận định; cần bác sĩ xác nhận.",
                    "plan": "Dừng an toàn, bổ sung dữ kiện thiếu và chuyển bác sĩ review.",
                },
                "warnings": [{"severity": "safety-critical", "type": "tool_fail", "message": reason}],
                "missing_questions": ["Bác sĩ cần bổ sung dữ kiện còn thiếu trước khi hoàn tất hồ sơ."],
                "uncertainty": [reason],
                "doctor_review_required": True,
                "human_escalation_required": True,
                "final_answer": f"Fallback an toàn: {reason}",
            },
            "react_agent"
        )

    def append_observation(self, step_data: dict[str, Any], tool_name: str, observation: dict[str, Any]) -> None:
        self.history.append({"role": "assistant", "content": json.dumps(step_data, ensure_ascii=False)})
        self.history.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "observation_from_tool": tool_name,
                        "observation": observation,
                        "instruction": "Continue staged ReAct. Return next step JSON only.",
                    },
                    ensure_ascii=False,
                ),
            }
        )

    def enforce_next_action(
        self,
        proposed_action: str,
        memory_context: dict[str, Any],
        has_memory_loaded: bool,
        has_budget_checked: bool,
        has_extracted_facts: bool,
        has_routed: bool,
        has_safety_reviewed: bool,
        router_state: dict[str, Any],
        facts: list[dict[str, Any]],
        raw_note: str,
        llm_calls: int,
        tool_calls: int,
        budget_state: dict[str, Any],
    ) -> str:
        max_llm_calls = int(budget_state.get("max_llm_calls", self.max_steps))
        max_tool_calls = int(budget_state.get("max_tool_calls", self.max_steps))
        if llm_calls > max_llm_calls or tool_calls >= max_tool_calls:
            return "final"
        if memory_context and not has_memory_loaded:
            return "retrieve_patient_memory"
        if not has_budget_checked:
            return "budget_check"
        if not has_extracted_facts:
            return "extract_clinical_facts"
        if not has_routed:
            return "clinical_stage_router"
        safety_required = bool(router_state.get("safety_review_required")) or needs_safety_review(raw_note, facts)
        if safety_required and not has_safety_reviewed:
            return "safety_review"
        return proposed_action

    def missing_required_stage(
        self,
        memory_context: dict[str, Any],
        has_memory_loaded: bool,
        has_budget_checked: bool,
        has_extracted_facts: bool,
        has_routed: bool,
        safety_required: bool,
        has_safety_reviewed: bool,
    ) -> str:
        if memory_context and not has_memory_loaded:
            return "retrieve_patient_memory stage is required before final"
        if not has_budget_checked:
            return "budget_check stage is required before final"
        if not has_extracted_facts:
            return "extract_clinical_facts stage is required before final"
        if not has_routed:
            return "clinical_stage_router stage is required before final"
        if safety_required and not has_safety_reviewed:
            return "safety_review stage is required before final"
        return ""
