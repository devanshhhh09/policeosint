"""Entity relationship graph endpoint — Phase 4"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.db.models.user import User
from app.api.deps import get_current_user
from app.services.graph_service import build_entity_graph

router = APIRouter()


@router.get("/{entity_id}")
async def get_entity_graph(
    entity_id: str,
    entity_type: str = Query("person"),
    depth: int = Query(2, ge=1, le=3),
    current_user: User = Depends(get_current_user),
):
    return build_entity_graph(entity_id, entity_type, depth)


@router.get("/stats/summary")
async def graph_stats(current_user: User = Depends(get_current_user)):
    return {
        "total_nodes":       847,
        "total_edges":       1423,
        "high_risk_entities":34,
        "clusters_detected": 12,
        "node_types": {
            "person":  124,
            "email":   203,
            "phone":   189,
            "upi":     156,
            "wallet":  78,
            "domain":  64,
            "ip":      33,
        },
    }
