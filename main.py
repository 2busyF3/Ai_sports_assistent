import argparse
from database.sqlite import SQLiteRepository
from graph.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Fitness Assistant")
    parser.add_argument("--text", required=True, help="Text containing workout, sleep, and body-weight data")
    parser.add_argument("--db", default="fitness.db", help="Path to the SQLite database")
    args = parser.parse_args()
    result = build_graph(SQLiteRepository(args.db)).invoke({"raw_text": args.text})
    print(result["response"])


if __name__ == "__main__":
    main()
