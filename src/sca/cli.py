import argparse
import json
from pathlib import Path

from .data import inspect_dataset
from .synthetic import create_fixture
from .train import train, write_json
from .evaluate import evaluate


def main():
    parser = argparse.ArgumentParser(description="AES profiling SCA research pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("dataset")
    inspect.add_argument("--output")
    fixture = commands.add_parser("synthetic")
    fixture.add_argument("output")
    fit = commands.add_parser("train")
    fit.add_argument("--config", required=True)
    fit.add_argument("--dataset")
    fit.add_argument("--run-dir")
    fit.add_argument("--device", choices=["auto", "cpu", "cuda"])
    fit.add_argument("--epochs", type=int)
    fit.add_argument("--resume", action="store_true")
    attack = commands.add_parser("evaluate")
    attack.add_argument("--run-dir", required=True)
    attack.add_argument("--config", required=True)
    attack.add_argument("--output-dir")
    attack.add_argument("--split", choices=["validation", "attack"], required=True)
    attack.add_argument("--dataset")
    attack.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()
    if args.command == "inspect":
        report = inspect_dataset(args.dataset)
        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, indent=2))
    elif args.command == "synthetic":
        create_fixture(args.output)
        print("Synthetic fixture created; not experimental evidence")
    elif args.command == "train":
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        for key in ("dataset", "run_dir", "device", "epochs"):
            value = getattr(args, key)
            if value is not None:
                config[key] = value
        print(json.dumps(train(config, resume=args.resume), indent=2))
    elif args.command == "evaluate":
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        evaluate(args.run_dir, config, args.device, args.output_dir, split=args.split, dataset_override=args.dataset)


if __name__ == "__main__":
    main()
