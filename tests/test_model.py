import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.model import GameState, build_state


def test_new_game_contains_52_cards():
    game = GameState.new(seed=1)
    assert game.remaining_cards == 52
    assert len(game.piles) == 7
    assert [len(p) for p in game.piles] == [8, 8, 8, 8, 8, 8, 4]


def test_cards_alternate_face_direction_in_each_pile():
    game = GameState.new(seed=2)
    for pile in game.piles:
        for i, pc in enumerate(pile):
            assert pc.face_up == (i % 2 == 0)


def test_flip_reverses_pile_and_toggles_visibility():
    game = build_state([[('A', '♠', True), ('2', '♠', False), ('3', '♠', True)]])
    before = [pc.card.rank for pc in game.piles[0]]
    before_faces = [pc.face_up for pc in game.piles[0]]
    game.flip_pile(0)
    assert [pc.card.rank for pc in game.piles[0]] == list(reversed(before))
    assert [pc.face_up for pc in game.piles[0]] == [not x for x in reversed(before_faces)]


def test_only_face_up_top_cards_can_be_selected():
    game = build_state([
        [('A', '♠', True), ('K', '♠', False)],
        [('Q', '♥', True)],
    ])
    assert game.toggle_select(0) is False
    assert game.toggle_select(1) is True
    assert game.selected == [1]


def test_matching_top_ranks_can_be_removed():
    game = build_state([
        [('2', '♠', True), ('K', '♠', True)],
        [('3', '♥', False), ('K', '♥', True)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.can_remove_selected()
    assert game.remove_selected()
    assert game.remaining_cards == 2
    assert game.removed_pairs == 1


def test_different_ranks_cannot_be_removed():
    game = build_state([
        [('K', '♠', True)],
        [('Q', '♥', True)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.remove_selected() is False
    assert game.remaining_cards == 2


def test_win_when_all_cards_removed():
    game = build_state([
        [('A', '♠', True)],
        [('A', '♥', True)],
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
