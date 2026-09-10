"""Fetch public, pinned inputs; evaluate.py verifies their local identity."""

import argparse
from pathlib import Path
import shutil

from huggingface_hub import hf_hub_download, snapshot_download

from evaluate import DATA_REVISION, MODEL_REVISION, ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "model-cache")
    args = parser.parse_args()
    (ROOT / "data").mkdir(exist_ok=True)
    for language in ("en", "zh"):
        source = hf_hub_download(
            "juletxara/mgsm", f"{language}/test-00000-of-00001.parquet",
            repo_type="dataset", revision=DATA_REVISION,
        )
        shutil.copyfile(source, ROOT / "data" / f"{language}-test.parquet")
    snapshot_download(
        "XHToken/Spark-X2.5-1.7B", revision=MODEL_REVISION,
        local_dir=args.model,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "LICENSE"],
        max_workers=3,
    )


if __name__ == "__main__":
    main()
