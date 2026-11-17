"""Command line: python -m copilot "what breaks if pg-prod-01 goes down?" """
import argparse

from .agent import OpsCopilot


def main() -> None:
    p = argparse.ArgumentParser(description="Ops Knowledge Copilot (POC)")
    p.add_argument("question", nargs="?", help="Question to ask. Omit for interactive mode.")
    p.add_argument("--window", help="Planned change window, e.g. '2026-11-20 02:00'")
    p.add_argument("--offline", action="store_true", help="Do not call Claude even if ANTHROPIC_API_KEY is set")
    args = p.parse_args()

    bot = OpsCopilot(use_llm=False if args.offline else None)
    mode = "Claude" if bot.use_llm else "offline (extractive)"
    if args.question:
        print(bot.ask(args.question, args.window).text)
        return
    print(f"Ops Copilot POC - mode: {mode}. Type a question, or 'quit'.")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit"):
            break
        if q:
            print(bot.ask(q).text)


if __name__ == "__main__":
    main()
