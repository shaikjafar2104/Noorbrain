from fastapi import APIRouter, Query

from services.habit_ai import habit_ai
from services.habit_ai.predictor import habit_predictor
from services.habit_ai.recommendation import habit_recommendation
from services.habit_engine import habit_engine


router = APIRouter(
    prefix="/habits",
    tags=["Habit Engine"]
)


@router.get("")
def get_habits(
    limit: int = Query(
        default=100,
        ge=1,
        le=300
    )
):
    return habit_engine.summary(limit)


@router.post("/clear")
def clear_habits():
    return habit_engine.clear()


@router.get("/insights")
def habit_insights():
    data = habit_engine.summary(100)
    return habit_ai.analyse(data)


@router.get("/predictions")
def habit_predictions():
    data = habit_engine.summary(100)
    return habit_predictor.predict(data)


@router.get("/recommendation")
def habit_recommendation_status():
    data = habit_engine.summary(300)
    return habit_recommendation.evaluate(data)
