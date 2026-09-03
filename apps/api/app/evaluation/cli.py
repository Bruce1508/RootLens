import argparse

from app.evaluation.runner import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.evaluation.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Run the FR-14 evaluation against a scenario split"
    )
    run_parser.add_argument("--split", choices=["dev", "held_out"], default="held_out")
    run_parser.add_argument("--model", default=None, help="Override the configured Ollama model")

    args = parser.parse_args()

    if args.command == "run":
        run_id = run_evaluation(args.split, args.model)
        print(f"Evaluation run {run_id} completed. See docs/evaluation/results/{run_id}.json")


if __name__ == "__main__":
    main()
