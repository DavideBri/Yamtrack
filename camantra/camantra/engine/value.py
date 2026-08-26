"""Value engine: proiezioni fantapunti, VOR (value over replacement) e tiers.

In un draft a crediti infiniti la risorsa scarsa sono le CHIAMATE: la metrica
giusta non e' il prezzo ma il *valore rispetto al rimpiazzo* nel ruolo (VOR).
Un giocatore vale tanto quanto batte il miglior giocatore che resterebbe
comunque disponibile nel suo ruolo.

Il FVM (valuta ufficiale del listone, che pilota anche il bilanciamento
dell'ordine di chiamata) e' il prior di mercato; le proiezioni da fantamedia
x presenze aggiungono segnale sul rendimento atteso.

Colonne aggiunte:
    primary_role, proj_fantamedia, proj_presenze, proj_points,
    value, value_role (ruolo che massimizza il VOR), vor, tier, rank
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import League

# stagione Euroleghe: si gioca solo quando giocano tutti e 5 i campionati
DEFAULT_SEASON_MATCHES = 30


def _minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(skipna=True), s.max(skipna=True)
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def add_projections(df: pd.DataFrame, season_matches: int = DEFAULT_SEASON_MATCHES) -> pd.DataFrame:
    df = df.copy()
    # fantamedia proiettata: usa quella storica se presente, altrimenti stima da FVM
    fvm = df["fvm"].fillna(0.0)
    fm_from_fvm = 6.0 + fvm / 220.0
    df["proj_fantamedia"] = df["fanta_media"].where(df["fanta_media"].notna(), fm_from_fvm)
    df["proj_fantamedia"] = df["proj_fantamedia"].clip(upper=9.5)

    # presenze proiettate: scala le presenze storiche sulla stagione, cap al totale
    pres = df["presenze"].fillna(0.0)
    max_hist = pres.max() if len(pres) else 0
    if max_hist and max_hist > 0:
        proj_pres = (pres / max_hist * season_matches).clip(upper=season_matches)
    else:
        proj_pres = pd.Series(np.full(len(df), season_matches * 0.6), index=df.index)
    # chi non ha storia (presenze 0) ma ha FVM alto: assume titolarita' medio-alta
    proj_pres = proj_pres.where(pres > 0, np.maximum(proj_pres, season_matches * 0.55))
    df["proj_presenze"] = proj_pres.round(1)

    df["proj_points"] = (df["proj_fantamedia"] * df["proj_presenze"]).round(1)
    return df


def add_value(df: pd.DataFrame, w_fvm: float = 0.6, w_points: float = 0.4) -> pd.DataFrame:
    """`value` = combinazione normalizzata di FVM e fantapunti proiettati (0-100)."""
    df = df.copy()
    if "proj_points" not in df:
        df = add_projections(df)
    nf = _minmax(df["fvm"].fillna(0.0))
    npt = _minmax(df["proj_points"].fillna(0.0))
    total = (w_fvm * nf + w_points * npt)
    df["value"] = (total / total.max() * 100 if total.max() else total).round(2)
    df["primary_role"] = df["roles"].apply(lambda r: r[0] if isinstance(r, list) and r else None)
    return df


def replacement_levels(df: pd.DataFrame, league: League) -> dict[str, float]:
    """Valore di rimpiazzo per ruolo = value del giocatore in posizione
    (managers * fabbisogno_ruolo) tra tutti gli eleggibili a quel ruolo."""
    targets = dict(league.roster_targets)
    targets["Por"] = league.n_goalkeepers
    managers = league.managers
    levels: dict[str, float] = {}
    for role, per_team in targets.items():
        demand = max(1, managers * int(per_team))
        eligible = df[df["roles"].apply(lambda rs: role in rs)]
        vals = eligible["value"].sort_values(ascending=False).to_numpy()
        if len(vals) == 0:
            levels[role] = 0.0
        else:
            idx = min(demand, len(vals) - 1)
            levels[role] = float(vals[idx])
    return levels


def add_vor(df: pd.DataFrame, league: League) -> pd.DataFrame:
    """VOR = value - miglior rimpiazzo tra i ruoli del giocatore (premia la flessibilita').

    `value_role` = il ruolo che massimizza il VOR (dove il giocatore e' piu' prezioso).
    """
    df = df.copy()
    levels = replacement_levels(df, league)

    def compute(row):
        roles = row["roles"] if isinstance(row["roles"], list) else []
        if not roles:
            return pd.Series({"vor": 0.0, "value_role": None})
        # VOR per ruolo = value - livello_rimpiazzo(ruolo); prendo il massimo
        best_role, best_vor = None, -1e9
        for r in roles:
            lvl = levels.get(r, 0.0)
            v = row["value"] - lvl
            if v > best_vor:
                best_vor, best_role = v, r
        return pd.Series({"vor": round(best_vor, 2), "value_role": best_role})

    df[["vor", "value_role"]] = df.apply(compute, axis=1)
    return df


def add_tiers(df: pd.DataFrame, gap_factor: float = 1.6) -> pd.DataFrame:
    """Assegna i tier DENTRO ogni ruolo primario per salti di valore (natural breaks).

    Nuovo tier quando il calo di value rispetto al giocatore precedente supera
    `gap_factor` volte il calo mediano nel ruolo. I tier bassi sono i migliori.
    """
    df = df.copy()
    df["tier"] = 0
    for role, grp in df.groupby("primary_role"):
        g = grp.sort_values("value", ascending=False)
        vals = g["value"].to_numpy()
        if len(vals) <= 1:
            df.loc[g.index, "tier"] = 1
            continue
        diffs = -np.diff(vals)  # cali positivi
        med = np.median(diffs[diffs > 0]) if np.any(diffs > 0) else 0.0
        tiers, cur = [1], 1
        for d in diffs:
            if med > 0 and d > gap_factor * med:
                cur += 1
            tiers.append(cur)
        df.loc[g.index, "tier"] = tiers
    return df


def build_big_board(df: pd.DataFrame, league: League,
                    w_fvm: float = 0.6, w_points: float = 0.4,
                    season_matches: int = DEFAULT_SEASON_MATCHES) -> pd.DataFrame:
    """Pipeline completa: proiezioni -> value -> VOR -> tiers -> ranking."""
    df = add_projections(df, season_matches=season_matches)
    df = add_value(df, w_fvm=w_fvm, w_points=w_points)
    df = add_vor(df, league)
    df = add_tiers(df)
    df = df.sort_values(["vor", "value"], ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df
