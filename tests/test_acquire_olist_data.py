"""Focused tests for safe acquisition and provenance helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "acquire_olist_data.py"
SPEC = importlib.util.spec_from_file_location("acquire_olist_data", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load acquisition module for tests.")
acquire = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = acquire
SPEC.loader.exec_module(acquire)


class AcquisitionHelpersTest(unittest.TestCase):
    def test_sha256_and_copy_are_idempotent_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source.csv"
            destination = directory / "raw" / "source.csv"
            source.write_bytes(b"a,b\n1,2\n")

            expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(acquire.sha256_file(source), expected_hash)
            self.assertEqual(
                acquire.copy_file_without_overwrite(source, destination), "created"
            )
            self.assertEqual(
                acquire.copy_file_without_overwrite(source, destination), "unchanged"
            )

            source.write_bytes(b"a,b\n3,4\n")
            with self.assertRaises(acquire.AcquisitionError):
                acquire.copy_file_without_overwrite(source, destination)
            self.assertEqual(destination.read_bytes(), b"a,b\n1,2\n")

    def test_manifest_records_relative_path_size_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_dir = Path(temporary) / "raw"
            dataset = acquire.DATASETS[0]
            path = raw_dir / dataset.directory / dataset.expected_files[0]
            path.parent.mkdir(parents=True)
            path.write_bytes(b"mql_id\nexample\n")

            with mock.patch.object(acquire, "RAW_DIR", raw_dir):
                manifest = acquire.build_manifest()

            files = manifest["files"]
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["relative_path"], f"{dataset.directory}/{path.name}")
            self.assertEqual(files[0]["size_bytes"], path.stat().st_size)
            self.assertEqual(files[0]["sha256"], acquire.sha256_file(path))


if __name__ == "__main__":
    unittest.main()
