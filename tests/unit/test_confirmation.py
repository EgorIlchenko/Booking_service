import pytest
from app.worker.confirmation import RandomConfirmationGateway


@pytest.mark.parametrize(
    ("failure_rate", "roll", "expected"),
    [
        (0.0, 0.0, True),  # сбоев нет — всегда успех
        (0.15, 0.14, False),  # бросок ниже порога — сбой
        (0.15, 0.15, True),  # ровно на пороге — успех (random >= rate)
        (0.15, 0.99, True),  # бросок выше порога — успех
        (1.0, 0.999999, False),  # сбой всегда
    ],
)
async def test_confirm_respects_threshold(
    monkeypatch: pytest.MonkeyPatch,
    failure_rate: float,
    roll: float,
    expected: bool,
) -> None:
    monkeypatch.setattr("app.worker.confirmation.random.random", lambda: roll)

    assert RandomConfirmationGateway(failure_rate=failure_rate).confirm() is expected
