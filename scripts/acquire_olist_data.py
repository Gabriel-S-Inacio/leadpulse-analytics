"""Safely acquire or organize the public Olist source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    identifier: str
    directory: str
    classification: str
    expected_files: tuple[str, ...]


DATASETS = (
    DatasetSpec(
        key="marketing_funnel",
        identifier="olistbr/marketing-funnel-olist",
        directory="olist_marketing_funnel",
        classification="REAL_WORLD",
        expected_files=(
            "olist_marketing_qualified_leads_dataset.csv",
            "olist_closed_deals_dataset.csv",
        ),
    ),
    DatasetSpec(
        key="brazilian_ecommerce",
        identifier="olistbr/brazilian-ecommerce",
        directory="olist_brazilian_ecommerce",
        classification="REAL_WORLD",
        expected_files=(
            "olist_customers_dataset.csv",
            "olist_geolocation_dataset.csv",
            "olist_order_items_dataset.csv",
            "olist_order_payments_dataset.csv",
            "olist_order_reviews_dataset.csv",
            "olist_orders_dataset.csv",
            "olist_products_dataset.csv",
            "olist_sellers_dataset.csv",
            "product_category_name_translation.csv",
        ),
    ),
)

FILE_TO_DATASET = {
    filename: dataset
    for dataset in DATASETS
    for filename in dataset.expected_files
}


class AcquisitionError(RuntimeError):
    """Raised when acquisition cannot proceed without risking local data."""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a seekable binary stream."""
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _copy_stream_without_overwrite(stream: BinaryIO, destination: Path, source_hash: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file():
            raise AcquisitionError(f"Destination is not a file: {destination}")
        if sha256_file(destination) == source_hash:
            return "unchanged"
        raise AcquisitionError(
            f"Refusing to overwrite divergent raw file: {destination}"
        )

    created_by_this_process = False
    try:
        with destination.open("xb") as output:
            created_by_this_process = True
            shutil.copyfileobj(stream, output, length=1024 * 1024)
    except Exception:
        if created_by_this_process and destination.exists():
            destination.unlink()
        raise

    if sha256_file(destination) != source_hash:
        destination.unlink()
        raise AcquisitionError(f"Checksum mismatch while writing: {destination}")
    return "created"


def copy_file_without_overwrite(source: Path, destination: Path) -> str:
    """Copy a local source file, refusing a divergent overwrite."""
    source_hash = sha256_file(source)
    with source.open("rb") as stream:
        return _copy_stream_without_overwrite(stream, destination, source_hash)


def import_zip(archive: Path) -> list[tuple[Path, str]]:
    """Import recognized CSV members from a ZIP without trusting archive paths."""
    actions: list[tuple[Path, str]] = []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir():
                continue
            filename = Path(member.filename).name
            dataset = FILE_TO_DATASET.get(filename)
            if dataset is None:
                continue
            destination = RAW_DIR / dataset.directory / filename
            with bundle.open(member, "r") as digest_stream:
                source_hash = sha256_stream(digest_stream)
            with bundle.open(member, "r") as copy_stream:
                action = _copy_stream_without_overwrite(
                    copy_stream, destination, source_hash
                )
            actions.append((destination, action))
    return actions


def import_local(source_dir: Path) -> list[tuple[Path, str]]:
    """Import recognized CSVs and ZIP archives from a user-provided directory."""
    source_dir = source_dir.expanduser().resolve()
    if not source_dir.is_dir():
        raise AcquisitionError(f"Local source directory does not exist: {source_dir}")
    if source_dir == RAW_DIR.resolve() or RAW_DIR.resolve() in source_dir.parents:
        raise AcquisitionError("Source directory must be outside data/raw.")

    actions: list[tuple[Path, str]] = []
    for source in sorted(source_dir.rglob("*")):
        if not source.is_file():
            continue
        if source.suffix.lower() == ".csv" and source.name in FILE_TO_DATASET:
            dataset = FILE_TO_DATASET[source.name]
            destination = RAW_DIR / dataset.directory / source.name
            actions.append((destination, copy_file_without_overwrite(source, destination)))
        elif source.suffix.lower() == ".zip":
            actions.extend(import_zip(source))
    if not actions:
        raise AcquisitionError(
            "No recognized Olist CSV was found in the supplied directory or ZIP archives."
        )
    return actions


def credential_source_present() -> bool:
    """Check authentication presence without reading or printing credential values."""
    environment_auth = any(
        os.environ.get(name)
        for name in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY")
    )
    configured_directory = os.environ.get("KAGGLE_CONFIG_DIR")
    kaggle_dir = (
        Path(configured_directory).expanduser()
        if configured_directory
        else Path.home() / ".kaggle"
    )
    file_auth = any(
        path.is_file()
        for path in (kaggle_dir / "access_token", kaggle_dir / "kaggle.json")
    )
    return environment_auth or file_auth


def download_dataset(dataset: DatasetSpec) -> list[tuple[Path, str]]:
    """Download one official Kaggle dataset into a temporary directory and import it."""
    executable = shutil.which("kaggle")
    if executable is None:
        raise AcquisitionError(
            "Kaggle CLI is unavailable. Install/configure the official CLI outside this "
            "project, or manually download the official ZIP and use import-local."
        )

    with tempfile.TemporaryDirectory(prefix="leadpulse-kaggle-") as temporary:
        download_dir = Path(temporary)
        command = [
            executable,
            "datasets",
            "download",
            dataset.identifier,
            "--path",
            str(download_dir),
        ]
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            auth_hint = (
                " Local credentials were detected; verify their validity."
                if credential_source_present()
                else " No local credential was detected; use official Kaggle authentication "
                "if logged-out public download is unavailable."
            )
            raise AcquisitionError(
                f"Official Kaggle download failed for {dataset.identifier}."
                f"{auth_hint} No credential value was read or printed."
            )

        archives = sorted(download_dir.glob("*.zip"))
        if len(archives) != 1:
            raise AcquisitionError(
                f"Expected one Kaggle ZIP for {dataset.identifier}; found {len(archives)}."
            )
        return import_zip(archives[0])


def expected_file_paths() -> Iterable[tuple[DatasetSpec, str, Path]]:
    for dataset in DATASETS:
        for filename in dataset.expected_files:
            yield dataset, filename, RAW_DIR / dataset.directory / filename


def missing_expected_files() -> list[str]:
    return [
        f"{dataset.identifier}:{filename}"
        for dataset, filename, path in expected_file_paths()
        if not path.is_file()
    ]


def build_manifest(acquisition_method: str = "verification_only") -> dict[str, object]:
    files: list[dict[str, object]] = []
    for dataset, filename, path in expected_file_paths():
        if not path.is_file():
            continue
        files.append(
            {
                "classification": dataset.classification,
                "dataset_identifier": dataset.identifier,
                "filename": filename,
                "relative_path": path.relative_to(RAW_DIR).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": 1,
        "acquisition_method": acquisition_method,
        "dataset_version": "UNKNOWN_NOT_CAPTURED",
        "files": sorted(files, key=lambda item: str(item["relative_path"])),
    }


def write_manifest(acquisition_method: str = "verification_only") -> Path:
    """Write a deterministic local manifest atomically."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        build_manifest(acquisition_method), indent=2, sort_keys=True
    ) + "\n"
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(MANIFEST_PATH)
    return MANIFEST_PATH


def print_status() -> int:
    cli_present = shutil.which("kaggle") is not None
    missing = missing_expected_files()
    print(f"kaggle_cli_present={'yes' if cli_present else 'no'}")
    print(
        "kaggle_credential_source_present="
        f"{'yes' if credential_source_present() else 'no'}"
    )
    print(f"expected_files_present={sum(1 for _ in expected_file_paths()) - len(missing)}")
    print(f"expected_files_missing={len(missing)}")
    for item in missing:
        print(f"missing={item}")
    return 0 if not missing else 2


def report_actions(actions: Iterable[tuple[Path, str]]) -> None:
    for path, action in actions:
        print(f"{action}={path.relative_to(PROJECT_ROOT).as_posix()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acquire or organize official Olist datasets without overwriting raw data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Report local tool and expected-file availability.")
    subparsers.add_parser(
        "download", help="Download both datasets with the official Kaggle CLI."
    )
    import_parser = subparsers.add_parser(
        "import-local", help="Import recognized CSVs/ZIPs downloaded from official pages."
    )
    import_parser.add_argument("--source-dir", required=True, type=Path)
    subparsers.add_parser("manifest", help="Regenerate and verify the local SHA-256 manifest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if args.command == "status":
            return print_status()
        if args.command == "download":
            actions: list[tuple[Path, str]] = []
            for dataset in DATASETS:
                actions.extend(download_dataset(dataset))
            report_actions(actions)
            acquisition_method = "official_kaggle_cli"
        elif args.command == "import-local":
            report_actions(import_local(args.source_dir))
            acquisition_method = "local_import_user_asserted_official"
        else:
            acquisition_method = "verification_only"

        manifest = write_manifest(acquisition_method)
        print(f"manifest={manifest.relative_to(PROJECT_ROOT).as_posix()}")
        missing = missing_expected_files()
        if missing:
            for item in missing:
                print(f"missing={item}")
            return 2
        print("acquisition_status=complete")
        return 0
    except (AcquisitionError, OSError, zipfile.BadZipFile) as error:
        print(f"acquisition_status=failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
