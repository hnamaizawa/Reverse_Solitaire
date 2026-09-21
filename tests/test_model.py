import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.model import GameState, build_state


def test_new_game_contains_52_cards_in_six_card_piles():
    game = GameState.new(seed=1)
    assert game.remaining_cards == 52
    assert len(game.piles) == 9
    assert [len(p) for p in game.piles] == [6] * 8 + [4]


def test_cards_alternate_face_direction_in_each_pile():
    game = GameState.new(seed=2)
    for pile in game.piles:
        for i, pc in enumerate(pile):
            assert pc.face_up == (i % 2 == 0)


def test_downward_flip_reverses_visual_card_order():
    game = build_state([[('A', '♣', True), ('4', '♠', False), ('9', '♥', True), ('7', '♦', False)]])

    game.flip_pile(0)

    assert game.flipped == [True]
    assert [pc.card.label for pc in game.piles[0]] == ['7♦', '9♥', '4♠', 'A♣']
    assert game.top_card(0).card.label == '7♦'


def test_downward_flip_makes_every_card_readable():
    game = build_state([[('A', '♣', True), ('4', '♠', False), ('9', '♥', True), ('7', '♦', False)]])

    game.flip_pile(0)

    assert all(pc.face_up for pc in game.piles[0])


def test_user_reference_packet_is_reversed_and_visible_when_flipped_down():
    game = build_state([[('A', '♣', True), ('4', '♠', False), ('9', '♥', True), ('7', '♦', False)]])

    game.flip_pile(0)

    assert [pc.card.label for pc in game.piles[0]] == ['7♦', '9♥', '4♠', 'A♣']
    assert [pc.face_up for pc in game.piles[0]] == [True, True, True, True]


def test_upward_flip_reverses_order_back_and_restores_alternating_faces():
    game = build_state([[('A', '♣', True), ('4', '♠', False), ('9', '♥', True), ('7', '♦', False)]])
    before_labels = [pc.card.label for pc in game.piles[0]]

    game.flip_pile(0)
    game.flip_pile(0)

    assert game.flipped == [False]
    assert [pc.card.label for pc in game.piles[0]] == before_labels
    assert [pc.face_up for pc in game.piles[0]] == [True, False, True, False]


def test_hidden_top_card_can_be_selected_by_memory_on_upper_side():
    game = build_state([
        [('A', '♠', False), ('K', '♠', True)],
        [('A', '♥', False), ('Q', '♥', True)],
    ])
    assert game.top_card(0).card.rank == 'A'
    assert game.top_card(0).face_up is False
    assert game.toggle_select(0) is True
    assert game.selected == [0]


def test_matching_top_ranks_can_be_removed_even_when_hidden():
    game = build_state([
        [('K', '♠', False), ('2', '♠', True)],
        [('K', '♥', True), ('3', '♥', False)],
    ])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.can_remove_selected()
    assert game.remove_selected()
    assert game.remaining_cards == 2
    assert game.removed_pairs == 1


def test_remove_after_downward_flip_pops_new_visual_top():
    game = build_state([
        [('7', '♠', True), ('A', '♠', False)],
        [('8', '♥', True), ('A', '♥', False)],
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
    game = build_state([[('K', '♠', True)], [('Q', '♥', True)]])
    game.toggle_select(0)
    game.toggle_select(1)
    assert game.remove_selected() is False
    assert game.remaining_cards == 2


def test_clear_selection_after_mismatch():
    game = build_state([[('K', '♠', True)], [('Q', '♥', True)]])
    game.toggle_select(0)
    game.toggle_select(1)
    game.clear_selection()
    assert game.selected == []


def test_win_when_all_cards_removed():
    game = build_state([[('A', '♠', True)], [('A', '♥', False)]])
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
