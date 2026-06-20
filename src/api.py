"""
Application API operations for importing and reading games.
"""

import json

from .enclosure_detector import EnclosureDetector
from .game_repository import (
    BlunderRecord,
    EnclosureStats,
    GameRepository,
    StoredGame,
    StoredPosition,
    StrategyStats,
)
from .kif_parser import KifParser
from .sfen_generator import SfenGenerator
from .strategy_detector import StrategyDetector


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

    def list_games(self) -> dict:
        return {
            "games": [
                self._game_summary_to_dict(game)
                for game in self.repository.list_games()
            ]
        }

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
            "move_number": position.move_number,
            "sfen": position.sfen,
            "move": position.move,
            "eval": position.eval,
            "best_move": position.best_move,
            "pv": position.pv,
            "candidates": json.loads(position.candidates),
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
