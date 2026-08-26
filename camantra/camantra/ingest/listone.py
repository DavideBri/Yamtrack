"""Parser del listone Euroleghe (FVM) in un DataFrame normalizzato.

Colonne di output (schema canonico usato da tutto il progetto):
    player_id, name, team, league, roles (list[str]), role_str,
    fvm, fanta_media, media_voto, presenze, gol, assist, source

Regge file .xlsx / .csv con layout eterogenei:
  - riga "banner" iniziale (tipica dei file quotazioni fantacalcio.it) saltata
    cercando la riga header reale;
  - nomi colonna riconosciuti via `columns.map_columns`;
  - ruoli normalizzati in canonico Mantra;
  - squadre riconciliate (fuzzy) con le 37 squadre Euroleghe del regolamento.
"""

from __future__ import annotations

from difflib import get_close_matches
from pathlib import Path

import pandas as pd

from ..config import League
from ..roles import normalize_roles
from .columns import map_columns

# alias comuni squadra file -> nome canonico regolamento
TEAM_ALIASES = {
    "man city": "Manchester City", "man. city": "Manchester City",
    "manchester c.": "Manchester City", "mancity": "Manchester City",
    "man utd": "Manchester United", "man united": "Manchester United",
    "man. united": "Manchester United",
    "bayern": "Bayern Monaco", "bayern munich": "Bayern Monaco",
    "dortmund": "Borussia Dortmund", "b. dortmund": "Borussia Dortmund",
    "leverkusen": "Bayer Leverkusen", "b. leverkusen": "Bayer Leverkusen",
    "leipzig": "Lipsia", "rb leipzig": "Lipsia",
    "stuttgart": "Stoccarda", "frankfurt": "Eintracht Francoforte",
    "eintracht": "Eintracht Francoforte",
    "atletico": "Atletico Madrid", "atl. madrid": "Atletico Madrid",
    "athletic": "Athletic Bilbao", "athletic club": "Athletic Bilbao",
    "barca": "Barcellona", "barcelona": "Barcellona",
    "real": "Real Madrid", "betis": "Betis", "real betis": "Betis",
    "marseille": "Marsiglia", "as monaco": "Monaco",
    "paris": "PSG", "paris sg": "PSG", "paris saint-germain": "PSG",
    "villa": "Aston Villa", "spurs": "Tottenham",
}


def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 8) -> int:
    """Trova l'indice di riga che sembra l'header reale (piu' celle 'testo-etichetta')."""
    best_row, best_score = 0, -1
    labels = {"nome", "calciatore", "ruolo", "squadra", "fvm", "r", "rm", "sq", "id"}
    for i in range(min(max_scan, len(df_raw))):
        row = [str(v).strip().lower() for v in df_raw.iloc[i].tolist()]
        score = sum(1 for v in row if v in labels or any(l in v for l in labels))
        if score > best_score:
            best_row, best_score = i, score
    return best_row


def _resolve_team(name: str, valid_teams: list[str]) -> str | None:
    if not name:
        return None
    key = str(name).strip()
    low = key.lower()
    if key in valid_teams:
        return key
    if low in TEAM_ALIASES:
        return TEAM_ALIASES[low]
    # fuzzy contro le squadre valide
    match = get_close_matches(key, valid_teams, n=1, cutoff=0.82)
    if match:
        return match[0]
    # match per contenimento (es. "Inter Milano" -> "Inter")
    for t in valid_teams:
        if t.lower() in low or low in t.lower():
            return t
    return None


def _read_any(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls", ".xlsm"):
        return pd.read_excel(path, header=None, dtype=object)
    # csv/tsv: prova a inferire il separatore
    return pd.read_csv(path, header=None, dtype=object, sep=None, engine="python")


def load_listone(path: str | Path, league: League,
                 keep_only_euroleghe_teams: bool = True) -> pd.DataFrame:
    """Carica un file listone reale e ritorna il DataFrame normalizzato."""
    path = Path(path)
    raw = _read_any(path)
    header_row = _find_header_row(raw)
    headers = [str(v).strip() for v in raw.iloc[header_row].tolist()]
    body = raw.iloc[header_row + 1:].copy()
    body.columns = headers
    body = body.dropna(how="all")

    mapping = map_columns(headers)
    if "name" not in mapping:
        raise ValueError(
            f"Impossibile individuare la colonna 'nome' in {path.name}. "
            f"Header letti: {headers}"
        )
    df = _project(body, mapping, league)
    if keep_only_euroleghe_teams:
        df = df[df["team"].notna()].reset_index(drop=True)
    df["source"] = path.name
    return df


def _project(body: pd.DataFrame, mapping: dict[str, str], league: League) -> pd.DataFrame:
    aliases = league.role_aliases
    valid_teams = league.all_teams
    canonical_roles = set(league.canonical_roles)

    def get(col_field: str, row) -> object:
        col = mapping.get(col_field)
        return row[col] if col is not None and col in row else None

    records = []
    for _, row in body.iterrows():
        name = get("name", row)
        if name is None or str(name).strip() == "" or str(name).lower() == "nan":
            continue
        role_src = get("role_mantra", row) or get("role_classic", row) or ""
        roles = [r for r in normalize_roles(role_src, aliases) if r in canonical_roles]
        team_resolved = _resolve_team(str(get("team", row) or ""), valid_teams)
        league_name = league.team_to_league.get(team_resolved) if team_resolved else None
        records.append({
            "player_id": _to_int(get("player_id", row)),
            "name": str(name).strip(),
            "team": team_resolved,
            "league": league_name,
            "roles": roles,
            "role_str": ";".join(roles),
            "fvm": _to_float(get("fvm", row)),
            "fanta_media": _to_float(get("fanta_media", row)),
            "media_voto": _to_float(get("media_voto", row)),
            "presenze": _to_float(get("presenze", row)),
            "gol": _to_float(get("gol", row)),
            "assist": _to_float(get("assist", row)),
        })
    return pd.DataFrame.from_records(records)


def _to_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(str(v).replace(",", ".").strip())
        return f
    except (ValueError, TypeError):
        return None


def _to_int(v) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None
