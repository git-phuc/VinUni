# Lab 12 — Complete Production Agent

Kết hợp TẤT CẢ những gì đã học trong 1 project hoàn chỉnh.

## Checklist Deliverable

- [x] Dockerfile (multi-stage, < 500 MB)
- [x] docker-compose.yml (nginx + agent + redis)
- [x] .dockerignore
- [x] Health check endpoint (`GET /health`)
- [x] Readiness endpoint (`GET /ready`)
- [x] API Key authentication
- [x] Rate limiting
- [x] Cost guard
- [x] Config từ environment variables
- [x] Structured logging
- [x] Graceful shutdown
- [x] Public URL ready (Railway / Render config)

---

## Cấu Trúc

```
06-lab-complete/
├── app/
│   ├── main.py         # Entry point — kết hợp tất cả
│   ├── config.py       # 12-factor config
│   ├── auth.py         # API Key + JWT
│   ├── rate_limiter.py # Rate limiting
│   └── cost_guard.py   # Budget protection
├── Dockerfile          # Multi-stage, production-ready
├── docker-compose.yml  # Full stack
├── railway.toml        # Deploy Railway
├── render.yaml         # Deploy Render
├── .env.example        # Template
├── .dockerignore
└── requirements.txt
```

---

## Chạy Local

```bash
# 1. Chạy với Docker Compose
docker compose up --build

# 2. Test qua Nginx
curl http://localhost:8080/health
curl http://localhost:8080/ready

# 3. Test endpoint có authentication
API_KEY=dev-key-change-me-in-production
curl -H "X-API-Key: $API_KEY" \
     -X POST http://localhost:8080/ask \
     -H "Content-Type: application/json" \
     -d '{"user_id": "student-001", "question": "What is deployment?"}'

# 4. Xem conversation history trong Redis
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8080/history/student-001
```

Scale local:

```bash
docker compose up --build --scale agent=3
```

---

## Deploy Railway (< 5 phút)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login và deploy
railway login
railway init
railway variables set OPENAI_API_KEY=sk-...
railway variables set AGENT_API_KEY=your-secret-key
railway up

# Nhận public URL!
railway domain
```

---

## Deploy Render

1. Push repo lên GitHub
2. Render Dashboard → New → Blueprint
3. Connect repo → Render đọc `render.yaml`
4. Set secrets: `OPENAI_API_KEY`, `AGENT_API_KEY`
5. Deploy → Nhận URL!

---

## Kiểm Tra Production Readiness

```bash
python check_production_ready.py
```

Script này kiểm tra tất cả items trong checklist và báo cáo những gì còn thiếu.

## Lưu Ý Deployment

`DEPLOYMENT.md` ở thư mục Day12 root đã có lệnh test local và hướng dẫn điền public URL sau khi deploy bằng Railway hoặc Render.
