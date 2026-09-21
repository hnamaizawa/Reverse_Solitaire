import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.model import GameState, build_state


def test_easy_mode_allows_at_most_one_pair_per_pile_and_keeps_pair_apart():
    for seed in range(100):
        game = GameState.new(seed=seed, easy_mode=True)
        assert [len(p) for p in game.piles] == [6] * 8 + [4]
        assert game.remaining_cards == 52

        for pile in game.piles:
            positions = defaultdict(list)
            for index, pc in enumerate(pile):
                positions[pc.card.rank].append(index)

            counts = Counter(pc.card.rank for pc in pile)
            duplicated = [rank for rank, count in counts.items() if count == 2]

            assert all(count <= 2 for count in counts.values())
            assert len(duplicated) <= 1
            for rank in duplicated:
                first, second = positions[rank]
                assert second - first >= 3  # at least two cards between the pair


def test_easy_mode_preserves_initial_face_alternation():
    game = GameState.new(seed=123, easy_mode=True)
    for pile in game.piles:
        assert [pc.face_up for pc in pile] == [i % 2 == 0 for i in range(len(pile))]


def test_snapshot_restore_undoes_flip_exactly():
    game = build_state([[('A', '♣', True), ('4', '♠', False)]])
    before = game.snapshot()
    game.flip_pile(0)
    assert game.moves == 1
    game.restore(before)
    assert game.moves == 0
    assert game.flipped == [False]
    assert [(pc.card.label, pc.face_up) for pc in game.piles[0]] == [('A♣', True), ('4♠', False)]


def test_snapshot_restore_undoes_pair_removal():
    game = build_state([[('9', '♠', True)], [('9', '♥', True)]])
    game.toggle_select(0)
    game.toggle_select(1)
    before = game.snapshot()
    game.remove_selected()
    assert game.won
    game.restore(before)
    assert game.remaining_cards == 2
    assert not game.won
    assert game.removed_pairs == 0


def test_snapshot_is_independent_copy():
    game = GameState.new(seed=1)
    snap = game.snapshot()
    original = snap.piles[0][0].card.label
    game.flip_pile(0)
    assert snap.piles[0][0].card.label == original
