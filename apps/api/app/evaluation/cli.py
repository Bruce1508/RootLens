import argparse

from app.db.session import (
    ReadOnlySessionLocal,
    WriteSessionLocal,
    readonly_engine,
    write_engine,
)
from app.evaluation.redteam import run_and_export
from app.evaluation.runner import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.evaluation.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Run the FR-14 evaluation against a scenario split"
    )
    run_parser.add_argument("--split", choices=["dev", "held_out"], default="held_out")
    run_parser.add_argument("--model", default=None, help="Override the configured Ollama model")

    subparsers.add_parser(
        "redteam", help="Run the FR-8 adversarial red-team suite against the SQL guardrail"
    )

    args = parser.parse_args()

    if args.command == "run":
        run_id = run_evaluation(args.split, args.model)
        print(f"Evaluation run {run_id} completed. See docs/evaluation/results/{run_id}.json")
    elif args.command == "redteam":
        # The prompt-injection probe writes fake Investigation/Hypothesis
        # rows (app.evaluation.redteam.check_prompt_injection) — these are
        # probe artifacts, not real evaluation history, so both sessions
        # are wrapped in a transaction that's always rolled back, the same
        # guarantee the pytest suite gets for free from its db_session
        # fixture (tests/redteam/conftest.py).
        write_connection = write_engine.connect()
        write_transaction = write_connection.begin()
        write_session = WriteSessionLocal(bind=write_connection)
        readonly_connection = readonly_engine.connect()
        readonly_transaction = readonly_connection.begin()
        readonly_session = ReadOnlySessionLocal(bind=readonly_connection)
        try:
            run_id = run_and_export(readonly_engine, write_session, readonly_session)
        finally:
            write_session.close()
            write_transaction.rollback()
            write_connection.close()
            readonly_session.close()
            readonly_transaction.rollback()
            readonly_connection.close()
        print(f"Red-team run {run_id} completed. See docs/evaluation/results/{run_id}.json")


if __name__ == "__main__":
    main()
