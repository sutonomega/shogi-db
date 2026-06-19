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
    raw_kif: str


class GameRepository:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path)
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
            """
        )
        self.connection.commit()

    def save_game(
        self,
        game: GameRecord,
        positions: list[PositionRecord],
        *,
        skip_duplicates: bool = True,
    ) -> int:
        if skip_duplicates:
            existing_id = self.find_game_id_by_raw_kif(game.raw_kif)
            if existing_id is not None:
                return existing_id

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO games (
                    played_at, black, white, winner, move_count, raw_kif
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    game.played_at,
                    game.black,
                    game.white,
                    game.winner,
                    game.move_count,
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

    def find_game_id_by_raw_kif(self, raw_kif: str) -> int | None:
        row = self.connection.execute(
            "SELECT id FROM games WHERE raw_kif = ? LIMIT 1",
            (raw_kif,),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def get_game(self, game_id: int) -> StoredGame | None:
        row = self.connection.execute(
            """
            SELECT id, played_at, black, white, winner, move_count, raw_kif
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
            raw_kif=row["raw_kif"],
        )

    def list_positions(self, game_id: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT
                    move_number, sfen, move, eval,
                    best_move, pv, candidates
                FROM positions
                WHERE game_id = ?
                ORDER BY move_number
                """,
                (game_id,),
            )
        )

    def _dump_candidates(self, position: PositionRecord) -> str:
        return json.dumps(
            [
                {"move": candidate.move, "eval": candidate.eval}
                for candidate in position.candidates
            ],
            ensure_ascii=False,
        )
