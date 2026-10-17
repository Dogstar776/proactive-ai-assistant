"""向量存储抽象：chromadb 可选，缺失时降级 NullVectorStore。

论文 5.4.3：个人/边缘部署的独特优势是数据主权。向量库同样本地优先；
未安装 chromadb 时系统不报错，只在日志中说明降级（P3 检索用到时再装）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from assistant.logging_setup import get_logger

logger = get_logger("memory.vector")


class VectorStore(ABC):
    @abstractmethod
    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None: ...

    @abstractmethod
    def query(self, text: str, n: int = 5) -> list[dict]: ...

    @abstractmethod
    def count(self) -> int: ...


class NullVectorStore(VectorStore):
    """降级实现：不存储，只告警。保证无 chromadb 环境全链路可跑。"""

    def __init__(self) -> None:
        logger.warning("vector.store.degraded: chromadb 未安装，使用 NullVectorStore")

    def add(self, ids, documents, metadatas) -> None:  # noqa: ANN001
        logger.warning("vector.add.skipped (NullVectorStore), n=%d", len(ids))

    def query(self, text: str, n: int = 5) -> list[dict]:  # noqa: ANN001
        return []

    def count(self) -> int:
        return 0


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str, collection: str = "memories") -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._col = self._client.get_or_create_collection(collection)

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self._col.add(ids=ids, documents=documents, metadatas=metadatas)

    def query(self, text: str, n: int = 5) -> list[dict]:
        res = self._col.query(query_texts=[text], n_results=n)
        out: list[dict] = []
        for i, doc_id in enumerate(res.get("ids", [[]])[0]):
            out.append({"id": doc_id, "document": res["documents"][0][i]})
        return out

    def count(self) -> int:
        return int(self._col.count())


def create_vector_store(persist_dir: str) -> VectorStore:
    """工厂：有 chromadb 用 chroma，没有就降级（P2 不依赖向量检索）。"""
    try:
        import chromadb  # noqa: F401

        return ChromaVectorStore(persist_dir)
    except ImportError:
        return NullVectorStore()
