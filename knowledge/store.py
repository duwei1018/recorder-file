# knowledge/store.py
"""
ChromaDB 本地向量库接口（预留，阶段二激活）
"""
from utils.logger import log


class KnowledgeStore:
    """
    TODO（阶段二）：
    import chromadb
    self.client = chromadb.PersistentClient(path=cfg["paths"]["knowledge_dir"])
    self.collection = self.client.get_or_create_collection("research_docs")
    """
    def __init__(self, cfg: dict):
        log.info("  [KnowledgeStore] 知识库模块预留，暂未激活")

    def add_document(self, doc_id: str, text: str, metadata: dict):
        pass

    def query(self, query_text: str, n_results: int = 5) -> list:
        return []
