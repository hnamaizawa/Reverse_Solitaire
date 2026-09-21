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


@dataclass
class GameSnapshot:
    piles: list[list[PileCard]]
    flipped: list[bool]
    selected: list[int]
    given_up: bool
    moves: int
    removed_pairs: int


class GameState:
    """Core rules for Reverse Solitaire."""

    def __init__(self, piles: list[list[PileCard]]):
        self.piles = piles
        self.flipped = [False for _ in piles]
        self.selected: list[int] = []
        self.given_up = False
        self.moves = 0
        self.removed_pairs = 0

    @staticmethod
    def _pile_capacities(card_count: int, pile_size: int) -> list[int]:
        return [min(pile_size, card_count - start) for start in range(0, card_count, pile_size)]

    @classmethod
    def _deal_easy(cls, rng: random.Random, pile_size: int) -> list[list[Card]]:
        """Deal so that no pile contains the same rank more than once."""
        deck_size = len(SUITS) * len(RANKS)
        capacities = cls._pile_capacities(deck_size, pile_size)
        if max(capacities, default=0) > len(RANKS):
            raise ValueError("easy_mode requires pile_size <= number of ranks")

        for _attempt in range(1000):
            piles: list[list[Card]] = [[] for _ in capacities]
            ranks_in_pile: list[set[str]] = [set() for _ in capacities]
            rank_order = list(RANKS)
            rng.shuffle(rank_order)
            failed = False

            for rank in rank_order:
                suits = list(SUITS)
                rng.shuffle(suits)
                candidates = [
                    i for i, capacity in enumerate(capacities)
                    if len(piles[i]) < capacity and rank not in ranks_in_pile[i]
                ]
                if len(candidates) < len(suits):
                    failed = True
                    break

                # Prefer piles with more free slots; random tie-breaking preserves variety.
                rng.shuffle(candidates)
                candidates.sort(key=lambda i: capacities[i] - len(piles[i]), reverse=True)
                chosen = candidates[:len(suits)]
                rng.shuffle(chosen)
                for suit, pile_index in zip(suits, chosen):
                    piles[pile_index].append(Card(rank, suit))
                    ranks_in_pile[pile_index].add(rank)

            if not failed and all(len(piles[i]) == capacities[i] for i in range(len(piles))):
                for pile in piles:
                    rng.shuffle(pile)
                return piles

        raise RuntimeError("could not create an easy-mode deal")

    @classmethod
    def new(
        cls,
        *,
        seed: int | None = None,
        pile_size: int = 6,
        easy_mode: bool = False,
    ) -> "GameState":
        if pile_size <= 0:
            raise ValueError("pile_size must be positive")
        rng = random.Random(seed)

        if easy_mode:
            card_piles = cls._deal_easy(rng, pile_size)
        else:
            deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
            rng.shuffle(deck)
            card_piles = [deck[start:start + pile_size] for start in range(0, len(deck), pile_size)]

        piles = [
            [PileCard(card=card, face_up=(i % 2 == 0)) for i, card in enumerate(chunk)]
            for chunk in card_piles
        ]
        return cls(piles)

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            piles=[
                [PileCard(Card(pc.card.rank, pc.card.suit), pc.face_up) for pc in pile]
                for pile in self.piles
            ],
            flipped=list(self.flipped),
            selected=list(self.selected),
            given_up=self.given_up,
            moves=self.moves,
            removed_pairs=self.removed_pairs,
        )

    def restore(self, snapshot: GameSnapshot) -> None:
        self.piles = [
            [PileCard(Card(pc.card.rank, pc.card.suit), pc.face_up) for pc in pile]
            for pile in snapshot.piles
        ]
        self.flipped = list(snapshot.flipped)
        self.selected = list(snapshot.selected)
        self.given_up = snapshot.given_up
        self.moves = snapshot.moves
        self.removed_pairs = snapshot.removed_pairs

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
        """Physically turn the packet over: reverse order and toggle every face."""
        if self.finished:
            return
        pile = self.piles[pile_index]
        if not pile:
            return

        pile.reverse()
        for pc in pile:
            pc.face_up = not pc.face_up
        self.flipped[pile_index] = not self.flipped[pile_index]
        self.selected.clear()
        self.moves += 1

    def toggle_select(self, pile_index: int) -> bool:
        """Select the visually uppermost card; it may be hidden by memory."""
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
