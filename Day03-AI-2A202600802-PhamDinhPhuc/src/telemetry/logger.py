import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers to prevent duplicate logging
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
            
        if log_dir is None:
            log_dir = str(Path(__file__).resolve().parents[2] / "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File Handler (JSON format)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        
        # Console Handler (Human-readable format)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Custom JSON Formatter for file logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage()
                }
                if hasattr(record, "extra_data"):
                    log_data.update(record.extra_data)
                return json.dumps(log_data, ensure_ascii=False)

        # Simple Formatter for console logging
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler.setFormatter(JSONFormatter())
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_event(self, event_type: str, message: str, extra_data: Dict[str, Any] = None):
        """
        Log structured events with extra data for JSON logging.
        """
        extra = {"extra_data": {**(extra_data or {}), "event_type": event_type}}
        self.logger.info(message, extra=extra)

    def log_llm_metric(self, provider: str, model: str, latency: float, prompt_tokens: int, completion_tokens: int):
        """
        Log specific LLM metrics for evaluation.
        """
        extra_data = {
            "provider": provider,
            "model": model,
            "latency_seconds": latency,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        self.log_event("LLM_METRIC", f"LLM Call - {model} - {latency:.2f}s", extra_data)

# Global logger instance
logger = IndustryLogger()
