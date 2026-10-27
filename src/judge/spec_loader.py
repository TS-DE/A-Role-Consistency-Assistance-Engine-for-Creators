"""载入判定输入（去泄漏版 sherlock.judge.yaml）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.judge.constants import JUDGE_YAML


class SpecLoader:
    """把 yaml 读成 dict，并额外提供 traits 的 id 索引。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or JUDGE_YAML

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(
                f"判定输入不存在：{self.path}\n"
                "先跑 python tools/build_judge_yaml.py 从 sherlock.yaml 重建。"
            )
        spec = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        spec["_traits_by_id"] = {t["id"]: t for t in spec["traits"]}
        return spec
