#!/usr/bin/env python3
"""Upload the generated manuscript dataset to a public Hugging Face dataset repo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from generate import SCRIPTS  # noqa: E402


EXPECTED_SPLITS = {"train": (1, 85), "validation": (86, 95), "test": (96, 100)}


def validate_output(output: Path) -> None:
    errors: list[str] = []
    expected_images = 0
    expected_annotations = 0
    for script in SCRIPTS:
        for split, (first, last) in EXPECTED_SPLITS.items():
            folder = output / script / split
            expected_stems = {
                f"{script}_{split}_{index:04d}"
                for index in range(first, last + 1)
            }
            images = {path.stem: path for path in folder.glob("*.png")}
            annotations = {path.stem: path for path in folder.glob("*.md")}
            expected_images += len(expected_stems)
            expected_annotations += len(expected_stems)

            if len(images) != len(expected_stems):
                errors.append(f"{folder}: expected {len(expected_stems)} PNGs, found {len(images)}")
            if len(annotations) != len(expected_stems):
                errors.append(f"{folder}: expected {len(expected_stems)} Markdown files, found {len(annotations)}")
            if set(images) != expected_stems:
                errors.append(f"{folder}: PNG names do not match the required {split} indices")
            if set(annotations) != expected_stems:
                errors.append(f"{folder}: Markdown names do not match the required {split} indices")

            for stem in sorted(expected_stems & set(images) & set(annotations)):
                try:
                    with Image.open(images[stem]) as image:
                        image.verify()
                except Exception as exc:
                    errors.append(f"{images[stem]}: invalid image ({exc})")
                try:
                    annotations[stem].read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    errors.append(f"{annotations[stem]}: unreadable Markdown ({exc})")

    all_images = list(output.rglob("*.png")) if output.exists() else []
    all_annotations = list(output.rglob("*.md")) if output.exists() else []
    if len(all_images) != 300:
        errors.append(f"{output}: expected exactly 300 PNG files across the dataset, found {len(all_images)}")
    if len(all_annotations) != 300:
        errors.append(f"{output}: expected exactly 300 Markdown files across the dataset, found {len(all_annotations)}")
    if expected_images != 300 or expected_annotations != 300:
        errors.append("Internal split counts do not total 300 images and 300 annotations")

    if errors:
        example = "\n".join(f"  - {error}" for error in errors[:20])
        more = f"\n  ... and {len(errors) - 20} more issue(s)" if len(errors) > 20 else ""
        raise SystemExit(f"Dataset verification failed; nothing was uploaded:\n{example}{more}")


def make_dataset(output: Path, script: str):
    from datasets import Dataset, DatasetDict, Features, Image as HFImage, Value

    splits = {}
    for split, (first, last) in EXPECTED_SPLITS.items():
        rows = []
        for index in range(first, last + 1):
            stem = f"{script}_{split}_{index:04d}"
            folder = output / script / split
            rows.append({
                "image": str(folder / f"{stem}.png"),
                "text": (folder / f"{stem}.md").read_text(encoding="utf-8"),
            })
        splits[split] = Dataset.from_list(
            rows,
            features=Features({"image": HFImage(), "text": Value("string")}),
        )
    return DatasetDict(splits)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output",
                        help="folder containing the generated script/split directories (default: output)")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi, create_repo, update_repo_settings, whoami
    except ImportError as exc:
        raise SystemExit("Install upload dependencies first: python -m pip install -r requirements-hub.txt") from exc
    except Exception as exc:
        raise SystemExit("Hugging Face login not found. Run `hf auth login` and try again.") from exc

    output = args.output.expanduser().resolve()
    validate_output(output)

    try:
        identity = whoami()
    except Exception as exc:
        raise SystemExit("Hugging Face authentication failed. Run `hf auth login` and try again.") from exc
    username = identity.get("name")
    if not username:
        raise SystemExit("Could not determine the authenticated Hugging Face username. Run `hf auth login`.")
    repo_id = f"{username}/synthetic-manuscript-generator"

    api = HfApi()
    try:
        # Keep a newly created or existing private repo private until all three
        # configurations have uploaded successfully.
        create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)
    except Exception as exc:
        raise SystemExit(f"Could not create or access dataset repository {repo_id}: {exc}") from exc

    for script in SCRIPTS:
        try:
            make_dataset(output, script).push_to_hub(repo_id, config_name=script)
        except Exception as exc:
            raise SystemExit(f"Upload of the {script} configuration failed: {exc}") from exc
        print(f"Hugging Face accepted the {script} configuration upload.")

    try:
        update_repo_settings(repo_id=repo_id, repo_type="dataset", private=False)
        repo_info = api.repo_info(repo_id, repo_type="dataset")
    except Exception as exc:
        raise SystemExit(
            f"All three configurations uploaded, but public visibility could not be verified: {exc}"
        ) from exc
    if repo_info.private:
        raise SystemExit("All three configurations uploaded, but the repository is still private.")

    print(f"Upload complete. Public dataset: https://huggingface.co/datasets/{repo_id}")


if __name__ == "__main__":
    main()
