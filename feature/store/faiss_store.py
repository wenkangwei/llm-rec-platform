"""Faiss 向量特征存储 — 支持向量索引构建与相似度检索"""

from __future__ import annotations

from typing import Any

import numpy as np

from feature.store.base import FeatureStore
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.store.faiss")


class FaissFeatureStore(FeatureStore):
    """基于 Faiss 的向量特征存储。

    支持高维向量的索引构建、相似度检索（L2/Inner Product/Cosine）。
    当 faiss-cpu 不可用时降级为暴力搜索。
    """

    def __init__(
        self,
        dimension: int = 64,
        metric: str = "ip",  # "ip" (内积), "l2", "cosine"
        nlist: int = 100,  # IVF 聚类数
        nprobe: int = 10,  # 搜索探测数
    ):
        self._dimension = dimension
        self._metric = metric
        self._nlist = nlist
        self._nprobe = nprobe
        self._index: Any = None
        self._id_map: dict[int, str] = {}  # faiss internal id → entity_id
        self._entity_vectors: dict[str, np.ndarray] = {}  # entity_id → vector
        self._faiss_available = False

    def _try_import_faiss(self) -> Any:
        """尝试导入 faiss，不可用时返回 None。"""
        try:
            import faiss
            self._faiss_available = True
            return faiss
        except ImportError:
            logger.warning("faiss-cpu 未安装，使用暴力搜索降级")
            self._faiss_available = False
            return None

    def _build_index(self) -> None:
        """构建 Faiss 索引。"""
        faiss = self._try_import_faiss()
        vectors = list(self._entity_vectors.values())
        if not vectors:
            return

        matrix = np.stack(vectors).astype(np.float32)
        n = matrix.shape[0]

        if faiss is not None and n > self._nlist:
            if self._metric == "l2":
                quantizer = faiss.IndexFlatL2(self._dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self._dimension, self._nlist)
            elif self._metric == "cosine":
                # cosine → normalize + inner product
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms = np.where(norms == 0, 1, norms)
                matrix = matrix / norms
                quantizer = faiss.IndexFlatIP(self._dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self._dimension, self._nlist)
            else:  # ip
                quantizer = faiss.IndexFlatIP(self._dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self._dimension, self._nlist)

            self._index.train(matrix)
            self._index.add(matrix)
            self._index.nprobe = self._nprobe
        elif faiss is not None:
            # 小数据集用 Flat 索引
            if self._metric == "l2":
                self._index = faiss.IndexFlatL2(self._dimension)
            elif self._metric == "cosine":
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms = np.where(norms == 0, 1, norms)
                matrix = matrix / norms
                self._index = faiss.IndexFlatIP(self._dimension)
            else:
                self._index = faiss.IndexFlatIP(self._dimension)
            self._index.add(matrix)

        self._id_map = {i: eid for i, eid in enumerate(self._entity_vectors.keys())}
        logger.info(f"Faiss 索引构建完成", n_vectors=n, metric=self._metric, faiss=self._faiss_available)

    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        """获取实体的向量特征。"""
        vector = self._entity_vectors.get(entity_id)
        if vector is None:
            return {}
        return {name: float(v) for name, v in zip(feature_names, vector)}

    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        """批量获取向量特征。"""
        results = []
        for eid in entity_ids:
            vector = self._entity_vectors.get(eid)
            if vector is not None:
                results.append({name: float(v) for name, v in zip(feature_names, vector)})
            else:
                results.append({})
        return results

    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        """设置实体向量特征。"""
        vector = np.array(list(features.values()), dtype=np.float32)
        self._entity_vectors[entity_id] = vector
        # 标记索引需要重建
        self._index = None

    def add_vectors(self, entity_ids: list[str], vectors: np.ndarray) -> None:
        """批量添加向量。"""
        for eid, vec in zip(entity_ids, vectors):
            self._entity_vectors[eid] = vec.astype(np.float32)
        self._index = None  # 标记需要重建

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        """向量相似度搜索。

        Returns:
            [(entity_id, score), ...] 按 score 降序
        """
        if not self._entity_vectors:
            return []

        query = query_vector.astype(np.float32).reshape(1, -1)

        # 重建索引（如果需要）
        if self._index is None:
            self._build_index()

        faiss = self._try_import_faiss()
        if faiss is not None and self._index is not None:
            scores, indices = self._index.search(query, min(top_k, len(self._id_map)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx in self._id_map:
                    results.append((self._id_map[idx], float(score)))
            return results

        # 暴力搜索降级
        return self._brute_force_search(query_vector, top_k)

    def _brute_force_search(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        """暴力搜索降级。"""
        query = query_vector.astype(np.float32)
        scores = []
        for eid, vec in self._entity_vectors.items():
            if self._metric == "l2":
                score = -float(np.linalg.norm(query - vec))  # 负距离，越大越相似
            elif self._metric == "cosine":
                norm_q = np.linalg.norm(query)
                norm_v = np.linalg.norm(vec)
                if norm_q == 0 or norm_v == 0:
                    score = 0.0
                else:
                    score = float(np.dot(query, vec) / (norm_q * norm_v))
            else:  # ip
                score = float(np.dot(query, vec))
            scores.append((eid, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    async def health_check(self) -> bool:
        """健康检查。"""
        return True
