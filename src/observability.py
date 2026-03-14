import json
import os
import platform
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any

import psutil

from app_paths import ensure_app_dirs
from version import APP_NAME, __version__


class Observability:
    def __init__(self) -> None:
        self.base_dir, self.logs_dir, self.diag_dir = ensure_app_dirs()

    def _today_log_file(self) -> str:
        day = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.logs_dir, f"gamechanger-{day}.jsonl")

    def write_log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        event = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "message": message,
            "extra": extra or {},
        }
        path = self._today_log_file()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")

    def capture_snapshot(self, label: str) -> dict[str, Any]:
        snap = {
            "label": label,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "cpu_percent": psutil.cpu_percent(interval=0.15),
            "ram_percent": psutil.virtual_memory().percent,
            "process_count": len(psutil.pids()),
        }
        return snap

    def snapshot_delta(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        return {
            "cpu_delta": round(float(after["cpu_percent"]) - float(before["cpu_percent"]), 2),
            "ram_delta": round(float(after["ram_percent"]) - float(before["ram_percent"]), 2),
            "process_delta": int(after["process_count"]) - int(before["process_count"]),
        }

    def export_diagnostics(self, engine: Any, latest_snapshot: dict[str, Any] | None = None) -> str:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_file = os.path.join(self.diag_dir, f"diagnostics-{ts}.json")

        tweak_catalog = [asdict(t) for t in engine.list_tweaks()]
        profile_catalog = [asdict(p) for p in engine.list_profiles()]

        recent_logs: list[dict[str, Any]] = []
        log_file = self._today_log_file()
        if os.path.isfile(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-300:]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    recent_logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "app": {
                "name": APP_NAME,
                "version": __version__,
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                "boot_time_epoch": int(psutil.boot_time()),
            },
            "latest_snapshot": latest_snapshot,
            "tweak_catalog": tweak_catalog,
            "profile_catalog": profile_catalog,
            "state_file": getattr(engine, "state_file", None),
            "recent_logs": recent_logs,
            "uptime_seconds": int(time.time() - psutil.boot_time()),
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return out_file
