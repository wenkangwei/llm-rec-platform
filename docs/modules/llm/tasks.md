# LLM 任务

4 个 LLM 驱动的下游任务。

## Embedder — 向量生成

批量为物品/用户生成 Embedding，存入 Faiss。

```python
from llm.tasks.embedder import Embedder

embedder = Embedder(llm_backend)
vectors = await embedder.embed_items(["item_001", "item_002"])
```

## ContentGenerator — 冷启动内容

LLM 模拟用户交互数据，为新物品生成虚拟行为。

```python
from llm.tasks.content_gen import ContentGenerator

gen = ContentGenerator(llm_backend)
interactions = await gen.generate(item_info, num_interactions=50)
```

## SemanticSearch — 语义搜索

Query 扩展 → 向量检索 → LLM 重排。

```python
from llm.tasks.semantic_search import SemanticSearch

search = SemanticSearch(llm_backend, faiss_store)
results = await search.search("人工智能", top_k=20)
```

## RerankSummary — 搜索摘要

对搜索结果生成个性化摘要。

```python
from llm.tasks.rerank_summary import RerankSummary

summarizer = RerankSummary(llm_backend)
summary = await summarizer.generate(top_items, user_profile)
# → "为您找到了关于AI技术的5篇精选文章..."
```
