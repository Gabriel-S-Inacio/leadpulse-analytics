"""Generate the governed MVP synthetic advertising-spend snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from leadpulse.synthetic.marketing_spend import (
    DEFAULT_MQL_SOURCE,
    DEFAULT_OUTPUT,
    SyntheticSpendError,
    generate_marketing_spend,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mql-source", type=Path, default=DEFAULT_MQL_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    try:
        result = generate_marketing_spend(arguments.mql_source, arguments.output)
    except (FileNotFoundError, SyntheticSpendError) as error:
        parser.error(str(error))

    print(f"rows={result.row_count}")
    print(f"source_sha256={result.source_sha256}")
    print(f"output={result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
