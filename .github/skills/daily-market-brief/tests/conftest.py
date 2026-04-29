from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def skill_root() -> Path:
    return SKILL_ROOT


@pytest.fixture
def mock_data_dir() -> Path:
    return SKILL_ROOT / "tests" / "fixtures" / "mock_data"


@pytest.fixture
def load_mock_json(mock_data_dir: Path):
    def _loader(file_name: str) -> dict:
        return json.loads((mock_data_dir / file_name).read_text(encoding="utf-8"))

    return _loader


@pytest.fixture
def working_config(tmp_path: Path, skill_root: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_root / "config" / "config.example.yaml", config_dir / "config.example.yaml")
    shutil.copy(skill_root / "config" / "tracking-lists.yaml", config_dir / "tracking-lists.yaml")
    return config_dir / "config.example.yaml"