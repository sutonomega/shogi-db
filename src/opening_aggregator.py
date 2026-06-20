"""
Opening move aggregation from stored positions.
"""

from .game_repository import GameRepository, OpeningAggregate


class OpeningAggregator:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def aggregate(self, source: str = "self") -> list[OpeningAggregate]:
        return self.repository.list_opening_aggregates(source=source)

    def rebuild(self, source: str = "self") -> list[OpeningAggregate]:
        aggregates = self.aggregate(source=source)
        self.repository.upsert_opening_aggregates(aggregates)
        return aggregates
