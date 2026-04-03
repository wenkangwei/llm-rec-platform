"""DIN (Deep Interest Network) — 精排模型"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("din")


class AttentionLayer(nn.Module):
    """DIN 注意力层：目标物品对用户行为序列的注意力加权。"""

    def __init__(self, embedding_dim: int, hidden_units: list[int] | None = None):
        super().__init__()
        hidden = hidden_units or [64, 32]
        layers = []
        input_dim = embedding_dim * 4  # [item, behavior, item-behavior, item*behavior]
        for h in hidden:
            layers.extend([nn.Linear(input_dim, h), nn.ReLU()])
            input_dim = h
        layers.append(nn.Linear(input_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, item_emb: torch.Tensor, behavior_emb: torch.Tensor) -> torch.Tensor:
        """item_emb: [B, D], behavior_emb: [B, T, D]"""
        B, T, D = behavior_emb.shape
        item_expanded = item_emb.unsqueeze(1).expand(-1, T, -1)
        concat = torch.cat([
            item_expanded, behavior_emb,
            item_expanded - behavior_emb,
            item_expanded * behavior_emb,
        ], dim=-1)
        weights = torch.softmax(self.net(concat).squeeze(-1), dim=-1)  # [B, T]
        return (weights.unsqueeze(-1) * behavior_emb).sum(dim=1)  # [B, D]


class DINModel(ModelService):
    """DIN 精排模型：基于注意力机制的兴趣建模。"""

    def __init__(
        self,
        embedding_dim: int = 64,
        attention_hidden: list[int] | None = None,
        device: str = "auto",
    ):
        self._embedding_dim = embedding_dim
        self._attention_hidden = attention_hidden
        self._device = "cuda" if (device == "auto" and torch.cuda.is_available()) else device
        self._model: nn.Module | None = None

    def name(self) -> str:
        return "din"

    def version(self) -> str:
        return "v1"

    def warmup(self) -> None:
        self._model = self._build_model().to(self._device)
        self._model.eval()
        logger.info("DIN 模型初始化完成", device=self._device)

    def _build_model(self) -> nn.Module:
        emb_dim = self._embedding_dim

        class DIN(nn.Module):
            def __init__(self_inner):
                super().__init__()
                self_inner.attention = AttentionLayer(emb_dim, self._attention_hidden)
                self_inner.fc = nn.Sequential(
                    nn.Linear(emb_dim * 2, 128),
                    nn.ReLU(),
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Linear(64, 1),
                )

            def forward(self_inner, x):
                # 输入格式: [B, feature_dim]
                # 简化实现：将特征拆分为 item_emb + behavior_pool
                half = x.shape[-1] // 2
                item_emb = x[:, :half]
                behavior_pool = x[:, half:]
                # AttentionLayer.forward expects item_emb [B, D], behavior_emb [B, T, D]
                # Pass behavior_pool as [B, 1, D] for single behavior
                interest = self_inner.attention(
                    item_emb,
                    behavior_pool.unsqueeze(1),
                )
                combined = torch.cat([interest, item_emb[:, :emb_dim]], dim=-1)
                return torch.sigmoid(self_inner.fc(combined)).squeeze(-1)

        return DIN()

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self._model is None:
            return np.random.random(len(features)).astype(np.float32)
        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).to(self._device)
            return self._model(tensor).cpu().numpy()

    def shutdown(self) -> None:
        self._model = None
