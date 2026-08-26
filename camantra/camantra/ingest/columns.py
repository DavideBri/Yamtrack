"""Mapping fuzzy delle colonne del listone/quotazioni.

I file ufficiali di fantacalcio.it / Fantalab / Fantagazzetta cambiano nome
colonna tra Classic/Mantra/Euroleghe e tra un'annata e l'altra. Invece di
hardcodare i nomi, li riconosciamo per sinonimi + fuzzy match, cosi' il
parser regge layout diversi (obiettivo: robustezza, dato che non possiamo
verificare il file dal vivo).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# campo_normalizzato -> lista di sinonimi/etichette possibili nell'header
SYNONYMS: dict[str, list[str]] = {
    "player_id": ["id", "id giocatore", "codice"],
    "name": ["nome", "calciatore", "giocatore", "player", "name"],
    "team": ["squadra", "sq", "team", "club"],
    "role_mantra": ["ruolo mantra", "rm", "r mantra", "ruoli", "ruolo", "r", "mantra"],
    "role_classic": ["ruolo classic", "rc", "r classic", "ruolo classico"],
    "fvm": ["fvm", "fvm mantra", "fvm m", "fantavalore", "fanta valore di mercato",
            "fvm/1000", "fvm 1000"],
    "qt_a": ["qt.a", "qta", "quotazione attuale", "qt a", "qa", "quot attuale"],
    "qt_i": ["qt.i", "qti", "quotazione iniziale", "qt i", "qi", "quot iniziale"],
    "fanta_media": ["fantamedia", "fm", "fanta media", "media fanta"],
    "media_voto": ["media voto", "mv", "mediavoto", "media"],
    "presenze": ["presenze", "pv", "partite", "pres", "gettoni"],
    "gol": ["gol", "goal", "reti", "gf"],
    "assist": ["assist", "ass", "a"],
    "league": ["campionato", "lega", "league", "competizione"],
}


def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[._/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def map_columns(headers: list[str], min_ratio: float = 0.86) -> dict[str, str]:
    """Ritorna {campo_normalizzato: nome_colonna_originale}.

    Priorita': match esatto sul sinonimo, poi fuzzy sopra `min_ratio`.
    Ogni colonna originale e' assegnata al massimo a un campo.
    """
    norm_headers = {h: _norm(h) for h in headers}
    used: set[str] = set()
    mapping: dict[str, str] = {}

    # 1) match esatti
    for field, syns in SYNONYMS.items():
        syn_norm = {_norm(s) for s in syns}
        for orig, nh in norm_headers.items():
            if orig in used:
                continue
            if nh in syn_norm:
                mapping[field] = orig
                used.add(orig)
                break

    # 2) fuzzy per i campi ancora scoperti
    for field, syns in SYNONYMS.items():
        if field in mapping:
            continue
        syn_norm = [_norm(s) for s in syns]
        best_orig, best_ratio = None, 0.0
        for orig, nh in norm_headers.items():
            if orig in used:
                continue
            r = max(_similar(nh, s) for s in syn_norm)
            # bonus se un sinonimo e' contenuto nell'header (o viceversa)
            if any(s in nh or nh in s for s in syn_norm):
                r = max(r, 0.9)
            if r > best_ratio:
                best_orig, best_ratio = orig, r
        if best_orig is not None and best_ratio >= min_ratio:
            mapping[field] = best_orig
            used.add(best_orig)

    return mapping
