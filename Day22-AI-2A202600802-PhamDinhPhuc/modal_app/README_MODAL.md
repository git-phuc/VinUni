# Lab 22 trên Modal (A100 80GB) — Hướng dẫn chạy

Chạy **detached**: submit job xong là **tắt máy local được**, training tiếp trên cloud.
Khác Day 21: file này **execute thẳng 6 notebook gốc** (jupytext + nbconvert) nên output
gồm **executed `.ipynb` (giữ output cells, đúng yêu cầu nộp)** + toàn bộ artifact + 6 screenshot.

Nhắm **Core (100pt) + full bonus** (NB5 GGUF +6, NB6 benchmark +8, β-sweep +6, HF push +5/+3).

---

## 1. Cài Modal client (1 lần, trên máy bạn)

```powershell
pip install -r modal_app/requirements-local.txt
modal token new      # mở browser (bỏ qua nếu ~/.modal.toml đã có)
```

## 2. Paste API key vào `modal_app/.env`

| Key | Lấy ở đâu | Dùng cho |
|-----|-----------|----------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | judge NB4 + AlpacaEval-lite NB6 |
| `HF_TOKEN` | https://huggingface.co/settings/tokens (**Write**) | push adapter + GGUF (Option B) |

> `.env` đã gitignore — paste thoải mái. Để trống key nào thì phần đó tự skip
> (NB4 rơi về manual rubric, không push HF).

## 3. Chạy (detached — tắt máy được)

```powershell
modal run --detach modal_app/lab22_modal.py
```

In ra **FunctionCall ID**. Ghi lại rồi cứ tắt máy. Job 7B + full bonus chạy lâu.

## 4. Theo dõi

```powershell
modal app logs lab22-dpo-alignment      # log server lưu sẵn
```
Hoặc dashboard: https://modal.com/apps

## 5. Tải kết quả về

```powershell
modal volume get lab22-outputs /lab22 ./lab22_output
```

> Trên Windows, `modal volume get` 1 **folder** đôi khi hỏng → nếu lỗi, lấy từng file:
> `modal volume ls lab22-outputs /lab22` rồi get từng path con (KHÔNG có dấu `/` đầu khi cần).

Sau đó `lab22_output/lab22/` có:

```
notebooks/01..06_*.ipynb          ← executed notebooks (output cells) → copy vào repo notebooks/
adapters/sft-mini/  dpo/          ← NB1 + NB3 adapters (+ dpo_metrics.json)
adapters/dpo-b0.05 / b0.10 / b0.50   ← β-sweep
data/pref/train.parquet  eval.parquet
data/eval/side_by_side.jsonl  judge_results.json  benchmark_results.json  deploy_meta.json
gguf/*.gguf                       ← NB5 GGUF Q4_K_M
submission/screenshots/*.png      ← 02-sft-loss, 03-dpo-reward-curves, 04-side-by-side,
                                     06-gguf-smoke, 07-benchmark, bonus-beta-sweep
results/run_summary.json  LINKS.md   ← số tổng hợp cho REFLECTION
logs/run.log
```

---

## Pipeline làm gì (khớp rubric Lab 22)

| Rubric | Trong run |
|--------|-----------|
| NB1 SFT-mini adapter + loss curve | `run_nb("01_sft_mini")` |
| NB2 preference parquet (prompt/chosen/rejected) | `run_nb("02_preference_data")` |
| NB3 DPO adapter + reward curves (chosen & rejected) | `run_nb("03_dpo_train")` |
| NB4 side-by-side 8 prompt + judge win/loss/tie | `run_nb("04_compare_and_eval")` (OpenAI) |
| NB5 GGUF Q4_K_M + smoke (+6) | `DO_DEPLOY=1` |
| NB6 IFEval/GSM8K/MMLU/AlpacaEval + 4-bar (+8) | `DO_BENCH=1` |
| β-sweep {0.05,0.1,0.5} (+6) | `DO_BETA_SWEEP=1` |
| Push adapter HF (+5) / GGUF release (+3) | `DO_HF_PUSH=1` + `HF_TOKEN` |

## Tinh chỉnh / cắt chi phí (sửa `.env`, không đụng code)

- Bỏ phần lâu nhất: `DO_BENCH=0` (NB6 MMLU 5000×2 trên 7B là long pole).
- Bỏ β-sweep (tiết kiệm ~3 lần train DPO): `DO_BETA_SWEEP=0`.
- Đổi tier nhẹ/rẻ: `COMPUTE_TIER=T4` (Qwen2.5-3B).

## Ước tính thời gian / chi phí (A100 80GB, BIGGPU 7B)

| Phần | ~Thời gian |
|------|-----------|
| Core NB1–NB4 | ~35–50 min |
| NB5 GGUF | ~10–15 min |
| NB6 benchmark (MMLU 5000 ×2) | ~60–120 min |
| β-sweep (3× DPO) | ~60–90 min |
| **Full bonus** | **~3–4.5 h ⇒ ~$8–18** |

Core-only (`DO_BENCH=0 DO_BETA_SWEEP=0`) ≈ 50–70 min ⇒ ~$2–4.

## Troubleshoot

- `Secret.from_dotenv` không thấy `.env`: chạy `modal run` từ thư mục gốc Day 22.
- Push HF 401: token thiếu quyền **Write** → tạo lại token Write.
- GGUF build lỗi: NB5 chạy `--allow-errors`, core vẫn đủ điểm; chỉ mất bonus GGUF.
- Re-run nhanh: base 7B cache ở Volume `lab22-hf-cache`, lần 2 không tải lại.
