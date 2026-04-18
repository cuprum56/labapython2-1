from __future__ import annotations

from collections.abc import Iterator

import pytest

from task_model import Task
from task_queue import TaskQueue


def _make_tasks() -> list[Task]:
    return [
        Task(task_id="A-1", description="Импорт данных", priority=3, status="new"),
        Task(task_id="A-2", description="Отправка письма", priority=8, status="queued"),
        Task(task_id="A-3", description="Подсчёт метрик", priority=5, status="done"),
        Task(task_id="A-4", description="Очистка кэша", priority=1, status="failed"),
    ]


def test_queue_len_enqueue_dequeue() -> None:
    queue = TaskQueue()
    assert len(queue) == 0

    task = Task(task_id="A-5", description="Новая задача", priority=7)
    queue.enqueue(task)

    assert len(queue) == 1
    assert queue.dequeue() == task
    assert len(queue) == 0


def test_dequeue_from_empty_queue_raises() -> None:
    queue = TaskQueue()
    with pytest.raises(IndexError):
        queue.dequeue()


def test_queue_iteration_is_repeatable() -> None:
    queue = TaskQueue(_make_tasks())

    first_pass_ids = [task.task_id for task in queue]
    second_pass_ids = [task.task_id for task in queue]

    assert first_pass_ids == ["A-1", "A-2", "A-3", "A-4"]
    assert second_pass_ids == first_pass_ids


def test_iterator_stop_iteration() -> None:
    queue = TaskQueue(_make_tasks()[:1])
    iterator = iter(queue)

    assert next(iterator).task_id == "A-1"
    with pytest.raises(StopIteration):
        next(iterator)


def test_filter_by_status_is_lazy_and_correct() -> None:
    queue = TaskQueue(_make_tasks())
    generator = queue.filter_by_status("queued")

    assert isinstance(generator, Iterator)
    assert [task.task_id for task in generator] == ["A-2"]


def test_filter_by_priority_range() -> None:
    queue = TaskQueue(_make_tasks())

    filtered = list(queue.filter_by_priority(min_priority=3, max_priority=6))
    assert [task.task_id for task in filtered] == ["A-1", "A-3"]


def test_iter_pending_returns_only_ready_tasks() -> None:
    queue = TaskQueue(_make_tasks())

    pending = list(queue.iter_pending())
    assert [task.task_id for task in pending] == ["A-1", "A-2"]


def test_queue_is_compatible_with_standard_python_constructs() -> None:
    queue = TaskQueue(_make_tasks())

    tasks_list = list(queue)
    total_priority = sum(task.priority for task in queue)

    assert len(tasks_list) == 4
    assert total_priority == 17


def test_filters_do_not_materialize_extra_collections() -> None:
    queue = TaskQueue(_make_tasks())

    by_status = queue.filter_by_status("done")
    by_priority = queue.filter_by_priority(min_priority=8)

    assert isinstance(by_status, Iterator)
    assert isinstance(by_priority, Iterator)
    assert [task.task_id for task in by_status] == ["A-3"]
    assert [task.task_id for task in by_priority] == ["A-2"]
