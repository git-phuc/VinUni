# Họ Tên: Phạm Đình Phúc - 2A202600802
# Day 10 Reliability Report

## 1. Architecture summary

The gateway sits in front of two `FakeLLMProvider` instances ("primary", "backup"), each
wrapped in its own `CircuitBreaker`. Every request first checks the response cache
(semantic n-gram similarity match); on a miss it walks the provider chain in order,
calling each provider through its breaker. The first provider to succeed answers the
request and its response is cached. If every provider's breaker is open or every call
raises `ProviderError`, the gateway returns a static degraded message instead of
propagating an exception.

```
User Request
    |
    v
[Gateway.complete(prompt)]
    |
    v
[Cache.get(prompt)] ---> HIT (score >= 0.92, not a false-hit, not privacy-sensitive)
    |                        |
    | MISS                   v
    v                    return cached text, route="cache_hit:<score>"
[Circuit Breaker: primary] --(OPEN? skip, try next)--> Provider "primary".complete()
    |  success -> cache.set(), route="primary"
    |  ProviderError/CircuitOpenError -> record error, continue
    v
[Circuit Breaker: backup] --(OPEN? skip, try next)--> Provider "backup".complete()
    |  success -> cache.set(), route="fallback"
    |  ProviderError/CircuitOpenError -> record error, continue
    v
[Static fallback message], route="static_fallback", error=<last provider error>
```

The `ResponseCache` (in-memory) can be swapped for `SharedRedisCache` via config
(`cache.backend: redis`) with no changes to `ReliabilityGateway` — both expose the
same `get(query) -> (value, score)` / `set(query, value, metadata)` contract.

## 2. Configuration

| Setting | Value | Reason |
|---|---:|---|
| failure_threshold | 3 | 3 consecutive failures is enough signal to distinguish a real outage from one-off jitter, without being so low that a single flaky response trips the breaker |
| reset_timeout_seconds | 2 | Short enough that chaos scenarios (a few hundred ms per request) can observe multiple OPEN→HALF_OPEN cycles within one 200-request scenario, giving measurable recovery-time data |
| success_threshold | 1 | A single successful probe in HALF_OPEN is enough to trust the provider again; requiring more would keep HALF_OPEN traffic degraded longer for no measured benefit in these scenarios |
| cache TTL | 300s | Long enough to capture repeat/similar FAQ-style queries within one load-test run (200 requests execute in a few seconds), short enough that stale answers would still be considered "fresh" for a real support session |
| similarity_threshold | 0.92 | Tested 0.85 first and got false hits between queries differing only in a 4-digit year/date (caught by `_looks_like_false_hit`); 0.92 keeps near-duplicate phrasing hits while forcing near-exact wording for a match |
| load_test requests | 200 per scenario (800 total across 4 scenarios) | Large enough sample that P95/P99 latency and per-scenario pass/fail criteria are stable across repeated runs, without making the chaos run slow to iterate on |

## 3. SLO definitions

SLO targets are evaluated against the **aggregate** `metrics.json`, which blends four
scenarios — two of which (`primary_timeout_100`, `both_providers_degraded`) deliberately
inject near-total provider failure. That intentionally drags blended availability and
fallback-success-rate below what a real steady-state deployment would show; see
`reports/metrics.json` for the raw numbers and Section 7 for the per-scenario pass/fail
view, which is the correct lens for chaos testing.

| SLI | SLO target | Actual value | Met? |
|---|---|---:|---|
| Availability | >= 99% | 80.0% | No (dragged down by 2 of 4 adversarial scenarios; `all_healthy` alone measures ~100% in isolation) |
| Latency P95 | < 2500 ms | 317.43 ms | Yes |
| Fallback success rate | >= 95% | 40.96% | No (denominator includes `both_providers_degraded`, where fallback is expected to be unavailable by design) |
| Cache hit rate | >= 10% | 55.5% | Yes |
| Recovery time | < 5000 ms | 2282.21 ms | Yes |

## 4. Metrics

Paste from `reports/metrics.json` (memory cache, all 4 scenarios, 800 total requests;
also exported to `reports/metrics.csv`):

| Metric | Value |
|---|---:|
| availability | 0.8 |
| error_rate | 0.2 |
| latency_p50_ms | 272.56 |
| latency_p95_ms | 317.43 |
| latency_p99_ms | 318.49 |
| fallback_success_rate | 0.4096 |
| cache_hit_rate | 0.555 |
| estimated_cost_saved | 0.444 |
| circuit_open_count | 17 |
| recovery_time_ms | 2282.21 |

Note: these blended numbers vary somewhat run-to-run because the chaos scenarios use
randomized failures/latencies (`FakeLLMProvider`); per-scenario pass/fail (Section 7)
is stable across runs even though the exact aggregate percentages are not — see
`reports/test_output.log` and re-run `python scripts/run_chaos.py` to reproduce.

## 5. Cache comparison

Ran the identical 4-scenario load test twice via `configs/default.yaml`
(`cache.enabled: true`) and `configs/no_cache.yaml` (`cache.enabled: false`),
800 requests each:

| Metric | Without cache | With cache | Delta |
|---|---:|---:|---|
| latency_p50_ms | 265.32 | 272.56 | +7.24 ms (not meaningful — see note below) |
| latency_p95_ms | 312.62 | 317.43 | +4.81 ms (not meaningful — see note below) |
| estimated_cost | 0.263612 | 0.088154 | -0.175458 (-66.6%) |
| cache_hit_rate | 0 | 0.555 | +0.555 |

Note on latency: `run_scenario()` only appends a request's latency to the percentile
sample when `latency_ms > 0`, and cache hits are recorded with `latency_ms=0` (see
`gateway.py`'s cache-hit branch). So P50/P95 here are computed **only over the
provider calls that still happened** — cache hits are excluded from the sample rather
than pulling the percentiles down. That's why enabling the cache doesn't reduce the
reported P50/P95 in this run; the latency benefit of a cache hit (~0ms vs ~200-260ms)
is real per-request but isn't visible in these two aggregate percentile numbers. The
cache's benefit shows up in **cost** (-66.6%) and in **availability/circuit stability**
instead: availability was materially better with cache enabled (0.8 vs 0.7238) and
`circuit_open_count` was much lower (17 vs 41) — cache hits never touch a provider or
its breaker, so fewer live requests means fewer chances to accumulate failures and trip
a breaker.

## 6. Redis shared cache

- Why in-memory cache is insufficient for multi-instance deployments: `ResponseCache`
  stores entries in a plain Python list on the gateway process's heap. If the gateway
  is horizontally scaled (multiple pods/processes behind a load balancer), each
  instance has its own empty cache — a query cached by instance A produces no hit on
  instance B, so effective cache hit rate collapses as instance count grows, and cost
  savings are lost.
- How `SharedRedisCache` solves this: cache entries are stored as Redis hashes
  (`{prefix}{query_hash}` -> `{query, response}`) with `EXPIRE` for TTL. Any gateway
  instance pointed at the same Redis URL reads and writes the same keyspace, so a
  cache write from one instance is immediately visible to all others.

### Evidence of shared state

Ran a script instantiating two independent `SharedRedisCache` objects against the same
Redis URL, writing through one and reading through the other:

```
Instance A sets a response...
Instance B (separate object, same Redis) looks it up...
  instance_b.get(...) -> value='Refunds are processed within 5 business days.', score=1.0

SHARED STATE CONFIRMED: instance B read a value written by instance A.
```

This is also covered by `tests/test_redis_cache.py::test_shared_state_across_instances`,
which passes (see `reports/test_output.log`).

### Redis CLI output

```bash
$ docker compose exec redis redis-cli KEYS "rl:cache:*"
rl:cache:3dab98c0e49e
rl:cache:3936614ac4c2
rl:cache:d354658dc020
rl:cache:9e413fd814eb
rl:cache:734852f3cf4a
rl:cache:0bc3b1acf73d
rl:cache:da61fb49b4f6
rl:cache:095946136fea
rl:cache:fff10da1c72c
rl:cache:dacb2b833659
rl:cache:844ef0143a5c
rl:cache:4fc3c69b9376
rl:cache:98332d0d1c9c
```
(Captured after running the 800-request chaos load test against `configs/redis_cache.yaml`.)

### In-memory vs Redis latency comparison (optional)

| Metric | In-memory cache | Redis cache | Notes |
|---|---:|---:|---|
| latency_p50_ms | 272.56 | 271.12 | Both computed only over non-cache-hit (provider) calls — see the latency note in Section 5; not a clean measurement of Redis round-trip cost |
| latency_p95_ms | 317.43 | 315.04 | Effectively identical at P95 — dominated by cache-miss provider latency in both cases |

Redis-backed run also had the highest cache_hit_rate (72.5% vs 55.5% in-memory) and
lowest cost (0.0747 vs 0.0882) in this sample — plausible since Redis persisted entries
across the whole 800-request run with no per-process fragmentation, but this single
run isn't enough to attribute the difference purely to the backend versus random query
ordering (each run picks random queries from the same 20-query pool).

## 7. Chaos scenarios

| Scenario | Expected behavior | Observed behavior | Pass/Fail |
|---|---|---|---|
| primary_timeout_100 | All traffic fallback to backup, circuit opens | Primary breaker opened; ~94-98% of requests succeeded via backup (`route=fallback`), remainder hit backup's own baseline 5% failures during its brief OPEN windows | Pass |
| primary_flaky_50 | Circuit oscillates, mix of primary and fallback | Primary breaker opened and closed multiple times across the run (contributes to the 17 total circuit_open events in `reports/metrics.json`); requests routed to both `primary` and `fallback` depending on breaker state at call time | Pass |
| all_healthy | All requests via primary, no circuit opens | 0 circuit-open events, all requests routed `primary`, ~100% availability in isolation | Pass |
| both_providers_degraded (custom) | Primary and backup both fail 60% of calls — expect both breakers to trip and most/all traffic to land on the static fallback message rather than erroring | Both breakers opened; in an isolated run 100/100 requests received the static degraded message (0 successful provider responses) — the gateway degraded gracefully instead of raising | Pass |

Pass/fail criteria are scenario-specific (see `_scenario_passed` in `chaos.py`): each
scenario is judged against the failure mode it's designed to exercise (e.g.
`all_healthy` fails if the circuit ever opens; `both_providers_degraded` fails only if
some request gets neither a real response nor a static fallback, i.e. an unhandled
error escapes the gateway).

## 8. Failure analysis

**What could still go wrong:** the circuit breaker state is per-process and in-memory
(`CircuitBreaker` is a plain dataclass on the gateway instance). In a real multi-instance
deployment behind a load balancer, each instance accumulates its own failure count
independently — instance A might have already opened its primary breaker after 3
failures while instance B, having received a different slice of traffic, is still
sending live requests to a fully down primary. The fleet as a whole reacts to an outage
more slowly and unevenly than the single-process chaos runs in this report suggest,
and the aggregate SLOs in Section 3 would look better in this lab than in production
multi-instance reality.

**Proposed fix:** move circuit breaker counters into Redis (the stretch goal in the
README), using `INCR`/`EXPIRE` for failure counts and a shared key for current state,
so all gateway instances observe the same breaker transitions — mirroring what
`SharedRedisCache` already does for the response cache.

## 9. Next steps

1. Share circuit breaker state via Redis (INCR/EXPIRE counters) so breaker
   transitions are consistent across horizontally-scaled gateway instances.
2. Add cost-aware routing: once cumulative spend crosses a budget threshold, prefer
   cache-only or the cheaper backup provider instead of always trying primary first.
3. Re-run the SLO check per-scenario rather than only on the blended aggregate, so
   dashboards distinguish "system is unhealthy" from "we are intentionally chaos-testing
   a failure mode."
