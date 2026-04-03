"""ModelService — 模型服务抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class ModelService(ABC):
    """模型服务抽象接口。

    所有模型（召回、粗排、精排）必须实现此接口。
    通过 ModelManager 统一管理生命周期。
    """

    @abstractmethod
    def name(self) -> str:
        """模型名称。"""

    @abstractmethod
    def version(self) -> str:
        """模型版本。"""

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        """推理接口：输入特征矩阵，输出预测分数。"""

    @abstractmethod
    def warmup(self) -> None:
        """预热模型（加载权重等）。"""

    @abstractmethod
    def shutdown(self) -> None:
        """释放模型资源。"""

    def input_schema(self) -> dict[str, Any]:
        """输入特征 schema。默认空。"""
        return {}

    def output_dim(self) -> int:
        """输出维度。默认 1（单分数）。"""
        return 1

    def health_check(self) -> bool:
        """健康检查。默认 True。"""
        return True
