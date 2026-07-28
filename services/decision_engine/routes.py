from fastapi import APIRouter
from .decision_engine import decision_engine

router = APIRouter(prefix="/api/decision", tags=["Sprint 8.2 Decision Engine"])

@router.get("/health")
def health():
    return decision_engine.health()

@router.get("/current")
def current_decision():
    return decision_engine.evaluate()

@router.get("/explain")
def explain():
    result = decision_engine.evaluate()
    return {
        "decision": result["decision"],
        "priority": result["priority"],
        "score": result["score"],
        "explanation": result["explanation"],
        "reasons": result["reasons"],
    }
