from __future__ import annotations

from datetime import datetime, timezone

import pytest

from task_model import (
    InvalidDescriptionError,
    InvalidPriorityError,
    InvalidStatusError,
    InvalidTaskIdError,
    Task,
    TaskValidationError,
)


def test_task_valid_creation() -> None:
    task = Task(task_id="T-1", description="Подготовить отчёт", priority=5)

    assert task.task_id == "T-1"
    assert task.description == "Подготовить отчёт"
    assert task.priority == 5
    assert task.status == "new"
    assert isinstance(task.created_at, datetime)
    assert task.created_at.tzinfo == timezone.utc


def test_task_id_validation() -> None:
    with pytest.raises(InvalidTaskIdError):
        Task(task_id="", description="ok desc", priority=2)

    with pytest.raises(InvalidTaskIdError):
        Task(task_id="   ", description="ok desc", priority=2)


def test_description_validation() -> None:
    with pytest.raises(InvalidDescriptionError):
        Task(task_id="T-2", description="ab", priority=2)


@pytest.mark.parametrize("priority", [0, -1, 11, 100])
def test_priority_validation(priority: int) -> None:
    with pytest.raises(InvalidPriorityError):
        Task(task_id="T-3", description="Нормальное описание", priority=priority)


def test_status_validation_on_create_and_update() -> None:
    with pytest.raises(InvalidStatusError):
        Task(task_id="T-4", description="Описание", priority=1, status="draft")

    task = Task(task_id="T-5", description="Описание", priority=1)
    with pytest.raises(InvalidStatusError):
        task.set_status("unknown")


def test_created_at_property_validation() -> None:
    task = Task(task_id="T-6", description="Описание", priority=4)
    with pytest.raises(TaskValidationError):
        task.created_at = "2026-01-01"  # type: ignore[assignment]


def test_is_ready_to_run_property() -> None:
    task = Task(task_id="T-7", description="Описание", priority=2, status="queued")
    assert task.is_ready_to_run is True

    task.set_status("in_progress")
    assert task.is_ready_to_run is False


def test_data_descriptor_enforces_validation_on_attribute_assignment() -> None:
    task = Task(task_id="T-8", description="Описание", priority=2)

    with pytest.raises(InvalidPriorityError):
        task.priority = 999

    task.priority = 8
    assert task.priority == 8


def test_non_data_descriptor_can_be_shadowed_by_instance_attribute() -> None:
    task = Task(task_id="T-9", description="Описание", priority=3)

    initial_label = task.public_label
    assert initial_label == "Task<T-9>:new"

    task.public_label = "Локальная метка"
    assert task.public_label == "Локальная метка"


def test_whitespace_is_trimmed_by_descriptors() -> None:
    task = Task(task_id="  T-10  ", description="   Сборка проекта   ", priority=6)

    assert task.task_id == "T-10"
    assert task.description == "Сборка проекта"
