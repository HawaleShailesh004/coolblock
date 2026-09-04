from __future__ import annotations

import json

import pytest
from engine.ingest.d16_literature import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D16 not registered yet -- run engine.ingest.d16_literature"
)


def test_smoke() -> None:
    with open(version_dir(SOURCE_ID, VERSION) / "citations.json") as f:
        data = json.load(f)
    assert len(data["papers"]) == 5
    for paper in data["papers"]:
        assert paper["title"]
        assert paper["used_for"]
