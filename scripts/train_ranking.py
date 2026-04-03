#!/usr/bin/env python3
"""精排模型训练脚本 (DCN-v2 / DIN)"""

from __future__ import annotations

import argparse
import os

import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset


class RankDataset(Dataset):
    """排序训练数据集。"""

    def __init__(self, data_path: str):
        # TODO: 从 Parquet 加载训练样本
        # 格式: features (concat user+item+context), label (clicked)
        self.samples: list[tuple[np.ndarray, int]] = []

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        feat, label = self.samples[idx]
        return torch.from_numpy(feat.astype(np.float32)), torch.tensor(label, dtype=torch.float32)


def train(
    model_name: str = "dcn",
    data_path: str = "data/training/",
    input_dim: int = 256,
    epochs: int = 10,
    batch_size: int = 128,
    lr: float = 1e-3,
    save_path: str = "models/dcn_v2_v1.pt",
):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if model_name == "dcn":
        from pipeline.model_service.models.dcn import DCNModel
        model_svc = DCNModel(input_dim=input_dim)
    elif model_name == "din":
        from pipeline.model_service.models.din import DINModel
        model_svc = DINModel(embedding_dim=64)
    else:
        raise ValueError(f"未知模型: {model_name}")

    model_svc.warmup()
    model = model_svc._model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.BCELoss()

    dataset = RankDataset(data_path)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    for epoch in range(epochs):
        total_loss = 0.0
        for features, labels in loader:
            features, labels = features.to(device), labels.to(device)
            preds = model(features)
            loss = criterion(preds, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / max(len(loader), 1)
        print(f"Epoch {epoch + 1}/{epochs} | Loss: {avg_loss:.4f}")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"模型已保存: {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="精排模型训练")
    parser.add_argument("--model", default="dcn", choices=["dcn", "din"])
    parser.add_argument("--data", default="data/training/")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--save", default="models/dcn_v2_v1.pt")
    args = parser.parse_args()
    train(model_name=args.model, data_path=args.data, epochs=args.epochs, save_path=args.save)
