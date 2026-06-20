"""
SQLite persistence for parsed games and generated positions.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .kif_parser import GameRecord
from .sfen_generator import PositionRecord


@dataclass
class StoredGame:
    id: int
    played_at: str | None
    black: str
    white: str
    winner: str | None
    move_count: int
    strategy: str | None
    enclosure: str | None
    raw_kif: str


@dataclass
class StoredPosition:
    move_number: int
    sfen: str
    move: str | None
    eval: int | None
    best_move: str | None
    pv: str | None
    candidates: str


@dataclass
class StrategyStats:
    strategy: str
    games: int
    wins: int
    losses: int
    draws: int

    @property
    def win_rate(self) -> float | None:
        decisive_games = self.wins + self.losses
        if decisive_games == 0:
            return None
        return self.wins / decisive_games


@dataclass
class EnclosureStats:
    enclosure: str
    games: int
    wins: int
    losses: int
    draws: int

    @property
    def win_rate(self) -> float | None:
        decisive_games = self.wins + self.losses
        if decisive_games == 0:
            return None
        return self.wins / decisive_games


@dataclass
class BlunderRecord:
    game_id: int
    move_number: int
    move: str
    black: str
    white: str
    eval_before: int
    eval_after: int
    eval_delta: int
    loss: int


@dataclass
class OpeningAggregate:
    source: str
    sfen: str
    move: str
    count: int
    avg_eval: int | None


class GameRepository:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.connection.close()

    def init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at   TEXT,
                black       TEXT NOT NULL,
                white       TEXT NOT NULL,
                winner      TEXT,
                move_count  INTEGER,
                strategy    TEXT,
                enclosure   TEXT,
                raw_kif     TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS positions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id     INTEGER NOT NULL REFERENCES games(id),
                move_number INTEGER NOT NULL,
                sfen        TEXT NOT NULL,
                move        TEXT,
                eval        INTEGER,
                best_move   TEXT,
                pv          TEXT,
                candidates  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_positions_game_id
                ON positions(game_id);
            CREATE INDEX IF NOT EXISTS idx_positions_sfen
                ON positions(sfen);

            CREATE TABLE IF NOT EXISTS openings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT NOT NULL DEFAULT 'self',
                sfen        TEXT NOT NULL,
                move        TEXT NOT NULL,
                count       INTEGER NOT NULL DEFAULT 0,
                avg_eval    INTEGER,
                updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(source, sfen, move)
            );

            CREATE INDEX IF NOT EXISTS idx_openings_sfen
                ON openings(sfen);
            CREATE INDEX IF NOT EXISTS idx_openings_source_sfen
                ON openings(source, sfen);
            """
        )
        self.connection.commit()

    def save_game(
        self,
        game: GameRecord,
        positions: list[PositionRecord],
        *,
        strategy: str | None = None,
        enclosure: str | None = None,
        skip_duplicates: bool = True,
    ) -> int:
        if skip_duplicates:
            existing_id = self.find_game_id_by_raw_kif(game.raw_kif)
            if existing_id is not None:
                self._replace_game(existing_id, game, positions, strategy, enclosure)
                return existing_id

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO games (
                    played_at, black, white, winner, move_count,
                    strategy, enclosure, raw_kif
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game.played_at,
                    game.black,
                    game.white,
                    game.winner,
                    game.move_count,
                    strategy,
                    enclosure,
                    game.raw_kif,
                ),
            )
            game_id = int(cursor.lastrowid)

            self.connection.executemany(
                """
                INSERT INTO positions (
                    game_id, move_number, sfen, move, eval,
                    best_move, pv, candidates
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        game_id,
                        position.move_number,
                        position.sfen,
                        position.move_usi,
                        position.eval,
                        position.best_move,
                        position.pv,
                        self._dump_candidates(position),
                    )
                    for position in positions
                ],
            )

        return game_id

    def _replace_game(
        self,
        game_id: int,
        game: GameRecord,
        positions: list[PositionRecord],
        strategy: str | None,
        enclosure: str | None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE games
                SET played_at = ?,
                    black = ?,
                    white = ?,
                    winner = ?,
                    move_count = ?,
                    strategy = ?,
                    enclosure = ?,
                    raw_kif = ?
                WHERE id = ?
                """,
                (
                    game.played_at,
                    game.black,
                    game.white,
                    game.winner,
                    game.move_count,
                    strategy,
                    enclosure,
                    game.raw_kif,
                    game_id,
                ),
            )
            self.connection.execute(
                "DELETE FROM positions WHERE game_id = ?",
                (game_id,),
            )
            self.connection.executemany(
                """
                INSERT INTO positions (
                    game_id, move_number, sfen, move, eval,
                    best_move, pv, candidates
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        game_id,
                        position.move_number,
                        position.sfen,
                        position.move_usi,
                        position.eval,
                        position.best_move,
                        position.pv,
                        self._dump_candidates(position),
                    )
                    for position in positions
                ],
            )

    def find_game_id_by_raw_kif(self, raw_kif: str) -> int | None:
        row = self.connection.execute(
            "SELECT id FROM games WHERE raw_kif = ? LIMIT 1",
            (raw_kif,),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def get_game(self, game_id: int) -> StoredGame | None:
        row = self.connection.execute(
            """
            SELECT
                id, played_at, black, white, winner, move_count,
                strategy, enclosure, raw_kif
            FROM games
            WHERE id = ?
            """,
            (game_id,),
        ).fetchone()
        if row is None:
            return None
        return StoredGame(
            id=int(row["id"]),
            played_at=row["played_at"],
            black=row["black"],
            white=row["white"],
            winner=row["winner"],
            move_count=int(row["move_count"]),
            strategy=row["strategy"],
            enclosure=row["enclosure"],
            raw_kif=row["raw_kif"],
        )

    def list_games(self) -> list[StoredGame]:
        rows = self.connection.execute(
            """
            SELECT
                id, played_at, black, white, winner, move_count,
                strategy, enclosure
            FROM games
            ORDER BY id DESC
            """
        ).fetchall()
        return [
            StoredGame(
                id=int(row["id"]),
                played_at=row["played_at"],
                black=row["black"],
                white=row["white"],
                winner=row["winner"],
                move_count=int(row["move_count"]),
                strategy=row["strategy"],
                enclosure=row["enclosure"],
                raw_kif="",
            )
            for row in rows
        ]

    def list_positions(self, game_id: int) -> list[StoredPosition]:
        rows = self.connection.execute(
            """
            SELECT
                move_number, sfen, move, eval,
                best_move, pv, candidates
            FROM positions
            WHERE game_id = ?
            ORDER BY move_number
            """,
            (game_id,),
        ).fetchall()
        return [
            StoredPosition(
                move_number=int(row["move_number"]),
                sfen=row["sfen"],
                move=row["move"],
                eval=row["eval"],
                best_move=row["best_move"],
                pv=row["pv"],
                candidates=row["candidates"],
            )
            for row in rows
        ]

    def list_strategy_stats(self) -> list[StrategyStats]:
        rows = self.connection.execute(
            """
            SELECT
                strategy,
                COUNT(*) AS games,
                SUM(CASE WHEN winner = 'black' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN winner = 'white' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN winner = 'draw' THEN 1 ELSE 0 END) AS draws
            FROM games
            WHERE strategy IS NOT NULL
            GROUP BY strategy
            ORDER BY games DESC, strategy ASC
            """
        ).fetchall()
        return [
            StrategyStats(
                strategy=row["strategy"],
                games=int(row["games"]),
                wins=int(row["wins"]),
                losses=int(row["losses"]),
                draws=int(row["draws"]),
            )
            for row in rows
        ]

    def list_enclosure_stats(self) -> list[EnclosureStats]:
        rows = self.connection.execute(
            """
            SELECT
                enclosure,
                COUNT(*) AS games,
                SUM(CASE WHEN winner = 'black' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN winner = 'white' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN winner = 'draw' THEN 1 ELSE 0 END) AS draws
            FROM games
            WHERE enclosure IS NOT NULL
            GROUP BY enclosure
            ORDER BY games DESC, enclosure ASC
            """
        ).fetchall()
        return [
            EnclosureStats(
                enclosure=row["enclosure"],
                games=int(row["games"]),
                wins=int(row["wins"]),
                losses=int(row["losses"]),
                draws=int(row["draws"]),
            )
            for row in rows
        ]

    def list_blunders(self, limit: int = 20) -> list[BlunderRecord]:
        rows = self.connection.execute(
            """
            SELECT
                games.id AS game_id,
                games.black AS black,
                games.white AS white,
                current.move_number AS move_number,
                current.move AS move,
                previous.eval AS eval_before,
                current.eval AS eval_after,
                CASE
                    WHEN current.move_number % 2 = 1
                    THEN current.eval - previous.eval
                    ELSE previous.eval - current.eval
                END AS eval_delta
            FROM positions AS current
            JOIN positions AS previous
                ON previous.game_id = current.game_id
                AND previous.move_number = current.move_number - 1
            JOIN games
                ON games.id = current.game_id
            WHERE current.eval IS NOT NULL
                AND previous.eval IS NOT NULL
                AND current.move IS NOT NULL
                AND (
                    CASE
                        WHEN current.move_number % 2 = 1
                        THEN current.eval - previous.eval
                        ELSE previous.eval - current.eval
                    END
                ) < 0
            ORDER BY eval_delta ASC, current.move_number ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            BlunderRecord(
                game_id=int(row["game_id"]),
                move_number=int(row["move_number"]),
                move=row["move"],
                black=row["black"],
                white=row["white"],
                eval_before=int(row["eval_before"]),
                eval_after=int(row["eval_after"]),
                eval_delta=int(row["eval_delta"]),
                loss=abs(int(row["eval_delta"])),
            )
            for row in rows
        ]

    def list_opening_aggregates(self, source: str = "self") -> list[OpeningAggregate]:
        rows = self.connection.execute(
            """
            SELECT
                ? AS source,
                previous.sfen AS sfen,
                current.move AS move,
                COUNT(*) AS count,
                CAST(ROUND(AVG(current.eval)) AS INTEGER) AS avg_eval
            FROM positions AS current
            JOIN positions AS previous
                ON previous.game_id = current.game_id
                AND previous.move_number = current.move_number - 1
            WHERE current.move IS NOT NULL
            GROUP BY previous.sfen, current.move
            ORDER BY count DESC, previous.sfen ASC, current.move ASC
            """,
            (source,),
        ).fetchall()
        return [
            OpeningAggregate(
                source=row["source"],
                sfen=row["sfen"],
                move=row["move"],
                count=int(row["count"]),
                avg_eval=int(row["avg_eval"]) if row["avg_eval"] is not None else None,
            )
            for row in rows
        ]

    def _dump_candidates(self, position: PositionRecord) -> str:
        return json.dumps(
            [
                {"move": candidate.move, "eval": candidate.eval}
                for candidate in position.candidates
            ],
            ensure_ascii=False,
        )
