"""
配置文件加载模块
读取 config.yaml，返回结构化配置字典，外部模块按需取用。
"""

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_config: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    """加载配置文件（带缓存，只读一次）。"""
    global _config
    if _config is not None:
        return _config

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)

    return _config


def get(key: str, default: Any = None) -> Any:
    """按点号分隔的路径取值，如 get("server.port") → 5000。"""
    cfg = load_config()
    parts = key.split(".")
    current = cfg
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return default
        else:
            return default
    return current