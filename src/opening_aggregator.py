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

    def rebuild_with_progress(
        self,
        source: str = "self",
        *,
        progress_callback=None,
        should_cancel=None,
    ) -> tuple[list[OpeningAggregate], int, int, bool]:
        aggregates, processed, total, canceled = self.aggregate_with_progress(
            source=source,
            progress_callback=progress_callback,
            should_cancel=should_cancel,
        )
        if canceled:
            return aggregates, processed, total, True
        self.repository.upsert_opening_aggregates(aggregates)
        return aggregates, processed, total, False

    def aggregate_with_progress(
        self,
        source: str = "self",
        *,
        progress_callback=None,
        should_cancel=None,
    ) -> tuple[list[OpeningAggregate], int, int, bool]:
        total = self.repository.count_opening_position_pairs()
        processed = 0
        grouped: dict[tuple[str, str], list[int | None]] = defaultdict(list)
        if progress_callback is not None:
            progress_callback(processed, total)

        for sfen, move, eval_value in self.repository.iter_opening_position_pairs():
            if should_cancel is not None and should_cancel():
                return [], processed, total, True
            grouped[(sfen, move)].append(eval_value)
            processed += 1
            if progress_callback is not None:
                progress_callback(processed, total)

        aggregates = self._groups_to_aggregates(grouped, source=source)
        return aggregates, processed, total, False

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

        return self._groups_to_aggregates(grouped, source=source)

    @staticmethod
    def _groups_to_aggregates(
        grouped: dict[tuple[str, str], list[int | None]],
        *,
        source: str,
    ) -> list[OpeningAggregate]:
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
