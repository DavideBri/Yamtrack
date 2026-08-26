"""Rosa & Moduli — copertura tattica della tua rosa.

Mostra quali dei moduli ammessi sei in grado di schierare (matching ruoli↔slot),
i buchi tattici, e un 'miglior XI' indicativo per il modulo scelto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_league, init_page  # noqa: E402

from camantra.engine import draft as D  # noqa: E402
from camantra.roles import assign_module, best_module_coverage  # noqa: E402

board = init_page("Rosa & Moduli", "🧩")
league = get_league()

st.title("🧩 Rosa & Moduli")

if "draft" not in st.session_state or not st.session_state["draft"]["picks"]:
    st.info("Nessuna rosa ancora. Vai in **Draft Room**, avvia il draft e registra "
            "le chiamate: qui vedrai la copertura tattica in tempo reale.")
    with st.expander("📐 Requisiti dei moduli ammessi"):
        for name, slots in league.modules.items():
            st.markdown(f"**{name}** — " + " · ".join("/".join(sl) for sl in slots))
    st.stop()

state = st.session_state["draft"]
names = state["managers"]

# quale rosa analizzare
who = st.selectbox("Analizza la rosa di", range(league.managers),
                   index=state["my_index"],
                   format_func=lambda m: names[m] + (" (tu)" if m == state["my_index"] else ""))

my_pids = [p["player_id"] for p in state["picks"] if p["manager"] == who]
mine = board[board["player_id"].isin(my_pids)].copy()
if mine.empty:
    st.info("Rosa vuota.")
    st.stop()

mine = mine.sort_values("value", ascending=False).reset_index(drop=True)
roles_list = mine["roles"].tolist()

st.caption(f"{len(mine)} giocatori in rosa.")

# --------------------------------------------------------------------- #
# Copertura di tutti i moduli
# --------------------------------------------------------------------- #
st.subheader("Moduli schierabili")
cov = best_module_coverage(roles_list, league.modules)
rows = [{"modulo": c.module,
         "schierabile": "✅" if c.playable else "❌",
         "slot coperti": f"{c.filled}/{c.total}",
         "buchi": ", ".join(c.missing_slots) if c.missing_slots else "—"} for c in cov]
st.dataframe(rows, hide_index=True, use_container_width=True)

playable = [c.module for c in cov if c.playable]
if playable:
    st.success(f"Puoi schierare **{len(playable)}** moduli: {', '.join(playable)}")
else:
    best = cov[0]
    st.warning(f"Nessun modulo completo. Più vicino: **{best.module}** "
               f"({best.filled}/{best.total}). Ti mancano: {', '.join(best.missing_slots)}")

# --------------------------------------------------------------------- #
# Miglior XI indicativo per un modulo
# --------------------------------------------------------------------- #
st.subheader("Miglior XI indicativo")
module_choice = st.selectbox("Modulo", list(league.modules.keys()),
                             index=(list(league.modules).index(playable[0]) if playable else 0))
slots = league.modules[module_choice]
# priorità per valore decrescente (mine è già ordinata per value desc)
match_of_slot = assign_module(roles_list, slots, priority=list(range(len(mine))))

xi_rows = []
used_value = 0.0
for j, slot in enumerate(slots):
    pidx = match_of_slot[j]
    if pidx == -1:
        xi_rows.append({"slot": "/".join(slot), "giocatore": "— VUOTO —",
                        "ruolo": "", "FVM": "", "value": ""})
    else:
        prow = mine.iloc[pidx]
        used_value += float(prow["value"])
        xi_rows.append({"slot": "/".join(slot), "giocatore": prow["name"],
                        "ruolo": prow["value_role"], "FVM": int(prow["fvm"]),
                        "value": round(float(prow["value"]), 1)})
st.dataframe(xi_rows, hide_index=True, use_container_width=True)
n_filled = sum(1 for j in range(len(slots)) if match_of_slot[j] != -1)
st.caption(f"Slot coperti: {n_filled}/11 · valore titolari (somma): {used_value:.0f}")

# --------------------------------------------------------------------- #
# Riepilogo per ruolo vs target
# --------------------------------------------------------------------- #
st.subheader("Conteggio per ruolo vs target")
targets = dict(league.roster_targets)
targets["Por"] = league.n_goalkeepers
counts = D.role_counts(state, board, who)
role_rows = [{"ruolo": role, "hai": counts.get(role, 0), "target": tgt,
              "diff": counts.get(role, 0) - tgt} for role, tgt in targets.items()]
st.dataframe(role_rows, hide_index=True, use_container_width=True)
st.caption("Nota: i multi-ruolo sono contati nel loro *ruolo di valore*; la "
           "copertura reale dei moduli (sopra) è spesso migliore del conteggio.")
