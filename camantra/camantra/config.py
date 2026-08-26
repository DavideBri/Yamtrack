"""Caricamento della configurazione lega (config/league.yaml).

Espone un oggetto `League` con accessi comodi e cache, cosi' il resto del
codice non rilegge/riparsa lo YAML in giro.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Percorso di default: <repo>/camantra/config/league.yaml
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "league.yaml"


@dataclass
class League:
    """Vista tipata sulla configurazione della lega."""

    raw: dict[str, Any]
    path: Path

    # --- meta ---------------------------------------------------------- #
    @property
    def name(self) -> str:
        return self.raw["league"]["name"]

    @property
    def managers(self) -> int:
        return int(self.raw["league"]["managers"])

    # --- rosa ---------------------------------------------------------- #
    @property
    def roster_size(self) -> int:
        return int(self.raw["roster"]["size_total"])

    @property
    def n_goalkeepers(self) -> int:
        return int(self.raw["roster"]["goalkeepers"])

    @property
    def roster_targets(self) -> dict[str, int]:
        return dict(self.raw["roster"]["roster_targets"])

    # --- ruoli --------------------------------------------------------- #
    @property
    def canonical_roles(self) -> list[str]:
        return list(self.raw["roles"]["canonical"])

    @property
    def role_aliases(self) -> dict[str, str]:
        return dict(self.raw["roles"].get("aliases", {}))

    @property
    def role_department(self) -> dict[str, str]:
        return dict(self.raw["roles"]["department"])

    # --- moduli -------------------------------------------------------- #
    @property
    def modules(self) -> dict[str, list[list[str]]]:
        return {name: [list(slot) for slot in slots]
                for name, slots in self.raw["modules"].items()}

    # --- draft --------------------------------------------------------- #
    @property
    def draft(self) -> dict[str, Any]:
        return dict(self.raw["draft"])

    @property
    def later_round_order(self) -> str:
        return self.raw["draft"]["later_round_order"]

    # --- scoring ------------------------------------------------------- #
    @property
    def scoring(self) -> dict[str, Any]:
        return dict(self.raw["scoring"])

    # --- leghe / squadre ---------------------------------------------- #
    @property
    def leagues(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.raw["leagues"].items()}

    @functools.cached_property
    def team_to_league(self) -> dict[str, str]:
        """Mappa 'squadra' -> 'campionato' per tutte le 37 squadre."""
        out: dict[str, str] = {}
        for league_name, teams in self.leagues.items():
            for t in teams:
                out[t] = league_name
        return out

    @property
    def all_teams(self) -> list[str]:
        return list(self.team_to_league.keys())


def load_league(path: str | Path | None = None) -> League:
    """Carica e valida minimamente il file di configurazione."""
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        raise FileNotFoundError(f"Config lega non trovata: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    _validate(raw, p)
    return League(raw=raw, path=p)


def _validate(raw: dict[str, Any], p: Path) -> None:
    for key in ("league", "roster", "roles", "modules", "leagues"):
        if key not in raw:
            raise ValueError(f"Config {p}: sezione mancante '{key}'")
    targets = raw["roster"]["roster_targets"]
    outfield = int(raw["roster"]["outfield"])
    total_targets = sum(int(v) for v in targets.values())
    if total_targets != outfield:
        raise ValueError(
            f"Config {p}: roster_targets somma {total_targets} "
            f"ma outfield atteso = {outfield}. Ricalibra roster_targets."
        )
    for mod, slots in raw["modules"].items():
        if len(slots) != 11:
            raise ValueError(f"Config {p}: modulo {mod} ha {len(slots)} slot (attesi 11).")
