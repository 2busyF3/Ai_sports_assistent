from __future__ import annotations

import os
import re
from models import ExerciseEntry, SetEntry, WorkoutInput

SET_PATTERN = re.compile(r"(?P<weight>\d+(?:[.,]\d+)?)\s*[x×*]\s*(?P<reps>\d+)", re.IGNORECASE)
SLEEP_PATTERN = re.compile(r"sleep\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*(?:hours?|hrs?|h)", re.IGNORECASE)
BODY_WEIGHT_PATTERN = re.compile(r"(?:body )?weight\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*kg", re.IGNORECASE)


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def extract_locally(text: str) -> WorkoutInput:
    exercises: list[ExerciseEntry] = []
    current_name: str | None = None
    current_sets: list[SetEntry] = []

    def flush() -> None:
        nonlocal current_name, current_sets
        if current_sets:
            exercises.append(ExerciseEntry(name=current_name or "Exercise", sets=current_sets))
        current_name, current_sets = None, []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        lower = line.lower()
        if SLEEP_PATTERN.search(lower) or BODY_WEIGHT_PATTERN.search(lower):
            continue
        matches = list(SET_PATTERN.finditer(line))
        if not matches:
            flush()
            continue
        prefix = line[: matches[0].start()].strip(" :,-–—")
        if prefix:
            flush()
            current_name = prefix
        current_sets.extend(SetEntry(weight_kg=_number(match["weight"]), reps=int(match["reps"])) for match in matches)
    flush()

    return WorkoutInput(
        exercises=exercises,
        sleep_hours=_number(match.group(1)) if (match := SLEEP_PATTERN.search(text)) else None,
        body_weight_kg=_number(match.group(1)) if (match := BODY_WEIGHT_PATTERN.search(text)) else None,
    )


def extract_workout(text: str) -> WorkoutInput:
    """Use OpenAI structured extraction when configured; otherwise use local parser."""
    if not os.getenv("OPENAI_API_KEY"):
        return extract_locally(text)
    from openai import OpenAI
    client = OpenAI()
    completion = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Extract workout data from the text. Do not invent exercises, sets, sleep, or body weight."},
            {"role": "user", "content": text},
        ],
        response_format=WorkoutInput,
    )
    result = completion.choices[0].message.parsed
    if result is None:
        raise ValueError("The model did not return structured workout data")
    return result
