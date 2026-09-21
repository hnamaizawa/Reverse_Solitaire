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
