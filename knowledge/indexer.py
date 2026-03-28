# knowledge/indexer.py
"""
文档嵌入 + 索引构建（预留，阶段二激活）
"""
from pathlib import Path
from utils.logger import log


def index_directory(directory: Path, store, cfg: dict):
    """
    TODO（阶段二）：
    遍历目录下所有 Markdown 文件（包括 Recorder-File 的 info-collector 的文档）
    调用 ollama embed 生成嵌入向量
    写入 KnowledgeStore
    """
    log.info(f"  [indexer] 索引模块预留：{directory}")
