# pipeline/classify.py
"""Step 4：智能分类打标签（预留，阶段二激活）
当前版本：空实现，不影响主流程运行
"""
from pathlib import Path
from utils.logger import log


def run(summary_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> dict:
    """
    TODO（阶段二）：
    1. 让 Ollama 从摘要中提取：行业、公司名、核心话题
    2. 按分类在 output_dir 下创建子目录
    3. 将三个 Markdown 文件复制/移动到对应子目录
    返回：{"industry": "...", "company": "...", "topics": [...]}
    """
    log.info("  [classify] 分类模块预留，暂未激活")
    return {}
