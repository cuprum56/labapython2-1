from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from task_model import Task


class TaskExecutorError(RuntimeError):
    """Базовая ошибка асинхронного исполнителя"""


class HandlerNotFoundError(TaskExecutorError):
    """Для задачи не найден обработчик"""


@dataclass(slots=True)
class LogEntry:
    """Логирование"""

    level: str
    message: str
    task_id: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(slots=True)
class TaskExecutionResult:
    """Результат обработки задачи"""

    task_id: str
    handler_name: str
    success: bool
    details: str


@runtime_checkable
class TaskHandler(Protocol):
    """Контракт обработчика задачи"""

    name: str

    def can_handle(self, task: Task) -> bool:
        """Проверка обработчика"""

    async def handle(self, task: Task) -> str:
        """Асинхронная обработка задачи"""


@runtime_checkable
class ExecutionLoggerProtocol(Protocol):
    """Контракт централизованного логирования"""

    def info(self, task_id: str, message: str) -> None:
        """Записать информационное сообщение"""

    def error(self, task_id: str, message: str) -> None:
        """Записать сообщение об ошибке"""


class ExecutionLogger:
    """Логирование"""

    def __init__(self, filepath: str = "task_executor.log") -> None:
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, level: str, task_id: str, message: str) -> None:
        entry = LogEntry(level=level, message=message, task_id=task_id)
        line = (
            f"{entry.created_at.isoformat()} "
            f"[{entry.level}] "
            f"task_id={entry.task_id} "
            f"{entry.message}\n"
        )
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(line)

    def info(self, task_id: str, message: str) -> None:
        self._write("INFO", task_id, message)

    def error(self, task_id: str, message: str) -> None:
        self._write("ERROR", task_id, message)


class AsyncTaskQueue:
    """Асинхронная очередь задач"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Task] = asyncio.Queue()

    async def put(self, task: Task) -> None:
        task.set_status("queued")
        await self._queue.put(task)

    async def put_many(self, tasks: Iterable[Task]) -> None:
        for task in tasks:
            await self.put(task)

    async def get(self) -> Task:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def qsize(self) -> int:
        return self._queue.qsize()


class TaskExecutionContext:
    """Контекстный менеджер обработки задачи"""

    def __init__(self, task: Task, logger: ExecutionLoggerProtocol) -> None:
        self._task = task
        self._logger = logger

    async def __aenter__(self) -> Task:
        self._task.set_status("in_progress")
        self._logger.info(self._task.task_id, "Начало обработки задачи")
        return self._task

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            if self._task.status == "in_progress":
                self._task.set_status("done")
            self._logger.info(self._task.task_id, "Задача обработана успешно")
            return False

        self._task.set_status("failed")
        self._logger.error(self._task.task_id, f"Ошибка обработки: {exc}")
        return False


class AsyncTaskExecutor:
    """Асинхронный исполнитель задач"""

    def __init__(
        self,
        handlers: Iterable[TaskHandler] | None = None,
        logger: ExecutionLoggerProtocol | None = None,
    ) -> None:
        self._handlers = []
        self.queue = AsyncTaskQueue()
        self.logger = logger or ExecutionLogger()

        if handlers is not None:
            for handler in handlers:
                self.register_handler(handler)

    def register_handler(self, handler: TaskHandler) -> None:
        if not isinstance(handler, TaskHandler):
            raise TypeError("Обработчик не реализует контракт TaskHandler")
        self._handlers.append(handler)

    async def submit(self, task: Task) -> None:
        await self.queue.put(task)

    async def submit_many(self, tasks: Iterable[Task]) -> None:
        await self.queue.put_many(tasks)

    def _resolve_handler(self, task: Task) -> TaskHandler:
        for handler in self._handlers:
            if handler.can_handle(task):
                return handler
        raise HandlerNotFoundError(
            f"Для задачи {task.task_id} не найден подходящий обработчик"
        )

    async def run_once(self) -> TaskExecutionResult:
        task = await self.queue.get()
        handler_name = "unresolved"

        try:
            handler = self._resolve_handler(task)
            handler_name = handler.name
            async with TaskExecutionContext(task, self.logger) as active_task:
                details = await handler.handle(active_task)
            return TaskExecutionResult(
                task_id=task.task_id,
                handler_name=handler_name,
                success=True,
                details=details,
            )
        except (TaskExecutorError, Exception) as exc:
            task.set_status("failed")
            self.logger.error(task.task_id, str(exc))
            return TaskExecutionResult(
                task_id=task.task_id,
                handler_name=handler_name,
                success=False,
                details=str(exc),
            )
        finally:
            self.queue.task_done()

    async def run_until_empty(self) -> list[TaskExecutionResult]:
        results: = []
        while self.queue.qsize() > 0:
            results.append(await self.run_once())
        return results
