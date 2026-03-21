from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Any, Sequence
import json
import random
import time

@dataclass(frozen=True, slots=True)
class Task:
    """
    Структура данных задачи
    """
    id: str
    payload: Any

@runtime_checkable
class TaskSource(Protocol):
    """
    Контракт для источников задач
    """
    
    def get_tasks(self) -> Sequence[Task]:
        """
        Получить список задач из источника
        """
        ...

@dataclass
class FileTaskSource:
    """
    Источник задач, загружаемых из файла
    """
    filepath: str
    
    def get_tasks(self) -> list[Task]:
        """
        Загрузить задачи из JSON-файла
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tasks = []
        for item in data:
            task = Task(
                id = item['id'],
                payload = item.get('payload')
            )
            tasks.append(task)
        
        return tasks

@dataclass
class GeneratorTaskSource:
    """
    Источник задач, генерируемых программно
    """
    count: int
    prefix: str = "generated"
    
    def get_tasks(self) -> list[Task]:
        """
        Сгенерировать задачи программно
        """
        tasks = []
        for i in range(1, self.count + 1):
            task = Task(
                id=f"{self.prefix}_{i}",
                payload={
                    "value": random.randint(1, 100),
                    "timestamp": time.time(),
                    "index": i
                }
            )
            tasks.append(task)
        return tasks

@dataclass
class APITaskSource:
    """
    Источник задач, получаемых из API-заглушки
    """
    endpoint: str
    mock_data: dict[str, Any] = field(default_factory=dict)
    
    def get_tasks(self) -> list[Task]:
        """
        Получить задачи из API-заглушки
        """
        tasks = []
        for item in self.mock_data.get("tasks", []):
            task = Task(
                id=item['id'],
                payload=item.get('payload')
            )
            tasks.append(task)
        
        return tasks

def validate_task_source(obj: Any) -> bool:
    """
    Проверить, реализует ли объект контракт TaskSource
    """
    return isinstance(obj, TaskSource)


def process_task_sources(sources: list[Any]) -> list[Task]:
    """
    Обработать все источники задач и собрать все задачи.
    """
    all_tasks = []
    
    for source in sources:
        if not validate_task_source(source):
            raise TypeError(
                f"Источник {source!r} не реализует контракт TaskSource. "
            )
        tasks = source.get_tasks()
        all_tasks.extend(tasks)
        print(f"Получено {len(tasks)} задач от источника {source.__class__.__name__}")
    
    return all_tasks

def main() -> None:
    """
    Демонстрация работы системы приёма задач.
    """
    sample_tasks_file = "sample_tasks.json"
    
    file_source = FileTaskSource(filepath=sample_tasks_file)
    
    generator_source = GeneratorTaskSource(count=3, prefix="gen")
    
    api_source = APITaskSource(
        endpoint="https://api.example.com/tasks",
        mock_data={
            "tasks": [
                {"id": "api_task_1", "payload": {"source": "api", "status": "pending"}},
                {"id": "api_task_2", "payload": {"source": "api", "status": "processing"}},
            ]
        }
    ) 
    sources = [file_source, generator_source, api_source]
    
    for source in sources:
        is_valid = validate_task_source(source)
        print(f"{source.__class__.__name__}: контракт соблюдён = {is_valid}")

    try:
        all_tasks = process_task_sources(sources)
        
        print(f"\nВсего получено задач: {len(all_tasks)}")
        print("\nСписок задач:")
        for task in all_tasks:
            print(f"  - {task.id}: {task.payload}")
            
    except TypeError as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
