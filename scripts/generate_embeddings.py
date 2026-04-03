#!/usr/bin/env python3
"""批量生成 Embedding 脚本"""

from __future__ import annotations

import argparse
import asyncio
import json

import numpy as np

from llm.backends.mock_backend import MockBackend
from llm.tasks.embedder import Embedder


async def generate(
    input_file: str = "data/items.jsonl",
    output_file: str = "data/item_embeddings.npy",
    id_file: str = "data/item_ids.json",
    batch_size: int = 32,
    use_mock: bool = True,
):
    """批量生成物品 Embedding 并保存为 Faiss 可加载格式。"""
    # 读取物品
    items = []
    with open(input_file, "r") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    if not items:
        print("无物品数据，跳过")
        return

    # 创建 Embedder
    if use_mock:
        backend = MockBackend()
    else:
        from llm.backends.vllm_backend import VLLMBackend
        backend = VLLMBackend()

    embedder = Embedder(backend)
    await backend.warmup()

    # 批量生成
    texts = [
        f"{item.get('title', '')} {' '.join(item.get('tags', []))} {item.get('description', '')}".strip()
        for item in items
    ]
    embeddings = await embedder.embed_batch(texts, batch_size=batch_size)

    # 保存
    emb_array = np.array(embeddings, dtype=np.float32)
    np.save(output_file, emb_array)

    ids = [item.get("item_id", str(i)) for i, item in enumerate(items)]
    with open(id_file, "w") as f:
        json.dump(ids, f)

    print(f"生成完成: {len(embeddings)} 条 embedding, 维度={emb_array.shape[1]}")
    print(f"保存到: {output_file}, {id_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量生成 Embedding")
    parser.add_argument("--input", default="data/items.jsonl")
    parser.add_argument("--output", default="data/item_embeddings.npy")
    parser.add_argument("--ids", default="data/item_ids.json")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    asyncio.run(generate(
        input_file=args.input,
        output_file=args.output,
        id_file=args.ids,
        batch_size=args.batch_size,
        use_mock=args.mock,
    ))
