"""Train the complete answer-bearing MedQuAD QA retrieval model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from medquad_qa import SOURCE, ARTIFACT, train


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=ARTIFACT)
    args = parser.parse_args()
    print(json.dumps(train(args.source, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
