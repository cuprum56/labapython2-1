import json
import os
import tempfile

import pytest

from task_sources import (
    APITaskSource,
    FileTaskSource,
    GeneratorTaskSource,
    Task,
    TaskSource,
    process_task_sources,
    validate_task_source,
)


def test_task_creation():
    task = Task(id="test_id", payload={"data": 123})
    assert task.id == "test_id"
    assert task.payload == {"data": 123}


def test_task_equality():
    task1 = Task(id="1", payload={"a": 1})
    task2 = Task(id="1", payload={"a": 1})
    assert task1 == task2


def test_task_immutability():
    task = Task(id="1", payload={})
    with pytest.raises(AttributeError):
        task.id = "2"


def test_file_source_implements_protocol():
    source = FileTaskSource(filepath="dummy.json")
    assert validate_task_source(source) is True


def test_generator_source_implements_protocol():
    source = GeneratorTaskSource(count=5)
    assert validate_task_source(source) is True


def test_api_source_implements_protocol():
    source = APITaskSource(endpoint="http://test.com")
    assert validate_task_source(source) is True


def test_invalid_object_not_protocol():
    assert validate_task_source({}) is False
    assert validate_task_source("string") is False
    assert validate_task_source(123) is False


def test_object_with_gettasks_is_valid():
    class MockSource:
        def get_tasks(self):
            return [Task(id="1", payload={})]
    assert validate_task_source(MockSource()) is True


def test_file_task_source_load():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump([{"id": "task_1", "payload": {"key": "value1"}}, {"id": "task_2", "payload": {"key": "value2"}}], f)
        temp_path = f.name
    try:
        source = FileTaskSource(filepath=temp_path)
        tasks = source.get_tasks()
        assert len(tasks) == 2
        assert tasks[0].id == "task_1"
    finally:
        os.remove(temp_path)


def test_file_not_found():
    source = FileTaskSource(filepath="nonexistent.json")
    with pytest.raises(FileNotFoundError):
        source.get_tasks()


def test_generator_task_source():
    source = GeneratorTaskSource(count=5, prefix="test")
    tasks = source.get_tasks()
    assert len(tasks) == 5
    assert "test_1" in [t.id for t in tasks]


def test_generator_zero_tasks():
    source = GeneratorTaskSource(count=0)
    tasks = source.get_tasks()
    assert len(tasks) == 0


def test_api_task_source():
    mock_data = {"tasks": [{"id": "api_1", "payload": {"status": "pending"}}, {"id": "api_2", "payload": {"status": "done"}}]}
    source = APITaskSource(endpoint="http://test.com", mock_data=mock_data)
    tasks = source.get_tasks()
    assert len(tasks) == 2
    assert tasks[0].id == "api_1"


def test_api_empty_mock():
    source = APITaskSource(endpoint="http://test.com", mock_data={})
    assert len(source.get_tasks()) == 0


def test_process_multiple_sources():
    sources = [GeneratorTaskSource(count=2, prefix="gen"), GeneratorTaskSource(count=3, prefix="other")]
    all_tasks = process_task_sources(sources)
    assert len(all_tasks) == 5


def test_process_empty_list():
    assert len(process_task_sources([])) == 0


def test_process_invalid_source_raises():
    with pytest.raises(TypeError):
        process_task_sources([GeneratorTaskSource(count=1), "invalid"])


def test_isinstance_with_protocol():
    sources = [FileTaskSource(filepath="test.json"), GeneratorTaskSource(count=1), APITaskSource(endpoint="test")]
    for source in sources:
        assert isinstance(source, TaskSource)
        assert hasattr(source, 'get_tasks')
        assert callable(source.get_tasks)


def test_duck_typing():
    class CustomSource:
        def get_tasks(self):
            return [Task(id="custom_1", payload={})]
    custom = CustomSource()
    assert validate_task_source(custom) is True
    tasks = process_task_sources([custom])
    assert len(tasks) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
