from __future__ import annotations

import argparse
import re
from pathlib import Path


ID_LINE_PATTERN = re.compile(r"^\s*\d+\.\s+`([^`]+)`:", re.MULTILINE)
DEFAULT_INPUT_PATH = Path(__file__).resolve().parents[1] / "arxiv_id" / "core_pool" / "latest.md"


def extract_arxiv_ids(markdown_text: str) -> list[str]:
    return ID_LINE_PATTERN.findall(markdown_text)


def write_id_file(source_path: Path, output_path: Path | None = None) -> Path:
    resolved_source_path = source_path.resolve()
    resolved_output_path = output_path.resolve() if output_path is not None else resolved_source_path.with_name("id.md")
    arxiv_ids = extract_arxiv_ids(resolved_source_path.read_text(encoding="utf-8"))
    payload = "".join(f"{arxiv_id}\n" for arxiv_id in arxiv_ids)
    resolved_output_path.write_text(payload, encoding="utf-8")
    return resolved_output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract arXiv IDs from latest.md into id.md.")
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the source latest.md file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to the output id.md file. Defaults to a sibling id.md next to the source file.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    output_path = write_id_file(args.source, args.output)
    print(f"Wrote arXiv IDs to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
