import os
import json
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseWorker(ABC):
    """
    Standard abstraction for "Local Lambda" workers.
    Each worker is responsible for a single task (e.g., rendering one chapter).
    It handles its own checkpointing, logging, and error recovery.
    """

    def __init__(self, name: str, cache_dir: str):
        self.name = name
        self.cache_dir = cache_dir
        self.log_path = os.path.join(cache_dir, f"{name}_worker.log")
        os.makedirs(cache_dir, exist_ok=True)

    def log(self, message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] [{self.name}] {message}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(msg)
        print(msg.strip())

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public entry point. Handles boilerplate error catching.
        """
        self.log("Worker started.")
        start_time = time.time()
        
        try:
            result = self.execute(payload)
            elapsed = time.time() - start_time
            self.log(f"Worker completed successfully in {elapsed:.2f}s.")
            return {
                "status": "success",
                "result": result,
                "elapsed": elapsed
            }
        except Exception as e:
            err_msg = str(e)
            stack = traceback.format_exc()
            self.log(f"CRITICAL ERROR: {err_msg}\n{stack}")
            return {
                "status": "failed",
                "error": err_msg,
                "stack": stack
            }

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Any:
        """
        Subclasses must implement the actual unit of work here.
        """
        pass

    def save_checkpoint(self, data: Dict[str, Any], filename: str):
        path = os.path.join(self.cache_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.log(f"Checkpoint saved: {filename}")

    def load_checkpoint(self, filename: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.cache_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
