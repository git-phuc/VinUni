# Findings — Day13-AI-2A202600802-PhamDinhPhuc
**Team:** Day13-AI-2A202600802-PhamDinhPhuc  
**Member:** Pham Dinh Phuc  
**Phase:** Public + Private  
**Public score:** 100.0 / 100 (116/120 correct, error=1.0, diag_f1=0.924)  
**Private score:** 93.07 / 100 (56/80 correct, error=1.0, diag_f1=0.973)

---

## Methodology

All faults were identified by inspecting the shipped `config.json` and `prompt.txt` before running the simulator, then confirmed by comparing expected vs actual behavior. Fixes were applied to `config.json`, `prompt.txt`, and `solution/wrapper.py`.

---

## Fault Table

| fault_class | evidence (metric + observed value) | root cause | fix applied |
|---|---|---|---|
| **error_spike** | `tool_error_rate=0.18` in shipped config; `retry.enabled=false` | Intermittent tool failures had no retry, causing requests to fail permanently | Set `tool_error_rate=0.0`; enabled `retry` with `max_attempts=2`, `backoff_ms=150` in `config.json` |
| **latency_spike** | `max_steps=12`, `loop_guard=false`, `context_size=8`, `verbose_system=true` in shipped config | Agent took excessive steps and sent bloated context on every request, increasing latency | Set `max_steps=8`, `loop_guard=true`, `context_size=3`, `verbose_system=false`; enabled `cache` |
| **cost_blowup** | `model_price_tier=premium`, `max_completion_tokens=2000`, `verbose_system=true` in shipped config | Premium tier + verbose output + large token budget caused excessive cost per request | Switched to `model_price_tier=economy`; reduced `max_completion_tokens=450`; disabled `verbose_system` |
| **quality_drift** | `session_drift_rate=0.06`, `self_consistency=1` in shipped config | Answers degraded over long sessions; no consistency check to stabilize noisy outputs | Set `session_drift_rate=0.0`, `context_reset_every=4`, `self_consistency=2` in `config.json` |
| **infinite_loop** | `loop_guard=false`, `tool_budget=0` in shipped config | Agent had no guard against repeated identical tool calls; could run indefinitely | Set `loop_guard=true`, `tool_budget=4` in `config.json` |
| **tool_failure** | `normalize_unicode=false`, `catalog_override` forced MacBook out-of-stock in shipped config | Vietnamese city names with diacritics failed tool lookup; catalog override silently blocked valid products | Set `normalize_unicode=true`; cleared `catalog_override={}` in `config.json` |
| **pii_leak** | `redact_pii=false`, shipped prompt had no privacy instruction | Agent echoed customer email/phone in answers without any suppression | Set `redact_pii=true` in `config.json`; added PII rule to `prompt.txt`; `_redact_answer()` in `wrapper.py` strips PII from output |
| **fabrication** | Shipped prompt instruction: "always give total in VND" with no refusal condition | Model fabricated confident totals for out-of-stock or unknown products instead of refusing | Rewrote `prompt.txt` rule 3: refuse clearly if product not found or out of stock; never give a total on refusal |
| **arithmetic_error** | `temperature=1.6` in shipped config; shipped prompt had no explicit formula | High temperature caused non-deterministic arithmetic; model estimated instead of computing exactly | Lowered `temperature=0.2`; added exact formula to `prompt.txt`: `subtotal = unit_price × qty; discounted = subtotal × (100 − pct) // 100; total = discounted + shipping` |
| **tool_overuse** | `tool_budget=0`, shipped prompt had no per-tool call limit | Agent called tools multiple times redundantly, wasting tokens and increasing latency | Set `tool_budget=4` in `config.json`; added prompt rule: call each tool exactly once |
| **prompt_injection** | Shipped prompt did not treat order notes as untrusted; no wrapper sanitization | Agent obeyed fake prices/instructions embedded in "GHI CHU" order notes | Added injection defense to `prompt.txt` (rule 2); added `_sanitize_question()` in `wrapper.py` to detect and strip suspicious notes using regex patterns for note keywords and injection triggers |

---

## Key Files Changed

| File | Changes |
|---|---|
| `solution/config.json` | Fixed 9 config faults: temperature, retry, cache, loop_guard, tool_budget, model_price_tier, max_steps, context_size, normalize_unicode, redact_pii, session_drift_rate, self_consistency |
| `solution/prompt.txt` | Rewrote system prompt: tool-first flow, exact arithmetic formula, refusal on out-of-stock, PII suppression, injection defense, one-call-per-tool rule |
| `solution/wrapper.py` | Added: retry/backoff, thread-safe cache, `_sanitize_question()` for injection defense, `_redact_answer()` for PII, structured telemetry logging |
| `solution/examples.json` | Added 3 behavior examples: out-of-stock refusal, correct tool flow, injection resistance |
