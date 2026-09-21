from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reverse_solitaire.model import GameState  # type: ignore
else:
    from .model import GameState

CARD_W = 82
CARD_H = 118
OFFSET_Y = 40
MARGIN_X = 16
MARGIN_Y = 60
PILE_GAP = 20


def project_card_vertical_bounds(
    natural_y: float,
    card_h: float,
    hinge_y: float,
    angle: float,
) -> tuple[float, float]:
    """Project a card while rotating around a horizontal hinge.

    angle=0   : original position above the hinge
    angle=pi/2: edge-on at the hinge
    angle=pi  : physically flipped to the opposite (lower) side

    The sign of cos(angle) is intentionally preserved. That makes every card
    cross the hinge and land in the reversed vertical order, exactly like a
    real overlapped packet being toppled over.
    """
    c = math.cos(angle)
    top = hinge_y - (hinge_y - natural_y) * c
    bottom = hinge_y - (hinge_y - (natural_y + card_h)) * c
    return min(top, bottom), max(top, bottom)


class ReverseSolitaireApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reverse Solitaire v0.1.8")
        self.geometry("1280x900")
        self.minsize(1080, 780)
        self.configure(bg="#0b5d35")

        self.game = GameState.new()
        self.status = tk.StringVar()
        self.animating = False

        self.flip_angle: dict[int, float] = {}
        self.remove_scale: dict[int, float] = {}
        self.frame_slot = 0

        toolbar = tk.Frame(self, bg="#123c2a")
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="新しいゲーム", command=self.new_game).pack(side="left", padx=8, pady=8)
        tk.Button(toolbar, text="ギブアップ", command=self.give_up).pack(side="left", padx=4, pady=8)
        tk.Label(toolbar, textvariable=self.status, fg="white", bg="#123c2a",
                 font=("Yu Gothic UI", 11, "bold")).pack(side="right", padx=12)

        guide = tk.Label(
            self,
            text=(
                "一番上のカードを2枚クリック。同じ数字なら自動で消えます。"
                "［ひっくり返す ↓/↑］でカードの山を物理的に上下へ倒します。"
            ),
            fg="white", bg="#0b5d35", font=("Yu Gothic UI", 10),
        )
        guide.pack(fill="x", pady=(8, 0))

        self.canvas = tk.Canvas(self, bg="#0b5d35", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.bind("<Configure>", lambda _e: self.redraw() if not self.animating else None)

        self.hit_regions: list[tuple[str, int, tuple[float, float, float, float]]] = []
        self.redraw()

    def new_game(self):
        if self.animating:
            return
        self.game = GameState.new()
        self.flip_angle.clear()
        self.redraw()

    def give_up(self):
        if self.animating:
            return
        if messagebox.askyesno("ギブアップ", "このゲームを終了しますか？"):
            self.game.give_up()
            self.redraw()

    def on_canvas_click(self, event):
        if self.game.finished or self.animating:
            return
        for action, pile_index, (x1, y1, x2, y2) in reversed(self.hit_regions):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if action == "top":
                    self.select_top(pile_index)
                elif action == "flip":
                    self.animate_flip(pile_index)
                return

    def select_top(self, pile_index: int):
        if not self.game.toggle_select(pile_index):
            return
        self.redraw()
        if len(self.game.selected) == 2:
            selected = list(self.game.selected)
            if self.game.can_remove_selected():
                self.animate_remove(selected)
            else:
                self.bell()
                self.after(220, self._clear_mismatch)

    def _clear_mismatch(self):
        self.game.clear_selection()
        self.redraw()

    def animate_flip(self, pile_index: int):
        pile = self.game.piles[pile_index]
        if not pile:
            return

        self.animating = True
        frames = 22
        midpoint = frames // 2
        flipping_down = not self.game.flipped[pile_index]
        start_angle = 0.0 if flipping_down else math.pi
        end_angle = math.pi if flipping_down else 0.0

        def frame(step: int):
            t = step / frames
            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            angle = start_angle + (end_angle - start_angle) * eased
            self.flip_angle[pile_index] = angle

            if step == midpoint:
                # At 90 degrees the packet is almost edge-on. Commit the rule
                # state there, while the card faces/order transition is hidden.
                self.game.flip_pile(pile_index)

            self.redraw()

            if step < frames:
                self.after(20, lambda: frame(step + 1))
            else:
                self.flip_angle.pop(pile_index, None)
                self.animating = False
                self.redraw()

        frame(0)

    def animate_remove(self, pile_indices: list[int]):
        self.animating = True
        frames = 9

        def frame(step: int):
            scale = max(0.08, 1.0 - step / frames)
            for idx in pile_indices:
                self.remove_scale[idx] = scale
            self.redraw()
            if step < frames:
                self.after(32, lambda: frame(step + 1))
            else:
                self.remove_scale.clear()
                self.game.remove_selected()
                self.animating = False
                self.redraw()
                if self.game.won:
                    messagebox.showinfo("ゲームクリア", f"全てのカードを取り除きました！\n手数: {self.game.moves}")

        frame(0)

    @staticmethod
    def _scaled_rect(x: float, y: float, w: float, h: float, scale: float) -> tuple[float, float, float, float]:
        cx, cy = x + w / 2, y + h / 2
        hw, hh = w * scale / 2, h * scale / 2
        return cx - hw, cy - hh, cx + hw, cy + hh

    def _frame_tags(self) -> tuple[str, str]:
        new_tag = f"frame_{self.frame_slot}"
        old_tag = f"frame_{1 - self.frame_slot}"
        self.frame_slot = 1 - self.frame_slot
        return new_tag, old_tag

    def redraw(self):
        new_tag, old_tag = self._frame_tags()
        self.canvas.delete(new_tag)
        self.hit_regions.clear()

        width = max(self.canvas.winfo_width(), 1050)
        pile_count = len(self.game.piles)
        total_w = pile_count * CARD_W + max(0, pile_count - 1) * PILE_GAP
        start_x = max(MARGIN_X, (width - total_w) / 2)

        for i, pile in enumerate(self.game.piles):
            base_x = start_x + i * (CARD_W + PILE_GAP)
            base_y = MARGIN_Y
            natural_height = CARD_H if not pile else (len(pile) - 1) * OFFSET_Y + CARD_H
            hinge_y = base_y + natural_height

            if i in self.flip_angle:
                angle = self.flip_angle[i]
            else:
                angle = math.pi if self.game.flipped[i] else 0.0

            if not pile:
                self.canvas.create_rectangle(
                    base_x, base_y, base_x + CARD_W, base_y + CARD_H,
                    outline="#8bc6a7", dash=(4, 4), width=2, tags=(new_tag,),
                )
                pile_bottom = base_y + CARD_H
            else:
                top_idx = self.game.top_index(i)

                # The same free-end card is painted last on both sides. Its
                # spatial position crosses the hinge, so the visual order is
                # reversed by physics rather than by a logical 'keep top' rule.
                render_indices = range(len(pile))

                pile_bottom = base_y
                for j in render_indices:
                    pc = pile[j]
                    natural_y = base_y + j * OFFSET_Y
                    y1, y2 = project_card_vertical_bounds(natural_y, CARD_H, hinge_y, angle)
                    card_h = max(3.0, y2 - y1)
                    y2 = y1 + card_h
                    pile_bottom = max(pile_bottom, y2)
                    x = base_x

                    is_top = j == top_idx
                    selected = i in self.game.selected and is_top
                    card_scale = self.remove_scale.get(i, 1.0) if is_top else 1.0
                    if card_scale != 1.0:
                        x1, yy1, x2, yy2 = self._scaled_rect(x, y1, CARD_W, card_h, card_scale)
                    else:
                        x1, yy1, x2, yy2 = x, y1, x + CARD_W, y2

                    if pc.face_up:
                        outline = "#ffd54f" if selected else "#222222"
                        width_line = 4 if selected else 2
                        self.canvas.create_rectangle(
                            x1, yy1, x2, yy2, fill="#fffdf5",
                            outline=outline, width=width_line, tags=(new_tag,),
                        )
                        if card_h > 30 and card_scale > 0.35:
                            suit_red = pc.card.suit in ("♥", "♦")
                            self.canvas.create_text(
                                x1 + 7, yy1 + 7, text=pc.card.label, anchor="nw",
                                font=("Arial", 14, "bold"),
                                fill="#b00020" if suit_red else "#111111",
                                tags=(new_tag,),
                            )
                    else:
                        self.canvas.create_rectangle(
                            x1, yy1, x2, yy2, fill="#273c75",
                            outline="#ffd54f" if selected else "#d9e7ff",
                            width=4 if selected else 2, tags=(new_tag,),
                        )
                        if card_h > 30 and card_scale > 0.35:
                            stripe_step = max(6.0, card_h / 6.0)
                            for k in range(5):
                                yy = yy1 + stripe_step * (k + 1)
                                if yy < yy2 - 3:
                                    self.canvas.create_line(
                                        x1 + 6, yy, x2 - 6, yy - min(7, stripe_step / 2),
                                        fill="#a8c6ff", tags=(new_tag,),
                                    )

                    if is_top and not self.animating:
                        self.hit_regions.append(("top", i, (x1, yy1, x2, yy2)))

            y_button = pile_bottom + 14
            direction = "↑" if self.game.flipped[i] else "↓"
            self.canvas.create_rectangle(
                base_x, y_button, base_x + CARD_W, y_button + 30,
                fill="#f2f2f2", outline="#111111", tags=(new_tag,),
            )
            self.canvas.create_text(
                base_x + CARD_W / 2, y_button + 15, text=f"ひっくり返す {direction}",
                font=("Yu Gothic UI", 9, "bold"), tags=(new_tag,),
            )
            if not self.animating:
                self.hit_regions.append(("flip", i, (base_x, y_button, base_x + CARD_W, y_button + 30)))
            self.canvas.create_text(
                base_x + CARD_W / 2, y_button + 47, text=f"組 {i + 1}",
                fill="white", font=("Yu Gothic UI", 9), tags=(new_tag,),
            )

        state_text = "クリア！" if self.game.won else (
            "ギブアップ" if self.game.given_up else "ペアを探してください"
        )
        self.status.set(
            f"残り {self.game.remaining_cards}枚 / 取り除いたペア {self.game.removed_pairs} / "
            f"手数 {self.game.moves} / {state_text}"
        )

        self.canvas.delete(old_tag)


if __name__ == "__main__":
    ReverseSolitaireApp().mainloop()
