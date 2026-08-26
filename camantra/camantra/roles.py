"""Ruoli Mantra: normalizzazione e copertura moduli.

Due funzioni chiave:
  - `normalize_roles`: da stringa listone ("Dd;Ds", "E/W", "A;Pc") -> lista canonica.
  - `best_module_coverage`: dato l'insieme dei giocatori (con i loro ruoli
    ammessi) e i moduli della lega, calcola quali moduli sono schierabili
    tramite matching bipartito giocatori<->slot (Hopcroft-Karp / augmenting path).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


def normalize_roles(raw: str | list[str], aliases: dict[str, str]) -> list[str]:
    """Converte la notazione ruoli del listone in ruoli canonici, deduplicati.

    Accetta separatori ';', '/', ',', spazi. Applica gli alias (P->Por,
    Td->Dd, Ts->Ds, ...). Mantiene l'ordine di prima apparizione.
    """
    if isinstance(raw, list):
        tokens = raw
    else:
        tokens = re.split(r"[;/,\s|]+", str(raw).strip())
    out: list[str] = []
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        t = aliases.get(t, aliases.get(t.capitalize(), t))
        # canonicalizza capitalizzazione tipo "dc" -> "Dc", "PC" -> "Pc"
        canon = _canon_case(t)
        canon = aliases.get(canon, canon)
        if canon and canon not in out:
            out.append(canon)
    return out


def _canon_case(t: str) -> str:
    special = {"POR": "Por", "DC": "Dc", "DD": "Dd", "DS": "Ds", "PC": "Pc"}
    if t.upper() in special:
        return special[t.upper()]
    if len(t) == 1:
        return t.upper()
    return t[0].upper() + t[1:].lower()


# ---------------------------------------------------------------------- #
# Copertura moduli via matching bipartito
# ---------------------------------------------------------------------- #

@dataclass
class CoverageResult:
    module: str
    playable: bool
    filled: int          # slot coperti
    total: int           # 11
    missing_slots: list[str]   # descrizione slot non coperti (ruoli ammessi)


def _can_fill(player_roles: list[str], slot_roles: list[str]) -> bool:
    return any(r in slot_roles for r in player_roles)


def _max_matching(players: list[list[str]], slots: list[list[str]]) -> tuple[int, list[int]]:
    """Massimo matching bipartito players->slots (augmenting path, Kuhn).

    Ritorna (dimensione_matching, match_of_slot) dove match_of_slot[j] = indice
    del giocatore assegnato allo slot j, oppure -1.
    """
    match_of_slot = [-1] * len(slots)

    def try_assign(p: int, seen: list[bool]) -> bool:
        for j, slot in enumerate(slots):
            if seen[j]:
                continue
            if _can_fill(players[p], slot):
                seen[j] = True
                if match_of_slot[j] == -1 or try_assign(match_of_slot[j], seen):
                    match_of_slot[j] = p
                    return True
        return False

    size = 0
    for p in range(len(players)):
        seen = [False] * len(slots)
        if try_assign(p, seen):
            size += 1
    return size, match_of_slot


def module_coverage(player_roles_list: list[list[str]],
                    module_name: str,
                    slots: list[list[str]]) -> CoverageResult:
    """Verifica se l'insieme di giocatori puo' riempire tutti gli 11 slot."""
    size, match_of_slot = _max_matching(player_roles_list, slots)
    missing = [
        "/".join(slots[j]) for j in range(len(slots)) if match_of_slot[j] == -1
    ]
    return CoverageResult(
        module=module_name,
        playable=(size == len(slots)),
        filled=size,
        total=len(slots),
        missing_slots=missing,
    )


def assign_module(player_roles_list: list[list[str]],
                  slots: list[list[str]],
                  priority: list[int] | None = None) -> list[int]:
    """Ritorna match_of_slot[j] = indice giocatore assegnato allo slot j (o -1).

    Se `priority` è dato (es. indici ordinati per valore decrescente), i
    giocatori vengono provati in quell'ordine, così l'assegnazione tende a
    usare i titolari migliori (utile per un 'miglior XI' indicativo).
    """
    order = priority if priority is not None else list(range(len(player_roles_list)))
    ordered = [player_roles_list[i] for i in order]
    _, match_local = _max_matching(ordered, slots)
    # rimappa gli indici locali (ordinati) sugli indici originali
    return [order[p] if p != -1 else -1 for p in match_local]


def best_module_coverage(player_roles_list: list[list[str]],
                         modules: dict[str, list[list[str]]]) -> list[CoverageResult]:
    """Copertura per tutti i moduli, ordinata: schierabili prima, poi per slot coperti."""
    results = [module_coverage(player_roles_list, name, slots)
               for name, slots in modules.items()]
    results.sort(key=lambda r: (not r.playable, -(r.filled)))
    return results
