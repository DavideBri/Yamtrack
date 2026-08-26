"""Helper condivisi dalle pagine Streamlit (caricamento dati, sidebar, stato)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# rendi importabile il pacchetto camantra quando si lancia `streamlit run`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camantra.config import League, load_league  # noqa: E402
from camantra.engine.value import build_big_board  # noqa: E402
from camantra.store import DATA_DIR, find_real_listone, load_players  # noqa: E402

TIER_COLORS = ["#1a9850", "#66bd63", "#a6d96a", "#fee08b", "#fdae61", "#f46d43", "#d73027"]


@st.cache_resource
def get_league() -> League:
    return load_league()


@st.cache_data(show_spinner=False)
def _load_board(source_key: str, w_fvm: float, w_points: float) -> pd.DataFrame:
    league = get_league()
    path = None if source_key == "SAMPLE" else source_key
    players = load_players(league, path=path)
    board = build_big_board(players, league, w_fvm=w_fvm, w_points=w_points)
    return board


def data_source_sidebar() -> str:
    """Gestisce il caricamento del listone reale. Ritorna la source-key
    ('SAMPLE' oppure il path del file reale)."""
    st.sidebar.header("📂 Dati")
    real = find_real_listone()
    if real is not None:
        st.sidebar.success(f"Listone reale: **{real.name}**")
        source = str(real)
    else:
        st.sidebar.warning("Dati **SAMPLE** (sintetici). Carica il listone reale.")
        source = "SAMPLE"

    up = st.sidebar.file_uploader("Carica listone Euroleghe (xlsx/csv)",
                                  type=["xlsx", "xls", "csv"])
    if up is not None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(up.name).suffix.lower()
        dest = DATA_DIR / ("listone" + (ext if ext in (".xlsx", ".csv") else ".xlsx"))
        dest.write_bytes(up.getbuffer())
        st.sidebar.success(f"Salvato in {dest.name}. Ricarico…")
        _load_board.clear()
        st.rerun()
    return source


def value_weights_sidebar() -> tuple[float, float]:
    st.sidebar.header("⚖️ Pesi valore")
    w_fvm = st.sidebar.slider("Peso FVM (mercato)", 0.0, 1.0, 0.6, 0.05)
    w_points = round(1.0 - w_fvm, 2)
    st.sidebar.caption(f"Peso fantapunti proiettati: **{w_points}**")
    return w_fvm, w_points


def get_board() -> pd.DataFrame:
    source = st.session_state.get("source", "SAMPLE")
    w_fvm = st.session_state.get("w_fvm", 0.6)
    w_points = st.session_state.get("w_points", 0.4)
    return _load_board(source, w_fvm, w_points)


def init_page(title: str, icon: str = "⚽") -> pd.DataFrame:
    """Config pagina + sidebar comuni. Ritorna la big board pronta."""
    st.set_page_config(page_title=f"Camantra · {title}", page_icon=icon, layout="wide")
    st.session_state["source"] = data_source_sidebar()
    w_fvm, w_points = value_weights_sidebar()
    st.session_state["w_fvm"], st.session_state["w_points"] = w_fvm, w_points
    board = get_board()
    if bool(board["is_sample"].iloc[0]):
        st.info("⚠️ Stai lavorando su **dati SAMPLE sintetici**. "
                "Carica il listone Euroleghe reale (sidebar) per decisioni vere.", icon="⚠️")
    return board


def tier_style(df: pd.DataFrame):
    def color_tier(v):
        try:
            c = TIER_COLORS[min(int(v) - 1, len(TIER_COLORS) - 1)]
            return f"background-color: {c}; color: #111;"
        except Exception:
            return ""
    if "tier" in df.columns:
        return df.style.map(color_tier, subset=["tier"])
    return df.style
