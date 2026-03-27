# pipeline/transcribe.py
"""Step 1：使用 Whisper 将音频文件转录为文字。
模型全局缓存，批量处理时只加载一次。
"""
import sys
from pathlib import Path
from datetime import datetime
from utils.logger import log

_model_cache: dict = {}


def transcribe(audio_path: Path, cfg: dict) -> str:
    """转录音频，返回纯文字字符串"""
    try:
        import whisper
    except ImportError:
        log.error("请先执行: pip install openai-whisper")
        sys.exit(1)

    model_name = cfg["whisper"]["model"]

    if model_name not in _model_cache:
        log.info(f"  加载 Whisper [{model_name}]（首次需下载，请稍候）...")
        _model_cache[model_name] = whisper.load_model(model_name)

    model = _model_cache[model_name]
    log.info(f"  开始转录: {audio_path.name}")

    result = model.transcribe(
        str(audio_path),
        language=cfg["whisper"].get("language", "zh"),
        verbose=False,
        fp16=cfg["whisper"].get("fp16", False),
    )
    text = result["text"].strip()
    log.info(f"  转录完成，共 {len(text)} 字")
    return text


def run(audio_path: Path, output_dir: Path, cfg: dict) -> str:
    """执行 Step 1，落盘并返回文字内容"""
    text = transcribe(audio_path, cfg)
    out_path = output_dir / f"{audio_path.stem}_1_原始转录.md"
    out_path.write_text(
        f"# 原始转录 — {audio_path.stem}\n\n"
        f"> 转录时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{text}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return text
