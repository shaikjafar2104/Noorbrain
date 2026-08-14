from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .router import NodeNotFoundError, NodeTrustError, NodeUnavailableError, PlaybackRoutingError, playback_router


router = APIRouter(prefix="/api/playback", tags=["Room Playback and Intercom"])


def _run(call):
    try:
        return call()
    except NodeNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except NodeTrustError as error:
        raise HTTPException(409, str(error)) from error
    except NodeUnavailableError as error:
        raise HTTPException(503, str(error)) from error
    except (PlaybackRoutingError, ValueError) as error:
        raise HTTPException(422, str(error)) from error


@router.get("/nodes")
def list_nodes(probe: bool = Query(default=False)) -> dict[str, Any]:
    nodes = playback_router.list_nodes(probe=probe)
    return {"status": "ok", "count": len(nodes), "nodes": nodes}


@router.post("/nodes", status_code=201)
def create_node(payload: dict = Body(...)) -> dict[str, Any]:
    return {"status": "created", "node": _run(lambda: playback_router.create_node(payload))}


@router.put("/nodes/{node_id}")
def update_node(node_id: str, payload: dict = Body(...)) -> dict[str, Any]:
    return {"status": "updated", "node": _run(lambda: playback_router.update_node(node_id, payload))}


@router.delete("/nodes/{node_id}")
def delete_node(node_id: str) -> dict[str, Any]:
    return _run(lambda: playback_router.delete_node(node_id))


@router.get("/nodes/{node_id}/health")
def node_health(node_id: str) -> dict[str, Any]:
    return _run(lambda: playback_router.health(node_id))


@router.post("/play")
def play(payload: dict = Body(...)) -> dict[str, Any]:
    return _run(lambda: playback_router.play(payload))


@router.post("/stop/{node_id}")
def stop(node_id: str) -> dict[str, Any]:
    return _run(lambda: playback_router.stop(node_id))


@router.post("/listen/start/{node_id}")
def start_listen(node_id: str) -> dict[str, Any]:
    return _run(lambda: playback_router.start_listen(node_id))


@router.post("/listen/{session_id}/chunk")
def listen_chunk(session_id: str, seconds: int = Query(default=1, ge=1, le=3)) -> dict[str, Any]:
    return _run(lambda: playback_router.listen_chunk(session_id, seconds))


@router.post("/listen/{session_id}/stop")
def stop_listen(session_id: str) -> dict[str, Any]:
    return _run(lambda: playback_router.stop_listen(session_id))


@router.post("/talk/{node_id}")
def talk(node_id: str, payload: dict = Body(...)) -> dict[str, Any]:
    return _run(lambda: playback_router.play({**payload, "target_node": node_id, "type": "intercom"}))
