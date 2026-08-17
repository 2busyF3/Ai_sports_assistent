from __future__ import annotations

from analytics.fatigue import recovery_risks
from analytics.progression import volume_change_percent
from analytics.volume import format_sets
from database.sqlite import SQLiteRepository
from graph.state import FitnessState
from llm.extractor import detect_language, extract_workout


def extract_node(state: FitnessState) -> dict:
    """Use already structured interactive input, or extract it from raw text."""
    if "workout" in state:
        return {"language": state.get("language", "en")}
    raw_text = state["raw_text"]
    return {"workout": extract_workout(raw_text), "language": detect_language(raw_text)}


def history_node(repository: SQLiteRepository):
    def node(state: FitnessState) -> dict:
        # Read history before persisting current workout, so comparison is valid.
        workout = state["workout"]
        if workout.sleep_hours is None:
            latest_sleep = repository.latest_sleep_hours(workout.performed_at)
            if latest_sleep is not None:
                workout = workout.model_copy(update={"sleep_hours": latest_sleep})
        previous = {exercise.name: repository.latest_exercise(exercise.name) for exercise in workout.exercises}
        repository.save_workout(workout)
        return {"workout": workout, "previous": previous}
    return node


def analytics_node(state: FitnessState) -> dict:
    workout = state["workout"]
    return {"volume_changes": {
        exercise.name: volume_change_percent(exercise, state["previous"].get(exercise.name))
        for exercise in workout.exercises
    }}


def risks_node(state: FitnessState) -> dict:
    workout = state["workout"]
    language = state["language"]
    risks = recovery_risks(workout.sleep_hours, language)
    if workout.duration_minutes and workout.duration_minutes >= 120:
        risks.append(
            "Тренировка длилась не менее двух часов; при накоплении усталости сократите объём."
            if language == "ru" else "The session lasted at least two hours; consider reducing volume if fatigue is accumulating."
        )
    if workout.heart_rate_max and workout.heart_rate_max >= 170:
        risks.append(
            "Пиковый пульс был высоким; дайте себе достаточно времени на восстановление и следите за самочувствием."
            if language == "ru" else "Peak heart rate was high; allow adequate recovery and monitor how you feel."
        )
    return {"risks": risks}


def analysis_node(state: FitnessState) -> dict:
    changes = [item for item in state["volume_changes"].values() if item is not None]
    russian = state["language"] == "ru"
    if changes and min(changes) <= -10:
        recommendation = "сохраните текущий вес и восстановите объём на следующей тренировке." if russian else "keep the current weight and rebuild volume in the next workout."
    elif changes and all(change >= 0 for change in changes):
        recommendation = "добавьте одно повторение в одном подходе или 2,5 кг при уверенной технике." if russian else "add one rep to one set or 2.5 kg if your technique is solid."
    else:
        recommendation = "повторите текущую нагрузку и ориентируйтесь на технику и самочувствие." if russian else "repeat the current load and prioritize technique and how you feel."
    return {"recommendation": recommendation}


def response_node(state: FitnessState) -> dict:
    workout = state["workout"]
    russian = state["language"] == "ru"
    lines: list[str] = []
    for exercise in workout.exercises:
        lines.append(f"{exercise.name}: {'сейчас' if russian else 'current'} {format_sets(exercise)}")
        previous = state["previous"].get(exercise.name)
        if previous:
            old_sets = ", ".join(f"{item.weight_kg:g}x{item.reps}" for item in previous.sets)
            lines.append(f"{'прошлый раз' if russian else 'previous workout'} {old_sets}")
            change = state["volume_changes"][exercise.name]
            if russian:
                lines.append(f"объём {'вырос' if change >= 0 else 'снизился'} на {abs(change):.0f}%")
            else:
                lines.append(f"volume {'increased' if change >= 0 else 'decreased'} by {abs(change):.0f}%")
        else:
            lines.append("первая запись: это базовая точка для следующего сравнения." if russian else "first record: this is the baseline for your next comparison.")
    if state["risks"]:
        lines.extend(state["risks"])
    recommendation = state["recommendation"]
    if state["risks"]:
        recommendation = "не повышайте рабочий вес; повторите тренировку не раньше чем через 72 часа." if russian else "do not increase working weight; repeat this workout no earlier than 72 hours from now."
    lines.append(f"{'Рекомендация' if russian else 'Recommendation'}: {recommendation}")
    return {"response": "\n".join(lines)}
