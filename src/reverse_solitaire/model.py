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
    """Core rules for Reverse Solitaire.

    Rule interpretation from v0.1.1:
    - A standard 52-card deck is shuffled and dealt into piles, 8 cards per pile
      (the final pile may contain fewer cards).
    - Cards in each pile alternate face-up / face-down from bottom to top.
    - Flipping a pile does not move any card. It only toggles every card's
      face-up / face-down state, so known/unknown cards trade places while
      staying in exactly the same positions.
    - Only the top card of a pile can be selected for matching.
    - Two face-up top cards with the same rank can be removed.
    - The player wins when all cards are removed.
    - The player can give up at any time.
    """

    def __init__(self, piles: list[list[PileCard]]):
        self.piles = piles
        self.selected: list[int] = []
        self.given_up = False
        self.moves = 0
        self.removed_pairs = 0

    @classmethod
    def new(cls, *, seed: int | None = None, pile_size: int = 8) -> "GameState":
        if pile_size <= 0:
            raise ValueError("pile_size must be positive")
        deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        rng = random.Random(seed)
        rng.shuffle(deck)
        piles: list[list[PileCard]] = []
        for start in range(0, len(deck), pile_size):
            chunk = deck[start:start + pile_size]
            # bottom card face-up, then alternate as cards rise through the pile
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

    def top_card(self, pile_index: int) -> PileCard | None:
        pile = self.piles[pile_index]
        return pile[-1] if pile else None

    def flip_pile(self, pile_index: int) -> None:
        if self.finished:
            return
        pile = self.piles[pile_index]
        if not pile:
            return
        for pc in pile:
            pc.face_up = not pc.face_up
        self.selected.clear()
        self.moves += 1

    def toggle_select(self, pile_index: int) -> bool:
        if self.finished:
            return False
        top = self.top_card(pile_index)
        if top is None or not top.face_up:
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
        return bool(ca and cb and ca.face_up and cb.face_up and ca.card.rank == cb.card.rank)

    def remove_selected(self) -> bool:
        if not self.can_remove_selected():
            return False
        for pile_index in sorted(self.selected, reverse=True):
            self.piles[pile_index].pop()
        self.selected.clear()
        self.moves += 1
        self.removed_pairs += 1
        return True

    def available_matches(self) -> list[tuple[int, int]]:
        tops: list[tuple[int, PileCard]] = []
        for i, pile in enumerate(self.piles):
            if pile and pile[-1].face_up:
                tops.append((i, pile[-1]))
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
    """Small test helper: iterable of (rank, suit, face_up), bottom -> top."""
    return GameState([
        [PileCard(Card(rank, suit), face_up) for rank, suit, face_up in pile]
        for pile in piles
    ])
