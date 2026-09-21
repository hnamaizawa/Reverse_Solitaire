from __future__ import annotations

import io
import math
from pathlib import Path
import struct
import sys
import tkinter as tk
from tkinter import messagebox
import wave

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reverse_solitaire.model import GameState  # type: ignore
else:
    from .model import GameState

CARD_W = 82
CARD_H = 118
OFFSET_Y = 48
MARGIN_X = 16
MARGIN_Y = 60
PILE_GAP = 20
FLIP_BUTTON_H = 22


def project_card_vertical_bounds(
    natural_y: float,
    card_h: float,
    base_y: float,
    hinge_y: float,
    angle: float,
) -> tuple[float, float]:
    """Project one visual slot while the packet rotates around a horizontal hinge."""
    scale = abs(math.cos(angle))
    slot_offset = natural_y - base_y

    if math.cos(angle) >= 0:
        y1 = hinge_y - (hinge_y - natural_y) * scale
    else:
        y1 = hinge_y + slot_offset * scale

    y2 = y1 + card_h * scale
    return y1, y2


def centered_flip_button_y(hinge_y: float, button_height: float = FLIP_BUTTON_H) -> float:
    """Place the flip control at the midpoint crossed by the packet.

    The packet is above the hinge before a downward turnover and below it after
    the turnover. Centering the control on the hinge puts it halfway between the
    two resting positions and keeps it at exactly the same place for up/down
    repeats of the same pile.
    """
    return hinge_y - button_height / 2.0


def build_soft_error_wav(
    *,
    frequency: float = 420.0,
    duration: float = 0.09,
    volume: float = 0.08,
    sample_rate: int = 22050,
) -> bytes:
    """Create a short, restrained PCM tone for mismatch feedback."""
    frame_count = max(1, int(sample_rate * duration))
    pcm = bytearray()
    for i in range(frame_count):
        t = i / sample_rate
        envelope = min(1.0, i / max(1, int(sample_rate * 0.008)))
        envelope *= max(0.0, 1.0 - i / frame_count)
        sample = int(32767 * volume * envelope * math.sin(2.0 * math.pi * frequency * t))
        pcm.extend(struct.pack("<h", sample))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(pcm))
    return buffer.getvalue()


class ReverseSolitaireApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reverse Solitaire v0.1.14")
        self.geometry("1280x900")
        self.minsize(1080, 780)
        self.configure(bg="#0b5d35")

        self.game = GameState.new()
        self.status = tk.StringVar()
        self.animating = False
        self.muted = tk.BooleanVar(value=False)
        self._mismatch_wav = build_soft_error_wav()
        self.flip_angle: dict[int, float] = {}
        self.remove_scale: dict[int, float] = {}
        self.frame_slot = 0

        toolbar = tk.Frame(self, bg="#123c2a")
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="新しいゲーム", command=self.new_game).pack(side="left", padx=8, pady=8)
        tk.Button(toolbar, text="ギブアップ", command=self.give_up).pack(side="left", padx=4, pady=8)
        tk.Checkbutton(
            toolbar,
            text="消音",
            variable=self.muted,
            bg="#123c2a",
            fg="white",
            activebackground="#123c2a",
            activeforeground="white",
            selectcolor="#123c2a",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(side="left", padx=(14, 4), pady=8)
        tk.Label(
            toolbar,
            textvariable=self.status,
            fg="white",
            bg="#123c2a",
            font=("Yu Gothic UI", 11, "bold"),
        ).pack(side="right", padx=12)

        guide = tk.Label(
            self,
            text=(
                "一番上のカードを2枚クリック。同じ数字なら自動で消えます。"
                "［ひっくり返す ↓/↑］は反転前後の中央に固定されています。"
            ),
            fg="white",
            bg="#0b5d35",
            font=("Yu Gothic UI", 10),
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

    def _play_mismatch_sound(self) -> None:
        if self.muted.get() or winsound is None:
            return
        try:
            winsound.PlaySound(self._mismatch_wav, winsound.SND_MEMORY)
        except RuntimeError:
            pass

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
                self._play_mismatch_sound()
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

    def _rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        *,
        fill: str,
        outline: str,
        width: int,
        tags: tuple[str, ...],
    ) -> None:
        if y2 - y1 < 14 or x2 - x1 < 14:
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tags
            )
            return
        r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=12,
            fill=fill,
            outline=outline,
            width=width,
            tags=tags,
        )

    def _draw_face_card(
        self,
        pc,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        card_h: float,
        selected: bool,
        card_scale: float,
        tag: str,
    ) -> None:
        outline = "#d9a514" if selected else "#272727"
        text_color = "#b51d2a" if pc.card.suit in ("♥", "♦") else "#111111"
        soft_suit = "#d9a4aa" if pc.card.suit in ("♥", "♦") else "#8f959a"

        if card_h > 18:
            self._rounded_rectangle(
                x1 + 2,
                y1 + 2,
                x2 + 2,
                y2 + 2,
                8,
                fill="#0a492c",
                outline="#0a492c",
                width=1,
                tags=(tag,),
            )
        self._rounded_rectangle(
            x1,
            y1,
            x2,
            y2,
            8,
            fill="#fffdf7",
            outline=outline,
            width=4 if selected else 2,
            tags=(tag,),
        )

        if card_h > 30 and card_scale > 0.35:
            self.canvas.create_text(
                x1 + 7,
                y1 + 6,
                text=pc.card.label,
                anchor="nw",
                font=("Arial", 14, "bold"),
                fill=text_color,
                tags=(tag,),
            )
            self.canvas.create_text(
                x2 - 7,
                y2 - 14,
                text=pc.card.label,
                anchor="se",
                font=("Arial", 14, "bold"),
                fill=text_color,
                tags=(tag,),
            )

        if card_h > 76 and card_scale > 0.45:
            center_text = pc.card.suit if pc.card.rank not in ("J", "Q", "K") else f"{pc.card.rank}{pc.card.suit}"
            center_size = 29 if len(center_text) == 1 else 22
            self.canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=center_text,
                font=("Arial", center_size, "bold"),
                fill=soft_suit,
                tags=(tag,),
            )

    def _draw_back_card(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        card_h: float,
        selected: bool,
        card_scale: float,
        tag: str,
    ) -> None:
        self._rounded_rectangle(
            x1,
            y1,
            x2,
            y2,
            8,
            fill="#203c78",
            outline="#ffd54f" if selected else "#e2ecff",
            width=4 if selected else 2,
            tags=(tag,),
        )
        if card_h > 28 and card_scale > 0.35:
            inset = 7
            self._rounded_rectangle(
                x1 + inset,
                y1 + inset,
                x2 - inset,
                y2 - inset,
                5,
                fill="#294985",
                outline="#88a9e7",
                width=1,
                tags=(tag,),
            )
            usable_h = max(1.0, y2 - y1 - 2 * inset)
            step = max(8.0, usable_h / 7.0)
            yy = y1 + inset + step
            while yy < y2 - inset - 2:
                self.canvas.create_line(
                    x1 + inset + 3,
                    yy,
                    x2 - inset - 3,
                    yy - 7,
                    fill="#9db9ef",
                    tags=(tag,),
                )
                yy += step

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
            angle = self.flip_angle.get(i, math.pi if self.game.flipped[i] else 0.0)

            if not pile:
                self._rounded_rectangle(
                    base_x,
                    base_y,
                    base_x + CARD_W,
                    base_y + CARD_H,
                    8,
                    fill="#0b5d35",
                    outline="#8bc6a7",
                    width=2,
                    tags=(new_tag,),
                )
            else:
                top_idx = self.game.top_index(i)
                render_indices = range(len(pile) - 1, -1, -1)

                for j in render_indices:
                    pc = pile[j]
                    natural_y = base_y + j * OFFSET_Y
                    y1, y2 = project_card_vertical_bounds(
                        natural_y, CARD_H, base_y, hinge_y, angle
                    )
                    card_h = max(3.0, y2 - y1)
                    y2 = y1 + card_h
                    x = base_x

                    is_top = j == top_idx
                    selected = i in self.game.selected and is_top
                    card_scale = self.remove_scale.get(i, 1.0) if is_top else 1.0
                    if card_scale != 1.0:
                        x1, yy1, x2, yy2 = self._scaled_rect(x, y1, CARD_W, card_h, card_scale)
                    else:
                        x1, yy1, x2, yy2 = x, y1, x + CARD_W, y2

                    if pc.face_up:
                        self._draw_face_card(
                            pc, x1, yy1, x2, yy2, card_h, selected, card_scale, new_tag
                        )
                    else:
                        self._draw_back_card(
                            x1, yy1, x2, yy2, card_h, selected, card_scale, new_tag
                        )

                    if is_top and not self.animating:
                        self.hit_regions.append(("top", i, (x1, yy1, x2, yy2)))

            # The control is centered on the turnover hinge: the packet crosses
            # this exact row when it flips, so repeated up/down clicks require
            # no pointer travel toward either resting packet position.
            y_button = centered_flip_button_y(hinge_y)
            direction = "↑" if self.game.flipped[i] else "↓"
            self._rounded_rectangle(
                base_x,
                y_button,
                base_x + CARD_W,
                y_button + FLIP_BUTTON_H,
                5,
                fill="#f7f7f4",
                outline="#1f1f1f",
                width=1,
                tags=(new_tag,),
            )
            self.canvas.create_text(
                base_x + CARD_W / 2,
                y_button + FLIP_BUTTON_H / 2,
                text=f"ひっくり返す {direction}",
                font=("Yu Gothic UI", 8, "bold"),
                fill="#202020",
                tags=(new_tag,),
            )
            if not self.animating:
                self.hit_regions.append((
                    "flip",
                    i,
                    (base_x, y_button, base_x + CARD_W, y_button + FLIP_BUTTON_H),
                ))
            self.canvas.create_text(
                base_x + CARD_W / 2,
                y_button + FLIP_BUTTON_H + 17,
                text=f"組 {i + 1}",
                fill="white",
                font=("Yu Gothic UI", 9),
                tags=(new_tag,),
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
