# =============================================================================
# Lab 22 — DPO/ORPO Alignment · MODAL EDITION (A100 80GB)
# AICB-P2T3 · Ngày 22 · Track 3 — From SFT to Preference Learning
# -----------------------------------------------------------------------------
# Chạy detached trên Modal: tắt máy local vẫn chạy tiếp; executed notebooks +
# adapters + screenshots + report lưu vào Modal Volume để lấy về sau.
#
#   modal run --detach modal_app/lab22_modal.py
#
# Khác Day 21: thay vì port logic, file này EXECUTE thẳng 6 notebook gốc qua
# jupytext + nbconvert. Output là executed .ipynb (giữ output cells, đúng yêu cầu
# nộp) + toàn bộ artifact mà scripts/verify.py cần.
#
# Pipeline (tier BIGGPU = Qwen2.5-7B, full bonus):
#   NB1 sft-mini → NB2 pref-data → NB3 DPO → NB4 compare/eval   (CORE, 100pt)
#   NB5 GGUF deploy (+6) · NB6 benchmark (+8) · β-sweep (+6) · HF push (+5/+3)
#
# Secrets: paste vào modal_app/.env  (OPENAI_API_KEY, HF_TOKEN, [WANDB_API_KEY])
# Tinh chỉnh scope/tier qua .env (COMPUTE_TIER, DO_DEPLOY, DO_BENCH, ...).
# =============================================================================
import os

import modal

# --- nơi chứa .env + source repo (parent của modal_app/) ---------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_NB_DIR = os.path.join(_REPO, "notebooks")
_SCRIPTS_DIR = os.path.join(_REPO, "scripts")
_REQ = os.path.join(_REPO, "requirements.txt")

# -----------------------------------------------------------------------------
# Image: CUDA devel base (cần nvcc/cmake cho GGUF build) + lab stack từ
# requirements.txt (cùng pins lab đã test) + jupyter execute tooling.
# -----------------------------------------------------------------------------
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11"
    )
    .apt_install(
        "git", "build-essential", "cmake", "curl", "wget",
        "libcurl4-openssl-dev",
    )
    # ĐẶT TRƯỚC pip: Modal standalone Python khai CC=clang (không cài) ⇒
    # llama-cpp-python build fail. Ép gcc/g++ (có sẵn từ build-essential).
    # Gộp luôn runtime env (HF cache, tier...).
    .env({
        "CC": "gcc",
        "CXX": "g++",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_HOME": "/cache/huggingface",
        "COMPUTE_TIER": "BIGGPU",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_DATASETS_TRUST_REMOTE_CODE": "1",
    })
    # unsloth trước để nó kéo torch/transformers/bnb/xformers tương thích
    .pip_install("unsloth", "unsloth_zoo")
    # phần còn lại đúng pins lab (trl, peft, bnb, datasets, llama-cpp-python,
    # lm-eval[ifeval,math], jupytext, openai, anthropic, ...)
    .pip_install_from_requirements(_REQ)
    # extra cho Modal: execute notebooks + HF fast download + W&B
    .pip_install(
        "nbconvert>=7", "ipykernel", "jupyter-client",
        "hf_transfer", "wandb", "sentencepiece", "protobuf",
    )
    # Gỡ xformers: bản trong image không có backward kernel cho GQA (BMGHK) của
    # Qwen2.5 ⇒ DPO crash. Không có xformers, Unsloth tự fallback sang SDPA (hỗ
    # trợ GQA backward). Layer nhỏ, các layer pip nặng vẫn cache.
    .run_commands("pip uninstall -y xformers || true")
    # bake source notebooks + scripts (read-only mount); copy ra Volume lúc chạy
    .add_local_dir(_NB_DIR, remote_path="/repo_src/notebooks")
    .add_local_dir(_SCRIPTS_DIR, remote_path="/repo_src/scripts")
)

app = modal.App("lab22-dpo-alignment")

# Volume 1: output artifacts (executed notebooks, adapters, data, gguf, report)
OUT_VOL = modal.Volume.from_name("lab22-outputs", create_if_missing=True)
# Volume 2: HF cache — re-run không phải tải lại base model 7B
CACHE_VOL = modal.Volume.from_name("lab22-hf-cache", create_if_missing=True)

# Thư mục làm việc (= REPO_ROOT trong notebook) nằm TRÊN Volume để mọi artifact
# persist. nbconvert chạy với cwd=WORK/notebooks ⇒ notebook tự suy REPO_ROOT=WORK.
WORK = "/outputs/lab22"

try:
    DOTENV_SECRET = modal.Secret.from_dotenv(_HERE)
except Exception:
    DOTENV_SECRET = modal.Secret.from_dict({})


# =============================================================================
# MAIN — chạy toàn bộ lab trên 1 A100 80GB
# =============================================================================
@app.function(
    image=image,
    gpu="L4",  # 24GB — đủ cho DPO 7B (batch=1); né gate "payment method" của A100
    volumes={"/outputs": OUT_VOL, "/cache": CACHE_VOL},
    secrets=[DOTENV_SECRET],
    timeout=60 * 60 * 6,  # 6h
)
def run_lab():
    import json
    import shutil
    import subprocess
    import sys
    import time
    from pathlib import Path

    # ---- config (đọc .env, có default) --------------------------------------
    def _env(key, default):
        v = (os.environ.get(key) or "").strip()
        return v if v else default

    def _flag(key, default="1"):
        return _env(key, default) not in ("0", "false", "False", "no", "")

    def _secret(key):
        v = (os.environ.get(key) or "").strip()
        low = v.lower()
        if not v or low in {"paste_here", "your_token_here", "changeme"} or v.startswith(("hf_xxx", "sk-...")):
            return ""
        return v

    COMPUTE_TIER = _env("COMPUTE_TIER", "BIGGPU").upper()
    DO_DEPLOY = _flag("DO_DEPLOY")          # NB5 GGUF (+6)
    DO_BENCH = _flag("DO_BENCH")            # NB6 benchmark (+8)
    DO_BETA_SWEEP = _flag("DO_BETA_SWEEP")  # β-sweep (+6)
    DO_HF_PUSH = _flag("DO_HF_PUSH")        # push adapter + gguf lên HF (+5/+3)
    GPU_COST = float(_env("GPU_COST_USD_PER_HOUR", "2.50"))

    OPENAI_API_KEY = _secret("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = _secret("ANTHROPIC_API_KEY")
    HF_TOKEN = _secret("HF_TOKEN")
    HF_USERNAME = _secret("HF_USERNAME")
    HF_REPO = _secret("HF_REPO")
    WANDB_API_KEY = _secret("WANDB_API_KEY")

    # propagate vào env cho notebook con
    os.environ["COMPUTE_TIER"] = COMPUTE_TIER
    if OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        os.environ.setdefault("JUDGE_MODEL", "gpt-4o-mini")
    if ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    if WANDB_API_KEY:
        os.environ["WANDB_API_KEY"] = WANDB_API_KEY

    # ---- WORK dir trên Volume -----------------------------------------------
    work = Path(WORK)
    work.mkdir(parents=True, exist_ok=True)
    (work / "notebooks").mkdir(exist_ok=True)
    # copy source mỗi lần (idempotent) — đảm bảo notebook .py mới nhất
    for sub in ("notebooks", "scripts"):
        src = Path("/repo_src") / sub
        dst = work / sub
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
    for d in ("data/pref", "data/eval", "adapters", "gguf",
              "submission/screenshots", "results", "logs"):
        (work / d).mkdir(parents=True, exist_ok=True)

    LOG_PATH = work / "logs" / "run.log"
    _log_lines = []

    def log(msg=""):
        line = str(msg)
        print(line, flush=True)
        _log_lines.append(line)
        try:
            LOG_PATH.write_text("\n".join(_log_lines), encoding="utf-8")
            OUT_VOL.commit()
        except Exception:
            pass

    log("=" * 72)
    log("LAB 22 — DPO/ORPO Alignment · Modal A100 80GB")
    log("=" * 72)

    import torch
    assert torch.cuda.is_available(), "❌ Không thấy GPU"
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"✓ GPU: {gpu_name}  |  VRAM: {vram:.1f} GB  |  CUDA: {torch.version.cuda}")
    log(f"✓ Tier: {COMPUTE_TIER}")
    log(f"✓ Scope: deploy={DO_DEPLOY} bench={DO_BENCH} beta_sweep={DO_BETA_SWEEP} hf_push={DO_HF_PUSH}")
    log(f"✓ Judge: {'OpenAI '+os.environ.get('JUDGE_MODEL','') if OPENAI_API_KEY else ('Anthropic' if ANTHROPIC_API_KEY else 'MANUAL (no key)')}")
    log(f"✓ HF push: {'yes' if (DO_HF_PUSH and HF_TOKEN) else 'no'}  |  W&B: {'yes' if WANDB_API_KEY else 'no'}")

    # register kernel cho nbconvert
    subprocess.run(
        [sys.executable, "-m", "ipykernel", "install", "--sys-prefix",
         "--name", "python3", "--display-name", "python3"],
        check=False, capture_output=True,
    )

    timings = {}

    # ---- helper: jupytext convert .py → .ipynb ------------------------------
    def to_ipynb(stem):
        py = work / "notebooks" / f"{stem}.py"
        subprocess.run(
            ["jupytext", "--to", "notebook", "--update", str(py)],
            check=True, cwd=str(work),
        )

    # ---- helper: execute 1 notebook -----------------------------------------
    def run_nb(stem, allow_errors=False, fatal=True):
        to_ipynb(stem)
        nb = f"notebooks/{stem}.ipynb"
        cmd = [
            "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
            "--ExecutePreprocessor.timeout=-1",
            "--ExecutePreprocessor.kernel_name=python3",
        ]
        if allow_errors:
            cmd.append("--allow-errors")
        cmd.append(nb)
        log(f"\n── RUN {stem} ──────────────────────────────────────────")
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
        wall = time.time() - t0
        timings[stem] = round(wall / 60, 2)
        tail = (proc.stdout or "")[-1500:] + (proc.stderr or "")[-1500:]
        log(tail)
        OUT_VOL.commit()
        if proc.returncode != 0:
            log(f"⚠ {stem} exit code {proc.returncode} ({wall/60:.1f} min)")
            if fatal:
                raise RuntimeError(f"{stem} failed — xem log ở trên")
        else:
            log(f"✓ {stem} done in {wall/60:.1f} min")
        return proc.returncode

    # =========================================================================
    # CORE — NB1 → NB4 (fail-fast, vì phụ thuộc nhau)
    # Skip NB1/NB2 nếu output đã có trên Volume (iterate nhanh khi fix NB3+).
    # =========================================================================
    if (work / "adapters" / "sft-mini" / "adapter_config.json").exists():
        log("⏭  skip NB1 — adapters/sft-mini đã có trên Volume")
    else:
        run_nb("01_sft_mini")

    if (work / "data" / "pref" / "train.parquet").exists():
        log("⏭  skip NB2 — data/pref/train.parquet đã có trên Volume")
    else:
        run_nb("02_preference_data")

    run_nb("03_dpo_train")
    run_nb("04_compare_and_eval")

    # =========================================================================
    # BONUS — NB5 GGUF / NB6 benchmark (best-effort, allow-errors)
    # =========================================================================
    if DO_DEPLOY:
        try:
            run_nb("05_merge_deploy_gguf", allow_errors=True, fatal=False)
        except Exception as e:
            log(f"⚠ NB5 fail (không sao, core vẫn đủ): {e}")

    if DO_BENCH:
        try:
            run_nb("06_benchmark", allow_errors=True, fatal=False)
        except Exception as e:
            log(f"⚠ NB6 fail (không sao, core vẫn đủ): {e}")

    # =========================================================================
    # BONUS — β-sweep (scripts/train_dpo.py ×3 + eval_judge.py plot)
    # =========================================================================
    if DO_BETA_SWEEP:
        log("\n── β-sweep {0.05, 0.1, 0.5} ────────────────────────────────")
        sft = str(work / "adapters" / "sft-mini")
        pref = str(work / "data" / "pref" / "train.parquet")
        for beta, name in [("0.05", "dpo-b0.05"), ("0.1", "dpo-b0.10"), ("0.5", "dpo-b0.50")]:
            try:
                t0 = time.time()
                subprocess.run(
                    [sys.executable, "scripts/train_dpo.py",
                     "--beta", beta, "--sft-path", sft, "--pref-path", pref,
                     "--output-dir", str(work / "adapters" / name)],
                    check=True, cwd=str(work),
                )
                timings[f"beta-{beta}"] = round((time.time() - t0) / 60, 2)
                OUT_VOL.commit()
                log(f"✓ β={beta} done")
            except Exception as e:
                log(f"⚠ β={beta} fail: {e}")
        try:
            subprocess.run(
                [sys.executable, "scripts/eval_judge.py",
                 "--sweep-dir", str(work / "adapters"),
                 "--output", str(work / "submission" / "screenshots" / "bonus-beta-sweep.png")],
                check=True, cwd=str(work),
            )
            OUT_VOL.commit()
            log("✓ β-sweep plot saved")
        except Exception as e:
            log(f"⚠ β-sweep plot fail: {e}")

    # =========================================================================
    # BONUS — push adapter + GGUF lên HuggingFace Hub
    # =========================================================================
    links = {}
    if DO_HF_PUSH and HF_TOKEN:
        log("\n── HuggingFace push ────────────────────────────────────────")
        try:
            from huggingface_hub import HfApi, whoami
            api = HfApi(token=HF_TOKEN)
            if not HF_USERNAME:
                HF_USERNAME = whoami(token=HF_TOKEN).get("name", "")
            repo_id = HF_REPO or f"{HF_USERNAME}/lab22-dpo-vn"

            # model card
            dpo_metrics = {}
            mpath = work / "adapters" / "dpo" / "dpo_metrics.json"
            if mpath.exists():
                dpo_metrics = json.loads(mpath.read_text())
            card = f"""---
base_model: {dpo_metrics.get('base_model', 'unsloth/Qwen2.5-7B-bnb-4bit')}
library_name: peft
tags: [dpo, alignment, vietnamese, lora, trl]
---

# lab22-dpo-vn — DPO-aligned LoRA adapter

DPO adapter (Track 3 · Day 22) trained on top of an SFT-mini checkpoint.

- **Base model:** {dpo_metrics.get('base_model', '')}
- **Method:** Direct Preference Optimization (TRL DPOTrainer)
- **Preference data:** argilla/ultrafeedback-binarized-preferences-cleaned
- **Hyperparameters:** beta={dpo_metrics.get('beta')}, lr={dpo_metrics.get('lr')}, epochs={dpo_metrics.get('epochs')}
- **End reward gap (chosen − rejected):** {dpo_metrics.get('end_reward_gap')}
- **Final DPO loss:** {dpo_metrics.get('final_train_loss')}

Trained on Modal A100 80GB. Stack: Unsloth + TRL + PEFT + bitsandbytes.
"""
            (work / "adapters" / "dpo" / "README.md").write_text(card, encoding="utf-8")
            api.create_repo(repo_id, exist_ok=True, repo_type="model")
            api.upload_folder(folder_path=str(work / "adapters" / "dpo"), repo_id=repo_id, repo_type="model")
            links["adapter"] = f"https://huggingface.co/{repo_id}"
            log(f"✓ adapter pushed → {links['adapter']}")
        except Exception as e:
            log(f"⚠ push adapter fail: {e}")

        # GGUF release (+3) nếu NB5 đã tạo file
        gguf_files = list((work / "gguf").glob("*.gguf"))
        if gguf_files:
            try:
                grepo = f"{HF_USERNAME}/lab22-dpo-vn-gguf"
                api.create_repo(grepo, exist_ok=True, repo_type="model")
                api.upload_folder(
                    folder_path=str(work / "gguf"), repo_id=grepo, repo_type="model",
                    allow_patterns=["*.gguf", "*.md"],
                )
                links["gguf"] = f"https://huggingface.co/{grepo}"
                log(f"✓ GGUF pushed → {links['gguf']}")
            except Exception as e:
                log(f"⚠ push GGUF fail: {e}")

    # =========================================================================
    # SUMMARY — consolidate numbers cho REFLECTION
    # =========================================================================
    log("\n── Summary ─────────────────────────────────────────────────")

    def _read_json(p):
        p = work / p
        return json.loads(p.read_text()) if p.exists() else None

    summary = {
        "compute_tier": COMPUTE_TIER,
        "gpu": gpu_name,
        "vram_gb": round(vram, 1),
        "timings_min": timings,
        "total_train_min": round(sum(timings.values()), 1),
        "est_cost_usd": round(sum(timings.values()) / 60 * GPU_COST, 2),
        "dpo_metrics": _read_json("adapters/dpo/dpo_metrics.json"),
        "benchmark": _read_json("data/eval/benchmark_results.json"),
        "deploy": _read_json("data/eval/deploy_meta.json"),
        "links": links,
    }

    # win/loss/tie từ NB4 judge (A=SFT-only, B=SFT+DPO)
    judge = _read_json("data/eval/judge_results.json")
    if judge:
        from collections import Counter
        c = Counter(r.get("winner") for r in judge)
        summary["judge_winloss"] = {
            "sft_only_A": c.get("A", 0), "sft_dpo_B": c.get("B", 0), "tie": c.get("tie", 0),
            "total": len(judge),
        }

    # β-sweep gaps
    sweep = []
    for d in sorted((work / "adapters").glob("dpo-b*")):
        mp = d / "dpo_metrics.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            sweep.append({"beta": m.get("beta"), "reward_gap": m.get("end_reward_gap"),
                          "chosen": m.get("end_chosen_reward"), "rejected": m.get("end_rejected_reward")})
    if sweep:
        summary["beta_sweep"] = sweep

    (work / "results" / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(work / "results" / "LINKS.md", "w", encoding="utf-8") as f:
        f.write("# Lab 22 — Links & headline numbers\n\n")
        if summary.get("dpo_metrics"):
            dm = summary["dpo_metrics"]
            f.write(f"- **Reward gap (chosen−rejected):** {dm.get('end_reward_gap')}\n")
            f.write(f"- **chosen / rejected reward:** {dm.get('end_chosen_reward')} / {dm.get('end_rejected_reward')}\n")
            f.write(f"- **DPO final loss:** {dm.get('final_train_loss')}\n")
        if summary.get("judge_winloss"):
            j = summary["judge_winloss"]
            f.write(f"- **NB4 judge (8 prompts):** SFT+DPO wins {j['sft_dpo_B']}, SFT-only {j['sft_only_A']}, tie {j['tie']}\n")
        for k, v in links.items():
            f.write(f"- **HF {k}:** {v}\n")
        f.write(f"- **Total train:** {summary['total_train_min']} min  ·  est. ${summary['est_cost_usd']}\n")

    OUT_VOL.commit()
    log("\n" + "=" * 72)
    log("✅ DONE. Artifacts trong Volume 'lab22-outputs' tại /lab22/")
    log("   notebooks/*.ipynb (executed) · adapters/ · data/ · gguf/ · submission/screenshots/")
    log("   results/run_summary.json · results/LINKS.md · logs/run.log")
    log("   Lấy về:  modal volume get lab22-outputs /lab22 ./lab22_output")
    log("=" * 72)
    return summary


# =============================================================================
# Local entrypoint — `modal run --detach modal_app/lab22_modal.py`
# =============================================================================
@app.local_entrypoint()
def main():
    # FIRE-AND-FORGET: .spawn() submit job rồi CLI thoát NGAY (không block).
    # Phải kèm `modal run --detach` để app ephemeral không teardown khi CLI thoát.
    # KHÔNG dùng .remote(): nó block CLI; CLI bị kill → function bị cancel.
    print(">> Lab 22 — spawning run_lab trên Modal A100 80GB (fire-and-forget)...")
    fc = run_lab.spawn()
    print(f">> ✓ Spawned OK. FunctionCall ID: {fc.object_id}")
    print(">> Job chạy ĐỘC LẬP trên cloud — TẮT MÁY THOẢI MÁI, không bị hủy.")
    print(">> Theo dõi:  modal app logs lab22-dpo-alignment   ·  https://modal.com/apps")
    print(">> Lấy kết quả khi xong:  modal volume get lab22-outputs /lab22 ./lab22_output")
