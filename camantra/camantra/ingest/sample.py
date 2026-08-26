"""Generatore di un listone Euroleghe SINTETICO (dati di esempio).

ATTENZIONE — dati NON reali (tranne pochi seed dichiarati):
  Serve solo a far girare la pipeline e la dashboard end-to-end senza il file
  reale (che non e' raggiungibile da questo ambiente per policy di rete).
  I nomi sintetici hanno la forma "<Squadra> <Ruolo><n>" e la colonna
  `synthetic=True`. Sostituisci con il listone vero appena disponibile:
      streamlit -> pagina "Listone" -> carica file  (oppure data/listone.xlsx)

I pochi `SEED_REAL` provengono dallo screenshot del regolamento (FVM dati
dalla lega), inclusi solo come riferimento illustrativo.
"""

from __future__ import annotations

import random

import pandas as pd

from ..config import League
from ..roles import normalize_roles

# Seed reali dallo screenshot del regolamento: (nome, squadra, ruolo, FVM)
SEED_REAL = [
    ("Kane", "Bayern Monaco", "A", 499),
    ("Haaland", "Manchester City", "A;Pc", 415),
    ("Mbappe", "Real Madrid", "A", 414),
    ("Olise", "Bayern Monaco", "W;T", 365),
    ("Lamine Yamal", "Barcellona", "W", 295),
    ("Luis Diaz", "Bayern Monaco", "A;W", 288),
    ("Palmer", "Chelsea", "T;C", 203),
    ("Bruno Fernandes", "Manchester United", "C;T", 195),
    ("Dimarco", "Inter", "Ds;E", 192),
    ("Martinez L.", "Inter", "A;Pc", 269),
    ("Bellingham", "Real Madrid", "C;T", 193),
    ("Paz N.", "Como", "C;T", 188),
    ("Malen", "Roma", "A;W", 252),
    ("Guirassy", "Borussia Dortmund", "Pc;A", 244),
]

# Template ruoli per una rosa-tipo di movimento (oltre ai 3 portieri).
_OUTFIELD_TEMPLATE = [
    ("Dc", None), ("Dc", None), ("Dc", "B"), ("B", "Dc"),
    ("Dd", "E"), ("Ds", "E"), ("Dd", None), ("Ds", None),
    ("E", "W"), ("E", "M"), ("M", None), ("M", "C"),
    ("C", "T"), ("C", None), ("W", "A"), ("W", "T"),
    ("T", "C"), ("A", "Pc"), ("Pc", "A"), ("A", "W"),
    ("M", "C"), ("E", None),
]


def generate_sample_listone(league: League, players_per_team: int = 25,
                            seed: int = 42) -> pd.DataFrame:
    """Costruisce un DataFrame nello schema normalizzato, con dati sintetici."""
    rng = random.Random(seed)
    aliases = league.role_aliases
    canonical = set(league.canonical_roles)
    seed_by_key = {(n, t): (r, f) for n, t, r, f in SEED_REAL}

    records = []
    pid = 1
    for team in league.all_teams:
        league_name = league.team_to_league[team]
        team_strength = rng.uniform(0.6, 1.4)  # forza relativa della squadra

        # 3 portieri
        for k in range(league.n_goalkeepers):
            fvm = max(1, int(rng.uniform(8, 60) * (team_strength if k == 0 else 0.3)))
            records.append(_mk(pid, f"{team} Por{k+1}", team, league_name,
                               ["Por"], fvm, rng, is_gk=True)); pid += 1

        # movimento
        n_out = max(len(_OUTFIELD_TEMPLATE), players_per_team - league.n_goalkeepers)
        for k in range(n_out):
            primary, secondary = _OUTFIELD_TEMPLATE[k % len(_OUTFIELD_TEMPLATE)]
            roles = [primary] + ([secondary] if secondary else [])
            # decadimento del valore per profondita' di rosa
            depth = 1.0 - (k / (n_out + 4))
            base = _role_base_value(primary) * team_strength * depth
            fvm = max(1, int(base * rng.uniform(0.7, 1.3)))
            name = f"{team} {primary}{k+1}"
            # sovrascrivi con seed reale se coincide squadra+ruolo e non ancora usato
            records.append(_mk(pid, name, team, league_name, roles, fvm, rng)); pid += 1

    df = pd.DataFrame.from_records(records)

    # inietta i seed reali (aggiunge/aggiorna, non sostituisce i sintetici a caso)
    seed_rows = []
    for name, team, role, fvm in SEED_REAL:
        if team not in league.all_teams:
            continue
        roles = [r for r in normalize_roles(role, aliases) if r in canonical]
        row = _mk(pid, name, team, league.team_to_league[team], roles, fvm, rng)
        row["synthetic"] = False
        seed_rows.append(row); pid += 1
    if seed_rows:
        df = pd.concat([pd.DataFrame(seed_rows), df], ignore_index=True)

    df["source"] = "SAMPLE (sintetico)"
    return df.reset_index(drop=True)


def _cli(argv: list[str] | None = None) -> int:
    """Entry point: genera un listone sample e lo scrive come CSV+XLSX in data/sample/."""
    import argparse
    from pathlib import Path

    from ..config import load_league

    ap = argparse.ArgumentParser(description="Genera un listone Euroleghe SINTETICO.")
    ap.add_argument("--out-dir", default="data/sample")
    ap.add_argument("--per-team", type=int, default=25)
    args = ap.parse_args(argv)

    league = load_league()
    df = generate_sample_listone(league, players_per_team=args.per_team)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    flat = df.assign(roles=df["roles"].apply(lambda r: ";".join(r)))
    flat.to_csv(out / "listone_sample.csv", index=False)
    try:
        flat.to_excel(out / "listone_sample.xlsx", index=False)
    except Exception as e:  # openpyxl mancante
        print(f"(xlsx saltato: {e})")
    print(f"OK: {len(df)} giocatori su {league.all_teams.__len__()} squadre -> {out}/")
    return 0


def _role_base_value(role: str) -> float:
    return {
        "Pc": 120, "A": 110, "W": 95, "T": 90, "C": 70, "M": 55,
        "E": 60, "Dd": 45, "Ds": 45, "B": 40, "Dc": 42,
    }.get(role, 45)


def _mk(pid, name, team, league_name, roles, fvm, rng, is_gk=False) -> dict:
    # fantamedia correlata al valore (piu' alto FVM -> media leggermente migliore)
    fm_base = 6.0 if is_gk else 5.9
    fm = round(min(8.5, fm_base + fvm / 220.0 + rng.uniform(-0.25, 0.35)), 2)
    mv = round(min(7.5, 5.9 + fvm / 400.0 + rng.uniform(-0.2, 0.2)), 2)
    presenze = int(min(38, max(0, rng.gauss(26 if fvm > 40 else 16, 7))))
    gol = 0 if is_gk else int(max(0, rng.gauss(fvm / 40.0, 2)))
    assist = 0 if is_gk else int(max(0, rng.gauss(fvm / 90.0, 1.5)))
    return {
        "player_id": pid, "name": name, "team": team, "league": league_name,
        "roles": roles, "role_str": ";".join(roles), "fvm": float(fvm),
        "fanta_media": fm, "media_voto": mv, "presenze": float(presenze),
        "gol": float(gol), "assist": float(assist), "synthetic": True,
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
