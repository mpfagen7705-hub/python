"""Contracts (quests) and the quest log — pure logic, no pygame.

A contract is a named goal with one or more objectives. The classic flavor is an
*assassination contract*: eliminate one or more marked targets, optionally
without raising the alarm, then optionally escape. Completing a contract awards
XP through the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ObjectiveStatus(Enum):
    ACTIVE = 0
    COMPLETE = 1
    FAILED = 2


@dataclass
class Objective:
    key: str
    description: str
    required: int = 1
    progress: int = 0
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE
    optional: bool = False  # optional objectives don't block completion

    def advance(self, amount: int = 1) -> None:
        if self.status is not ObjectiveStatus.ACTIVE:
            return
        self.progress = min(self.required, self.progress + amount)
        if self.progress >= self.required:
            self.status = ObjectiveStatus.COMPLETE

    def fail(self) -> None:
        if self.status is ObjectiveStatus.ACTIVE:
            self.status = ObjectiveStatus.FAILED

    @property
    def done(self) -> bool:
        return self.status is ObjectiveStatus.COMPLETE


class ContractStatus(Enum):
    ACTIVE = 0
    COMPLETE = 1
    FAILED = 2


@dataclass
class Contract:
    key: str
    name: str
    summary: str
    objectives: List[Objective] = field(default_factory=list)
    reward_xp: int = 0
    status: ContractStatus = ContractStatus.ACTIVE

    def objective(self, key: str) -> Optional[Objective]:
        for o in self.objectives:
            if o.key == key:
                return o
        return None

    def advance(self, key: str, amount: int = 1) -> None:
        obj = self.objective(key)
        if obj is not None:
            obj.advance(amount)
            self._refresh()

    def fail_objective(self, key: str) -> None:
        obj = self.objective(key)
        if obj is not None:
            obj.fail()
            self._refresh()

    def _refresh(self) -> None:
        """Recompute contract status from its required objectives."""
        if self.status is not ContractStatus.ACTIVE:
            return
        required = [o for o in self.objectives if not o.optional]
        if any(o.status is ObjectiveStatus.FAILED for o in required):
            self.status = ContractStatus.FAILED
        elif required and all(o.done for o in required):
            self.status = ContractStatus.COMPLETE

    @property
    def complete(self) -> bool:
        return self.status is ContractStatus.COMPLETE


class QuestLog:
    """Tracks contracts and reports total XP earned from completed ones."""

    def __init__(self) -> None:
        self.contracts: List[Contract] = []

    def add(self, contract: Contract) -> Contract:
        self.contracts.append(contract)
        return contract

    @property
    def active(self) -> List[Contract]:
        return [c for c in self.contracts if c.status is ContractStatus.ACTIVE]

    @property
    def completed(self) -> List[Contract]:
        return [c for c in self.contracts if c.status is ContractStatus.COMPLETE]

    def all_complete(self) -> bool:
        return bool(self.contracts) and all(
            c.status is ContractStatus.COMPLETE for c in self.contracts
        )

    def collect_rewards(self) -> int:
        """Return and zero out XP for newly completed contracts.

        A contract's reward is paid exactly once; ``reward_xp`` is consumed.
        """
        earned = 0
        for c in self.contracts:
            if c.status is ContractStatus.COMPLETE and c.reward_xp:
                earned += c.reward_xp
                c.reward_xp = 0
        return earned
