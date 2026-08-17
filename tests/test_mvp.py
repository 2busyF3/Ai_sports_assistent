from database.sqlite import SQLiteRepository
from graph.graph import build_graph
from llm.extractor import extract_locally


TEXT = """Жим лёжа 100x8
100x8
100x6

Разводка 20x12
20x10
20x9

Сон 6 часов
Вес 83 кг"""


def test_local_extractor() -> None:
    workout = extract_locally(TEXT)
    assert len(workout.exercises) == 2
    assert workout.exercises[0].name == "Жим лёжа"
    assert workout.exercises[0].sets[-1].reps == 6
    assert workout.sleep_hours == 6


def test_graph_persists_and_compares(tmp_path) -> None:
    graph = build_graph(SQLiteRepository(tmp_path / "test.db"))
    first = graph.invoke({"raw_text": TEXT})
    second = graph.invoke({"raw_text": TEXT})
    assert "первая запись" in first["response"]
    assert "прошлый раз 100x8, 100x8, 100x6" in second["response"]
    assert "Сон ниже целевого уровня" in second["response"]
