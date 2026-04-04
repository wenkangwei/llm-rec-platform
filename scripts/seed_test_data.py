"""种子数据脚本 — 灌入测试 user/item 数据到 Redis，使推荐链路产出结果。

用法: python3.10 scripts/seed_test_data.py
清理: python3.10 scripts/seed_test_data.py --clean
"""

from __future__ import annotations

import json
import random
import sys

import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# ===== 测试物料 =====

CATEGORIES = ["科技", "音乐", "游戏", "美食", "旅行", "健身", "读书", "摄影"]
ITEM_COUNT = 200
USER_COUNT = 10

random.seed(42)


def generate_items() -> list[dict]:
    """生成测试物料数据。"""
    items = []
    for i in range(1, ITEM_COUNT + 1):
        cat = random.choice(CATEGORIES)
        items.append({
            "item_id": f"item_{i:04d}",
            "title": f"{cat}内容#{i}",
            "category": cat,
            "tags": json.dumps([cat, random.choice(CATEGORIES)]),
            "author": f"author_{random.randint(1, 20)}",
            "score": round(random.uniform(0.5, 1.0), 3),
            "created_at": f"2026-03-{random.randint(1, 28):02d}",
        })
    return items


def generate_users() -> list[dict]:
    """生成测试用户数据。"""
    users = []
    for i in range(1, USER_COUNT + 1):
        uid = f"user_{i:03d}"
        users.append({
            "user_id": uid,
            "age": random.randint(18, 45),
            "gender": random.choice(["M", "F"]),
            "interests": json.dumps(random.sample(CATEGORIES, k=random.randint(2, 5))),
            "embedding": json.dumps([round(random.gauss(0, 0.3), 4) for _ in range(32)]),
            "recent_click_items": json.dumps([
                f"item_{random.randint(1, ITEM_COUNT):04d}" for _ in range(random.randint(3, 10))
            ]),
            "following_ids": json.dumps([
                f"user_{random.randint(1, USER_COUNT):03d}" for _ in range(random.randint(1, 5))
            ]),
            "community_ids": json.dumps(random.sample([
                "comm_tech", "comm_music", "comm_game", "comm_food",
                "comm_travel", "comm_fitness", "comm_book", "comm_photo",
            ], k=random.randint(1, 4))),
            "following_count": json.dumps(random.randint(5, 50)),
            "follower_count": json.dumps(random.randint(5, 50)),
            "session_duration": json.dumps(random.randint(60, 3600)),
            "click_count_24h": json.dumps(random.randint(5, 100)),
            "cold_start": json.dumps(False),
        })
    return users


def seed(client: redis.Redis) -> None:
    """灌入全部测试数据。"""
    items = generate_items()
    users = generate_users()
    item_ids = [it["item_id"] for it in items]

    pipe = client.pipeline(transaction=False)

    # 1. 热门物料 ZSET
    print("1. 写入 hot_items:global ...")
    for it in items[:100]:  # 前 100 个作为热门
        pipe.zadd("hot_items:global", {it["item_id"]: it["score"]})

    # 2. 物料池 SET (cold start explore)
    print("2. 写入 item_pool:all ...")
    pipe.sadd("item_pool:all", *item_ids)

    # 3. 物料画像 HASH
    print("3. 写入 item 特征 ...")
    for it in items:
        key = f"item_feat:{it['item_id']}"
        mapping = {k: json.dumps(v) if not isinstance(v, str) else v
                   for k, v in it.items() if k != "score"}
        pipe.hset(key, mapping=mapping)

    # 4. 用户画像 HASH (feat:{user_id})
    print("4. 写入 user 特征 ...")
    for u in users:
        key = f"feat:{u['user_id']}"
        mapping = {k: v for k, v in u.items() if k != "user_id"}
        pipe.hset(key, mapping=mapping)

    # 5. 物料相似度 (item_sim:{item_id})
    print("5. 写入 item_sim 相似度矩阵 ...")
    for it in items[:50]:  # 前 50 个物料有相似度数据
        similar = random.sample([x for x in item_ids if x != it["item_id"]], k=5)
        sim_list = [[sid, round(random.uniform(0.5, 0.99), 3)] for sid in similar]
        pipe.set(f"item_sim:{it['item_id']}", json.dumps(sim_list))

    # 6. 用户社交互动 (user_interactions:{uid})
    print("6. 写入 user_interactions ...")
    for u in users:
        for fid in json.loads(u["following_ids"]):
            interacted = random.sample(item_ids, k=random.randint(5, 15))
            for iid in interacted:
                pipe.zadd(f"user_interactions:{fid}", {iid: round(random.uniform(0.5, 1.0), 3)})

    # 7. 社区热门 (community_hot:{cid})
    print("7. 写入 community_hot ...")
    communities = ["comm_tech", "comm_music", "comm_game", "comm_food",
                   "comm_travel", "comm_fitness", "comm_book", "comm_photo"]
    for cid in communities:
        community_items = random.sample(item_ids, k=30)
        for iid in community_items:
            pipe.zadd(f"community_hot:{cid}", {iid: round(random.uniform(50, 100), 1)})

    pipe.execute()
    print(f"\n完成! 灌入 {len(items)} 个物料, {len(users)} 个用户")


def clean(client: redis.Redis) -> None:
    """清理所有测试数据。"""
    print("清理测试数据 ...")
    patterns = [
        "hot_items:global", "item_pool:all",
        "item_feat:*", "feat:*", "item_sim:*",
        "user_interactions:*", "community_hot:*",
    ]
    total = 0
    for pattern in patterns:
        if "*" in pattern:
            keys = client.keys(pattern)
        else:
            keys = [pattern]
        if keys:
            deleted = client.delete(*keys)
            total += deleted
    print(f"已清理 {total} 个 key")


def main():
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    client.ping()
    print(f"Redis 连接成功 ({REDIS_HOST}:{REDIS_PORT})")

    if "--clean" in sys.argv:
        clean(client)
        return

    # 先清理旧数据
    clean(client)
    print()
    seed(client)


if __name__ == "__main__":
    main()
