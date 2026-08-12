"""CLI interface for the Vera-Finance local RAG Q&A assistant.

Usage: python main.py
Type a question and press Enter; type 'quit' (or Ctrl+C / Ctrl+D) to exit.
"""

import time

from answer import answer_query


def main() -> None:
    print("Vera-Finance Q&A assistant (local, offline — Foundry Local)")
    print("Loading models, first question may take a bit longer...")
    print('Type "quit" to exit.\n')

    while True:
        try:
            question = input("Question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            print("Please enter a question.\n")
            continue

        start = time.perf_counter()
        print("Answer: ", end="", flush=True)
        answer_query(question, stream=True)
        elapsed = time.perf_counter() - start
        print(f"({elapsed:.1f}s)\n")

    print("Goodbye!")


if __name__ == "__main__":
    main()
