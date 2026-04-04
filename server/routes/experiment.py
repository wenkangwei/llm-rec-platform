"""实验管理路由 — A/B 实验的 CRUD 和结果查询"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/experiments", tags=["experiment"])


class VariantInput(BaseModel):
    name: str
    traffic_percent: float = 50.0
    config: dict = Field(default_factory=dict)


class CreateExperimentInput(BaseModel):
    id: str
    name: str
    layer: str = "default"
    variants: list[VariantInput]


@router.get("")
async def list_experiments(request: Request, status: str | None = None):
    """列出所有实验。"""
    from experiment.models import ExperimentStatus
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"experiments": []}
    filter_status = ExperimentStatus(status) if status else None
    return {"experiments": mgr.list_experiments(filter_status)}


@router.post("")
async def create_experiment(body: CreateExperimentInput, request: Request):
    """创建实验（DRAFT 状态）。"""
    from experiment.models import Experiment, ExperimentVariant
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    variants = [
        ExperimentVariant(name=v.name, traffic_percent=v.traffic_percent, config=v.config)
        for v in body.variants
    ]
    exp = Experiment(id=body.id, name=body.name, variants=variants)
    mgr.create_experiment(exp)
    return {"id": body.id, "status": "draft"}


@router.post("/{experiment_id}/start")
async def start_experiment(experiment_id: str, request: Request):
    """启动实验。"""
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    mgr.start_experiment(experiment_id)
    return {"id": experiment_id, "status": "running"}


@router.post("/{experiment_id}/stop")
async def stop_experiment(experiment_id: str, request: Request):
    """停止实验。"""
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    mgr.stop_experiment(experiment_id)
    return {"id": experiment_id, "status": "completed"}


@router.post("/{experiment_id}/pause")
async def pause_experiment(experiment_id: str, request: Request):
    """暂停实验。"""
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    mgr.pause_experiment(experiment_id)
    return {"id": experiment_id, "status": "paused"}


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, request: Request):
    """获取实验结果分析。"""
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    return mgr.get_results(experiment_id)


@router.get("/{experiment_id}/variant")
async def get_user_variant(experiment_id: str, user_id: str, request: Request):
    """查询用户在实验中的分组。"""
    mgr = getattr(request.app.state, "experiment_manager", None)
    if not mgr:
        return {"error": "experiment manager not initialized"}
    variant = mgr.get_variant(experiment_id, user_id)
    if variant:
        return {"experiment_id": experiment_id, "variant": variant.name, "config": variant.config}
    return {"experiment_id": experiment_id, "variant": None}
