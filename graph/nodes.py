from __future__ import annotations

from analytics.fatigue import recovery_risks
from analytics.progression import volume_change_percent
from analytics.volume import format_sets
from database.sqlite import SQLiteRepository
from graph.state import FitnessState
from llm.extractor import extract_workout


def extract_node(state: FitnessState) -> dict:
    return {"workout": extract_workout(state["raw_text"])}


def history_node(repository: SQLiteRepository):
    def node(state: FitnessState) -> dict:
        # Read history before persisting current workout, so comparison is valid.
        workout = state["workout"]
        previous = {exercise.name: repository.latest_exercise(exercise.name) for exercise in workout.exercises}
        repository.save_workout(workout)
        return {"previous": previous}
    return node


def analytics_node(state: FitnessState) -> dict:
    workout = state["workout"]
    return {"volume_changes": {
        exercise.name: volume_change_percent(exercise, state["previous"].get(exercise.name))
        for exercise in workout.exercises
    }}


def risks_node(state: FitnessState) -> dict:
    return {"risks": recovery_risks(state["workout"].sleep_hours)}


def analysis_node(state: FitnessState) -> dict:
    changes = [item for item in state["volume_changes"].values() if item is not None]
    if changes and min(changes) <= -10:
        recommendation = "сохранить текущий вес и восстановить объём на следующей тренировке."
    elif changes and all(change >= 0 for change in changes):
        recommendation = "можно прибавить 1 повтор в одном подходе или 2,5 кг при уверенной технике."
    else:
        recommendation = "повторить текущую нагрузку и ориентироваться на технику и самочувствие."
    return {"recommendation": recommendation}


def response_node(state: FitnessState) -> dict:
    workout = state["workout"]
    lines: list[str] = []
    for exercise in workout.exercises:
        lines.append(f"{exercise.name}: сейчас {format_sets(exercise)}")
        previous = state["previous"].get(exercise.name)
        if previous:
            old_sets = ", ".join(f"{item.weight_kg:g}x{item.reps}" for item in previous.sets)
            lines.append(f"прошлый раз {old_sets}")
            change = state["volume_changes"][exercise.name]
            lines.append(f"объём {'вырос' if change >= 0 else 'снизился'} на {abs(change):.0f}%")
        else:
            lines.append("первая запись: базовая точка для следующего сравнения.")
    if state["risks"]:
        lines.extend(state["risks"])
    recommendation = state["recommendation"]
    if state["risks"]:
        recommendation = "не повышать рабочий вес; повторить тренировку не раньше чем через 72 часа."
    lines.append(f"Рекомендация: {recommendation}")
    return {"response": "\n".join(lines)}
