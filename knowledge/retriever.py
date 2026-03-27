# knowledge/retriever.py
"""
语义检索（预留，阶段二激活）
"""
from utils.logger import log


def retrieve(query: str, store, n: int = 5) -> list:
    """
    TODO（阶段二）：
    从 KnowledgeStore 检索与 query 最相关的 n 条文档片段
    返回：[{"text": "...", "source": "...", "score": 0.xx}, ...]
    """
    log.info(f"  [retriever] 检索模块预留: {query}")
    return []
