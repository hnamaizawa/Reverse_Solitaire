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


def test_flip_keeps_visual_card_order_and_toggles_physical_side():
    game = build_state([[('A', '♠', True), ('2', '♠', False), ('3', '♠', True)]])
    before = [pc.card.rank for pc in game.piles[0]]
    assert game.flipped == [False]

    game.flip_pile(0)

    assert [pc.card.rank for pc in game.piles[0]] == before
    assert game.flipped == [True]


def test_flip_toggles_every_card_face_state():
    game = build_state([[
        ('A', '♣', True),
        ('4', '♠', False),
        ('9', '♥', True),
        ('7', '♦', False),
    ]])

    game.flip_pile(0)

    assert [pc.face_up for pc in game.piles[0]] == [False, True, False, True]


def test_user_reference_packet_preserves_order_and_reveals_previous_backs():
    """Regression for the user's four-card reference image.

    Before flip, top-to-bottom is A♣ face, hidden, 9♥ face, hidden.
    After flip the card identities remain in those same four slots, while all
    face states toggle: back, readable, back, readable.
    """
    game = build_state([[
        ('A', '♣', True),
        ('4', '♠', False),
        ('9', '♥', True),
        ('7', '♦', False),
    ]])

    game.flip_pile(0)

    assert [pc.card.label for pc in game.piles[0]] == ['A♣', '4♠', '9♥', '7♦']
    assert [pc.face_up for pc in game.piles[0]] == [False, True, False, True]
    assert game.top_card(0).card.label == 'A♣'
    assert game.top_card(0).face_up is False


def test_second_flip_restores_original_face_pattern_and_upper_side():
    game = build_state([[('A', '♠', True), ('2', '♥', False), ('K', '♦', True)]])
    before = [(pc.card.label, pc.face_up) for pc in game.piles[0]]

    game.flip_pile(0)
    assert game.flipped[0] is True
    game.flip_pile(0)

    assert game.flipped[0] is False
    assert [(pc.card.label, pc.face_up) for pc in game.piles[0]] == before


def test_hidden_top_card_can_be_selected_by_memory():
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
    assert [pc.card.rank for pc in game.piles[0]] == ['2']
    assert [pc.card.rank for pc in game.piles[1]] == ['3']


def test_remove_after_flip_pops_visual_first_card():
    game = build_state([
        [('A', '♠', True), ('7', '♠', False)],
        [('A', '♥', True), ('8', '♥', False)],
    ])
    game.flip_pile(0)
    game.flip_pile(1)
    assert game.top_card(0).card.rank == 'A'
    assert game.top_card(1).card.rank == 'A'
    assert game.top_card(0).face_up is False
    assert game.top_card(1).face_up is False
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
