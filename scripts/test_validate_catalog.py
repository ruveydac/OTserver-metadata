import json
import tempfile
import unittest
from pathlib import Path

from validate_catalog import read, validate


class CatalogReferences(unittest.TestCase):
    def test_rejects_schema_valid_but_inconsistent_shards(self):
        source = Path(__file__).resolve().parents[1]
        row = read(next((source / "data").glob("ot-devices*.json")))[0]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema").symlink_to(source / "schema")
            data = root / "data"
            data.mkdir()
            (data / "ot-manufacturers.json").symlink_to(source / "data/ot-manufacturers.json")
            (data / "ot-devices-a.json").write_text(json.dumps([row]))
            self.assertEqual(validate(root)[1], 1)
            unknown = "00000000-0000-7000-8000-000000000001"
            for extra, error in [
                (row, "duplicate device ID"),
                (dict(row, id=unknown, manufacturer_id=unknown), "unknown manufacturer"),
                (dict(row, id=unknown, device_type_id=unknown), "device type"),
            ]:
                with self.subTest(error=error):
                    (data / "ot-devices-b.json").write_text(json.dumps([extra]))
                    with self.assertRaisesRegex(ValueError, error):
                        validate(root)
