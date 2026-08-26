"""Draft Room live — assistente durante l'asta draft.

Mostra chi è di turno, le migliori chiamate per la TUA squadra (VOR pesato sui
bisogni + probabilità di sopravvivenza), e registra le chiamate di tutti.
L'ordine dei round ≥2 si ricalcola da solo sul FVM di rosa (regolamento).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_league, init_page  # noqa: E402

from camantra.engine import draft as D  # noqa: E402

board = init_page("Draft Room", "🎯")
league = get_league()
fvm_by_pid = dict(zip(board["player_id"], board["fvm"].fillna(0.0)))

st.title("🎯 Draft Room")

# --------------------------------------------------------------------- #
# Setup del draft
# --------------------------------------------------------------------- #
if "draft" not in st.session_state:
    st.subheader("Imposta il draft")
    with st.form("setup"):
        cols = st.columns(2)
        names = []
        for i in range(league.managers):
            with cols[i % 2]:
                names.append(st.text_input(f"Manager {i+1}", value=f"Team{i+1}", key=f"mgr{i}"))
        my_name = st.selectbox("Qual è la TUA squadra?", names)
        st.caption("Ordine del round 1 (sorteggiato in lega). Lascia l'ordine dei nomi "
                   "sopra oppure sorteggialo qui sotto.")
        randomize = st.checkbox("Sorteggia ordine round 1")
        submitted = st.form_submit_button("🚀 Avvia draft", type="primary")
    if submitted:
        order = list(range(league.managers))
        if randomize:
            import random
            random.shuffle(order)
        st.session_state["draft"] = D.new_state(
            league, names, my_index=names.index(my_name), round1_order=order)
        st.rerun()
    st.stop()

state = st.session_state["draft"]
me = state["my_index"]
names = state["managers"]
total_picks = league.managers * league.roster_size

# --------------------------------------------------------------------- #
# Barra di stato
# --------------------------------------------------------------------- #
clock = D.on_the_clock(state, league, fvm_by_pid)
gap = D.my_next_gap(state, league, fvm_by_pid)
r, s = D.current_round_slot(state, league)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Round", f"{r+1} / {league.roster_size}")
k2.metric("Chiamata", f"{len(state['picks'])} / {total_picks}")
if clock is None:
    k3.metric("Di turno", "— fine —")
else:
    is_me = clock == me
    k3.metric("Di turno", ("🟢 TU" if is_me else names[clock]))
k4.metric("Al tuo prossimo turno", "ora" if gap == 0 else (f"-{gap}" if gap > 0 else "—"))

if clock is not None and clock == me:
    st.success("🟢 **Tocca a te!** Scegli dalla lista raccomandata qui sotto.", icon="🟢")

tab_pick, tab_reco, tab_rose = st.tabs(["📋 Registra chiamata", "⭐ Raccomandazioni", "👥 Rose"])

# --------------------------------------------------------------------- #
# TAB — registra chiamata
# --------------------------------------------------------------------- #
with tab_pick:
    avail = D.available(board, state).sort_values(["vor", "value"], ascending=False)
    st.caption(f"{len(avail)} giocatori disponibili.")

    fc1, fc2, fc3 = st.columns(3)
    q_role = fc1.multiselect("Filtra ruolo", sorted({x for rs in avail["roles"] for x in rs}))
    q_league = fc2.selectbox("Filtra campionato", ["(tutti)"] + sorted(avail["league"].dropna().unique().tolist()))
    q_name = fc3.text_input("Cerca nome/squadra")

    fview = avail
    if q_role:
        fview = fview[fview["roles"].apply(lambda rs: any(x in rs for x in q_role))]
    if q_league != "(tutti)":
        fview = fview[fview["league"] == q_league]
    if q_name:
        m = fview["name"].str.contains(q_name, case=False, na=False) | \
            fview["team"].str.contains(q_name, case=False, na=False)
        fview = fview[m]

    options = fview.head(300)
    labels = {int(row.player_id): f"{row.name}  ·  {row.team}  ·  {row.role_str}  ·  FVM {int(row.fvm)}  ·  VOR {row.vor}"
              for row in options.itertuples()}
    if clock is not None and labels:
        sel = st.selectbox(f"Assegna a **{names[clock]}**", list(labels.keys()),
                           format_func=lambda pid: labels[pid])
        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("✅ Assegna", type="primary"):
            row = board[board["player_id"] == sel].iloc[0].to_dict()
            D.make_pick(state, league, row, fvm_by_pid)
            st.rerun()
        if b2.button("⚡ Best-available (avversario)"):
            row = avail.iloc[0].to_dict()
            D.make_pick(state, league, row, fvm_by_pid)
            st.rerun()
    elif clock is None:
        st.info("Draft completo.")

    st.divider()
    u1, u2, u3 = st.columns([1, 1, 2])
    if u1.button("↩️ Annulla ultima"):
        D.undo_pick(state)
        st.rerun()
    if u2.button("🗑️ Reset draft"):
        del st.session_state["draft"]
        st.rerun()
    u3.download_button("💾 Salva stato (JSON)",
                       data=json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="camantra_draft.json", mime="application/json")
    up = st.file_uploader("Carica stato draft (JSON)", type=["json"])
    if up is not None:
        st.session_state["draft"] = json.loads(up.getvalue().decode("utf-8"))
        st.rerun()

    if state["picks"]:
        st.caption("Ultime chiamate")
        recent = [{"#": p["overall"], "round": p["round"], "manager": names[p["manager"]],
                   "giocatore": p["name"], "ruolo": p["value_role"], "FVM": p["fvm"]}
                  for p in state["picks"][-12:][::-1]]
        st.dataframe(recent, hide_index=True, use_container_width=True)

# --------------------------------------------------------------------- #
# TAB — raccomandazioni per me
# --------------------------------------------------------------------- #
with tab_reco:
    st.caption("Migliori chiamate per la **tua** squadra: VOR pesato sui bisogni di "
               "rosa, con probabilità di sopravvivenza fino al tuo prossimo turno.")
    recs = D.recommend(board, state, league, top_n=12)
    if not recs:
        st.info("Nessun giocatore disponibile.")
    else:
        rows = [{"giocatore": r.name, "ruolo": r.value_role, "squadra": r.team,
                 "campionato": r.league, "VOR": r.vor, "score": r.score,
                 "survival": r.survival, "note": r.reason} for r in recs]
        st.dataframe(rows, hide_index=True, use_container_width=True, height=460)
        top = recs[0]
        st.success(f"👉 Consiglio ora: **{top.name}** ({top.value_role}, {top.team}) — {top.reason}")

# --------------------------------------------------------------------- #
# TAB — rose
# --------------------------------------------------------------------- #
with tab_rose:
    targets = dict(league.roster_targets)
    targets["Por"] = league.n_goalkeepers

    st.markdown(f"### 👑 La tua rosa — {names[me]}")
    my_counts = D.role_counts(state, board, me)
    n_mine = len(D.my_roster_ids(state))
    st.caption(f"{n_mine} / {league.roster_size} giocatori")
    fill_cols = st.columns(6)
    for i, (role, tgt) in enumerate(targets.items()):
        have = my_counts.get(role, 0)
        with fill_cols[i % 6]:
            st.metric(role, f"{have}/{tgt}", delta=(have - tgt if have != tgt else None))
    mine = [p for p in state["picks"] if p["manager"] == me]
    if mine:
        st.dataframe([{"#": p["overall"], "round": p["round"], "giocatore": p["name"],
                       "ruolo": p["value_role"], "FVM": p["fvm"]} for p in mine],
                     hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("### 👥 Rose avversari & FVM squadra")
    totals = D.team_fvm_after(state, len(state["picks"]), fvm_by_pid)
    standings = sorted(range(league.managers), key=lambda m: totals[m])
    st.dataframe(
        [{"squadra": names[m] + (" (tu)" if m == me else ""),
          "giocatori": sum(1 for p in state["picks"] if p["manager"] == m),
          "FVM rosa": round(totals[m], 1)} for m in standings],
        hide_index=True, use_container_width=True,
    )
    st.caption("Nel draft Camantra chi ha **meno FVM chiama prima** nei round ≥2: "
               "tenere il FVM basso ti dà scelte anticipate.")
