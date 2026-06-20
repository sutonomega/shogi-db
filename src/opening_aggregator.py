"""
Opening move aggregation from stored positions.
"""

from .game_repository import GameRepository, OpeningAggregate


class OpeningAggregator:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def aggregate(self, source: str = "self") -> list[OpeningAggregate]:
        return self.repository.list_opening_aggregates(source=source)
