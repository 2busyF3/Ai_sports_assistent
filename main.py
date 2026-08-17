import argparse
from database.sqlite import SQLiteRepository
from graph.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Fitness Assistant")
    parser.add_argument("--text", required=True, help="Текст с тренировкой, сном и весом")
    parser.add_argument("--db", default="fitness.db", help="Путь к SQLite базе")
    args = parser.parse_args()
    result = build_graph(SQLiteRepository(args.db)).invoke({"raw_text": args.text})
    print(result["response"])


if __name__ == "__main__":
    main()
