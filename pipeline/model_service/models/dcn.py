"""DCN-v2 (Deep & Cross Network v2) — 精排模型"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("dcn")


class CrossLayer(nn.Module):
    """Cross Network 层：显式特征交叉。"""

    def __init__(self, input_dim: int):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(input_dim))
        self.bias = nn.Parameter(torch.zeros(input_dim))

    def forward(self, x0: torch.Tensor, xi: torch.Tensor) -> torch.Tensor:
        return x0 * (xi @ self.weight.unsqueeze(0).T) + self.bias + xi


class DCNModel(ModelService):
    """DCN-v2 精排模型。

    Cross Network 捕获显式特征交叉，Deep Network 学习隐式交叉。
    """

    def __init__(
        self,
        input_dim: int = 256,
        cross_layers: int = 3,
        deep_layers: list[int] | None = None,
        device: str = "auto",
    ):
        self._input_dim = input_dim
        self._cross_layers_count = cross_layers
        self._deep_dims = deep_layers or [256, 128, 64]
        self._device = "cuda" if (device == "auto" and torch.cuda.is_available()) else device
        self._model: nn.Module | None = None

    def name(self) -> str:
        return "dcn"

    def version(self) -> str:
        return "v1"

    def warmup(self) -> None:
        self._model = self._build_model().to(self._device)
        self._model.eval()
        logger.info("DCN-v2 模型初始化完成", device=self._device)

    def _build_model(self) -> nn.Module:
        class DCN(nn.Module):
            def __init__(self, input_dim, num_cross, deep_dims):
                super().__init__()
                self.cross_layers = nn.ModuleList([CrossLayer(input_dim) for _ in range(num_cross)])
                deep = []
                prev = input_dim
                for dim in deep_dims:
                    deep.extend([nn.Linear(prev, dim), nn.ReLU()])
                    prev = dim
                self.deep = nn.Sequential(*deep)
                self.output = nn.Linear(input_dim + deep_dims[-1], 1)

            def forward(self, x):
                x_cross = x
                for layer in self.cross_layers:
                    x_cross = layer(x, x_cross)
                x_deep = self.deep(x)
                combined = torch.cat([x_cross, x_deep], dim=-1)
                return torch.sigmoid(self.output(combined)).squeeze(-1)

        return DCN(self._input_dim, self._cross_layers_count, self._deep_dims)

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self._model is None:
            return np.random.random(len(features)).astype(np.float32)
        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).to(self._device)
            return self._model(tensor).cpu().numpy()

    def shutdown(self) -> None:
        self._model = None
