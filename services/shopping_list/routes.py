from __future__ import annotations

from fastapi import APIRouter, Body, Path

from services.shopping_list.store import shopping_list_store

router = APIRouter(
    prefix="/api/shopping-list",
    tags=["Shopping List"],
)


@router.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "shopping_list",
    }


@router.get("/lists")
async def list_names() -> dict:
    """Return available list names (e.g., shopping, to_do, reminders)."""
    return {
        "status": "ok",
        "lists": shopping_list_store.list_names(),
    }


@router.get("/{list_name}/items")
async def get_list(
    list_name: str = Path(..., description="List name, e.g. 'shopping'"),
) -> dict:
    items = shopping_list_store.list_items(list_name)
    return {
        "status": "ok",
        "list": list_name,
        "count": len(items),
        "items": items,
    }


@router.post("/{list_name}/items")
async def add_item(
    list_name: str = Path(..., description="List name, e.g. 'shopping'"),
    payload: dict = Body(..., description='{"text": "milk"}'),
) -> dict:
    text = str(payload.get("text", "")).strip()
    if not text:
        return {"status": "error", "message": "Item text is required"}
    item = shopping_list_store.add_item(text, list_name)
    return {
        "status": "added",
        "list": list_name,
        "item": item,
    }


@router.delete("/{list_name}/items/{item_id}")
async def delete_item(
    list_name: str = Path(...),
    item_id: int = Path(...),
) -> dict:
    removed = shopping_list_store.remove_item(item_id, list_name)
    return {
        "status": "deleted" if removed else "not_found",
        "list": list_name,
        "item_id": item_id,
    }


@router.patch("/{list_name}/items/{item_id}/toggle")
async def toggle_item(
    list_name: str = Path(...),
    item_id: int = Path(...),
) -> dict:
    item = shopping_list_store.toggle_item(item_id, list_name)
    return {
        "status": "toggled" if item else "not_found",
        "list": list_name,
        "item": item,
    }


@router.delete("/{list_name}/items/clear")
async def clear_list(
    list_name: str = Path(...),
) -> dict:
    count = shopping_list_store.clear_list(list_name)
    return {
        "status": "cleared",
        "list": list_name,
        "items_removed": count,
    }
