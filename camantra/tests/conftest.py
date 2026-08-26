import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from camantra.config import load_league
from camantra.engine.value import build_big_board
from camantra.store import load_players


@pytest.fixture(scope="session")
def league():
    return load_league()


@pytest.fixture(scope="session")
def board(league):
    return build_big_board(load_players(league), league)
