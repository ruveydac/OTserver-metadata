import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root):
    def schema(name):
        document = read(root / "schema" / f"ot-{name}.schema.json")
        Draft202012Validator.check_schema(document)
        return document

    groups = schema("device-types")
    registry = Registry().with_resource(groups["$id"], Resource.from_contents(groups))

    def validator(document):
        return Draft202012Validator(
            document, registry=registry, format_checker=Draft202012Validator.FORMAT_CHECKER
        )

    entries = [choice["const"] for choice in groups["$defs"]["deviceType"]["oneOf"]]
    validator(groups).validate(entries)
    types = {entry["id"].lower(): entry["name"] for entry in entries}
    if not types or len(types) != len(entries):
        raise ValueError("Missing or duplicate device type ID")

    manufacturers = read(root / "data/ot-manufacturers.json")
    validator(schema("manufacturers")).validate(manufacturers)
    owners = {row["id"].lower() for row in manufacturers}
    if len(owners) != len(manufacturers):
        raise ValueError("Duplicate manufacturer ID")

    devices = validator(schema("devices"))
    seen = set()
    for path in sorted((root / "data").glob("ot-devices*.json")):
        rows = read(path)
        devices.validate(rows)
        for row in rows:
            key = row["id"].lower()
            if key in seen:
                raise ValueError(f"{path.name}: duplicate device ID {key}")
            if row["manufacturer_id"].lower() not in owners:
                raise ValueError(f"{path.name}: {key} references an unknown manufacturer")
            if types.get(row["device_type_id"].lower()) != row["data"]["device_type"]:
                raise ValueError(f"{path.name}: {key} has an unknown or mismatched device type")
            seen.add(key)
    if not seen:
        raise ValueError("No devices found")
    return len(owners), len(seen)


if __name__ == "__main__":
    manufacturers, devices = validate(Path(__file__).resolve().parents[1])
    print(f"Validated {manufacturers} manufacturers and {devices} devices.")
