# AI Fitness Assistant

A LangGraph-powered workout decision-support MVP. It is not a general-purpose chatbot: it extracts workout data from plain text, stores it in SQLite, compares it with the previous session, and produces an explainable recommendation.

## Features

- Parses English workout text: exercises, sets, sleep, and body weight.
- Stores workout history in SQLite.
- Calculates training volume and volume change.
- Flags recovery risks based on sleep.
- Orchestrates the workflow as `extract → history → analytics → (analysis + risks) → response` with LangGraph.
- Uses a local parser by default; OpenAI Structured Outputs are optional.

## Installation (Windows / PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

If `py` is unavailable, install Python 3.11+ from [python.org](https://www.python.org/downloads/) and select **Add Python to PATH** during installation.

## Usage

Pass your workout in the `--text` argument. Put each set on a new line and separate exercises with a blank line. Sleep and body weight are optional.

```powershell
fitness-assistant --text "Bench press 100x8`n100x8`n100x6`n`nChest fly 20x12`n20x10`n20x9`n`nSleep 6 hours`nWeight 83 kg"
```

The first run creates `fitness.db` beside the application. Keep this file: it contains the training history used for comparisons. Provide `--db` to use a different database:

```powershell
fitness-assistant --db data\my-workouts.db --text "Squat 100x5`n100x5`n100x5`n`nSleep 8 hours"
```

Run the command again after your next workout with the same database file. The response will show the previous sets, volume change, recovery risks, and a recommendation.

If the console command is unavailable, run the entry point directly:

```powershell
.venv\Scripts\python.exe main.py --text "Bench press 100x8`n100x8`n100x6`n`nSleep 6 hours"
```

### Optional OpenAI extraction

Without an API key, the app uses the local parser and sends no workout data over the network. To handle more natural, free-form English notes, set an OpenAI API key before running the command:

```powershell
$env:OPENAI_API_KEY="your_api_key"
fitness-assistant --text "Today I performed three bench press sets: 100 kg for 8, 100 kg for 8, and 100 kg for 6. I slept six hours."
```

Set `$env:OPENAI_MODEL` to select another model; the default is `gpt-4o-mini`.

## Project layout

```text
analytics/   # volume, progression, and recovery calculations
database/    # SQLite repository
graph/       # state, nodes, and LangGraph orchestration
llm/         # OpenAI and local text extraction
```

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The test suite covers text extraction, SQLite persistence, historical comparisons, volume changes, and the LangGraph workflow.
