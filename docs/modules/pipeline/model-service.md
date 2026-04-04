# 模型服务

## ModelManager

模型生命周期管理：注册、预测、预热、关闭。

```python
from pipeline.model_service import ModelManager

mgr = ModelManager()
mgr.register("two_tower", TwoTowerModel(dim=64))
mgr.register("dcn", DCNModel())
mgr.warmup_all()

pred = mgr.predict("dcn", features)
batch = mgr.predict_batch("dcn", feature_list)
```

## 模型后端

| 模型 | 类 | 用途 | 框架 |
|------|-----|------|------|
| TwoTower | `TwoTowerModel` | 向量召回 | PyTorch |
| DCN-v2 | `DCNModel` | 精排（特征交叉） | PyTorch |
| DIN | `DINModel` | 精排（行为注意力） | PyTorch |
| LightGBM | `LightGBMModel` | 粗排 | LightGBM |
| 通用 PyTorch | `TorchModel` | 自定义模型 | PyTorch |
| ONNX | `ONNXModel` | 推理优化 | ONNX Runtime |
| Triton | `TritonModelBackend` | GPU 推理服务 | Triton gRPC |

## 接口

```python
class ModelService(ABC):
    def name(self) -> str
    def version(self) -> str
    async def predict(self, features: dict) -> dict
    def warmup(self) -> None
    def shutdown(self) -> None
    def health_check(self) -> bool
```

## 配置

```yaml
# configs/model/models.yaml
two_tower:
  dim: 64
  checkpoint: "data/models/two_tower.pt"
dcn:
  input_dim: 128
  checkpoint: "data/models/dcn.pt"
lightgbm:
  model_path: "data/models/lightgbm.txt"
```
