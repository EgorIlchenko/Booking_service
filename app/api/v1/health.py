from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Проверка живости сервиса.

    Returns:
        Признак доступности сервиса.
    """
    return {"status": "ok"}
