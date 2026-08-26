"""Camantra — Home / Big Board.

Avvio:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import streamlit as st

from common import get_league, init_page, tier_style

board = init_page("Big Board", "🎯")
league = get_league()

st.title("🎯 Camantra — Big Board Euroleghe")
st.caption(
    f"Draft Mantra a {league.managers} · crediti infiniti · "
    f"ranking per **VOR** (value over replacement) con **FVM** come prior di mercato."
)

# ---- metriche di testa ------------------------------------------------ #
c1, c2, c3, c4 = st.columns(4)
c1.metric("Giocatori nel listone", len(board))
c2.metric("Squadre", board["team"].nunique())
c3.metric("Campionati", board["league"].nunique())
c4.metric("Chiamate totali draft", league.managers * league.roster_size)

# ---- filtri ----------------------------------------------------------- #
st.sidebar.header("🔎 Filtri board")
roles = sorted({r for rs in board["roles"] for r in rs})
leagues_opt = ["(tutti)"] + sorted(board["league"].dropna().unique().tolist())
f_role = st.sidebar.multiselect("Ruolo (ammesso)", roles)
f_league = st.sidebar.selectbox("Campionato", leagues_opt)
f_team = st.sidebar.text_input("Squadra contiene")
f_name = st.sidebar.text_input("Nome contiene")
max_tier = st.sidebar.slider("Tier massimo (per ruolo)", 1, 7, 7)

view = board.copy()
if f_role:
    view = view[view["roles"].apply(lambda rs: any(r in rs for r in f_role))]
if f_league != "(tutti)":
    view = view[view["league"] == f_league]
if f_team:
    view = view[view["team"].str.contains(f_team, case=False, na=False)]
if f_name:
    view = view[view["name"].str.contains(f_name, case=False, na=False)]
view = view[view["tier"] <= max_tier]

cols = ["rank", "name", "team", "league", "role_str", "value_role",
        "fvm", "proj_fantamedia", "proj_points", "value", "vor", "tier"]
show = view[cols].rename(columns={
    "role_str": "ruoli", "value_role": "ruolo_val", "proj_fantamedia": "fm_proj",
    "proj_points": "pt_proj",
})

st.subheader(f"Listone ordinato per VOR — {len(show)} giocatori")
st.dataframe(tier_style(show), use_container_width=True, height=560, hide_index=True)

st.download_button(
    "⬇️ Scarica big board (CSV)",
    data=show.to_csv(index=False).encode("utf-8"),
    file_name="camantra_big_board.csv",
    mime="text/csv",
)

# ---- migliori per ruolo ---------------------------------------------- #
st.subheader("🏅 Top 5 per ruolo (per VOR)")
role_cols = st.columns(4)
target_roles = league.canonical_roles
for i, role in enumerate(target_roles):
    grp = board[board["roles"].apply(lambda rs: role in rs)].nlargest(5, "vor")
    with role_cols[i % 4]:
        st.markdown(f"**{role}**")
        st.dataframe(grp[["name", "team", "vor"]], hide_index=True,
                     use_container_width=True, height=210)

with st.expander("ℹ️ Come leggere la board / metodo"):
    st.markdown(
        """
- **VOR** (Value Over Replacement): quanto un giocatore batte il *rimpiazzo* nel
  suo ruolo (il miglior giocatore che resterebbe comunque disponibile).
  In un draft a crediti infiniti è la metrica corretta: premia chi è scarso nel ruolo.
- **value_role**: il ruolo in cui il giocatore rende il VOR massimo (utile per i multi-ruolo).
- **FVM**: valuta ufficiale del listone; pilota anche l'ordine di chiamata dai round ≥2.
- **tier**: fasce per ruolo calcolate sui *salti* di valore (dentro lo stesso ruolo).
- Regola i **pesi FVM/fantapunti** dalla sidebar per spostare l'accento tra
  mercato e rendimento atteso.
        """
    )
