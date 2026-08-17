from datetime import datetime, timedelta

from database.sqlite import SQLiteRepository
from graph.graph import build_graph
from llm.extractor import extract_locally
from main import collect_workout_note, initialize_or_update_profile


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


def test_russian_free_form_parser_and_session_metrics() -> None:
    workout = extract_locally("""Скручивания на пресс
15 без веса
5кг на 15
10кг на 15

Приседания в Смите, до 90 градусов
25х12
65х8
95х8

Поднимания на носки
60кг на 15 2 подхода
8х14 на 3

Тренировка длилась 1:30
Средний пульс 126 диапазон от 82 до 171""")
    assert [exercise.name for exercise in workout.exercises] == [
        "Скручивания на пресс", "Приседания в смите, до 90 градусов", "Поднимания на носки",
    ]
    assert [(item.weight_kg, item.reps) for item in workout.exercises[0].sets] == [(0, 15), (5, 15), (10, 15)]
    assert len(workout.exercises[2].sets) == 5
    assert workout.duration_minutes == 90
    assert (workout.average_heart_rate, workout.heart_rate_min, workout.heart_rate_max) == (126, 82, 171)


def test_note_input_and_weekly_profile(tmp_path) -> None:
    note_answers = iter(["Bench press 100x8", "100x8", "END"])
    assert collect_workout_note(lambda _: next(note_answers)) == "Bench press 100x8\n100x8"
    repository = SQLiteRepository(tmp_path / "profile.db")
    first_setup = iter(["180", "83"])
    initialize_or_update_profile(repository, lambda _: next(first_setup))
    profile = repository.get_profile()
    assert profile and (profile.height_cm, profile.body_weight_kg) == (180, 83)
    assert not repository.weight_update_due(profile.weight_updated_at + timedelta(days=6))
    repository.save_profile(180, 83, datetime.now() - timedelta(days=8))
    update = iter(["82"])
    initialize_or_update_profile(repository, lambda _: next(update))
    assert repository.get_profile().body_weight_kg == 82


def test_graph_persists_and_compares(tmp_path) -> None:
    graph = build_graph(SQLiteRepository(tmp_path / "test.db"))
    first = graph.invoke({"raw_text": TEXT})
    second = graph.invoke({"raw_text": TEXT})
    assert "first record" in first["response"]
    assert "previous workout 100x8, 100x8, 100x6" in second["response"]
    assert "Sleep is below the target range" in second["response"]
