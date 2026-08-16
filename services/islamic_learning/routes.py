"""Islamic Learning — FastAPI routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .questions import DUAS, NAMES_99, SURAH_QUIZ, ARABIC_MATCH, ISLAMIC_KNOWLEDGE, KIDS_DATA
from .store import islamic_learning_store

router = APIRouter(prefix="/api/islamic-learning", tags=["Islamic Learning"])

C = {"dua-challenge": DUAS, "names-99": NAMES_99, "surah-quiz": SURAH_QUIZ,
     "arabic-match": ARABIC_MATCH, "islamic-knowledge": ISLAMIC_KNOWLEDGE}


def _require_enabled() -> None:
    if not islamic_learning_store.settings().get("enabled", True):
        raise HTTPException(403, detail="Islamic Learning is disabled.")


# ------------------------------------------------------------------
# Health / Hub
# ------------------------------------------------------------------

@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "healthy", "service": "islamic_learning", "version": "1.0.0",
            "enabled": islamic_learning_store.settings().get("enabled", True)}


@router.get("/hub")
async def hub() -> dict[str, Any]:
    _require_enabled()
    cats = islamic_learning_store.read().get("categories", [])
    return {"status": "ok", "categories": cats,
            "total_questions": sum(c.get("question_count", 0) for c in cats)}


@router.get("/categories")
async def categories() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "categories": islamic_learning_store.read().get("categories", [])}


# ------------------------------------------------------------------
# Quiz framework — dispatch by quiz_type
# ------------------------------------------------------------------

@router.get("/quiz/{quiz_type}")
async def quiz(quiz_type: str) -> dict[str, Any]:
    _require_enabled()
    data = C.get(quiz_type)
    if data is None:
        raise HTTPException(404, detail=f"Quiz {quiz_type} not found.")
    return {"status": "ok", "quiz_type": quiz_type, "questions": data}


@router.post("/quiz/{quiz_type}/answer")
async def quiz_answer(quiz_type: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_enabled()
    questions = C.get(quiz_type)
    if questions is None:
        raise HTTPException(404, detail=f"Quiz {quiz_type} not found.")

    qid = str(payload.get("question_id") or "").strip()
    idx = int(payload.get("answer_index", -1))

    if qid:
        for q in questions:
            if q.get("id") == qid:
                correct = idx == q.get("correct_index", -1)
                islamic_learning_store.record_quiz_result(correct, total_this_session=1)
                return {"status": "ok", "correct": correct, "question": q,
                        "quiz_stats": islamic_learning_store.get_quiz_stats()}
    else:
        qi = int(payload.get("question_index", 0))
        if 0 <= qi < len(questions):
            q = questions[qi]
            correct = idx == q.get("correct_index", -1)
            islamic_learning_store.record_quiz_result(correct, total_this_session=1)
            return {"status": "ok", "correct": correct, "question": q,
                    "quiz_stats": islamic_learning_store.get_quiz_stats()}

    raise HTTPException(422, detail="question_id or question_index required")


# ------------------------------------------------------------------
# Dua Challenge
# ------------------------------------------------------------------

@router.get("/dua-challenge")
async def dua_challenge() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "category": "Dua Challenge", "questions": DUAS}


@router.get("/dua-challenge/{dua_id}")
async def dua_detail(dua_id: str) -> dict[str, Any]:
    _require_enabled()
    for d in DUAS:
        if d.get("id") == dua_id:
            return {"status": "ok", "dua": d}
    raise HTTPException(404, detail=f"Dua {dua_id} not found.")


# ------------------------------------------------------------------
# 99 Names
# ------------------------------------------------------------------

@router.get("/names-99")
async def names_99() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "names": NAMES_99}


@router.get("/names-99/{name_id}")
async def name_detail(name_id: str) -> dict[str, Any]:
    _require_enabled()
    for n in NAMES_99:
        if n.get("id") == name_id:
            return {"status": "ok", "name": n}
    raise HTTPException(404, detail=f"Name {name_id} not found.")


# ------------------------------------------------------------------
# Surah Quiz
# ------------------------------------------------------------------

@router.get("/surah-quiz")
async def surah_quiz() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "questions": SURAH_QUIZ}


@router.get("/surah-quiz/{question_id}")
async def surah_question_detail(question_id: str) -> dict[str, Any]:
    _require_enabled()
    for q in SURAH_QUIZ:
        if q.get("id") == question_id:
            return {"status": "ok", "question": q}
    raise HTTPException(404, detail=f"Question {question_id} not found.")


# ------------------------------------------------------------------
# Arabic Match
# ------------------------------------------------------------------

@router.get("/arabic-match")
async def arabic_match() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "pairs": ARABIC_MATCH}


@router.get("/arabic-match/{pair_id}")
async def arabic_match_detail(pair_id: str) -> dict[str, Any]:
    _require_enabled()
    for p in ARABIC_MATCH:
        if p.get("id") == pair_id:
            return {"status": "ok", "pair": p}
    raise HTTPException(404, detail=f"Pair {pair_id} not found.")


# ------------------------------------------------------------------
# Islamic Knowledge
# ------------------------------------------------------------------

@router.get("/islamic-knowledge")
async def islamic_knowledge() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "questions": ISLAMIC_KNOWLEDGE}


@router.get("/islamic-knowledge/{question_id}")
async def islamic_knowledge_detail(question_id: str) -> dict[str, Any]:
    _require_enabled()
    for q in ISLAMIC_KNOWLEDGE:
        if q.get("id") == question_id:
            return {"status": "ok", "question": q}
    raise HTTPException(404, detail=f"Question {question_id} not found.")


# ------------------------------------------------------------------
# Family Quiz (combines surah + islamic knowledge)
# ------------------------------------------------------------------

@router.get("/family-quiz")
async def family_quiz() -> dict[str, Any]:
    _require_enabled()
    questions = SURAH_QUIZ + ISLAMIC_KNOWLEDGE
    return {"status": "ok", "questions": questions,
            "note": "Family Quiz combines Surah Quiz and Islamic Knowledge."}


# ------------------------------------------------------------------
# Kids Mode
# ------------------------------------------------------------------

@router.get("/kids-mode")
async def kids_mode() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "data": KIDS_DATA}


# ------------------------------------------------------------------
# Voice Quiz (where TTS available)
# ------------------------------------------------------------------

@router.get("/voice-quiz")
async def voice_quiz() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "available": islamic_learning_store.settings().get("voice_quiz", False),
            "questions": DUAS[:5],
            "note": "Voice Quiz uses device TTS to read questions aloud."}


# ------------------------------------------------------------------
# Quiz stats / mastery
# ------------------------------------------------------------------

@router.get("/quiz-stats")
async def quiz_stats() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "stats": islamic_learning_store.get_quiz_stats()}


@router.post("/mastered/{question_id}")
async def mark_mastered(question_id: str) -> dict[str, Any]:
    _require_enabled()
    result = islamic_learning_store.add_mastered_question(question_id)
    return result


@router.get("/mastered")
async def mastered_list() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "mastered": islamic_learning_store.read().get("mastered_questions", [])}


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

@router.patch("/settings")
async def update_settings(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_enabled()
    return {"status": "updated", "settings": islamic_learning_store.update_settings(payload)}


# ------------------------------------------------------------------
# Child profiles (Kids Mode)
# ------------------------------------------------------------------

@router.post("/child-profiles")
async def add_child(profile: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_enabled()
    return islamic_learning_store.add_child_profile(profile)


@router.get("/child-profiles")
async def child_profiles() -> dict[str, Any]:
    _require_enabled()
    return {"status": "ok", "profiles": islamic_learning_store.list_child_profiles()}


@router.delete("/child-profiles/{child_id}")
async def delete_child(child_id: str) -> dict[str, Any]:
    _require_enabled()
    return islamic_learning_store.delete_child_profile(child_id)
