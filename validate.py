#!/usr/bin/env python3
"""Check generated split counts, image/Markdown pairing, dimensions, and source text."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from generate import DEFAULT_TEXTS, SCRIPTS, load_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args()
    failures: list[str] = []
    expected = {"train": 85, "validation": 10, "test": 5}
    total = 0

    for script in SCRIPTS:
        passages = load_lines(DEFAULT_TEXTS[script])
        for split, count in expected.items():
            folder = args.output / script / split
            images = sorted(folder.glob("*.png"))
            annotations = sorted(folder.glob("*.md"))
            if len(images) != count:
                failures.append(f"{script}/{split}: expected {count} images, found {len(images)}")
            if {path.stem for path in images} != {path.stem for path in annotations}:
                failures.append(f"{script}/{split}: PNG and Markdown filenames do not match")
            for path in images:
                try:
                    with Image.open(path) as image:
                        image.load()
                        if image.size != (args.width, args.height):
                            failures.append(f"{path}: expected {args.width}x{args.height}, found {image.width}x{image.height}")
                except Exception as exc:
                    failures.append(f"{path}: cannot decode image ({exc})")
                md_path = path.with_suffix(".md")
                if not md_path.exists():
                    continue
                markdown = md_path.read_text(encoding="utf-8")
                if not markdown.startswith("# Main text\n\n"):
                    failures.append(f"{md_path}: missing main-text section")
                    continue
                main_text = markdown.split("\n## Marginal note\n\n", 1)[0][len("# Main text\n\n"):].rstrip("\n")
                try:
                    index = int(path.stem.rsplit("_", 1)[1]) - 1
                    expected_text = passages[index % len(passages)]
                    if main_text != expected_text:
                        failures.append(f"{md_path}: main-text annotation differs from source")
                except (ValueError, IndexError):
                    failures.append(f"{md_path}: filename has no valid sample index")
                if "\n## Marginal note\n\n" in markdown:
                    note = markdown.split("\n## Marginal note\n\n", 1)[1].strip()
                    if note not in main_text.split():
                        failures.append(f"{md_path}: marginal note is not present in main text")
            total += len(images)

    if failures:
        print("Validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print(f"Validation passed: {total} paired folios; 85/10/5 splits for each of the three scripts.")


if __name__ == "__main__":
    main()
