"""Smoke test: gira l'intera pipeline su dati SAMPLE senza dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camantra.config import load_league
from camantra.engine import draft as D
from camantra.engine.value import build_big_board
from camantra.roles import best_module_coverage
from camantra.store import load_players

league = load_league()
print(f"Lega: {league.name} | manager: {league.managers} | squadre: {len(league.all_teams)}")

df = load_players(league)
print(f"Listone: {len(df)} giocatori | sample={df['is_sample'].iloc[0]}")

board = build_big_board(df, league)
cols = ["rank", "name", "team", "league", "role_str", "value_role", "fvm", "proj_points", "vor", "tier"]
print("\nTop 12 big board:")
print(board[cols].head(12).to_string(index=False))

# simulazione mini-draft
names = [f"Team{i+1}" for i in range(league.managers)]
state = D.new_state(league, names, my_index=0, round1_order=list(range(league.managers)))
fvm_by_pid = dict(zip(board["player_id"], board["fvm"].fillna(0.0)))

# fai 20 chiamate: gli avversari prendono il best-available, io seguo le reco
for _ in range(20):
    mgr = D.on_the_clock(state, league, fvm_by_pid)
    if mgr is None:
        break
    if mgr == state["my_index"]:
        rec = D.recommend(board, state, league, top_n=3)[0]
        row = board[board["player_id"] == rec.player_id].iloc[0].to_dict()
        D.make_pick(state, league, row, fvm_by_pid)
    else:
        avail = D.available(board, state).sort_values("vor", ascending=False)
        D.make_pick(state, league, avail.iloc[0].to_dict(), fvm_by_pid)

print(f"\nChiamate totali simulate: {len(state['picks'])}")
mine = [p for p in state["picks"] if p["manager"] == 0]
print("La MIA rosa finora:", [(p["name"], p["value_role"]) for p in mine])

# ordine del round 2 (deve ripartire dal FVM piu' basso)
order_r2 = D.order_for_round(state, league, 1, fvm_by_pid)
totals = D.team_fvm_after(state, league.managers, fvm_by_pid)
print("\nFVM squadra dopo round 1:", {names[i]: round(totals[i], 1) for i in range(league.managers)})
print("Ordine round 2 (FVM crescente):", [names[i] for i in order_r2])

# raccomandazioni correnti
print("\nRaccomandazioni per la mia squadra ORA:")
for r in D.recommend(board, state, league, top_n=5):
    print(f"  {r.name:26s} {r.value_role:3s} vor={r.vor:6.2f} score={r.score:6.2f} surv={r.survival} | {r.reason}")

# copertura moduli della mia rosa
my_pids = D.my_roster_ids(state)
my_roles = board[board["player_id"].isin(my_pids)]["roles"].tolist()
cov = best_module_coverage(my_roles, league.modules)
print("\nCopertura moduli (mia rosa parziale):")
for c in cov[:4]:
    tag = "OK" if c.playable else f"manca {c.filled}/{c.total}"
    print(f"  {c.module:8s} {tag}")

print("\nSMOKE OK")
