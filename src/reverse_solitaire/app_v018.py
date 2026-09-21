from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reverse_solitaire.app import ReverseSolitaireApp as BaseApp  # type: ignore
    from reverse_solitaire.model import GameSnapshot, GameState  # type: ignore
else:
    from .app import ReverseSolitaireApp as BaseApp
    from .model import GameSnapshot, GameState


class ReverseSolitaireApp(BaseApp):
    """v0.1.19 UI extensions kept separate from the stable renderer."""

    def __init__(self):
        self._undo_snapshot: GameSnapshot | None = None
        self.current_easy_mode = False
        super().__init__()
        self.title("Reverse Solitaire v0.1.19")

        self.easy_mode = tk.BooleanVar(value=False)
        toolbar = next(
            child for child in self.winfo_children()
            if isinstance(child, tk.Frame)
        )
        tk.Button(toolbar, text="Undo", command=self.undo_last_action).pack(
            side="left", padx=(12, 4), pady=8
        )
        tk.Checkbutton(
            toolbar,
            text="イージー（次ゲーム）",
            variable=self.easy_mode,
            bg="#123c2a",
            fg="white",
            activebackground="#123c2a",
            activeforeground="white",
            selectcolor="#123c2a",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(side="left", padx=4, pady=8)
        self.redraw()

    def _silent_dialog(
        self,
        title: str,
        message: str,
        *,
        question: bool = False,
    ) -> bool:
        """Show an in-app modal without invoking Windows MessageBox sounds."""
        result = {"value": False}
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg="#f7f7f4")

        tk.Label(
            dialog,
            text=message,
            justify="left",
            wraplength=420,
            bg="#f7f7f4",
            fg="#202020",
            font=("Yu Gothic UI", 11),
            padx=24,
            pady=20,
        ).pack(fill="both", expand=True)

        buttons = tk.Frame(dialog, bg="#f7f7f4")
        buttons.pack(fill="x", padx=16, pady=(0, 16))

        def close(value: bool) -> None:
            result["value"] = value
            dialog.destroy()

        if question:
            tk.Button(buttons, text="はい", width=10, command=lambda: close(True)).pack(
                side="right", padx=4
            )
            tk.Button(buttons, text="いいえ", width=10, command=lambda: close(False)).pack(
                side="right", padx=4
            )
            dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
        else:
            tk.Button(buttons, text="OK", width=10, command=lambda: close(True)).pack(
                side="right", padx=4
            )
            dialog.protocol("WM_DELETE_WINDOW", lambda: close(True))

        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_reqheight()) // 3)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_force()
        self.wait_window(dialog)
        return result["value"]

    def _show_info(self, title: str, message: str) -> None:
        self._silent_dialog(title, message, question=False)

    def _ask_yes_no(self, title: str, message: str) -> bool:
        return self._silent_dialog(title, message, question=True)

    def new_game(self):
        if self.animating:
            return
        easy = bool(getattr(self, "easy_mode", None) and self.easy_mode.get())
        self.current_easy_mode = easy
        self.game = GameState.new(easy_mode=easy)
        self._undo_snapshot = None
        self.flip_angle.clear()
        self.remove_scale.clear()
        self.finale_step = None
        self._stop_all_audio()
        self.redraw()

    def _remember_for_undo(self, *, clear_selection: bool = False) -> None:
        snapshot = self.game.snapshot()
        if clear_selection:
            snapshot.selected = []
        self._undo_snapshot = snapshot

    def undo_last_action(self) -> None:
        if self.animating:
            return
        if self._undo_snapshot is None:
            self._show_info("Undo", "戻せる操作はありません。")
            return
        self._stop_all_audio()
        self.game.restore(self._undo_snapshot)
        self._undo_snapshot = None
        self.flip_angle.clear()
        self.remove_scale.clear()
        self.finale_step = None
        self.redraw()

    def animate_flip(self, pile_index: int):
        if self.game.finished or not self.game.piles[pile_index]:
            return
        self._remember_for_undo()
        super().animate_flip(pile_index)

    def animate_remove(self, pile_indices: list[int]):
        self._remember_for_undo(clear_selection=True)
        super().animate_remove(pile_indices)

    def give_up(self):
        if self.animating:
            return
        if self._ask_yes_no("ギブアップ", "このゲームを終了しますか？"):
            self._remember_for_undo(clear_selection=True)
            self.game.give_up()
            self.redraw()

    def show_hint(self) -> None:
        if self.animating:
            return
        if self.game.finished:
            self._show_info("ヒント", "ゲームは終了しています。")
            return
        if self.game.available_matches():
            self._show_info("ヒント", "現在、削除できるペアがあります。")
        else:
            self._show_info(
                "ヒント",
                "現在、削除できるペアはありません。\nカードをひっくり返して探してみてください。",
            )

    def animate_finale(self) -> None:
        """Same finale animation, with an application-drawn silent result dialog."""
        self.animating = True
        self.finale_step = 0
        self._play_wav_async(self._victory_wav)

        def frame(step: int) -> None:
            self.finale_step = step
            self.redraw()
            if step < 28:
                self.after(34, lambda: frame(step + 1))
            else:
                self.animating = False
                self.redraw()
                self.after(
                    120,
                    lambda: self._show_info(
                        "ゲームクリア",
                        f"全てのカードを取り除きました！\n手数: {self.game.moves}",
                    ),
                )

        frame(0)

    def redraw(self):
        super().redraw()
        if getattr(self, "current_easy_mode", False):
            current = self.status.get()
            if "イージー" not in current:
                self.status.set(f"{current} / イージー")


if __name__ == "__main__":
    ReverseSolitaireApp().mainloop()
