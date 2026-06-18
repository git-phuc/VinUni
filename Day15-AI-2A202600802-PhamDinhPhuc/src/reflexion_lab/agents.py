from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .mock_runtime import FAILURE_MODE_BY_QID, actor_answer, evaluator, reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        for attempt_id in range(1, self.max_attempts + 1):
            from .mock_runtime import reset_last_run_metadata, get_last_run_metadata
            import time
            
            reset_last_run_metadata()
            start_time = time.time()
            
            answer = actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            judge = evaluator(example, answer)
            
            # Calculate elapsed time for actor + evaluator
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            reflection_entry = None
            if self.agent_type == "reflexion" and judge.score != 1 and attempt_id < self.max_attempts:
                ref_start = time.time()
                reflection_entry = reflector(example, attempt_id, judge)
                ref_elapsed = int((time.time() - ref_start) * 1000)
                elapsed_ms += ref_elapsed
                
                reflections.append(reflection_entry)
                reflection_memory.append(
                    f"Attempt {attempt_id} failed. Reason: {reflection_entry.failure_reason}. "
                    f"Lesson: {reflection_entry.lesson}. "
                    f"Strategy: {reflection_entry.next_strategy}"
                )
            
            meta = get_last_run_metadata()
            if meta.get("tokens", 0) > 0:
                token_estimate = meta["tokens"]
            else:
                token_estimate = 320 + (attempt_id * 65) + (120 if self.agent_type == "reflexion" else 0)
                
            if meta.get("latency_ms", 0) > 0:
                latency_ms = meta["latency_ms"]
            else:
                # If mock mode, elapsed_ms might be extremely low (0ms), so use the mock formula as fallback
                latency_ms = elapsed_ms if elapsed_ms > 2 else (160 + (attempt_id * 40) + (90 if self.agent_type == "reflexion" else 0))
                
            trace = AttemptTrace(
                attempt_id=attempt_id,
                answer=answer,
                score=judge.score,
                reason=judge.reason,
                reflection=reflection_entry,
                token_estimate=token_estimate,
                latency_ms=latency_ms
            )
            
            final_answer = answer
            final_score = judge.score
            traces.append(trace)
            
            if judge.score == 1:
                break
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = "none" if final_score == 1 else FAILURE_MODE_BY_QID.get(example.qid, "wrong_final_answer")
        return RunRecord(qid=example.qid, question=example.question, gold_answer=example.gold_answer, agent_type=self.agent_type, predicted_answer=final_answer, is_correct=bool(final_score), attempts=len(traces), token_estimate=total_tokens, latency_ms=total_latency, failure_mode=failure_mode, reflections=reflections, traces=traces)

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
