"""Faiss 向量检索封装 — Embedding ANN"""

from __future__ import annotations

from typing import Any

import numpy as np

from utils.logger import get_struct_logger

logger = get_struct_logger("storage.faiss")


class FaissStore:
    """Faiss 向量存储封装，支持 ANN 检索。"""

    def __init__(self, dimension: int = 64, index_type: str = "ivf_flat", nlist: int = 100):
        self._dimension = dimension
        self._index_type = index_type
        self._nlist = nlist
        self._index = None
        self._id_map: dict[int, str] = {}  # 内部ID → 业务ID

    def build(self, embeddings: np.ndarray, ids: list[str]) -> None:
        """构建索引。"""
        import faiss

        n = len(embeddings)
        dim = embeddings.shape[1]

        if self._index_type == "ivf_flat":
            quantizer = faiss.IndexFlatIP(dim)
            self._index = faiss.IndexIVFFlat(quantizer, dim, min(self._nlist, n // 10))
            self._index.train(embeddings.astype(np.float32))
            self._index.add(embeddings.astype(np.float32))
        elif self._index_type == "flat":
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(embeddings.astype(np.float32))
        else:
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(embeddings.astype(np.float32))

        self._id_map = {i: eid for i, eid in enumerate(ids)}
        logger.info(f"Faiss 索引构建完成", index_type=self._index_type, count=n, dim=dim)

    def search(self, query: np.ndarray, top_k: int = 100) -> tuple[np.ndarray, list[list[str]]]:
        """ANN 检索。"""
        if self._index is None:
            return np.array([]), []

        query = query.astype(np.float32)
        if query.ndim == 1:
            query = query.reshape(1, -1)

        scores, indices = self._index.search(query, top_k)

        # 转换为业务 ID
        id_results = []
        for row in indices:
            id_results.append([self._id_map.get(int(idx), "") for idx in row if idx >= 0])

        return scores, id_results

    def add(self, embedding: np.ndarray, entity_id: str) -> None:
        """增量添加向量。"""
        if self._index is None:
            return
        idx = self._index.ntotal
        self._index.add(embedding.reshape(1, -1).astype(np.float32))
        self._id_map[idx] = entity_id

    def count(self) -> int:
        """索引中的向量数量。"""
        return self._index.ntotal if self._index else 0
