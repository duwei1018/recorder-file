# pipeline/dialogue.py
"""
Step 2：将原始转录文字整理成问答对话格式。
"""
from pathlib import Path
from datetime import datetime
from utils.llm import call_llm
from utils.logger import log

SYSTEM = """你是一位专业的访谈记录整理员。
将原始录音转录文字整理成清晰的问答对话格式。

规则：
- 识别提问者（研究员/分析师）和受访者（行业专家/公司人员）
- 格式：
  **【提问】** 问题内容
  **【受访】** 回答内容
- 若无法区分说话人，按话题分段并加小标题
- 修正明显口语错误，保留原意、专业术语和数字
- 输出纯 Markdown，不加任何额外解释"""


def run(raw_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> str:
    log.info("  整理对话格式...")
    prompt = f"请将以下转录文字整理成对话格式：\n\n{raw_text}"
    dialogue = call_llm(SYSTEM, prompt, cfg["ollama"])

    out_path = output_dir / f"{audio_stem}_2_对话整理.md"
    out_path.write_text(
        f"# 访谈对话 — {audio_stem}\n\n"
        f"> 整理时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{dialogue}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return dialogue
