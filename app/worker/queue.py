from uuid import UUID


class TaskiqConfirmationQueue:
    """Реализация очереди подтверждения поверх TaskIQ."""

    async def enqueue(self, booking_id: UUID) -> None:
        """Ставит задачу подтверждения брони в очередь.

        Args:
            booking_id: Идентификатор брони.
        """
        from app.worker.tasks import process_booking

        await process_booking.kiq(str(booking_id))
