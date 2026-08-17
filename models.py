from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SetEntry(BaseModel):
    weight_kg: float = Field(ge=0)
    reps: int = Field(ge=1)


class ExerciseEntry(BaseModel):
    name: str = Field(min_length=1)
    sets: list[SetEntry] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split()).capitalize()


class WorkoutInput(BaseModel):
    exercises: list[ExerciseEntry] = Field(min_length=1)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    body_weight_kg: float | None = Field(default=None, ge=0)
    performed_at: datetime = Field(default_factory=datetime.now)


class ExerciseSnapshot(BaseModel):
    name: str
    total_volume_kg: float
    sets: list[SetEntry]
    performed_at: datetime
