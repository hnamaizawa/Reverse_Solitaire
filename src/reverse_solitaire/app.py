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
PILE_GAP = 14


class ReverseSolitaireApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reverse Solitaire v0.1.4")
        self.geometry("1280x760")
        self.minsize(1080, 650)
        self.configure(bg="#0b5d35")

        self.game = GameState.new()
        self.status = tk.StringVar()
        self.animating = False

        self.flip_y_scale: dict[int, float] = {}
        self.flip_lift: dict[int, float] = {}
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
            text="一番上のカードを2枚クリック。同じ数字なら自動で消えます。［ひっくり返す］で位置を変えず上下に反転します。",
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
        if not self.game.piles[pile_index]:
            return
        self.animating = True
        frames = 16
        midpoint = frames // 2

        def frame(step: int):
            if step == midpoint:
                # The cards keep their screen positions. The model only toggles
                # face states and switches which end of the stack is exposed.
                self.game.flip_pile(pile_index)

            t = step / frames
            y_scale = max(0.035, abs(math.cos(math.pi * t)))
            lift = -math.sin(math.pi * t) * 10.0
            self.flip_y_scale[pile_index] = y_scale
            self.flip_lift[pile_index] = lift
            self.redraw()

            if step < frames:
                self.after(24, lambda: frame(step + 1))
            else:
                self.flip_y_scale.clear()
                self.flip_lift.clear()
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
            y_scale = self.flip_y_scale.get(i, 1.0)
            lift = self.flip_lift.get(i, 0.0)

            natural_height = CARD_H if not pile else (len(pile) - 1) * OFFSET_Y + CARD_H
            hinge_y = base_y + natural_height + lift

            if not pile:
                self.canvas.create_rectangle(
                    base_x, base_y, base_x + CARD_W, base_y + CARD_H,
                    outline="#8bc6a7", dash=(4, 4), width=2, tags=(new_tag,),
                )
                y_button = base_y + CARD_H + 14
            else:
                top_idx = self.game.top_index(i)
                # Screen positions never change. Only depth order changes after a
                # vertical turnover, so the newly exposed end is painted last.
                if self.game.exposed_from_start[i]:
                    render_indices = range(len(pile) - 1, -1, -1)
                else:
                    render_indices = range(len(pile))

                for j in render_indices:
                    pc = pile[j]
                    natural_y = base_y + j * OFFSET_Y
                    y = hinge_y - (hinge_y - natural_y) * y_scale
                    card_h = max(3.0, CARD_H * y_scale)
                    x = base_x

                    is_top = j == top_idx
                    selected = i in self.game.selected and is_top
                    card_scale = self.remove_scale.get(i, 1.0) if is_top else 1.0
                    if card_scale != 1.0:
                        x1, y1, x2, y2 = self._scaled_rect(x, y, CARD_W, card_h, card_scale)
                    else:
                        x1, y1, x2, y2 = x, y, x + CARD_W, y + card_h

                    if pc.face_up:
                        outline = "#ffd54f" if selected else "#222222"
                        width_line = 4 if selected else 2
                        self.canvas.create_rectangle(
                            x1, y1, x2, y2, fill="#fffdf5",
                            outline=outline, width=width_line, tags=(new_tag,),
                        )
                        if card_h > 30 and card_scale > 0.35:
                            suit_red = pc.card.suit in ("♥", "♦")
                            self.canvas.create_text(
                                x1 + 7, y1 + 7, text=pc.card.label, anchor="nw",
                                font=("Arial", 14, "bold"),
                                fill="#b00020" if suit_red else "#111111",
                                tags=(new_tag,),
                            )
                    else:
                        self.canvas.create_rectangle(
                            x1, y1, x2, y2, fill="#273c75",
                            outline="#ffd54f" if selected else "#d9e7ff",
                            width=4 if selected else 2, tags=(new_tag,),
                        )
                        if card_h > 30 and card_scale > 0.35:
                            stripe_step = max(6.0, card_h / 6.0)
                            for k in range(5):
                                yy = y1 + stripe_step * (k + 1)
                                if yy < y2 - 3:
                                    self.canvas.create_line(
                                        x1 + 6, yy, x2 - 6, yy - min(7, stripe_step / 2),
                                        fill="#a8c6ff", tags=(new_tag,),
                                    )

                    if is_top and not self.animating:
                        self.hit_regions.append(("top", i, (x1, y1, x2, y2)))

                y_button = MARGIN_Y + natural_height + 14

            self.canvas.create_rectangle(
                base_x, y_button, base_x + CARD_W, y_button + 30,
                fill="#f2f2f2", outline="#111111", tags=(new_tag,),
            )
            self.canvas.create_text(
                base_x + CARD_W / 2, y_button + 15, text="ひっくり返す",
                font=("Yu Gothic UI", 9, "bold"), tags=(new_tag,),
            )
            if not self.animating:
                self.hit_regions.append(("flip", i, (base_x, y_button, base_x + CARD_W, y_button + 30)))
            self.canvas.create_text(
                base_x + CARD_W / 2, y_button + 47, text=f"組 {i + 1}",
                fill="white", font=("Yu Gothic UI", 9), tags=(new_tag,),
            )

        state_text = "クリア！" if self.game.won else (
            "ギブアップ" if self.game.given_up else "記憶を頼りにペアを探してください"
        )
        self.status.set(
            f"残り {self.game.remaining_cards}枚 / 取り除いたペア {self.game.removed_pairs} / "
            f"手数 {self.game.moves} / {state_text}"
        )

        self.canvas.delete(old_tag)


if __name__ == "__main__":
    ReverseSolitaireApp().mainloop()
