# Deployment Information

## Public URL

Cloud public URL is pending an authenticated Railway or Render account deployment.

Local Docker URL verified in this workspace on June 12, 2026:

```text
http://localhost:8080
```

## Platform

- Local verification: Docker Compose
- Cloud-ready configs: Railway (`06-lab-complete/railway.toml`) and Render (`06-lab-complete/render.yaml`)

## Test Commands

### Start Locally

```bash
cd 06-lab-complete
docker compose up --build
```

### Health Check

```bash
curl http://localhost:8080/health
```

Expected:

```json
{"status":"ok","checks":{"redis":"ok"}}
```

### Readiness Check

```bash
curl http://localhost:8080/ready
```

Expected:

```json
{"ready":true,"redis":"ok"}
```

### Authentication Required

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test\",\"question\":\"Hello\"}"
```

Expected: `401 Unauthorized`

### API Test With Authentication

```bash
curl -X POST http://localhost:8080/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test\",\"question\":\"Hello\"}"
```

Expected: `200 OK` with a mock agent response.

Actual verified response included:

```json
{
  "user_id": "docker-test",
  "answer": "Docker packages the app and dependencies into a reproducible container.",
  "history_length": 2
}
```

### Rate Limit Test

```bash
for i in 1 2 3 4 5 6 7 8 9 10 11; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8080/ask \
    -H "X-API-Key: dev-key-change-me-in-production" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"rate-test\",\"question\":\"Test $i\"}"
done
```

Expected: first 10 requests return `200`; the 11th returns `429`.

Actual verified result:

```text
200,200,200,200,200,200,200,200,200,200,429
```

### Conversation History Test

```bash
curl -X GET http://localhost:8080/history/test \
  -H "X-API-Key: dev-key-change-me-in-production"
```

Expected: saved user and assistant messages for `user_id=test`.

Actual verified result: Redis-backed history returned the saved user and assistant messages for `user_id=docker-test`.

## Docker Verification

- `docker build -t day12-agent:local .`: passed
- `docker compose up -d --build`: passed
- `agent`: healthy
- `redis`: healthy
- `nginx`: running at `http://localhost:8080`
- Final compose image size: `06-lab-complete-agent:latest` = 307 MB
- Standalone local image size: `day12-agent:local` = 247 MB

## Environment Variables Set

- `PORT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `LOG_LEVEL`
- `RATE_LIMIT_PER_MINUTE`
- `MONTHLY_BUDGET_USD`
- `MAX_HISTORY_MESSAGES`
- `HISTORY_TTL_SECONDS`

## Screenshots

Screenshots are pending a real cloud deployment:

- Deployment dashboard: `screenshots/dashboard.png`
- Service running: `screenshots/running.png`
- Test results: `screenshots/test.png`

## Cloud Deployment Notes

Current cloud deployment blocker checked on June 12, 2026:

- `railway` CLI is not installed.
- `render` CLI is not installed.
- `gh` GitHub CLI is not installed.
- The repository remote exists: `https://github.com/VinUni-AI20k/day12_ha-tang-cloud_va_deployment`.

Because Railway/Render deployment requires an authenticated account login, the local Docker app is fully verified but the public URL and dashboard screenshots still need the student's cloud login step.

Railway:

```bash
cd 06-lab-complete
npm i -g @railway/cli
railway login
railway init
railway variables set ENVIRONMENT=production
railway variables set AGENT_API_KEY=<secure-key>
railway variables set REDIS_URL=<redis-url>
railway up
railway domain
```

Render:

1. Push this repository to GitHub.
2. Create a new Render Blueprint from `06-lab-complete/render.yaml`.
3. Confirm the generated `AGENT_API_KEY` and Redis service.
4. Deploy and copy the public service URL into this file.
