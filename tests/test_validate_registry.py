import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_registry as v  # noqa: E402

EXAMPLE = json.loads((ROOT / "examples" / "registry.example.json").read_text())


def _with(**over):
    payload = copy.deepcopy(EXAMPLE)
    payload["plugins"][0].update(over)
    return payload


def test_published_registry_is_valid():
    payload = json.loads((ROOT / "registry.json").read_text())
    assert v.validate(payload) == []


def _builtin():
    return json.loads((ROOT / "builtin.json").read_text())


def test_published_builtin_is_valid():
    assert v.validate_builtin(_builtin()) == []
    assert len(_builtin()["plugins"]) == 13


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(unknown=1),
        lambda e: e.update(install_commands=[["sh", "-c", "curl x | sh"]]),
        lambda e: e.update(install_commands=[["python", "-m", "pip", "uninstall", "x"]]),
        lambda e: e.update(validate_entrypoints=["../x"]),
        lambda e: e.update(validate_entrypoints=["/etc/passwd"]),
        lambda e: e.update(repo="https://evil/x"),
        lambda e: e.update(directory=".."),
        lambda e: e.pop("label"),
        lambda e: e.pop("description"),
        lambda e: e.update(description="too short"),
        lambda e: e.update(description="x" * 401),
        lambda e: e.update(validate_import="a b"),
    ],
)
def test_invalid_builtin_entries_are_reported(mutate):
    payload = _builtin()
    mutate(payload["plugins"][0])
    assert v.validate_builtin(payload)


def test_duplicate_builtin_key_is_reported():
    payload = _builtin()
    payload["plugins"].append(dict(payload["plugins"][0]))
    assert v.validate_builtin(payload)


def test_registry_entries_cannot_reuse_builtin_identity():
    for b in _builtin()["plugins"]:
        for over in ({"id": b["key"]}, {"repo": b["repo"]}, {"directory": b["directory"]}):
            assert v.validate(_with(**over)), (b["key"], over)


def test_builtin_schema_lists_the_same_fields():
    schema = json.loads((ROOT / "builtin.schema.json").read_text())
    props = schema["properties"]["plugins"]["items"]["properties"]
    assert set(props) == v.BUILTIN_FIELDS


def test_example_is_valid():
    assert v.validate(EXAMPLE) == []


@pytest.mark.parametrize(
    "over",
    [
        {"id": "Bad Id"},
        {"id": "hpc_simulator"},
        {"directory": "YServer"},
        {"repo": "YSocialTwin/YClient"},
        {"repo": "https://evil.example/a/b"},
        {"recipe": "curl | sh"},
        {"category": "other"},
        {"trust": "official"},  # not an official owner
        {"branch": "../x"},
        {"directory": ".."},
        {"unknown_field": 1},
        {"min_ysocial_version": "next"},
        {"name": ""},
        {"import_name": "a b"},
    ],
)
def test_invalid_entries_are_reported(over):
    assert v.validate(_with(**over))


def test_duplicates_are_reported():
    payload = copy.deepcopy(EXAMPLE)
    payload["plugins"].append(copy.deepcopy(payload["plugins"][0]))
    assert v.validate(payload)


def test_official_owner_may_use_official_trust():
    assert v.validate(_with(repo="YSocialTwin/sentiment-lab", trust="official")) == []


def test_wrong_schema_version():
    assert v.validate({"schema_version": 2, "plugins": []})


def test_schema_file_lists_the_same_fields():
    schema = json.loads((ROOT / "registry.schema.json").read_text())
    props = schema["properties"]["plugins"]["items"]["properties"]
    assert set(props) == v.KNOWN_FIELDS
