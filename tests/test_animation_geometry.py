import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.app import project_card_vertical_bounds


def test_downward_domino_flip_moves_packet_below_hinge():
    base_y = 60.0
    natural_y = 60.0
    card_h = 118.0
    hinge_y = 378.0

    start_top, start_bottom = project_card_vertical_bounds(
        natural_y, card_h, base_y, hinge_y, 0.0
    )
    mid_top, mid_bottom = project_card_vertical_bounds(
        natural_y, card_h, base_y, hinge_y, math.pi / 2
    )
    end_top, end_bottom = project_card_vertical_bounds(
        natural_y, card_h, base_y, hinge_y, math.pi
    )

    assert (start_top, start_bottom) == (natural_y, natural_y + card_h)
    assert abs(mid_top - hinge_y) < 1e-9
    assert abs(mid_bottom - hinge_y) < 1e-9
    assert end_top == hinge_y
    assert end_bottom == hinge_y + card_h


def test_upward_domino_flip_returns_card_to_original_position():
    base_y = 60.0
    natural_y = 140.0
    card_h = 118.0
    hinge_y = 378.0

    down_top, down_bottom = project_card_vertical_bounds(
        natural_y, card_h, base_y, hinge_y, math.pi
    )
    up_top, up_bottom = project_card_vertical_bounds(
        natural_y, card_h, base_y, hinge_y, 0.0
    )

    assert down_top >= hinge_y
    assert (up_top, up_bottom) == (natural_y, natural_y + card_h)


def test_four_card_packet_preserves_visual_vertical_order_after_flip():
    """A♣, hidden, 9♥, hidden must remain in the same four screen slots."""
    base_y = 60.0
    offset_y = 40.0
    card_h = 118.0
    count = 4
    hinge_y = base_y + (count - 1) * offset_y + card_h

    natural_ys = [base_y + i * offset_y for i in range(count)]
    final_tops = [
        project_card_vertical_bounds(y, card_h, base_y, hinge_y, math.pi)[0]
        for y in natural_ys
    ]

    visual_order = sorted(range(count), key=lambda i: final_tops[i])
    assert visual_order == [0, 1, 2, 3]
    assert final_tops == [hinge_y + i * offset_y for i in range(count)]
