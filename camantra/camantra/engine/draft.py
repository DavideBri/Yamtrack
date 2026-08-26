"""Draft engine: snake bilanciato sul FVM (regolamento Camantra).

Regole di ordine:
  - Round 1: ordine sorteggiato (`round1_order`).
  - Round >= 2: si riparte dalla squadra col FVM di rosa piu' BASSO, in ordine
    crescente di FVM. L'ordine di un round e' determinato dallo stato di rosa
    al termine del round precedente -> quindi e' deterministico dato lo storico
    delle chiamate.

Lo stato e' un semplice dict (serializzabile per la sessione Streamlit / JSON):
    {
      "managers": [nomi...],           # len == league.managers
      "my_index": int,                 # indice della MIA squadra
      "round1_order": [idx...],        # permutazione degli indici manager
      "picks": [ {overall, round, manager, player_id, name, value_role, fvm}, ...]
    }
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from ..config import League


# --------------------------------------------------------------------- #
# Stato e helper
# --------------------------------------------------------------------- #

def new_state(league: League, manager_names: list[str], my_index: int,
              round1_order: list[int] | None = None) -> dict:
    M = league.managers
    if len(manager_names) != M:
        raise ValueError(f"Attesi {M} nomi manager, ricevuti {len(manager_names)}")
    if round1_order is None:
        round1_order = list(range(M))
    if sorted(round1_order) != list(range(M)):
        raise ValueError("round1_order deve essere una permutazione di 0..managers-1")
    return {
        "managers": list(manager_names),
        "my_index": int(my_index),
        "round1_order": list(round1_order),
        "picks": [],
    }


def team_fvm_after(state: dict, n_picks: int, fvm_by_pid: dict[int, float]) -> dict[int, float]:
    """FVM cumulato per manager considerando solo i primi `n_picks`."""
    totals = {i: 0.0 for i in range(len(state["managers"]))}
    for pick in state["picks"][:n_picks]:
        totals[pick["manager"]] += float(fvm_by_pid.get(pick["player_id"], 0.0))
    return totals


def order_for_round(state: dict, league: League, round_idx: int,
                    fvm_by_pid: dict[int, float]) -> list[int]:
    """Ordine di chiamata (lista indici manager) per il round dato (0-based)."""
    M = league.managers
    if round_idx <= 0:
        return list(state["round1_order"])
    totals = team_fvm_after(state, round_idx * M, fvm_by_pid)
    pos_in_r1 = {m: i for i, m in enumerate(state["round1_order"])}
    # crescente per FVM; tie-break stabile sull'ordine del round 1
    return sorted(range(M), key=lambda m: (totals[m], pos_in_r1[m], m))


def current_round_slot(state: dict, league: League) -> tuple[int, int]:
    n = len(state["picks"])
    return n // league.managers, n % league.managers


def on_the_clock(state: dict, league: League, fvm_by_pid: dict[int, float]) -> int | None:
    """Indice del manager di turno, o None se draft completo."""
    total = league.managers * league.roster_size
    if len(state["picks"]) >= total:
        return None
    r, s = current_round_slot(state, league)
    return order_for_round(state, league, r, fvm_by_pid)[s]


def my_next_gap(state: dict, league: League, fvm_by_pid: dict[int, float]) -> int:
    """Quante chiamate mancano al MIO prossimo turno (0 = tocca a me ora).

    Esatto entro il round corrente; per il round successivo proietta l'ordine
    con il FVM attuale (l'ordine reale dipendera' dalle chiamate intermedie).
    """
    M = league.managers
    me = state["my_index"]
    n = len(state["picks"])
    total = M * league.roster_size
    r, s = current_round_slot(state, league)

    # resto del round corrente
    cur_order = order_for_round(state, league, r, fvm_by_pid)
    for slot in range(s, M):
        overall = r * M + slot
        if overall >= total:
            return -1
        if cur_order[slot] == me:
            return overall - n

    # round successivo: proiezione con FVM corrente
    if (r + 1) * M >= total:
        return -1
    proj_order = order_for_round(state, league, r + 1, fvm_by_pid)
    slot_next = proj_order.index(me)
    return (r + 1) * M + slot_next - n


def make_pick(state: dict, league: League, player_row: dict,
              fvm_by_pid: dict[int, float]) -> dict:
    """Assegna il giocatore al manager di turno e registra la chiamata."""
    manager = on_the_clock(state, league, fvm_by_pid)
    if manager is None:
        raise ValueError("Draft gia' completo.")
    r, _ = current_round_slot(state, league)
    pick = {
        "overall": len(state["picks"]) + 1,
        "round": r + 1,
        "manager": manager,
        "player_id": int(player_row["player_id"]),
        "name": player_row.get("name"),
        "value_role": player_row.get("value_role") or player_row.get("primary_role"),
        "fvm": float(player_row.get("fvm") or 0.0),
    }
    state["picks"].append(pick)
    return pick


def undo_pick(state: dict) -> dict | None:
    return state["picks"].pop() if state["picks"] else None


def drafted_player_ids(state: dict) -> set[int]:
    return {p["player_id"] for p in state["picks"]}


def my_roster_ids(state: dict) -> list[int]:
    return [p["player_id"] for p in state["picks"] if p["manager"] == state["my_index"]]


def available(board: pd.DataFrame, state: dict) -> pd.DataFrame:
    taken = drafted_player_ids(state)
    return board[~board["player_id"].isin(taken)].copy()


# --------------------------------------------------------------------- #
# Bisogni di rosa e raccomandazioni
# --------------------------------------------------------------------- #

def role_counts(state: dict, board: pd.DataFrame, manager: int) -> dict[str, int]:
    """Conteggio per ruolo-di-valore dei giocatori gia' presi dal manager."""
    by_pid = board.set_index("player_id")
    counts: dict[str, int] = {}
    for p in state["picks"]:
        if p["manager"] != manager:
            continue
        role = p.get("value_role")
        if role is None and p["player_id"] in by_pid.index:
            role = by_pid.loc[p["player_id"], "value_role"]
        if role:
            counts[role] = counts.get(role, 0) + 1
    return counts


def _need_multiplier(role: str, counts: dict[str, int], targets: dict[str, int]) -> float:
    have = counts.get(role, 0)
    target = targets.get(role, 0)
    if target == 0:
        return 0.9
    if have == 0:
        return 1.25          # ruolo scoperto: priorita' alta
    if have < target:
        return 1.12
    if have == target:
        return 1.0
    return 0.8               # ruolo gia' saturo


def survival_probability(board_pos: int, gap: int, scale: float = 1.6) -> float:
    """Prob. che un giocatore in posizione `board_pos` (tra i disponibili)
    sopravviva `gap` chiamate. Euristica logistica: sopravvive se ci sono piu'
    giocatori "sopra di lui" di quante chiamate lo separano dal tuo turno."""
    if gap <= 0:
        return 1.0
    x = (board_pos - gap) / scale
    return round(1.0 / (1.0 + math.exp(-x)), 3)


@dataclass
class Recommendation:
    player_id: int
    name: str
    value_role: str
    team: str
    league: str
    vor: float
    score: float
    need_mult: float
    survival: float
    reason: str


def recommend(board: pd.DataFrame, state: dict, league: League,
              top_n: int = 8) -> list[Recommendation]:
    """Migliori chiamate per la MIA squadra: VOR pesato sui bisogni di rosa,
    con probabilita' di sopravvivenza al prossimo turno."""
    avail = available(board, state).sort_values(["vor", "value"], ascending=False).reset_index(drop=True)
    targets = dict(league.roster_targets)
    targets["Por"] = league.n_goalkeepers
    counts = role_counts(state, board, state["my_index"])
    fvm_by_pid = dict(zip(board["player_id"], board["fvm"].fillna(0.0)))
    gap = my_next_gap(state, league, fvm_by_pid)

    recs: list[Recommendation] = []
    for pos, (_, row) in enumerate(avail.iterrows()):
        role = row["value_role"]
        nm = _need_multiplier(role, counts, targets)
        score = float(row["vor"]) * nm
        surv = survival_probability(pos, gap if gap > 0 else 0)
        have = counts.get(role, 0)
        tgt = targets.get(role, 0)
        reason = _reason(role, have, tgt, surv, gap)
        recs.append(Recommendation(
            player_id=int(row["player_id"]), name=row["name"], value_role=role,
            team=row.get("team") or "", league=row.get("league") or "",
            vor=float(row["vor"]), score=round(score, 2), need_mult=nm,
            survival=surv, reason=reason,
        ))
    recs.sort(key=lambda r: r.score, reverse=True)
    return recs[:top_n]


def _reason(role, have, tgt, surv, gap) -> str:
    bits = [f"{role}: hai {have}/{tgt}"]
    if have == 0 and tgt > 0:
        bits.append("ruolo scoperto")
    elif have >= tgt and tgt > 0:
        bits.append("ruolo pieno")
    if gap > 0:
        if surv < 0.35:
            bits.append(f"rischio alto di perderlo (surv {int(surv*100)}% a -{gap})")
        elif surv > 0.7:
            bits.append(f"probabile ancora al tuo turno (surv {int(surv*100)}%)")
    return " · ".join(bits)
