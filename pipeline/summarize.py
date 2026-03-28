# pipeline/summarize.py
"""
Step 3：从对话中提炼五维结构化研究摘要。
"""
from pathlib import Path
from datetime import datetime
from utils.llm import call_llm
from utils.logger import log

SYSTEM = """你是一位专业的行业研究分析师。
从访谈对话中提炼关键信息，生成结构化研究摘要。

严格按以下格式输出 Markdown（五个部分，缺失的写"暂无明确提及"）：

## 一、核心观点
- （每条一行，3-5条）

## 二、关键数据
（具体数字、比例、时间节点、金额）

## 三、行业现状
（市场规模、竞争格局、供需关系、上下游）

## 四、风险与挑战
（受访者提及的风险点、政策影响、竞争压力）

## 五、后续关注点
（值得深入研究的问题、需要验证的假设）"""


def run(dialogue_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> str:
    log.info("  提炼研究摘要...")
    prompt = f"请根据以下访谈对话提炼关键信息：\n\n{dialogue_text}"
    summary = call_llm(SYSTEM, prompt, cfg["ollama"])

    out_path = output_dir / f"{audio_stem}_3_研究摘要.md"
    out_path.write_text(
        f"# 研究摘要 — {audio_stem}\n\n"
        f"> 提炼时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{summary}\n\n"
        f"---\n\n"
        f"## 附：完整对话\n\n{dialogue_text}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return summary
