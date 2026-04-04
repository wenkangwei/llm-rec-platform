#!/usr/bin/env python3
"""双塔模型训练脚本"""

from __future__ import annotations

import argparse
import os

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

from utils.logger import get_struct_logger

logger = get_struct_logger("scripts.train_two_tower")


class PairwiseDataset(Dataset):
    """正负样本对数据集。

    支持从 Parquet 文件或直接传入 numpy 数组加载。
    """

    def __init__(self, data_path: str = "", samples: list | None = None):
        if samples is not None:
            self.samples: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = samples
        elif data_path and os.path.exists(data_path):
            self.samples = self._load_from_parquet(data_path)
        else:
            logger.warning(f"训练数据路径不存在或为空: {data_path}，生成随机样本")
            self.samples = self._generate_dummy_samples(1000, 128)

    def _load_from_parquet(self, data_path: str) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """从 Parquet 文件加载训练数据。

        预期格式: user_features, pos_item_features, neg_item_features
        """
        try:
            import pandas as pd
            df = pd.read_parquet(data_path)
            samples = []
            for _, row in df.iterrows():
                user_feat = np.array(row.get("user_features", []), dtype=np.float32)
                pos_feat = np.array(row.get("pos_item_features", []), dtype=np.float32)
                neg_feat = np.array(row.get("neg_item_features", []), dtype=np.float32)
                if user_feat.size > 0 and pos_feat.size > 0 and neg_feat.size > 0:
                    samples.append((user_feat, pos_feat, neg_feat))
            logger.info(f"从 Parquet 加载 {len(samples)} 训练样本", path=data_path)
            return samples
        except ImportError:
            logger.warning("pandas/pyarrow 未安装，生成随机样本")
            return self._generate_dummy_samples(1000, 128)
        except Exception as e:
            logger.error(f"Parquet 加载失败", error=str(e))
            return self._generate_dummy_samples(1000, 128)

    def _generate_dummy_samples(
        self, n: int, dim: int
    ) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """生成随机训练样本（用于测试/调试）。"""
        samples = []
        for _ in range(n):
            u = np.random.randn(dim).astype(np.float32)
            pos = np.random.randn(dim).astype(np.float32)
            neg = np.random.randn(dim).astype(np.float32)
            samples.append((u, pos, neg))
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        u, pos, neg = self.samples[idx]
        return (
            torch.from_numpy(u.astype(np.float32)),
            torch.from_numpy(pos.astype(np.float32)),
            torch.from_numpy(neg.astype(np.float32)),
        )


def train(
    data_path: str = "data/training/",
    input_dim: int = 128,
    output_dim: int = 64,
    epochs: int = 10,
    batch_size: int = 256,
    lr: float = 1e-3,
    save_path: str = "models/two_tower_v1.pt",
    device: str = "auto",
):
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    from pipeline.model_service.models.two_tower import UserTower, ItemTower

    user_tower = UserTower(input_dim, output_dim, output_dim).to(device)
    item_tower = ItemTower(input_dim, output_dim, output_dim).to(device)

    optimizer = optim.Adam(
        list(user_tower.parameters()) + list(item_tower.parameters()), lr=lr
    )

    dataset = PairwiseDataset(data_path)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2)

    for epoch in range(epochs):
        total_loss = 0.0
        for batch in loader:
            user_feat, pos_item, neg_item = [x.to(device) for x in batch]

            user_emb = user_tower(user_feat)
            pos_emb = item_tower(pos_item)
            neg_emb = item_tower(neg_item)

            # BPR Loss
            pos_score = (user_emb * pos_emb).sum(dim=-1)
            neg_score = (user_emb * neg_emb).sum(dim=-1)
            loss = -torch.log(torch.sigmoid(pos_score - neg_score)).mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / max(len(loader), 1)
        logger.info(f"Epoch {epoch + 1}/{epochs} | Loss: {avg_loss:.4f}")

    # 保存模型
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(
        {"user_tower": user_tower.state_dict(), "item_tower": item_tower.state_dict()},
        save_path,
    )
    logger.info(f"模型已保存: {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="双塔模型训练")
    parser.add_argument("--data", default="data/training/")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save", default="models/two_tower_v1.pt")
    args = parser.parse_args()

    train(
        data_path=args.data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        save_path=args.save,
    )
