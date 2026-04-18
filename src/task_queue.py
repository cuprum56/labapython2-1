from __future__ import annotations

from collections.abc import Iterable, Iterator

from task_model import Task


class TaskQueueIterator:
    """
    Итератор для очереди задач
    """

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks
        self._index = 0

    def __iter__(self) -> "TaskQueueIterator":
        return self

    def __next__(self) -> Task:
        if self._index >= len(self._tasks):
            raise StopIteration
        task = self._tasks[self._index]
        self._index += 1
        return task


class TaskQueue(Iterable[Task]):
    """
    Очередь задач
    """

    def __init__(self, tasks: Iterable[Task] | None = None) -> None:
        self._tasks = list(tasks) if tasks is not None else []

    def enqueue(self, task: Task) -> None:
        self._tasks.append(task)

    def dequeue(self) -> Task:
        if not self._tasks:
            raise IndexError("Очередь пуста")
        return self._tasks.pop(0)

    def __len__(self) -> int:
        return len(self._tasks)

    def __iter__(self) -> TaskQueueIterator:
        return TaskQueueIterator(self._tasks)

    def filter_by_status(self, status: str) -> Iterator[Task]:
        """
        Ленивый фильтр задач по статусу.
        """
        for task in self:
            if task.status == status:
                yield task

    def filter_by_priority(
        self,
        *,
        min_priority: int | None = None,
        max_priority: int | None = None,
    ) -> Iterator[Task]:
        """
        Ленивый фильтр задач по диапазону приоритетов.
        """
        for task in self:
            if min_priority is not None and task.priority < min_priority:
                continue
            if max_priority is not None and task.priority > max_priority:
                continue
            yield task

    def iter_pending(self) -> Iterator[Task]:
        """
        Ленивый поток задач, готовых к выполнению.
        """
        for task in self:
            if task.is_ready_to_run:
                yield task
