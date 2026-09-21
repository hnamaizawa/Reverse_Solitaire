import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reverse_solitaire.app import project_card_vertical_bounds


def test_downward_domino_flip_moves_card_below_hinge():
    natural_y = 60.0
    card_h = 118.0
    hinge_y = 378.0

    start_top, start_bottom = project_card_vertical_bounds(natural_y, card_h, hinge_y, 0.0)
    mid_top, mid_bottom = project_card_vertical_bounds(natural_y, card_h, hinge_y, math.pi / 2)
    end_top, end_bottom = project_card_vertical_bounds(natural_y, card_h, hinge_y, math.pi)

    assert (start_top, start_bottom) == (natural_y, natural_y + card_h)
    assert abs(mid_top - hinge_y) < 1e-9
    assert abs(mid_bottom - hinge_y) < 1e-9
    assert end_top >= hinge_y
    assert end_top > start_top


def test_upward_domino_flip_returns_card_to_original_position():
    natural_y = 140.0
    card_h = 118.0
    hinge_y = 378.0

    down_top, down_bottom = project_card_vertical_bounds(natural_y, card_h, hinge_y, math.pi)
    up_top, up_bottom = project_card_vertical_bounds(natural_y, card_h, hinge_y, 0.0)

    assert down_top >= hinge_y
    assert (up_top, up_bottom) == (natural_y, natural_y + card_h)


def test_four_card_packet_reverses_visual_vertical_order_after_flip():
    """The user's reference packet must land in exact reverse visual order.

    Original slots are 1, J♥, 3, 9♦ from hinge side to free end. After a
    180-degree downward turnover, 9♦ must be highest on the lower side, then
    card 3, then J♥, then card 1 at the bottom.
    """
    base_y = 60.0
    offset_y = 40.0
    card_h = 118.0
    count = 4
    hinge_y = base_y + (count - 1) * offset_y + card_h

    natural_ys = [base_y + i * offset_y for i in range(count)]
    final_tops = [
        project_card_vertical_bounds(y, card_h, hinge_y, math.pi)[0]
        for y in natural_ys
    ]

    # Smaller y means visually higher. The free-end card (index 3, 9♦) is
    # therefore first, followed by index 2, J♥ (index 1), and index 0.
    visual_order = sorted(range(count), key=lambda i: final_tops[i])
    assert visual_order == [3, 2, 1, 0]
