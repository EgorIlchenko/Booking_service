from uuid import UUID


class BookingError(Exception):
    """Базовое исключение броней."""


class BookingNotFound(BookingError):
    """Бронь с указанным идентификатором не найдена."""

    def __init__(self, booking_id: UUID) -> None:
        """Сохраняет идентификатор ненайденной брони.

        Args:
            booking_id: Идентификатор брони.
        """
        super().__init__(f"Бронь {booking_id} не найдена")
        self.booking_id = booking_id


class BookingNotCancellable(BookingError):
    """Бронь нельзя отменить из её текущего статуса."""

    def __init__(self, booking_id: UUID) -> None:
        """Сохраняет идентификатор неотменяемой брони.

        Args:
            booking_id: Идентификатор брони.
        """
        super().__init__(f"Бронь {booking_id} нельзя отменить")
        self.booking_id = booking_id
