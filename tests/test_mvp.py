from database.sqlite import SQLiteRepository
from graph.graph import build_graph
from llm.extractor import extract_locally
from main import collect_workout


TEXT = """Bench press 100x8
100x8
100x6

Chest fly 20x12
20x10
20x9

Sleep 6 hours
Weight 83 kg"""


def test_local_extractor() -> None:
    workout = extract_locally(TEXT)
    assert len(workout.exercises) == 2
    assert workout.exercises[0].name == "Bench press"
    assert workout.exercises[0].sets[-1].reps == 6
    assert workout.sleep_hours == 6


def test_interactive_input_collects_separate_fields() -> None:
    answers = iter(["Bench press", "100", "10", "3", "", "8", "83"])
    workout = collect_workout(lambda _: next(answers))
    assert workout.exercises[0].name == "Bench press"
    assert len(workout.exercises[0].sets) == 3
    assert workout.exercises[0].sets[0].weight_kg == 100
    assert workout.exercises[0].sets[0].reps == 10
    assert workout.sleep_hours == 8
    assert workout.body_weight_kg == 83


def test_graph_persists_and_compares(tmp_path) -> None:
    graph = build_graph(SQLiteRepository(tmp_path / "test.db"))
    first = graph.invoke({"raw_text": TEXT})
    second = graph.invoke({"raw_text": TEXT})
    assert "first record" in first["response"]
    assert "previous workout 100x8, 100x8, 100x6" in second["response"]
    assert "Sleep is below the target range" in second["response"]
