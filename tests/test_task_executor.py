from __future__ import annotations

import asyncio
from pathlib import Path

from task_executor import AsyncTaskExecutor, AsyncTaskQueue, ExecutionLogger
from task_model import Task


def run(coro):
    return asyncio.run(coro)


class ImportHandler:
    name = "import-handler"

    def can_handle(self, task: Task) -> bool:
        return task.task_id.startswith("IMP")

    async def handle(self, task: Task) -> str:
        await asyncio.sleep(0)
        return f"imported:{task.task_id}"


class FailingHandler:
    name = "failing-handler"

    def can_handle(self, task: Task) -> bool:
        return task.task_id.startswith("FAIL")

    async def handle(self, task: Task) -> str:
        await asyncio.sleep(0)
        raise RuntimeError("handler crashed")


def test_async_queue_put_sets_status_and_returns_same_task() -> None:
    async def scenario() -> None:
        queue = AsyncTaskQueue()
        task = Task(task_id="IMP-1", description="Импорт", priority=5)
        await queue.put(task)
        received = await queue.get()
        assert task.status == "queued"
        assert received is task
        queue.task_done()
        await queue.join()

    run(scenario())


def test_executor_processes_tasks_and_writes_success_log(tmp_path: Path) -> None:
    async def scenario() -> None:
        log_path = tmp_path / "success.log"
        executor = AsyncTaskExecutor([ImportHandler()], ExecutionLogger(str(log_path)))
        task = Task(task_id="IMP-10", description="Импорт", priority=2)
        await executor.submit(task)
        result = await executor.run_once()
        content = log_path.read_text(encoding="utf-8")
        assert result.success is True
        assert result.details == "imported:IMP-10"
        assert task.status == "done"
        assert "Начало обработки задачи" in content
        assert "Задача обработана успешно" in content

    run(scenario())


def test_executor_marks_failed_task_and_logs_error(tmp_path: Path) -> None:
    async def scenario() -> None:
        log_path = tmp_path / "failure.log"
        executor = AsyncTaskExecutor([FailingHandler()], ExecutionLogger(str(log_path)))
        task = Task(task_id="FAIL-1", description="Падающая задача", priority=3)
        result = await executor.submit(task) or await executor.run_once()
        content = log_path.read_text(encoding="utf-8")
        assert result.success is False
        assert task.status == "failed"
        assert "[ERROR]" in content
        assert "handler crashed" in content

    run(scenario())


def test_execution_logger_writes_info_and_error_lines(tmp_path: Path) -> None:
    logger = ExecutionLogger(str(tmp_path / "task_executor.log"))
    logger.info("IMP-20", "Начало обработки задачи")
    logger.error("IMP-20", "Ошибка обработки")
    content = (tmp_path / "task_executor.log").read_text(encoding="utf-8")
    assert "[INFO]" in content
    assert "[ERROR]" in content
    assert "task_id=IMP-20" in content
