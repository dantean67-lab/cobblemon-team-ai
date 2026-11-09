import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.data_loader import load_data  # noqa: E402
from engine.legality import Settings, allowed_species  # noqa: E402
from engine.sets import build_candidates  # noqa: E402


@pytest.fixture(scope="session")
def data():
    return load_data()


@pytest.fixture(scope="session")
def default_settings():
    return Settings()


@pytest.fixture(scope="session")
def all_on_settings():
    return Settings.all_on()


@pytest.fixture(scope="session")
def default_candidates(data, default_settings):
    return build_candidates(data, allowed_species(data, default_settings), default_settings)


@pytest.fixture(scope="session")
def all_on_candidates(data, all_on_settings):
    return build_candidates(data, allowed_species(data, all_on_settings), all_on_settings)
