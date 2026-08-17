import argparse

from database.sqlite import SQLiteRepository
from graph.graph import build_graph
from models import ExerciseEntry, SetEntry, WorkoutInput


def _required_number(label: str, input_fn=input) -> float:
    while True:
        value = input_fn(label).strip().replace(",", ".")
        try:
            number = float(value)
            if number > 0:
                return number
        except ValueError:
            pass
        print("Enter a number greater than zero.")


def _optional_number(label: str, input_fn=input) -> float | None:
    while True:
        value = input_fn(label).strip().replace(",", ".")
        if not value:
            return None
        try:
            number = float(value)
            if number >= 0:
                return number
        except ValueError:
            pass
        print("Enter a non-negative number, or press Enter to skip.")


def _required_integer(label: str, input_fn=input) -> int:
    while True:
        value = input_fn(label).strip()
        try:
            number = int(value)
            if number > 0:
                return number
        except ValueError:
            pass
        print("Enter a whole number greater than zero.")


def collect_workout(input_fn=input) -> WorkoutInput:
    """Collect structured workout data without requiring multiline shell input."""
    print("Enter each exercise. Leave the exercise name blank when you are finished.")
    exercises: list[ExerciseEntry] = []
    while True:
        name = input_fn("Exercise name: ").strip()
        if not name:
            break
        weight = _required_number("Weight (kg): ", input_fn)
        reps = _required_integer("Reps per set: ", input_fn)
        set_count = _required_integer("Number of sets: ", input_fn)
        exercises.append(ExerciseEntry(
            name=name,
            sets=[SetEntry(weight_kg=weight, reps=reps) for _ in range(set_count)],
        ))
    if not exercises:
        raise ValueError("At least one exercise is required.")
    sleep_hours = _optional_number("Sleep (hours, optional): ", input_fn)
    body_weight_kg = _optional_number("Body weight (kg, optional): ", input_fn)
    return WorkoutInput(exercises=exercises, sleep_hours=sleep_hours, body_weight_kg=body_weight_kg)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Fitness Assistant")
    parser.add_argument("--text", help="Free-form workout text (optional alternative to interactive input)")
    parser.add_argument("--interactive", action="store_true", help="Start structured interactive input")
    parser.add_argument("--db", default="fitness.db", help="Path to the SQLite database")
    args = parser.parse_args()
    if args.text and args.interactive:
        parser.error("Use either --text or --interactive, not both.")
    state = {"raw_text": args.text} if args.text else {"workout": collect_workout()}
    result = build_graph(SQLiteRepository(args.db)).invoke(state)
    print(result["response"])


if __name__ == "__main__":
    main()
