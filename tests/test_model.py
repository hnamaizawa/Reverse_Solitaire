import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.model import GameState, build_state


def test_new_game_contains_52_cards_in_five_card_piles():
    game = GameState.new(seed=1)
    assert game.remaining_cards == 52
    assert len(game.piles) == 11
    assert [len(p) for p in game.piles] == [5] * 10 + [2]


def test_cards_alternate_face_direction_in_each_pile():
    game = GameState.new(seed=2)
    for pile in game.piles:
        for i, pc in enumerate(pile):
            assert pc.face_up == (i % 2 == 0)


def test_flip_keeps_visual_order_and_flips_non_exposed_visibility():
    game = build_state([[('A', '♠', True), ('2', '♠', False), ('3', '♠', True)]])
    before = [pc.card.rank for pc in game.piles[0]]
    game.flip_pile(0)
    assert [pc.card.rank for pc in game.piles[0]] == before
    assert [pc.face_up for pc in game.piles[0]] == [True, True, False]


def test_flip_switches_exposed_end_without_reordering_cards():
    game = build_state([[('A', '♠', True), ('2', '♥', False), ('K', '♦', True)]])
    assert game.top_card(0).card.rank == 'K'
    game.flip_pile(0)
    assert [pc.card.rank for pc in game.piles[0]] == ['A', '2', 'K']
    assert game.top_card(0).card.rank == 'A'


def test_newly_exposed_card_is_always_face_up_after_flip():
    game = build_state([[('A', '♠', True), ('2', '♥', False), ('K', '♦', True)]])
    game.flip_pile(0)
    assert game.top_card(0).card.rank == 'A'
    assert game.top_card(0).face_up is True
    game.flip_pile(0)
    assert game.top_card(0).card.rank == 'K'
    assert game.top_card(0).face_up is True


def test_flip_twice_restores_exposed_end_without_reordering_cards():
    game = build_state([[('A', '♠', True), ('2', '♥', False), ('K', '♦', True)]])
    before_order = [(pc.card.rank, pc.card.suit) for pc in game.piles[0]]
    before_top = game.top_card(0).card.rank
    game.flip_pile(0)
    game.flip_pile(0)
    after_order = [(pc.card.rank, pc.card.suit) for pc in game.piles[0]]
    assert after_order == before_order
    assert game.top_card(0).card.rank == before_top
    assert game.top_card(0).face_up is True


def test_hidden_top_card_can_be_selected_by_memory():
    game = build_state([
        [('A', '♠', True), ('K', '♠', False)],
        [('Q', '♥', True)],
    ])
    assert game.toggle_select(0) is True
    assert game.selected == [0]


def test_matching_exposed_ranks_can_be_removed_even_when_hidden():
    game = build_state([
        [('2', '♠', True), ('K', '♠', False)],
        [('3', '♥', False), ('K', '♥', True)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.can_remove_selected()
    assert game.remove_selected()
    assert game.remaining_cards == 2
    assert game.removed_pairs == 1


def test_remove_after_flip_pops_newly_exposed_start_card():
    game = build_state([
        [('A', '♠', True), ('7', '♠', False)],
        [('A', '♥', False), ('8', '♥', True)],
    ])
    game.flip_pile(0)
    game.flip_pile(1)
    assert game.top_card(0).card.rank == 'A'
    assert game.top_card(1).card.rank == 'A'
    assert game.top_card(0).face_up is True
    assert game.top_card(1).face_up is True
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.remove_selected()
    assert [pc.card.rank for pc in game.piles[0]] == ['7']
    assert [pc.card.rank for pc in game.piles[1]] == ['8']


def test_different_ranks_cannot_be_removed():
    game = build_state([
        [('K', '♠', True)],
        [('Q', '♥', True)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.remove_selected() is False
    assert game.remaining_cards == 2


def test_clear_selection_after_mismatch():
    game = build_state([
        [('K', '♠', True)],
        [('Q', '♥', True)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    game.clear_selection()
    assert game.selected == []


def test_win_when_all_cards_removed():
    game = build_state([
        [('A', '♠', True)],
        [('A', '♥', False)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    game.remove_selected()
    assert game.won
    assert game.finished


def test_give_up_finishes_game_without_win():
    game = GameState.new(seed=3)
    game.give_up()
    assert game.given_up
    assert game.finished
    assert not game.won
