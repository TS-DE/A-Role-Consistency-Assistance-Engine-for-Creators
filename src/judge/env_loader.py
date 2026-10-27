"""读 .env。已存在的环境变量优先，便于临时覆盖。"""

from __future__ import annotations

import os
from pathlib import Path

from src.judge.constants import PROJECT_ROOT


class EnvLoader:
    """把 .env 里的键值灌进 os.environ，不覆盖已有值。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (PROJECT_ROOT / ".env")

    def load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    @staticmethod
    def get(*names: str, default: str | None = None) -> str | None:
        """按顺序取第一个非空环境变量，用于 JUDGE_* 优先、LLM_* 兜底的场景。"""
        for name in names:
            value = os.getenv(name)
            if value:
                return value
        return default
