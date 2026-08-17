from __future__ import annotations

import sqlite3
from pathlib import Path

from datetime import datetime, timedelta

from models import ExerciseSnapshot, UserProfile, WorkoutInput


class SQLiteRepository:
    def __init__(self, path: str | Path = "fitness.db") -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY,
                    performed_at TEXT NOT NULL,
                    sleep_hours REAL,
                    body_weight_kg REAL,
                    duration_minutes INTEGER,
                    average_heart_rate INTEGER,
                    heart_rate_min INTEGER,
                    heart_rate_max INTEGER
                );
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY,
                    workout_id INTEGER NOT NULL REFERENCES workouts(id),
                    name TEXT NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exercise_sets (
                    id INTEGER PRIMARY KEY,
                    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                    weight_kg REAL NOT NULL,
                    reps INTEGER NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name);
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    height_cm REAL NOT NULL,
                    body_weight_kg REAL NOT NULL,
                    weight_updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "workouts", "duration_minutes", "INTEGER")
            self._ensure_column(conn, "workouts", "average_heart_rate", "INTEGER")
            self._ensure_column(conn, "workouts", "heart_rate_min", "INTEGER")
            self._ensure_column(conn, "workouts", "heart_rate_max", "INTEGER")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def save_workout(self, workout: WorkoutInput) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO workouts
                (performed_at, sleep_hours, body_weight_kg, duration_minutes, average_heart_rate, heart_rate_min, heart_rate_max)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    workout.performed_at.isoformat(), workout.sleep_hours, workout.body_weight_kg,
                    workout.duration_minutes, workout.average_heart_rate,
                    workout.heart_rate_min, workout.heart_rate_max,
                ),
            )
            workout_id = cursor.lastrowid
            for exercise_position, exercise in enumerate(workout.exercises):
                cursor = conn.execute(
                    "INSERT INTO exercises (workout_id, name, position) VALUES (?, ?, ?)",
                    (workout_id, exercise.name, exercise_position),
                )
                exercise_id = cursor.lastrowid
                conn.executemany(
                    "INSERT INTO exercise_sets (exercise_id, weight_kg, reps, position) VALUES (?, ?, ?, ?)",
                    [(exercise_id, item.weight_kg, item.reps, position) for position, item in enumerate(exercise.sets)],
                )
            return int(workout_id)

    def get_profile(self) -> UserProfile | None:
        with self._connect() as conn:
            row = conn.execute("SELECT height_cm, body_weight_kg, weight_updated_at FROM user_profile WHERE id = 1").fetchone()
        if row is None:
            return None
        return UserProfile(
            height_cm=row["height_cm"], body_weight_kg=row["body_weight_kg"],
            weight_updated_at=datetime.fromisoformat(row["weight_updated_at"]),
        )

    def save_profile(self, height_cm: float, body_weight_kg: float, updated_at: datetime | None = None) -> None:
        timestamp = (updated_at or datetime.now()).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO user_profile (id, height_cm, body_weight_kg, weight_updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET height_cm = excluded.height_cm,
                    body_weight_kg = excluded.body_weight_kg, weight_updated_at = excluded.weight_updated_at""",
                (height_cm, body_weight_kg, timestamp),
            )

    def weight_update_due(self, now: datetime | None = None) -> bool:
        profile = self.get_profile()
        if profile is None:
            return True
        return (now or datetime.now()) - profile.weight_updated_at >= timedelta(days=7)

    def latest_exercise(self, name: str) -> ExerciseSnapshot | None:
        """Return the latest historical occurrence, before the just-saved current workout."""
        with self._connect() as conn:
            exercise = conn.execute(
                """
                SELECT e.id, e.name, w.performed_at
                FROM exercises e JOIN workouts w ON w.id = e.workout_id
                WHERE lower(e.name) = lower(?)
                ORDER BY w.performed_at DESC, e.id DESC LIMIT 1
                """,
                (name,),
            ).fetchone()
            if exercise is None:
                return None
            rows = conn.execute(
                "SELECT weight_kg, reps FROM exercise_sets WHERE exercise_id = ? ORDER BY position",
                (exercise["id"],),
            ).fetchall()
        from datetime import datetime
        from models import SetEntry
        sets = [SetEntry(weight_kg=row["weight_kg"], reps=row["reps"]) for row in rows]
        return ExerciseSnapshot(
            name=exercise["name"], sets=sets,
            total_volume_kg=sum(item.weight_kg * item.reps for item in sets),
            performed_at=datetime.fromisoformat(exercise["performed_at"]),
        )
