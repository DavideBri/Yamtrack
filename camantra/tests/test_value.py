from camantra.engine.value import (
    add_projections,
    add_value,
    add_vor,
    build_big_board,
    replacement_levels,
)


def test_board_has_expected_columns(board):
    for col in ["value", "vor", "tier", "rank", "primary_role", "value_role",
                "proj_points", "proj_fantamedia"]:
        assert col in board.columns


def test_board_sorted_by_vor_desc(board):
    vor = board["vor"].tolist()
    assert vor == sorted(vor, reverse=True)
    assert board["rank"].tolist() == list(range(1, len(board) + 1))


def test_value_is_normalized_0_100(board):
    assert board["value"].max() <= 100.0 + 1e-6
    assert board["value"].min() >= 0.0


def test_replacement_levels_cover_all_target_roles(league, board):
    levels = replacement_levels(board, league)
    for role in league.roster_targets:
        assert role in levels
    assert "Por" in levels


def test_projection_uses_history_when_present(league):
    import pandas as pd
    df = pd.DataFrame([
        {"player_id": 1, "name": "A", "team": "Inter", "league": "Serie A",
         "roles": ["Pc"], "role_str": "Pc", "fvm": 200.0, "fanta_media": 7.5,
         "media_voto": 6.5, "presenze": 30.0, "gol": 20.0, "assist": 5.0},
    ])
    out = add_projections(df)
    assert abs(out["proj_fantamedia"].iloc[0] - 7.5) < 1e-6


def test_vor_rewards_flexibility(league):
    import pandas as pd
    # due giocatori identici per value, ma uno e' anche di un ruolo piu' scarso
    df = pd.DataFrame([
        {"player_id": i, "name": f"p{i}", "team": "Inter", "league": "Serie A",
         "roles": r, "role_str": ";".join(r), "fvm": 100.0, "fanta_media": 6.5,
         "media_voto": 6.2, "presenze": 20.0, "gol": 3.0, "assist": 2.0}
        for i, r in enumerate([["M"], ["M", "Pc"]])
    ])
    df = add_value(add_projections(df))
    df = add_vor(df, league)
    # il multi-ruolo non puo' avere VOR inferiore (sceglie il ruolo migliore)
    assert df.loc[df["player_id"] == 1, "vor"].iloc[0] >= df.loc[df["player_id"] == 0, "vor"].iloc[0]
