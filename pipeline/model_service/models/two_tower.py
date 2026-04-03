"""双塔模型 — 个性化召回用"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("two_tower")


class UserTower(nn.Module):
    """用户塔：用户特征 → 用户 embedding。"""

    def __init__(self, input_dim: int = 128, hidden_dim: int = 128, output_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.normalize(self.net(x), p=2, dim=-1)


class ItemTower(nn.Module):
    """物品塔：物品特征 → 物品 embedding。"""

    def __init__(self, input_dim: int = 128, hidden_dim: int = 128, output_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.normalize(self.net(x), p=2, dim=-1)


class TwoTowerModel(ModelService):
    """双塔召回模型。

    encode_users / encode_items 分别生成用户和物品 embedding。
    用户 embedding 和物品 embedding 存入 Faiss 进行 ANN 检索。
    """

    def __init__(
        self,
        input_dim: int = 128,
        hidden_dim: int = 128,
        output_dim: int = 64,
        device: str = "auto",
    ):
        self._input_dim = input_dim
        self._output_dim = output_dim
        self._device = "cuda" if (device == "auto" and torch.cuda.is_available()) else device
        self.user_tower: UserTower | None = None
        self.item_tower: ItemTower | None = None

    def name(self) -> str:
        return "two_tower"

    def version(self) -> str:
        return "v1"

    def warmup(self) -> None:
        self.user_tower = UserTower(self._input_dim, self._output_dim, self._output_dim).to(self._device)
        self.item_tower = ItemTower(self._input_dim, self._output_dim, self._output_dim).to(self._device)
        self.user_tower.eval()
        self.item_tower.eval()
        logger.info("双塔模型初始化完成", device=self._device)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """predict 接口在此模型中返回用户 embedding。"""
        return self.encode_users(features)

    def encode_users(self, features: np.ndarray) -> np.ndarray:
        """批量生成用户 embedding。"""
        if self.user_tower is None:
            return np.zeros((len(features), self._output_dim), dtype=np.float32)
        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).to(self._device)
            return self.user_tower(tensor).cpu().numpy()

    def encode_items(self, features: np.ndarray) -> np.ndarray:
        """批量生成物品 embedding。"""
        if self.item_tower is None:
            return np.zeros((len(features), self._output_dim), dtype=np.float32)
        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).to(self._device)
            return self.item_tower(tensor).cpu().numpy()

    def shutdown(self) -> None:
        self.user_tower = None
        self.item_tower = None

    def output_dim(self) -> int:
        return self._output_dim
