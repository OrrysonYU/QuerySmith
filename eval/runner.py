"""CLI evaluation runner loading an explicit application adapter."""

import argparse
import asyncio
import importlib
from pathlib import Path
from typing import Any

from eval.core import EvalRunner, load_cases
from eval.report import write_report


def load_adapter(path: str) -> Any:
    module_name, separator, factory_name = path.partition(":")
    if not separator:
        raise ValueError("adapter must use module:factory format")
    return getattr(importlib.import_module(module_name), factory_name)()


async def run(adapter_path: str, output: Path) -> None:
    adapter = load_adapter(adapter_path)
    regular = await EvalRunner(adapter).run(load_cases(Path("eval/datasets/questions.json")))
    adversarial = await EvalRunner(adapter).run(
        load_cases(Path("eval/datasets/adversarial.json")), adversarial=True
    )
    write_report([record.model_dump(mode="json") for record in [*regular, *adversarial]], output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adapter", required=True, help="Python module:factory returning an async case runner"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.adapter, args.output))


if __name__ == "__main__":
    main()
