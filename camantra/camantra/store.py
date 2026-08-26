"""Persistenza: caricamento listone (file reale o sample) e stato del draft."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import League
from .ingest.listone import load_listone
from .ingest.sample import generate_sample_listone

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# nomi file cercati per il listone reale (in ordine di priorita')
LISTONE_CANDIDATES = ["listone.xlsx", "listone.csv", "quotazioni.xlsx", "quotazioni.csv"]


def find_real_listone() -> Path | None:
    for name in LISTONE_CANDIDATES:
        p = DATA_DIR / name
        if p.exists():
            return p
    return None


def load_players(league: League, path: str | Path | None = None) -> pd.DataFrame:
    """Ritorna il DataFrame giocatori normalizzato.

    Priorita': `path` esplicito -> file reale in data/ -> dataset SAMPLE.
    La colonna `is_sample` indica se stai lavorando su dati sintetici.
    """
    if path is not None:
        df = load_listone(path, league)
        df["is_sample"] = False
        return df
    real = find_real_listone()
    if real is not None:
        df = load_listone(real, league)
        df["is_sample"] = False
        return df
    df = generate_sample_listone(league)
    df["is_sample"] = True
    return df


# ----------------------------- stato draft ----------------------------- #

def save_draft_state(state: dict, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_draft_state(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
