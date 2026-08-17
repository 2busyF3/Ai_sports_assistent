from __future__ import annotations

from analytics.fatigue import recovery_risks
from analytics.progression import volume_change_percent
from analytics.volume import format_sets
from database.sqlite import SQLiteRepository
from graph.state import FitnessState
from llm.extractor import extract_workout


def extract_node(state: FitnessState) -> dict:
    """Use already structured interactive input, or extract it from raw text."""
    if "workout" in state:
        return {}
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
        recommendation = "keep the current weight and rebuild volume in the next workout."
    elif changes and all(change >= 0 for change in changes):
        recommendation = "add one rep to one set or 2.5 kg if your technique is solid."
    else:
        recommendation = "repeat the current load and prioritize technique and how you feel."
    return {"recommendation": recommendation}


def response_node(state: FitnessState) -> dict:
    workout = state["workout"]
    lines: list[str] = []
    for exercise in workout.exercises:
        lines.append(f"{exercise.name}: current {format_sets(exercise)}")
        previous = state["previous"].get(exercise.name)
        if previous:
            old_sets = ", ".join(f"{item.weight_kg:g}x{item.reps}" for item in previous.sets)
            lines.append(f"previous workout {old_sets}")
            change = state["volume_changes"][exercise.name]
            lines.append(f"volume {'increased' if change >= 0 else 'decreased'} by {abs(change):.0f}%")
        else:
            lines.append("first record: this is the baseline for your next comparison.")
    if state["risks"]:
        lines.extend(state["risks"])
    recommendation = state["recommendation"]
    if state["risks"]:
        recommendation = "do not increase working weight; repeat this workout no earlier than 72 hours from now."
    lines.append(f"Recommendation: {recommendation}")
    return {"response": "\n".join(lines)}
