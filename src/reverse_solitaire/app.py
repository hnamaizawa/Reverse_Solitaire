from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reverse_solitaire.model import GameState  # type: ignore
else:
    from .model import GameState

CARD_W = 92
CARD_H = 126
OFFSET_Y = 24
MARGIN_X = 24
MARGIN_Y = 72
PILE_GAP = 22


class ReverseSolitaireApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reverse Solitaire v0.1.1")
        self.geometry("1000x760")
        self.minsize(820, 640)
        self.configure(bg="#0b5d35")

        self.game = GameState.new()
        self.status = tk.StringVar()

        toolbar = tk.Frame(self, bg="#123c2a")
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="新しいゲーム", command=self.new_game).pack(side="left", padx=8, pady=8)
        tk.Button(toolbar, text="選択した2枚を取り除く", command=self.remove_selected).pack(side="left", padx=4, pady=8)
        tk.Button(toolbar, text="ギブアップ", command=self.give_up).pack(side="left", padx=4, pady=8)
        tk.Label(toolbar, textvariable=self.status, fg="white", bg="#123c2a", font=("Yu Gothic UI", 11, "bold")).pack(side="right", padx=12)

        guide = tk.Label(
            self,
            text="操作: 表向きの一番上のカードをクリックして2枚選択 / 山の下の［ひっくり返す］で同じ位置のまま表裏を反転",
            fg="white", bg="#0b5d35", font=("Yu Gothic UI", 10),
        )
        guide.pack(fill="x", pady=(8, 0))

        self.canvas = tk.Canvas(self, bg="#0b5d35", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.bind("<Configure>", lambda _e: self.redraw())

        self.hit_regions: list[tuple[str, int, tuple[float, float, float, float]]] = []
        self.redraw()

    def new_game(self):
        self.game = GameState.new()
        self.redraw()

    def remove_selected(self):
        if not self.game.remove_selected():
            messagebox.showinfo("取り除けません", "表向きの一番上のカードから、同じ数字を2枚選んでください。")
        self.redraw()
        if self.game.won:
            messagebox.showinfo("ゲームクリア", f"全てのカードを取り除きました！\n手数: {self.game.moves}")

    def give_up(self):
        if messagebox.askyesno("ギブアップ", "このゲームを終了しますか？"):
            self.game.give_up()
            self.redraw()

    def on_canvas_click(self, event):
        if self.game.finished:
            return
        for action, pile_index, (x1, y1, x2, y2) in reversed(self.hit_regions):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if action == "top":
                    self.game.toggle_select(pile_index)
                elif action == "flip":
                    self.game.flip_pile(pile_index)
                self.redraw()
                return

    def redraw(self):
        self.canvas.delete("all")
        self.hit_regions.clear()
        self.update_idletasks()
        width = max(self.canvas.winfo_width(), 800)

        active_piles = len(self.game.piles)
        total_w = active_piles * CARD_W + max(0, active_piles - 1) * PILE_GAP
        start_x = max(MARGIN_X, (width - total_w) / 2)

        for i, pile in enumerate(self.game.piles):
            x = start_x + i * (CARD_W + PILE_GAP)
            base_y = MARGIN_Y
            if not pile:
                self.canvas.create_rectangle(x, base_y, x + CARD_W, base_y + CARD_H, outline="#8bc6a7", dash=(4, 4), width=2)
                y_button = base_y + CARD_H + 14
            else:
                for j, pc in enumerate(pile):
                    y = base_y + j * OFFSET_Y
                    is_top = j == len(pile) - 1
                    selected = i in self.game.selected and is_top
                    if pc.face_up:
                        fill = "#fffdf5"
                        outline = "#ffd54f" if selected else "#222222"
                        width_line = 4 if selected else 2
                        self.canvas.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill=fill, outline=outline, width=width_line)
                        suit_red = pc.card.suit in ("♥", "♦")
                        self.canvas.create_text(x + 10, y + 9, text=pc.card.label, anchor="nw", font=("Arial", 15, "bold"), fill="#b00020" if suit_red else "#111111")
                    else:
                        self.canvas.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill="#273c75", outline="#d9e7ff", width=2)
                        for k in range(5):
                            self.canvas.create_line(x + 8, y + 18 + k * 18, x + CARD_W - 8, y + 8 + k * 18, fill="#a8c6ff")
                    if is_top:
                        self.hit_regions.append(("top", i, (x, y, x + CARD_W, y + CARD_H)))
                y_button = base_y + (len(pile) - 1) * OFFSET_Y + CARD_H + 12

            self.canvas.create_rectangle(x, y_button, x + CARD_W, y_button + 30, fill="#f2f2f2", outline="#111111")
            self.canvas.create_text(x + CARD_W / 2, y_button + 15, text="ひっくり返す", font=("Yu Gothic UI", 9, "bold"))
            self.hit_regions.append(("flip", i, (x, y_button, x + CARD_W, y_button + 30)))
            self.canvas.create_text(x + CARD_W / 2, y_button + 48, text=f"組 {i + 1}", fill="white", font=("Yu Gothic UI", 9))

        matches = len(self.game.available_matches())
        state_text = "クリア！" if self.game.won else ("ギブアップ" if self.game.given_up else f"現在取れるペア: {matches}")
        self.status.set(f"残り {self.game.remaining_cards}枚 / 取り除いたペア {self.game.removed_pairs} / 手数 {self.game.moves} / {state_text}")


if __name__ == "__main__":
    ReverseSolitaireApp().mainloop()
