# Lab 21 trên Modal (A100 80GB) — Hướng dẫn chạy

Chạy **detached**: submit job xong là **tắt máy local được**, training tiếp tục trên cloud.
Log + adapter + CSV + report lưu trong Modal **Volume**, lấy về bất cứ lúc nào.

Mục tiêu nhắm **Option B** (max điểm: 100 + 5 HF Hub + 10 stretch = 115).

---

## 1. Cài Modal client (chỉ 1 lần, trên máy bạn)

```powershell
pip install -r modal_app/requirements-local.txt
```

## 2. Đăng nhập Modal (chỉ 1 lần — mở browser)

```powershell
modal token new
```
> Auth của Modal lưu ở `~/.modal.toml`, **không** nằm trong `.env`.

## 3. Paste API key vào `.env`

Mở [modal_app/.env](.env) và điền:

| Key | Lấy ở đâu | Bắt buộc? |
|-----|-----------|-----------|
| `HF_TOKEN` | https://huggingface.co/settings/tokens (quyền **Write**) | ✅ cho Option B + GGUF push |
| `HF_USERNAME` | username HF của bạn (để trống = tự lấy từ token) | tuỳ chọn |
| `WANDB_API_KEY` | https://wandb.ai/authorize | tuỳ chọn (stretch W&B) |

> `.env` đã được gitignore — paste key thoải mái, không lo lộ lên git.
> Modal đọc `.env` và nạp vào container qua `Secret.from_dotenv()`.

## 4. Chạy (detached — tắt máy được)

```powershell
modal run --detach modal_app/lab21_modal.py
```

In ra một **App ID / URL dashboard**. Ghi lại rồi cứ tắt máy. Job chạy ~30–50 phút.

> Bỏ `--detach` nếu muốn xem log trực tiếp ở terminal (phải giữ máy mở).

## 5. Theo dõi / lấy log (sau khi bật máy lại)

```powershell
modal app list                          # xem app đang chạy / đã xong
modal app logs lab21-lora-finetuning    # xem toàn bộ log (server lưu sẵn)
```
Hoặc xem trực quan ở dashboard: https://modal.com/apps

## 6. Tải kết quả về máy

```powershell
modal volume get lab21-outputs /lab21 ./lab21_output
```

Sau lệnh này, thư mục `lab21_output/lab21/` có:

```
adapters/
  r8/  r16/  r64/  r16-all/  r16-dora/     ← 5 LoRA adapters
results/
  rank_experiment_summary.csv             ← bảng 3 ranks + base (4 perplexity)
  stretch_comparison.csv                  ← all-layers / DoRA vs baseline
  qualitative_comparison.csv              ← 20 prompts base vs fine-tuned
  loss_curve.png
  all_experiments.csv
  metrics.json
gguf/r16-q4_k_m/                          ← GGUF merge (stretch)
REPORT_DRAFT.md                           ← report điền sẵn số thật → review & cá nhân hoá
LINKS.md                                  ← link HF Hub adapter + GGUF
logs/run.log
```

---

## Pipeline làm gì (khớp rubric Lab 21)

| Rubric | Trong script |
|--------|--------------|
| Dataset Alpaca + token p95 + 90/10 split | `Bước 1` |
| Baseline r=16 (q,v) | `EXPERIMENTS[0]` |
| **Rank experiment** r=8 / r=64 (q,v) | core 25-pt |
| Perplexity 4 số (r8/r16/r64 + base) | `rank_experiment_summary.csv` |
| ≥5 (ở đây 20) qualitative prompts | `qualitative_comparison.csv` |
| **Option B** push adapter HF Hub (+5) | tự bật khi có `HF_TOKEN` |
| Stretch: ALL layers (+bonus) | `r16-all` |
| Stretch: DoRA (+bonus) | `r16-dora` |
| Stretch: W&B (+bonus) | tự bật khi có `WANDB_API_KEY` |
| Stretch: GGUF merge (+bonus) | `gguf/` + push HF |

## Tinh chỉnh nhanh (không cần sửa code)

Bỏ comment dòng tương ứng trong `.env`, ví dụ:
- Đổi dataset / domain: `DATASET_NAME=...`
- Nhiều samples hơn: `N_SAMPLES=1000`
- Tắt GGUF (nhanh hơn): `DO_GGUF=0`

## Lưu ý chi phí

A100 80GB ~ **$1.5–4/giờ** tuỳ region. Cả run ~30–50 phút ⇒ ước tính **$1–3**.
Đổi `GPU_COST_USD_PER_HOUR` trong `.env` cho khớp giá thực tế để report tính đúng.

## Troubleshoot

- **`Secret.from_dotenv` lỗi / không thấy .env**: chạy `modal run` từ thư mục gốc Day 21
  (script tự tìm `.env` cạnh `lab21_modal.py`).
- **Push HF 401**: token chưa có quyền **Write** → tạo lại token Write.
- **GGUF build lỗi**: không sao — core (40 pt) + rank experiment vẫn hoàn tất; chỉ mất bonus GGUF.
- **Re-run nhanh**: model 7B cache ở Volume `lab21-hf-cache`, lần 2 không tải lại.
