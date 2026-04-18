from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class TaskValidationError(ValueError):

class InvalidTaskIdError(TaskValidationError):

class InvalidDescriptionError(TaskValidationError):

class InvalidPriorityError(TaskValidationError):

class InvalidStatusError(TaskValidationError):


class DescriptorBase:
    """
    Базовый data-descriptor
    """

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self._name = name
        self._storage_name = f"_{name}"

    def __get__(self, instance: object | None, owner: type[Any]) -> Any:
        if instance is None:
            return self
        return getattr(instance, self._storage_name)


class TaskIdDescriptor(DescriptorBase):
    def __set__(self, instance: object, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InvalidTaskIdError("task_id должен быть непустой строкой")
        setattr(instance, self._storage_name, value.strip())


class DescriptionDescriptor(DescriptorBase):
    def __set__(self, instance: object, value: str) -> None:
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise InvalidDescriptionError(
                "description должен быть строкой длиной от 3 символов"
            )
        setattr(instance, self._storage_name, value.strip())


class PriorityDescriptor(DescriptorBase):
    def __set__(self, instance: object, value: int) -> None:
        if not isinstance(value, int) or not 1 <= value <= 10:
            raise InvalidPriorityError("priority должен быть целым числом от 1 до 10")
        setattr(instance, self._storage_name, value)


class StatusDescriptor(DescriptorBase):
    ALLOWED = {"new", "queued", "in_progress", "done", "failed"}

    def __set__(self, instance: object, value: str) -> None:
        if value not in self.ALLOWED:
            raise InvalidStatusError(
                f"status должен быть одним из: {', '.join(sorted(self.ALLOWED))}"
            )
        setattr(instance, self._storage_name, value)


class PublicLabelDescriptor:
    """
    Non-data descriptor
    """

    def __get__(self, instance: object | None, owner: type[Any]) -> str | "PublicLabelDescriptor":
        if instance is None:
            return self
        return f"Task<{instance.task_id}>:{instance.status}"


class Task:
    """
    Модель задачи
    """

    task_id = TaskIdDescriptor()
    description = DescriptionDescriptor()
    priority = PriorityDescriptor()
    status = StatusDescriptor()
    public_label = PublicLabelDescriptor()

    def __init__(
        self,
        task_id: str,
        description: str,
        priority: int,
        status: str = "new",
    ) -> None:
        self.task_id = task_id
        self.description = description
        self.priority = priority
        self.status = status
        self.created_at = datetime.now(timezone.utc)

    @property
    def created_at(self) -> datetime:
        """
        Чтение времени создания
        """
        return self._created_at

    @created_at.setter
    def created_at(self, value: datetime) -> None:
        if not isinstance(value, datetime):
            raise TaskValidationError("created_at должен быть datetime")
        self._created_at = value

    @property
    def is_ready_to_run(self) -> bool:
        """
        Задача готова к исполнению, если находится в очереди и валидна.
        """
        return self.status in {"new", "queued"} and bool(self.description)

    def set_status(self, new_status: str) -> None:
        """
        Смена статуса
        """
        self.status = new_status
