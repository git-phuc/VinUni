# =============================================================================
# Lab 21 — LoRA / QLoRA Fine-tuning · MODAL EDITION (A100 80GB)
# AICB-P2T3 · Ngày 21 · Chương 5 — Fine-tuning & An Toàn
# -----------------------------------------------------------------------------
# Chạy detached trên Modal (modal.com): tắt máy local vẫn chạy tiếp, log + adapter
# được lưu vào Modal Volume để lấy về sau.
#
#   modal run --detach modal_app/lab21_modal.py
#
# Toàn bộ pipeline (port từ notebook T4, scale lên A100 80GB + Qwen2.5-7B):
#   1. Dataset prep (Alpaca format, token p95, 90/10 split)
#   2. Base-model perplexity
#   3. Train baseline r=16 (q,v)  → push HF Hub (Option B) + GGUF (stretch)
#   4. Rank experiment: r=8, r=64 (q,v)            ← core 25-pt analysis
#   5. Stretch: r=16 ALL-LAYERS + r=16 DoRA        ← bonus +10
#   6. Eval (perplexity 4 numbers + 20 qualitative prompts)
#   7. Save CSVs + loss curve + REPORT_DRAFT.md vào Volume
#
# API keys: paste vào modal_app/.env  (HF_TOKEN, WANDB_API_KEY) — xem .env.example
# =============================================================================
import os

import modal

# --- nơi chứa .env (cùng folder file này) -----------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# Image: CUDA devel base (cần nvcc/cmake cho GGUF) + Unsloth stack
# Mirror cách cài trong notebook: unsloth trước, rồi pin trl 0.12–0.16 --no-deps
# -----------------------------------------------------------------------------
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11"
    )
    .apt_install(
        "git", "build-essential", "cmake", "curl", "wget",
        "libcurl4-openssl-dev",
    )
    .pip_install("unsloth", "unsloth_zoo")
    # pin TRL trong range lab spec, không đụng deps (giống notebook)
    .pip_install(
        "trl>=0.12,<0.16", "peft", "accelerate", "bitsandbytes",
        extra_options="--no-deps",
    )
    .pip_install(
        "datasets", "matplotlib", "pandas",
        "huggingface_hub", "hf_transfer", "wandb",
        "sentencepiece", "protobuf",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/cache/huggingface"})
)

app = modal.App("lab21-lora-finetuning")

# Volume 1: output artifacts (adapters, CSV, log, report) — lấy về sau khi xong
OUT_VOL = modal.Volume.from_name("lab21-outputs", create_if_missing=True)
# Volume 2: HF cache — re-run không phải download lại model 7B
CACHE_VOL = modal.Volume.from_name("lab21-hf-cache", create_if_missing=True)

OUT_ROOT = "/outputs/lab21"

# Secret nạp từ .env (HF_TOKEN, WANDB_API_KEY, + config overrides nếu muốn)
try:
    DOTENV_SECRET = modal.Secret.from_dotenv(_HERE)
except Exception:
    # .env chưa tồn tại — vẫn cho phép import; sẽ báo lỗi rõ ràng lúc chạy
    DOTENV_SECRET = modal.Secret.from_dict({})


# =============================================================================
# MAIN — chạy toàn bộ lab trên 1 A100 80GB
# =============================================================================
@app.function(
    image=image,
    gpu="A100-80GB",
    volumes={"/outputs": OUT_VOL, "/cache": CACHE_VOL},
    secrets=[DOTENV_SECRET],
    timeout=60 * 60 * 4,  # 4h — thừa cho 5 lần train 7B + GGUF
)
def run_lab():
    import gc
    import inspect
    import json
    import time

    import numpy as np
    import pandas as pd
    import torch

    # ---- config (đọc từ .env, có default) -----------------------------------
    def _env(key, default):
        v = (os.environ.get(key) or "").strip()
        return v if v else default

    MODEL_NAME = _env("MODEL_NAME", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    DATASET_NAME = _env("DATASET_NAME", "5CD-AI/Vietnamese-alpaca-gpt4-gg-translated")
    N_SAMPLES = int(_env("N_SAMPLES", "500"))
    MAX_SEQ_CAP = int(_env("MAX_SEQ_CAP", "2048"))
    NUM_EPOCHS = int(_env("NUM_EPOCHS", "3"))
    EFF_BATCH = int(_env("EFFECTIVE_BATCH", "8"))  # per_device=8, accum=1
    GPU_COST_USD_PER_HOUR = float(_env("GPU_COST_USD_PER_HOUR", "1.50"))  # A100 80GB ~ Modal

    def _secret(key):
        v = (os.environ.get(key) or "").strip()
        low = v.lower()
        if not v or low in {"paste_here", "your_token_here", "changeme"} or v.startswith("hf_xxx"):
            return ""
        return v

    HF_TOKEN = _secret("HF_TOKEN")
    HF_USERNAME = _secret("HF_USERNAME")
    WANDB_API_KEY = _secret("WANDB_API_KEY")
    PUSH_TO_HUB = bool(HF_TOKEN)            # Option B tự bật nếu có token
    USE_WANDB = bool(WANDB_API_KEY)         # stretch W&B tự bật nếu có key
    DO_GGUF = _env("DO_GGUF", "1") == "1"   # stretch GGUF

    # ---- output dirs --------------------------------------------------------
    ADAPTERS_DIR = os.path.join(OUT_ROOT, "adapters")
    RESULTS_DIR = os.path.join(OUT_ROOT, "results")
    GGUF_DIR = os.path.join(OUT_ROOT, "gguf")
    LOG_PATH = os.path.join(OUT_ROOT, "logs", "run.log")
    for d in (ADAPTERS_DIR, RESULTS_DIR, GGUF_DIR, os.path.dirname(LOG_PATH)):
        os.makedirs(d, exist_ok=True)

    _log_lines = []

    def log(msg=""):
        line = str(msg)
        print(line, flush=True)
        _log_lines.append(line)
        # flush log + commit volume định kỳ để tắt máy giữa chừng vẫn có log
        try:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(_log_lines))
            OUT_VOL.commit()
        except Exception:
            pass

    log("=" * 70)
    log("LAB 21 — LoRA/QLoRA Fine-tuning · Modal A100 80GB")
    log("=" * 70)

    # ---- GPU check ----------------------------------------------------------
    assert torch.cuda.is_available(), "❌ Không thấy GPU"
    gpu_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"✓ GPU: {gpu_name}  |  VRAM: {vram_total:.1f} GB  |  CUDA: {torch.version.cuda}")
    log(f"✓ Torch: {torch.__version__}")
    log(f"✓ Model: {MODEL_NAME}")
    log(f"✓ Dataset: {DATASET_NAME} (n={N_SAMPLES})")
    log(f"✓ Push HF Hub (Option B): {PUSH_TO_HUB} | W&B: {USE_WANDB} | GGUF: {DO_GGUF}")

    # ---- HF / W&B auth ------------------------------------------------------
    if HF_TOKEN:
        from huggingface_hub import login as hf_login, whoami
        try:
            hf_login(token=HF_TOKEN, add_to_git_credential=False)
            if not HF_USERNAME:
                HF_USERNAME = whoami(token=HF_TOKEN).get("name", "")
            log(f"✓ HuggingFace logged in as: {HF_USERNAME}")
        except Exception as e:
            log(f"⚠ HF login lỗi: {e} — sẽ skip push.")
            PUSH_TO_HUB = False
    if USE_WANDB:
        os.environ["WANDB_API_KEY"] = WANDB_API_KEY
        os.environ.setdefault("WANDB_PROJECT", "lab21-lora")
        log("✓ W&B enabled (project=lab21-lora)")

    # =========================================================================
    # 1. DATASET PREPARATION
    # =========================================================================
    log("\n── 1. Dataset preparation ──────────────────────────────────────")
    from datasets import load_dataset
    from transformers import AutoTokenizer

    raw = load_dataset(DATASET_NAME, split="train")
    raw = raw.shuffle(seed=42).select(range(min(N_SAMPLES, len(raw))))
    log(f"✓ Loaded {len(raw)} samples | columns: {raw.column_names}")

    cols = raw.column_names
    INSTRUCTION_COL = next((c for c in ["instruction", "instruction_vi", "prompt", "question"] if c in cols), None)
    INPUT_COL = next((c for c in ["input", "input_vi", "context"] if c in cols), None)
    OUTPUT_COL = next((c for c in ["output", "output_vi", "response", "answer"] if c in cols), None)
    assert INSTRUCTION_COL and OUTPUT_COL, f"Không tìm thấy instruction/output trong {cols}"
    log(f"✓ Columns dùng: instruction='{INSTRUCTION_COL}', input='{INPUT_COL}', output='{OUTPUT_COL}'")

    ALPACA = "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n{output}"
    ALPACA_NOINP = "### Instruction:\n{instruction}\n\n### Response:\n{output}"

    def format_alpaca(ex):
        inp = (ex.get(INPUT_COL, "") if INPUT_COL else "") or ""
        if inp.strip():
            text = ALPACA.format(instruction=ex[INSTRUCTION_COL], input=inp, output=ex[OUTPUT_COL])
        else:
            text = ALPACA_NOINP.format(instruction=ex[INSTRUCTION_COL], output=ex[OUTPUT_COL])
        return {"text": text}

    # clean: bỏ output quá ngắn (<10 tokens xấp xỉ qua ký tự), dedup theo text
    ds = raw.map(format_alpaca, remove_columns=raw.column_names)
    seen = set()

    def _keep(ex):
        t = ex["text"]
        if t in seen:
            return False
        seen.add(t)
        resp = t.split("### Response:")[-1].strip()
        return len(resp) >= 20
    ds = ds.filter(_keep)
    log(f"✓ Sau clean/dedup: {len(ds)} samples")

    # token length p95 → max_seq_length (round up power of 2, cap)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    lengths = [len(tok.encode(x["text"])) for x in ds]
    p50, p95, p99 = (int(np.percentile(lengths, q)) for q in (50, 95, 99))
    MAX_SEQ_LENGTH = min(MAX_SEQ_CAP, 1 << (max(p95, 256) - 1).bit_length())
    log(f"✓ Token length: min={min(lengths)} p50={p50} p95={p95} p99={p99} max={max(lengths)}")
    log(f"✓ max_seq_length = {MAX_SEQ_LENGTH} (cap {MAX_SEQ_CAP})")

    split = ds.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]
    log(f"✓ Train: {len(train_ds)} | Eval: {len(eval_ds)}")

    # =========================================================================
    # 2. Helpers — load model / wrap LoRA / build trainer / safe eval
    # =========================================================================
    from unsloth import FastLanguageModel

    def load_base_model():
        m, t = FastLanguageModel.from_pretrained(
            model_name=MODEL_NAME,
            max_seq_length=MAX_SEQ_LENGTH,
            dtype=None,          # bf16 trên A100
            load_in_4bit=True,   # QLoRA
        )
        return m, t

    QV = ["q_proj", "v_proj"]
    ALL_LAYERS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

    def wrap_with_lora(model, r, alpha, target_modules=QV, use_dora=False):
        return FastLanguageModel.get_peft_model(
            model,
            r=r,
            lora_alpha=alpha,
            target_modules=target_modules,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",  # -60% VRAM
            use_dora=use_dora,
            random_state=42,
        )

    # --- TRL/transformers version patch (port từ notebook) -------------------
    from transformers import TrainingArguments, Trainer
    from trl import SFTTrainer
    import trl as _trl
    import transformers as _tf
    log(f"✓ trl {_trl.__version__} | transformers {_tf.__version__}")

    if "tokenizer" not in inspect.signature(Trainer.__init__).parameters:
        _orig_t = Trainer.__init__

        def _t_init(self, *a, **kw):
            if "tokenizer" in kw and "processing_class" not in kw:
                kw["processing_class"] = kw.pop("tokenizer")
            return _orig_t(self, *a, **kw)
        Trainer.__init__ = _t_init

    try:
        from trl import SFTConfig
        _HAS_SFTCONFIG = True
    except ImportError:
        _HAS_SFTCONFIG = False

    _TA_PARAMS = inspect.signature(TrainingArguments.__init__).parameters
    _EVAL_KEY = "eval_strategy" if "eval_strategy" in _TA_PARAMS else "evaluation_strategy"
    _SFT_PARAMS = inspect.signature(SFTTrainer.__init__).parameters
    _SUPPORTS_OLD = "dataset_text_field" in _SFT_PARAMS

    per_device = max(1, EFF_BATCH)  # A100 80GB: effective batch=8 qua 1 device

    def make_trainer(model, tokenizer, out_subdir, run_name, **overrides):
        base = dict(
            output_dir=os.path.join(ADAPTERS_DIR, "_chk", out_subdir),
            per_device_train_batch_size=per_device,
            per_device_eval_batch_size=2,
            gradient_accumulation_steps=1,
            eval_accumulation_steps=4,
            prediction_loss_only=True,
            warmup_ratio=0.10,
            num_train_epochs=NUM_EPOCHS,
            learning_rate=2e-4,
            lr_scheduler_type="cosine",
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=2,
            save_strategy="no",          # adapter save thủ công sau train
            optim="adamw_8bit",          # paged AdamW
            weight_decay=0.01,
            seed=42,
            report_to="wandb" if USE_WANDB else "none",
            run_name=run_name,
        )
        base[_EVAL_KEY] = "epoch"        # A100 đủ VRAM → có eval loss curve
        base.update(overrides)

        if _HAS_SFTCONFIG:
            sft_extra = dict(dataset_text_field="text", packing=False, max_seq_length=MAX_SEQ_LENGTH)
            sp = inspect.signature(SFTConfig.__init__).parameters
            sft_extra = {k: v for k, v in sft_extra.items() if k in sp}
            valid = {k: v for k, v in base.items() if k in sp}
            args = SFTConfig(**valid, **sft_extra)
        else:
            args = TrainingArguments(**base)

        tk = {"model": model, "train_dataset": train_ds, "eval_dataset": eval_ds, "args": args}
        if "processing_class" in _SFT_PARAMS:
            tk["processing_class"] = tokenizer
        else:
            tk["tokenizer"] = tokenizer
        if _SUPPORTS_OLD:
            tk.update(dict(dataset_text_field="text", max_seq_length=MAX_SEQ_LENGTH, packing=False))
        return SFTTrainer(**tk)

    def safe_evaluate(trainer):
        gc.collect(); torch.cuda.empty_cache()
        try:
            from transformers.utils.notebook import NotebookProgressCallback
            trainer.remove_callback(NotebookProgressCallback)
        except Exception:
            pass
        try:
            return trainer.evaluate()["eval_loss"]
        except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
            log(f"⚠ evaluate() fail ({type(e).__name__}) → manual batch=1")
        gc.collect(); torch.cuda.empty_cache()
        m = trainer.model
        m.eval()
        total, n = 0.0, 0
        with torch.no_grad():
            for batch in trainer.get_eval_dataloader():
                batch = {k: v.to(m.device) for k, v in batch.items() if hasattr(v, "to")}
                total += m(**batch).loss.item(); n += 1
                torch.cuda.empty_cache()
        return total / max(n, 1)

    # =========================================================================
    # 2.5 BASE MODEL PERPLEXITY (pristine, no adapter)
    # =========================================================================
    log("\n── 2. Base-model perplexity ────────────────────────────────────")
    base_ppl = float("nan")
    try:
        bm, bt = load_base_model()
        btr = make_trainer(bm, bt, "base", "base", num_train_epochs=0)
        base_loss = safe_evaluate(btr)
        base_ppl = float(np.exp(base_loss))
        log(f"✓ Base eval loss={base_loss:.4f} | perplexity={base_ppl:.3f}")
        del bm, bt, btr
        gc.collect(); torch.cuda.empty_cache()
    except Exception as e:
        log(f"⚠ Base perplexity lỗi: {e}")

    # =========================================================================
    # 3-5. TRAIN EXPERIMENTS
    # =========================================================================
    # core rank experiment = r8/r16/r64 (q,v) | stretch = all-layers + dora
    EXPERIMENTS = [
        dict(tag="r16", r=16, alpha=32, target=QV, dora=False, group="rank", label="r=16 (baseline q,v)"),
        dict(tag="r8", r=8, alpha=16, target=QV, dora=False, group="rank", label="r=8 (q,v)"),
        dict(tag="r64", r=64, alpha=128, target=QV, dora=False, group="rank", label="r=64 (q,v)"),
        dict(tag="r16-all", r=16, alpha=32, target=ALL_LAYERS, dora=False, group="stretch", label="r=16 ALL-layers"),
        dict(tag="r16-dora", r=16, alpha=32, target=QV, dora=True, group="stretch", label="r=16 DoRA (q,v)"),
    ]

    metrics = {}
    loss_histories = {}
    links = {}

    def train_one(cfg):
        tag = cfg["tag"]
        log(f"\n========== Train {cfg['label']}  [{tag}] ==========")
        gc.collect(); torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        m, t = load_base_model()
        m = wrap_with_lora(m, r=cfg["r"], alpha=cfg["alpha"], target_modules=cfg["target"], use_dora=cfg["dora"])
        trainable = sum(p.numel() for p in m.parameters() if p.requires_grad)
        total = sum(p.numel() for p in m.parameters())
        log(f"  trainable={trainable:,} ({100*trainable/total:.3f}%)")

        tr = make_trainer(m, t, tag, f"lab21-{tag}")
        t0 = time.time()
        tr.train()
        wall = time.time() - t0
        vram = torch.cuda.max_memory_allocated() / 1e9

        # save adapter NGAY sau train (trước eval) — eval OOM cũng còn checkpoint
        adir = os.path.join(ADAPTERS_DIR, tag)
        tr.save_model(adir)
        OUT_VOL.commit()
        log(f"  ✓ adapter saved → {adir}  | {wall/60:.1f} min | peak VRAM {vram:.1f} GB")

        try:
            eloss = safe_evaluate(tr)
            ppl = float(np.exp(eloss))
        except Exception as e:
            log(f"  ⚠ eval fail: {e}")
            eloss, ppl = float("nan"), float("nan")
        log(f"  ✓ eval loss={eloss:.4f} | perplexity={ppl:.3f}")

        metrics[tag] = dict(
            tag=tag, label=cfg["label"], group=cfg["group"],
            rank=cfg["r"], alpha=cfg["alpha"],
            target_modules="+".join(cfg["target"]), dora=cfg["dora"],
            trainable_params=int(trainable),
            train_time_min=round(wall / 60, 3),
            peak_vram_gb=round(vram, 3),
            eval_loss=round(eloss, 5) if eloss == eloss else None,
            eval_perplexity=round(ppl, 4) if ppl == ppl else None,
        )
        loss_histories[tag] = tr.state.log_history
        return tr, m, t

    # --- train r16 đầu tiên, giữ model để qualitative + push + GGUF ----------
    cfg_r16 = EXPERIMENTS[0]
    tr16, model16, tok16 = train_one(cfg_r16)

    # ---- 6a. Qualitative: base vs r16 (20 prompts) --------------------------
    log("\n── 5. Qualitative comparison (base vs r=16) ────────────────────")
    TEST_PROMPTS = [
        "Giải thích khái niệm machine learning cho người mới bắt đầu.",
        "Viết đoạn code Python tính số Fibonacci thứ n.",
        "Liệt kê 5 nguyên tắc thiết kế UI/UX.",
        "Tóm tắt sự khác biệt giữa LoRA và QLoRA.",
        "Phân biệt prompt engineering, RAG, và fine-tuning.",
        "Khi nào nên dùng RAG thay vì fine-tuning?",
        "Giải thích cách hoạt động của Flash Attention.",
        "Liệt kê 3 câu hỏi phỏng vấn cho ML Engineer junior.",
        "Cho biết ưu điểm của Transformer so với RNN.",
        "Cách evaluate performance của một LLM fine-tuned model?",
        "Giải thích gradient checkpointing là gì.",
        "Viết một email xin nghỉ phép lịch sự bằng tiếng Việt.",
        "Tóm tắt nguyên lý hoạt động của QLoRA trong 3 câu.",
        "Cho ví dụ về overfitting và cách phòng tránh.",
        "Giải thích sự khác nhau giữa batch size và effective batch size.",
        "Liệt kê các bước chuẩn bị dataset cho fine-tuning.",
        "Khi nào KHÔNG nên fine-tune một LLM?",
        "Giải thích perplexity dùng để đo gì.",
        "Viết hàm Python đảo ngược một chuỗi.",
        "Cho lời khuyên học Deep Learning cho sinh viên năm nhất.",
    ]

    def gen(model, tokenizer, prompt, max_new_tokens=220):
        FastLanguageModel.for_inference(model)
        text = ALPACA_NOINP.format(instruction=prompt, output="")
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens,
            temperature=0.7, top_p=0.9, do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        full = tokenizer.decode(out[0], skip_special_tokens=True)
        return full.split("### Response:")[-1].strip()

    qual = []
    base_for_qual, tok_for_qual = load_base_model()  # base sạch để so sánh
    for i, p in enumerate(TEST_PROMPTS):
        try:
            b = gen(base_for_qual, tok_for_qual, p)
        except Exception as e:
            b = f"[gen error: {e}]"
        try:
            f = gen(model16, tok16, p)
        except Exception as e:
            f = f"[gen error: {e}]"
        qual.append({"prompt": p, "base": b, "finetuned_r16": f})
        log(f"  [{i+1}/{len(TEST_PROMPTS)}] {p[:60]}")
    del base_for_qual, tok_for_qual
    gc.collect(); torch.cuda.empty_cache()

    pd.DataFrame(qual).to_csv(os.path.join(RESULTS_DIR, "qualitative_comparison.csv"), index=False)
    log("  ✓ qualitative_comparison.csv saved")

    # ---- 6b. Option B: push r16 adapter lên HF Hub --------------------------
    if PUSH_TO_HUB and HF_USERNAME:
        repo = f"{HF_USERNAME}/lab21-qwen2.5-7b-vi-r16"
        log(f"\n── Option B: push adapter → https://huggingface.co/{repo}")
        try:
            model16.push_to_hub(repo, token=HF_TOKEN)
            tok16.push_to_hub(repo, token=HF_TOKEN)
            links["adapter_r16"] = f"https://huggingface.co/{repo}"
            log("  ✓ adapter pushed")
        except Exception as e:
            log(f"  ⚠ push adapter fail: {e}")

    # ---- 6c. Stretch GGUF: merge r16 + convert + (optional) push ------------
    if DO_GGUF:
        log("\n── Stretch: GGUF merge (q4_k_m) ────────────────────────────────")
        try:
            gdir = os.path.join(GGUF_DIR, "r16-q4_k_m")
            os.makedirs(gdir, exist_ok=True)
            model16.save_pretrained_gguf(gdir, tok16, quantization_method="q4_k_m")
            OUT_VOL.commit()
            links["gguf_local"] = gdir
            log(f"  ✓ GGUF saved → {gdir}")
            if PUSH_TO_HUB and HF_USERNAME:
                grepo = f"{HF_USERNAME}/lab21-qwen2.5-7b-vi-gguf"
                try:
                    model16.push_to_hub_gguf(grepo, tok16, quantization_method="q4_k_m", token=HF_TOKEN)
                    links["gguf_hub"] = f"https://huggingface.co/{grepo}"
                    log(f"  ✓ GGUF pushed → {grepo}")
                except Exception as e:
                    log(f"  ⚠ push GGUF fail: {e}")
        except Exception as e:
            log(f"  ⚠ GGUF fail (không sao, core vẫn đủ điểm): {e}")

    # free r16
    del tr16, model16, tok16
    gc.collect(); torch.cuda.empty_cache()

    # ---- train phần còn lại (r8, r64, all-layers, dora) ---------------------
    for cfg in EXPERIMENTS[1:]:
        try:
            tr, m, t = train_one(cfg)
            del tr, m, t
            gc.collect(); torch.cuda.empty_cache()
        except Exception as e:
            log(f"⚠ Train {cfg['tag']} fail: {e}")

    # =========================================================================
    # 7. SUMMARY CSV + LOSS CURVE + REPORT DRAFT
    # =========================================================================
    log("\n── 6. Summary + report ─────────────────────────────────────────")

    order = ["r8", "r16", "r64", "r16-all", "r16-dora"]
    rows = [metrics[k] for k in order if k in metrics]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RESULTS_DIR, "all_experiments.csv"), index=False)

    # core rank table (3 ranks + base)
    rank_rows = [metrics[k] for k in ["r8", "r16", "r64"] if k in metrics]
    rank_df = pd.DataFrame(rank_rows)[
        ["rank", "alpha", "trainable_params", "train_time_min", "peak_vram_gb", "eval_loss", "eval_perplexity"]
    ]
    base_row = pd.DataFrame([{
        "rank": "base", "alpha": None, "trainable_params": 0,
        "train_time_min": 0, "peak_vram_gb": 0,
        "eval_loss": round(np.log(base_ppl), 5) if base_ppl == base_ppl else None,
        "eval_perplexity": round(base_ppl, 4) if base_ppl == base_ppl else None,
    }])
    rank_out = pd.concat([rank_df, base_row], ignore_index=True)
    rank_out.to_csv(os.path.join(RESULTS_DIR, "rank_experiment_summary.csv"), index=False)
    log("\n=== Rank Experiment Summary ===")
    log(rank_out.to_string(index=False))

    # stretch table
    stretch_rows = [metrics[k] for k in ["r16", "r16-all", "r16-dora"] if k in metrics]
    pd.DataFrame(stretch_rows).to_csv(os.path.join(RESULTS_DIR, "stretch_comparison.csv"), index=False)

    # loss curve (train + eval) cho 3 ranks
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.figure(figsize=(9, 5))
        colors = {"r8": "#2E8B57", "r16": "#0E2A52", "r64": "#C8102E"}
        for tag in ["r8", "r16", "r64"]:
            if tag not in loss_histories:
                continue
            h = pd.DataFrame(loss_histories[tag])
            if "loss" in h:
                tr_ = h[h["loss"].notna()]
                plt.plot(tr_["step"], tr_["loss"], label=f"{tag} train", color=colors[tag])
            if "eval_loss" in h:
                ev_ = h[h["eval_loss"].notna()]
                if not ev_.empty:
                    plt.plot(ev_["step"], ev_["eval_loss"], "--o", label=f"{tag} eval", color=colors[tag])
        plt.xlabel("Step"); plt.ylabel("Loss"); plt.title("Loss Curve — rank experiment")
        plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
        plt.savefig(os.path.join(RESULTS_DIR, "loss_curve.png"), dpi=120)
        log("  ✓ loss_curve.png saved")
    except Exception as e:
        log(f"  ⚠ loss curve fail: {e}")

    # total cost
    total_min = sum(metrics[k]["train_time_min"] for k in metrics)
    total_cost = (total_min / 60) * GPU_COST_USD_PER_HOUR
    log(f"\n✓ Tổng train time: {total_min:.1f} phút | est. cost ${total_cost:.2f} @ ${GPU_COST_USD_PER_HOUR}/hr")

    # LINKS.md
    with open(os.path.join(OUT_ROOT, "LINKS.md"), "w", encoding="utf-8") as f:
        f.write("# Lab 21 — Links\n\n")
        for k, v in links.items():
            f.write(f"- **{k}**: {v}\n")
        if not links:
            f.write("_(chưa push HF — set HF_TOKEN trong .env để bật Option B)_\n")

    # ---- REPORT_DRAFT.md (điền sẵn numbers, sinh viên review + cá nhân hoá) --
    def g(tag, key):
        return metrics.get(tag, {}).get(key, "—")

    def ppl(tag):
        v = metrics.get(tag, {}).get("eval_perplexity")
        return f"{v}" if v is not None else "—"

    rank_md = "| Rank | Trainable Params | Train Time | Peak VRAM | Eval Loss | Perplexity |\n"
    rank_md += "|------|------------------|------------|-----------|-----------|------------|\n"
    for tag in ["r8", "r16", "r64"]:
        if tag in metrics:
            mm = metrics[tag]
            rank_md += (f"| {mm['rank']} | {mm['trainable_params']:,} | {mm['train_time_min']} min "
                        f"| {mm['peak_vram_gb']} GB | {mm['eval_loss']} | {mm['eval_perplexity']} |\n")
    rank_md += (f"| Base | 0 | – | – | "
                f"{round(np.log(base_ppl),5) if base_ppl==base_ppl else '—'} | "
                f"{round(base_ppl,4) if base_ppl==base_ppl else '—'} |\n")

    stretch_md = "| Config | Trainable Params | Train Time | Peak VRAM | Perplexity |\n"
    stretch_md += "|--------|------------------|------------|-----------|------------|\n"
    for tag in ["r16", "r16-all", "r16-dora"]:
        if tag in metrics:
            mm = metrics[tag]
            stretch_md += (f"| {mm['label']} | {mm['trainable_params']:,} | {mm['train_time_min']} min "
                           f"| {mm['peak_vram_gb']} GB | {mm['eval_perplexity']} |\n")

    qual_md = ""
    for i, q in enumerate(qual[:5]):
        qual_md += (f"\n### Example {i+1}\n**Prompt**: {q['prompt']}\n\n"
                    f"**Base**: {q['base'][:400]}\n\n"
                    f"**Fine-tuned (r=16)**: {q['finetuned_r16'][:400]}\n\n"
                    f"**Nhận xét**: _<điền: improved / same / degraded?>_\n")

    links_md = "\n".join(f"- {k}: {v}" for k, v in links.items()) or "_(N/A)_"

    report = f"""# Lab 21 — Evaluation Report

**Học viên**: Phạm Đình Phúc — 2A202600802
**Ngày nộp**: <YYYY-MM-DD>
**Submission option**: B (GitHub + HuggingFace Hub) ⭐

> 🤖 Đây là DRAFT auto-fill từ run thật trên Modal A100 80GB. Numbers là thật;
> phần nhận xét/kết luận hãy review & cá nhân hoá trước khi nộp.

## 1. Setup
- **Base model**: `{MODEL_NAME}`
- **Dataset**: {DATASET_NAME}, {len(ds)} samples ({len(train_ds)} train + {len(eval_ds)} eval)
- **max_seq_length**: {MAX_SEQ_LENGTH} (p95 = {p95}, rounded up to power of 2)
- **GPU**: {gpu_name}, {vram_total:.0f} GB VRAM (Modal serverless)
- **Hyperparams**: {NUM_EPOCHS} epochs, cosine LR 2e-4, warmup 0.10, effective batch {EFF_BATCH}, optim adamw_8bit
- **Training cost**: ~${total_cost:.2f} (~{total_min:.1f} phút @ ${GPU_COST_USD_PER_HOUR}/hr)
- **HF Hub**: {links.get('adapter_r16', '<chưa push>')}
- **GGUF**: {links.get('gguf_hub', links.get('gguf_local', '<N/A>'))}

## 2. Rank Experiment Results

{rank_md}

## 3. Loss Curve Analysis
![loss curve](results/loss_curve.png)

- Quan sát overfitting: _<train loss giảm đều; eval loss ở epoch cuối có tăng không?>_
- _<điền nhận xét dựa trên loss_curve.png — eval loss đi ngang/tăng = dấu hiệu overfit>_

## 4. Qualitative Comparison (5 examples)
{qual_md}
> Full 20 examples: `results/qualitative_comparison.csv`

## 5. Conclusion về Rank Trade-off

_<≥100 từ. Dựa trên bảng trên, trả lời 3 câu hỏi:>_
- **ROI tốt nhất**: rank nào cho perplexity tốt nhất so với chi phí params/VRAM/time?
- **Diminishing returns**: từ r=16 → r=64 perplexity cải thiện bao nhiêu so với params tăng {round(metrics.get('r64',{}).get('trainable_params',0)/max(metrics.get('r16',{}).get('trainable_params',1),1),1)}×?
- **Production recommendation**: deploy thì chọn rank nào? Tại sao?

## 6. Stretch Goals (bonus)
- **Target ALL layers vs q,v**: {stretch_md}
- **DoRA**: xem bảng trên — có cải thiện perplexity so với LoRA thường không?
- **W&B**: {'có (xem project lab21-lora)' if USE_WANDB else 'không bật'}
- **GGUF**: {links.get('gguf_hub', links.get('gguf_local', 'không tạo'))}

## 7. What I Learned
- _<insight cá nhân 1>_
- _<insight cá nhân 2>_
- _<insight cá nhân 3 (optional)>_

---
### Links
{links_md}
"""
    with open(os.path.join(OUT_ROOT, "REPORT_DRAFT.md"), "w", encoding="utf-8") as f:
        f.write(report)

    # save metrics json + final log
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"base_perplexity": base_ppl, "experiments": metrics,
                   "links": links, "total_train_min": total_min,
                   "est_cost_usd": total_cost}, f, ensure_ascii=False, indent=2)

    OUT_VOL.commit()
    log("\n" + "=" * 70)
    log("✅ DONE. Artifacts trong Volume 'lab21-outputs' tại /lab21/")
    log("   adapters/ (r8,r16,r64,r16-all,r16-dora) · results/ · gguf/ · REPORT_DRAFT.md · LINKS.md · logs/run.log")
    log("   Lấy về:  modal volume get lab21-outputs /lab21 ./lab21_output")
    log("=" * 70)

    return {"base_perplexity": base_ppl, "metrics": metrics, "links": links,
            "total_train_min": total_min, "est_cost_usd": total_cost}


# =============================================================================
# Local entrypoint — `modal run modal_app/lab21_modal.py`
# =============================================================================
@app.local_entrypoint()
def main():
    # FIRE-AND-FORGET: .spawn() gửi job rồi CLI thoát sạch NGAY (không block chờ).
    # Phải chạy kèm `modal run --detach` để app ephemeral không bị teardown khi CLI thoát.
    # KHÔNG dùng .remote(): nó block CLI; nếu CLI bị kill (timeout/tắt máy) → function bị cancel.
    print(">> Lab 21 — spawning run_lab trên Modal A100 80GB (fire-and-forget)...")
    fc = run_lab.spawn()
    print(f">> ✓ Spawned OK. FunctionCall ID: {fc.object_id}")
    print(">> Job chạy ĐỘC LẬP trên cloud — TẮT MÁY THOẢI MÁI, không bị hủy.")
    print(">> Theo dõi:  modal app logs <app-id>  ·  dashboard  ·  W&B project lab21-lora")
    print(">> Lấy kết quả khi xong:  modal volume get lab21-outputs /lab21 ./lab21_output")
