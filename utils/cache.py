# utils/cache.py
import json
import hashlib
from pathlib import Path

def file_id(path: Path) -> str:
    """根据文件路径和大小生成唯一 ID"""
    return hashlib.md5(f"{path}|{path.stat().st_size}".encode()).hexdigest()

def load_cache(cache_path: str) -> dict:
    p = Path(cache_path)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def save_cache(cache: dict, cache_path: str):
    Path(cache_path).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
