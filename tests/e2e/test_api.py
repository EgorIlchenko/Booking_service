from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.domain.models import BookingStatus

from tests.e2e.conftest import ApiContext, make_api_context, seed_booking
from tests.fakes import SpyConfirmationQueue


def valid_payload(**overrides: str) -> dict[str, str]:
    """Возвращает корректное тело создания брони.

    Args:
        **overrides: Поля для подмены.

    Returns:
        Словарь тела запроса.
    """
    payload = {
        "name": "Иван",
        "datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "service_type": "haircut",
    }
    payload.update(overrides)
    return payload


async def test_health_returns_ok(api: ApiContext) -> None:
    response = await api.client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_returns_201_pending_and_enqueues(api: ApiContext) -> None:
    response = await api.client.post("/api/v1/bookings", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["service_type"] == "haircut"
    assert UUID(body["id"]).version == 7

    assert api.queue.enqueued == [UUID(body["id"])]


@pytest.mark.parametrize(
    "payload",
    [
        valid_payload(datetime=(datetime.now(UTC) - timedelta(days=1)).isoformat()),
        valid_payload(service_type="dentist"),
        valid_payload(name=""),
        {"name": "Иван", "service_type": "haircut"},
    ],
)
async def test_create_invalid_payload_returns_422(api: ApiContext, payload: dict[str, str]) -> None:
    response = await api.client.post("/api/v1/bookings", json=payload)

    assert response.status_code == 422


async def test_get_returns_created_booking(api: ApiContext) -> None:
    created = (await api.client.post("/api/v1/bookings", json=valid_payload())).json()

    response = await api.client.get(f"/api/v1/bookings/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_unknown_returns_404(api: ApiContext) -> None:
    response = await api.client.get(f"/api/v1/bookings/{uuid4()}")

    assert response.status_code == 404
    assert "detail" in response.json()


async def test_list_filters_by_status(api: ApiContext) -> None:
    await api.client.post("/api/v1/bookings", json=valid_payload())
    await api.client.post("/api/v1/bookings", json=valid_payload())
    confirmed_id = await seed_booking(api.container, status=BookingStatus.CONFIRMED)

    pending = (await api.client.get("/api/v1/bookings", params={"status": "pending"})).json()
    assert pending["total"] == 2
    assert all(item["status"] == "pending" for item in pending["items"])

    confirmed = (await api.client.get("/api/v1/bookings", params={"status": "confirmed"})).json()
    assert confirmed["total"] == 1
    assert confirmed["items"][0]["id"] == str(confirmed_id)


async def test_list_pagination_reports_total(api: ApiContext) -> None:
    for _ in range(3):
        await api.client.post("/api/v1/bookings", json=valid_payload())

    page = (await api.client.get("/api/v1/bookings", params={"limit": 2, "offset": 0})).json()

    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert page["limit"] == 2
    assert page["offset"] == 0


async def test_list_rejects_limit_over_max(api: ApiContext) -> None:
    response = await api.client.get("/api/v1/bookings", params={"limit": 101})

    assert response.status_code == 422


async def test_delete_pending_returns_204(api: ApiContext) -> None:
    created = (await api.client.post("/api/v1/bookings", json=valid_payload())).json()

    response = await api.client.delete(f"/api/v1/bookings/{created['id']}")

    assert response.status_code == 204
    assert (await api.client.get(f"/api/v1/bookings/{created['id']}")).status_code == 404


async def test_delete_confirmed_returns_409(api: ApiContext) -> None:
    confirmed_id = await seed_booking(api.container, status=BookingStatus.CONFIRMED)

    response = await api.client.delete(f"/api/v1/bookings/{confirmed_id}")

    assert response.status_code == 409
    assert "detail" in response.json()


async def test_delete_unknown_returns_404(api: ApiContext) -> None:
    response = await api.client.delete(f"/api/v1/bookings/{uuid4()}")

    assert response.status_code == 404


async def test_rate_limit_returns_429_after_limit() -> None:
    async with make_api_context(rate_times=2) as api:
        first = await api.client.post("/api/v1/bookings", json=valid_payload())
        second = await api.client.post("/api/v1/bookings", json=valid_payload())
        third = await api.client.post("/api/v1/bookings", json=valid_payload())

    assert [first.status_code, second.status_code, third.status_code] == [201, 201, 429]
    assert third.json() == {"detail": "Слишком много запросов"}


async def test_request_id_present_in_response(api: ApiContext) -> None:
    response = await api.client.get("/health")

    assert "x-request-id" in response.headers


async def test_request_id_echoed_when_provided(api: ApiContext) -> None:
    response = await api.client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert response.headers["x-request-id"] == "trace-123"


async def test_internal_error_returns_500() -> None:
    failing_queue = SpyConfirmationQueue(fail=True)

    async with make_api_context(queue=failing_queue) as api:
        response = await api.client.post("/api/v1/bookings", json=valid_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}
