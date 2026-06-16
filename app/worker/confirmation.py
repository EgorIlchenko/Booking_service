import random


class RandomConfirmationGateway:
    """Подтверждает бронь, имитируя случайный сбой внешнего сервиса."""

    def __init__(self, failure_rate: float) -> None:
        """Сохраняет вероятность сбоя.

        Args:
            failure_rate: Вероятность сбоя подтверждения, от 0 до 1.
        """
        self._failure_rate = failure_rate

    def confirm(self) -> bool:
        """Пытается подтвердить бронь.

        Returns:
            True при успехе, False при сбое (с вероятностью failure_rate).
        """
        return random.random() >= self._failure_rate
