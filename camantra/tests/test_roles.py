from camantra.roles import (
    assign_module,
    best_module_coverage,
    module_coverage,
    normalize_roles,
)

ALIASES = {"P": "Por", "Td": "Dd", "Ts": "Ds"}


def test_normalize_separators_and_aliases():
    assert normalize_roles("Dd;Ds", ALIASES) == ["Dd", "Ds"]
    assert normalize_roles("E/W", ALIASES) == ["E", "W"]
    assert normalize_roles("P", ALIASES) == ["Por"]
    assert normalize_roles("Td;Ts", ALIASES) == ["Dd", "Ds"]
    assert normalize_roles("A, Pc", ALIASES) == ["A", "Pc"]


def test_normalize_dedup_and_case():
    assert normalize_roles("dc;DC;Dc", ALIASES) == ["Dc"]
    assert normalize_roles("pc", ALIASES) == ["Pc"]


def test_module_coverage_full_and_partial():
    # 11 giocatori mono-ruolo che coprono esattamente un 4-3-3
    slots = [["Por"], ["Dd"], ["Dc"], ["Dc"], ["Ds"], ["M", "C"], ["M"],
             ["C"], ["W", "A"], ["W", "A"], ["A", "Pc"]]
    players = [["Por"], ["Dd"], ["Dc"], ["Dc"], ["Ds"], ["M"], ["M"],
               ["C"], ["W"], ["A"], ["Pc"]]
    res = module_coverage(players, "4-3-3", slots)
    assert res.playable and res.filled == 11

    # togli il portiere -> non schierabile
    res2 = module_coverage(players[1:], "4-3-3", slots)
    assert not res2.playable and "Por" in res2.missing_slots


def test_multirole_player_fills_scarce_slot():
    # un solo giocatore E;W deve poter coprire uno slot [W] se serve
    slots = [["W"], ["E"]]
    players = [["E", "W"], ["E"]]
    match = assign_module(players, slots)
    assert -1 not in match  # entrambi gli slot coperti


def test_best_coverage_orders_playable_first(league, board):
    # una rosa reale-sample di 15 giocatori deve produrre un ordinamento coerente
    sample_players = board.head(30)["roles"].tolist()
    cov = best_module_coverage(sample_players, league.modules)
    # i moduli schierabili (se presenti) vengono prima dei non schierabili
    playable_flags = [c.playable for c in cov]
    assert playable_flags == sorted(playable_flags, reverse=True)
