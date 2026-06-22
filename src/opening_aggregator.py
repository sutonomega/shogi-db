"""
Opening move aggregation from stored positions.
"""

from collections import defaultdict

from .game_repository import GameRepository, OpeningAggregate
from .sfen_generator import PositionRecord


class OpeningAggregator:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def aggregate(self, source: str = "self") -> list[OpeningAggregate]:
        return self.repository.list_opening_aggregates(source=source)

    def rebuild(self, source: str = "self") -> list[OpeningAggregate]:
        aggregates = self.aggregate(source=source)
        self.repository.upsert_opening_aggregates(aggregates)
        return aggregates

    def aggregate_positions(
        self,
        positions: list[PositionRecord],
        *,
        source: str,
    ) -> list[OpeningAggregate]:
        grouped: dict[tuple[str, str], list[int | None]] = defaultdict(list)
        for previous, current in zip(positions, positions[1:]):
            if current.move_usi is None:
                continue
            grouped[(previous.sfen, current.move_usi)].append(current.eval)

        aggregates = []
        for (sfen, move), evals in grouped.items():
            numeric_evals = [value for value in evals if value is not None]
            avg_eval = (
                round(sum(numeric_evals) / len(numeric_evals))
                if numeric_evals
                else None
            )
            aggregates.append(
                OpeningAggregate(
                    source=source,
                    sfen=sfen,
                    move=move,
                    count=len(evals),
                    avg_eval=avg_eval,
                )
            )
        return sorted(aggregates, key=lambda aggregate: (-aggregate.count, aggregate.sfen, aggregate.move))
