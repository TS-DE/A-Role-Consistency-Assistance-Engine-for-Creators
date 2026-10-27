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
        for line in self._read().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    def _read(self) -> str:
        """按 UTF-8 → GBK 依次尝试。

        为什么需要：Windows 上的记事本、PowerShell 的 Set-Content 默认会用本地编码
        把 .env 写成 GBK，而配置文件里通常有中文注释。硬编码 utf-8 会直接崩在
        UnicodeDecodeError，而且崩的位置看起来跟"读配置"毫无关系，排查成本很高。
        """
        for encoding in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return self.path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise SystemExit(f"无法解码配置文件 {self.path}：请另存为 UTF-8")

    @staticmethod
    def get(*names: str, default: str | None = None) -> str | None:
        """按顺序取第一个非空环境变量，用于 JUDGE_* 优先、LLM_* 兜底的场景。"""
        for name in names:
            value = os.getenv(name)
            if value:
                return value
        return default
