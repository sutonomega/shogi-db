"""
Application API operations for importing and reading games.
"""

import json
import os
from pathlib import Path

from .enclosure_detector import EnclosureDetector
from .game_repository import (
    BlunderRecord,
    EnclosureStats,
    GameRepository,
    MoveFrequency,
    OpeningAggregate,
    StoredGame,
    StoredPosition,
    StrategyStats,
)
from .kif_encoding import decode_kif_bytes
from .kif_parser import KifParser
from .opening_aggregator import OpeningAggregator
from .position_explanation import (
    build_position_explanation_materials,
    build_position_explanation_prompt,
)
from .sfen_generator import SfenGenerator
from .strategy_detector import StrategyDetector
from .usi_engine import UsiEngineAnalyzer, UsiEngineError


class ApiError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ShogiDbApi:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository
        self.repository.init_schema()

    def import_game(self, kif_text: str) -> dict:
        if not kif_text.strip():
            raise ApiError("KIF text is empty", 400)

        game = KifParser().parse(kif_text)
        positions = SfenGenerator().generate(game)
        strategy = StrategyDetector().detect(positions)
        enclosure = EnclosureDetector().detect(positions)
        game_id = self.repository.save_game(
            game,
            positions,
            strategy=strategy,
            enclosure=enclosure,
        )

        return {
            "game": self._game_to_dict(self.repository.get_game(game_id)),
            "positions_count": len(positions),
        }

    def import_game_bytes(self, kif_data: bytes) -> dict:
        if not kif_data.strip():
            raise ApiError("KIF file is empty", 400)
        return self.import_game(decode_kif_bytes(kif_data))

    def import_games_from_directory(
        self,
        directory_path: str,
        *,
        recursive: bool = False,
        progress_callback=None,
        should_cancel=None,
    ) -> dict:
        if not directory_path.strip():
            raise ApiError("Directory path is empty", 400)
        directory = Path(directory_path).expanduser()
        if not directory.is_dir():
            raise ApiError(f"Directory not found: {directory_path}", 400)

        total = self.count_kif_files(directory, recursive=recursive)
        processed = 0
        imported = 0
        errors = []
        imported_games = []
        if progress_callback is not None:
            progress_callback(processed, total)

        for file_path in self._iter_kif_files(directory, recursive=recursive):
            if should_cancel is not None and should_cancel():
                break
            try:
                response = self.import_game_bytes(file_path.read_bytes())
            except Exception as exc:
                errors.append({
                    "path": str(file_path),
                    "error": str(exc),
                })
                processed += 1
                if progress_callback is not None:
                    progress_callback(processed, total)
                continue

            imported += 1
            game = dict(response["game"])
            game.pop("raw_kif", None)
            imported_games.append({
                "path": str(file_path),
                "game": game,
                "positions_count": response["positions_count"],
            })
            processed += 1
            if progress_callback is not None:
                progress_callback(processed, total)

        return {
            "path": str(directory),
            "recursive": recursive,
            "total": total,
            "imported": imported,
            "failed": len(errors),
            "errors": errors,
            "games": imported_games,
        }

    def list_games(self) -> dict:
        return {
            "games": [
                self._game_summary_to_dict(game)
                for game in self.repository.list_games()
            ]
        }

    @staticmethod
    def _iter_kif_files(directory: Path, *, recursive: bool):
        paths = directory.rglob("*") if recursive else directory.iterdir()
        for path in paths:
            if path.is_file() and path.suffix.lower() == ".kif":
                yield path

    def count_kif_files(self, directory: Path, *, recursive: bool) -> int:
        return sum(1 for _ in self._iter_kif_files(directory, recursive=recursive))

    def get_positions(self, game_id: int) -> dict:
        game = self.repository.get_game(game_id)
        if game is None:
            raise ApiError(f"Game not found: {game_id}", 404)

        return {
            "game": self._game_summary_to_dict(game),
            "positions": [
                self._position_to_dict(position)
                for position in self.repository.list_positions(game_id)
            ],
        }

    def get_strategy_stats(self) -> dict:
        return {
            "strategies": [
                self._strategy_stats_to_dict(stats)
                for stats in self.repository.list_strategy_stats()
            ]
        }

    def get_enclosure_stats(self) -> dict:
        return {
            "enclosures": [
                self._enclosure_stats_to_dict(stats)
                for stats in self.repository.list_enclosure_stats()
            ]
        }

    def get_blunders(self) -> dict:
        return {
            "blunders": [
                self._blunder_to_dict(record)
                for record in self.repository.list_blunders()
            ]
        }

    def get_position_frequency(self, sfen: str) -> dict:
        if not sfen.strip():
            raise ApiError("SFEN is empty", 400)
        frequencies = self.repository.list_move_frequencies(sfen)
        total = sum(frequency.count for frequency in frequencies)
        return {
            "sfen": sfen,
            "total": total,
            "moves": [
                self._move_frequency_to_dict(frequency, total)
                for frequency in frequencies
            ],
        }

    def rebuild_openings(self, source: str = "self") -> dict:
        if not source.strip():
            raise ApiError("Opening source is empty", 400)
        openings = OpeningAggregator(self.repository).rebuild(source=source)
        return {
            "source": source,
            "count": len(openings),
            "openings": [
                self._opening_to_dict(opening)
                for opening in openings
            ],
        }

    def get_openings(self, sfen: str, source: str = "self") -> dict:
        if not sfen.strip():
            raise ApiError("SFEN is empty", 400)
        if not source.strip():
            raise ApiError("Opening source is empty", 400)
        openings = self.repository.list_openings(source=source, sfen=sfen)
        total = sum(opening.count for opening in openings)
        return {
            "source": source,
            "sfen": sfen,
            "total": total,
            "moves": [
                self._opening_to_dict(opening, total=total)
                for opening in openings
            ],
        }

    def analyze_position(
        self,
        position_id: int,
        *,
        engine_path: str | None = None,
        engine_name: str | None = None,
        depth: int = 18,
    ) -> dict:
        position = self.repository.get_position(position_id)
        if position is None:
            raise ApiError(f"Position not found: {position_id}", 404)

        resolved_engine_path = engine_path or os.environ.get("SUISHO_ENGINE_PATH")
        if not resolved_engine_path:
            raise ApiError("Engine path is required", 400)

        try:
            analysis = UsiEngineAnalyzer(
                resolved_engine_path,
                engine_name=engine_name,
                depth=depth,
            ).analyze_sfen(position.sfen)
        except UsiEngineError as exc:
            raise ApiError(str(exc), 500) from exc
        except OSError as exc:
            raise ApiError(str(exc), 500) from exc

        stored = self.repository.update_position_analysis(
            position_id,
            eval_value=analysis.eval,
            best_move=analysis.best_move,
            pv=analysis.pv,
            candidates=analysis.candidates,
            engine_name=analysis.engine_name,
            engine_depth=analysis.engine_depth,
        )
        if stored is None:
            raise ApiError(f"Position not found: {position_id}", 404)

        return {
            "position": self._position_to_dict(stored),
        }

    def get_position_explanation_prompt(self, position_id: int) -> dict:
        position = self.repository.get_position(position_id)
        if position is None:
            raise ApiError(f"Position not found: {position_id}", 404)

        position_data = self._position_to_dict(position)
        openings = [
            self._opening_to_dict(opening, total=None)
            for opening in self.repository.list_openings(
                source="self",
                sfen=position.sfen,
            )
        ]
        materials = build_position_explanation_materials(position_data, openings)
        return {
            "position": position_data,
            "materials": materials,
            "prompt": build_position_explanation_prompt(materials),
        }

    def _game_to_dict(self, game: StoredGame | None) -> dict:
        if game is None:
            raise ApiError("Saved game could not be loaded", 500)
        data = self._game_summary_to_dict(game)
        data["raw_kif"] = game.raw_kif
        return data

    def _game_summary_to_dict(self, game: StoredGame) -> dict:
        return {
            "id": game.id,
            "played_at": game.played_at,
            "black": game.black,
            "white": game.white,
            "winner": game.winner,
            "move_count": game.move_count,
            "strategy": game.strategy,
            "enclosure": game.enclosure,
        }

    def _position_to_dict(self, position: StoredPosition) -> dict:
        return {
            "id": position.id,
            "move_number": position.move_number,
            "sfen": position.sfen,
            "move": position.move,
            "eval": position.eval,
            "best_move": position.best_move,
            "pv": position.pv,
            "candidates": json.loads(position.candidates),
            "analyzed_at": position.analyzed_at,
            "engine_name": position.engine_name,
            "engine_depth": position.engine_depth,
        }

    def _strategy_stats_to_dict(self, stats: StrategyStats) -> dict:
        return {
            "strategy": stats.strategy,
            "games": stats.games,
            "wins": stats.wins,
            "losses": stats.losses,
            "draws": stats.draws,
            "win_rate": stats.win_rate,
        }

    def _enclosure_stats_to_dict(self, stats: EnclosureStats) -> dict:
        return {
            "enclosure": stats.enclosure,
            "games": stats.games,
            "wins": stats.wins,
            "losses": stats.losses,
            "draws": stats.draws,
            "win_rate": stats.win_rate,
        }

    def _blunder_to_dict(self, record: BlunderRecord) -> dict:
        return {
            "game_id": record.game_id,
            "move_number": record.move_number,
            "move": record.move,
            "black": record.black,
            "white": record.white,
            "eval_before": record.eval_before,
            "eval_after": record.eval_after,
            "eval_delta": record.eval_delta,
            "loss": record.loss,
        }

    def _move_frequency_to_dict(
        self,
        frequency: MoveFrequency,
        total: int,
    ) -> dict:
        return {
            "move": frequency.move,
            "count": frequency.count,
            "ratio": frequency.count / total if total else None,
            "avg_eval": frequency.avg_eval,
        }

    def _opening_to_dict(
        self,
        opening: OpeningAggregate,
        total: int | None = None,
    ) -> dict:
        data = {
            "source": opening.source,
            "sfen": opening.sfen,
            "move": opening.move,
            "count": opening.count,
            "avg_eval": opening.avg_eval,
        }
        if total is not None:
            data["ratio"] = opening.count / total if total else None
        return data
