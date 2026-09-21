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
        # False: packet is on the upper side of its hinge.
        # True: packet is on the lower side after a downward turnover.
        # The list always represents the current visual top-to-bottom order.
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
        return None if not pile else 0

    def top_card(self, pile_index: int) -> PileCard | None:
        idx = self.top_index(pile_index)
        return None if idx is None else self.piles[pile_index][idx]

    def flip_pile(self, pile_index: int) -> None:
        """Physically turn the packet over, reversing its visible order.

        Every turnover reverses the visual top-to-bottom order. When turning
        downward, all cards are made face-up so rank/suit information is always
        readable. When turning upward again, the alternating face-up/face-down
        pattern is restored for the current packet, preserving the memory-game
        element on the upper side.
        """
        if self.finished:
            return
        pile = self.piles[pile_index]
        if not pile:
            return

        turning_down = not self.flipped[pile_index]
        pile.reverse()
        self.flipped[pile_index] = turning_down

        if turning_down:
            for pc in pile:
                pc.face_up = True
        else:
            for i, pc in enumerate(pile):
                pc.face_up = (i % 2 == 0)

        self.selected.clear()
        self.moves += 1

    def toggle_select(self, pile_index: int) -> bool:
        """Select the visually uppermost card; it may be hidden on the upper side."""
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
    """Small test helper: iterable of (rank, suit, face_up), visual top-to-bottom."""
    return GameState([
        [PileCard(Card(rank, suit), face_up) for rank, suit, face_up in pile]
        for pile in piles
    ])
