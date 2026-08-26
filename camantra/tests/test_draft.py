import pytest

from camantra.engine import draft as D


@pytest.fixture
def setup(league, board):
    names = [f"Team{i+1}" for i in range(league.managers)]
    state = D.new_state(league, names, my_index=0, round1_order=list(range(league.managers)))
    fvm_by_pid = dict(zip(board["player_id"], board["fvm"].fillna(0.0)))
    return state, board, fvm_by_pid


def test_new_state_validates_order(league):
    names = [f"T{i}" for i in range(league.managers)]
    with pytest.raises(ValueError):
        D.new_state(league, names, 0, round1_order=[0] * league.managers)


def test_round1_follows_draw_order(league, setup):
    state, board, fvm = setup
    assert D.on_the_clock(state, league, fvm) == state["round1_order"][0]


def test_round2_order_is_team_fvm_ascending(league, setup):
    state, board, fvm = setup
    M = league.managers
    top = board.sort_values("fvm", ascending=False)
    # round 1: ogni manager (in ordine) prende un giocatore a FVM decrescente,
    # cosi' Team1 accumula il FVM piu' alto e Team_M il piu' basso.
    for i in range(M):
        row = top.iloc[i].to_dict()
        D.make_pick(state, league, row, fvm)
    order2 = D.order_for_round(state, league, 1, fvm)
    totals = D.team_fvm_after(state, M, fvm)
    # il primo a chiamare nel round 2 deve avere il FVM piu' basso
    assert totals[order2[0]] == min(totals.values())
    assert totals[order2[-1]] == max(totals.values())
    # ordine effettivamente crescente per FVM
    seq = [totals[m] for m in order2]
    assert seq == sorted(seq)


def test_make_and_undo_pick(league, setup):
    state, board, fvm = setup
    row = board.iloc[0].to_dict()
    D.make_pick(state, league, row, fvm)
    assert len(state["picks"]) == 1
    assert row["player_id"] in D.drafted_player_ids(state)
    D.undo_pick(state)
    assert state["picks"] == []


def test_available_excludes_drafted(league, setup):
    state, board, fvm = setup
    pid = int(board.iloc[0]["player_id"])
    D.make_pick(state, league, board.iloc[0].to_dict(), fvm)
    assert pid not in set(D.available(board, state)["player_id"])


def test_my_next_gap_zero_when_my_turn(league, board):
    names = [f"Team{i+1}" for i in range(league.managers)]
    # metto la mia squadra prima nell'ordine del round 1
    state = D.new_state(league, names, my_index=3, round1_order=[3, 0, 1, 2, 4, 5, 6, 7])
    fvm = dict(zip(board["player_id"], board["fvm"].fillna(0.0)))
    assert D.on_the_clock(state, league, fvm) == 3
    assert D.my_next_gap(state, league, fvm) == 0


def test_recommend_prioritizes_uncovered_roles(league, setup):
    state, board, fvm = setup
    recs = D.recommend(board, state, league, top_n=5)
    assert recs
    # a rosa vuota, tutti i ruoli sono scoperti: la top-reco ha need_mult alto
    assert recs[0].need_mult >= 1.0
    assert 0.0 <= recs[0].survival <= 1.0


def test_full_draft_runs_to_completion(league, setup):
    state, board, fvm = setup
    total = league.managers * league.roster_size
    guard = 0
    while D.on_the_clock(state, league, fvm) is not None and guard < total + 5:
        avail = D.available(board, state).sort_values("vor", ascending=False)
        D.make_pick(state, league, avail.iloc[0].to_dict(), fvm)
        guard += 1
    assert len(state["picks"]) == total
    # ogni manager ha esattamente roster_size giocatori
    for m in range(league.managers):
        assert sum(1 for p in state["picks"] if p["manager"] == m) == league.roster_size
