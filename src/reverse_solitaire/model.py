from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def label(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass
class PileCard:
    card: Card
    face_up: bool


class GameState:
    """Core rules for Reverse Solitaire."""

    def __init__(self, piles: list[list[PileCard]]):
        self.piles = piles
        # Each pile physically alternates between the upper side (False) and
        # lower side (True) of its hinge. Card identity/order in the Python list
        # stays stable; the GUI's 180-degree projection naturally reverses the
        # visible top-to-bottom order after a turnover.
        self.flipped = [False for _ in piles]
        self.selected: list[int] = []
        self.given_up = False
        self.moves = 0
        self.removed_pairs = 0

    @classmethod
    def new(cls, *, seed: int | None = None, pile_size: int = 6) -> "GameState":
        if pile_size <= 0:
            raise ValueError("pile_size must be positive")
        deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        rng = random.Random(seed)
        rng.shuffle(deck)
        piles: list[list[PileCard]] = []
        for start in range(0, len(deck), pile_size):
            chunk = deck[start:start + pile_size]
            pile = [PileCard(card=card, face_up=(i % 2 == 0)) for i, card in enumerate(chunk)]
            piles.append(pile)
        return cls(piles)

    @property
    def remaining_cards(self) -> int:
        return sum(len(p) for p in self.piles)

    @property
    def won(self) -> bool:
        return self.remaining_cards == 0 and not self.given_up

    @property
    def finished(self) -> bool:
        return self.won or self.given_up

    def top_index(self, pile_index: int) -> int | None:
        pile = self.piles[pile_index]
        if not pile:
            return None
        # The physically uppermost card after the 180-degree turnover is still
        # the card at the packet's free end (list[-1]); its screen position is
        # what moves through the hinge. We do not force the previous visual top
        # to remain top by switching to the opposite list end.
        return len(pile) - 1

    def top_card(self, pile_index: int) -> PileCard | None:
        idx = self.top_index(pile_index)
        return None if idx is None else self.piles[pile_index][idx]

    def flip_pile(self, pile_index: int) -> None:
        """Turn a pile physically 180 degrees around its horizontal hinge.

        The GUI performs the real spatial turnover, so the visible vertical order
        reverses naturally: the old bottom of the displayed packet becomes the
        new top, the next card becomes second, and so on. We therefore do not
        switch the selectable end to preserve an old logical top.

        After the turnover all card faces in the packet are visible. This matches
        the physical reference supplied for the game: cards that were backs in
        the overlapped packet reveal their rank/suit after the turnover, while
        cards that were already showing a face remain readable.
        """
        if self.finished:
            return
        pile = self.piles[pile_index]
        if not pile:
            return

        self.flipped[pile_index] = not self.flipped[pile_index]
        for pc in pile:
            pc.face_up = True

        self.selected.clear()
        self.moves += 1

    def toggle_select(self, pile_index: int) -> bool:
        """Select the physically exposed top card."""
        if self.finished:
            return False
        top = self.top_card(pile_index)
        if top is None:
            return False
        if pile_index in self.selected:
            self.selected.remove(pile_index)
            return True
        if len(self.selected) >= 2:
            self.selected.clear()
        self.selected.append(pile_index)
        return True

    def can_remove_selected(self) -> bool:
        if len(self.selected) != 2:
            return False
        a, b = self.selected
        if a == b:
            return False
        ca, cb = self.top_card(a), self.top_card(b)
        return bool(ca and cb and ca.card.rank == cb.card.rank)

    def remove_selected(self) -> bool:
        if not self.can_remove_selected():
            return False
        for pile_index in self.selected:
            idx = self.top_index(pile_index)
            if idx is not None:
                self.piles[pile_index].pop(idx)
        self.selected.clear()
        self.moves += 1
        self.removed_pairs += 1
        return True

    def clear_selection(self) -> None:
        self.selected.clear()

    def available_matches(self) -> list[tuple[int, int]]:
        tops: list[tuple[int, PileCard]] = []
        for i, pile in enumerate(self.piles):
            if pile:
                top = self.top_card(i)
                if top is not None:
                    tops.append((i, top))
        matches: list[tuple[int, int]] = []
        for i, (pa, ca) in enumerate(tops):
            for pb, cb in tops[i + 1:]:
                if ca.card.rank == cb.card.rank:
                    matches.append((pa, pb))
        return matches

    def give_up(self) -> None:
        if not self.won:
            self.given_up = True
            self.selected.clear()


def build_state(piles: Iterable[Iterable[tuple[str, str, bool]]]) -> GameState:
    """Small test helper: iterable of (rank, suit, face_up), hinge -> free-end order."""
    return GameState([
        [PileCard(Card(rank, suit), face_up) for rank, suit, face_up in pile]
        for pile in piles
    ])
