"""
USI engine integration for post-game position analysis.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


MATE_EVAL = 100_000
MAX_CANDIDATES = 5


@dataclass
class EngineAnalysis:
    eval: int | None
    best_move: str | None
    pv: str | None
    candidates: list[dict]
    engine_name: str
    engine_depth: int


class UsiEngineError(RuntimeError):
    pass


class UsiEngineAnalyzer:
    _RE_INFO = re.compile(r"\binfo\b.*\bscore\s+(cp|mate)\s+([+-]?\d+).*?(?:\bpv\s+(.+))?$")
    _RE_BESTMOVE = re.compile(r"^bestmove\s+(\S+)")
    _RE_NAME = re.compile(r"^id\s+name\s+(.+)")
    _RE_MULTIPV = re.compile(r"\bmultipv\s+(\d+)")

    def __init__(
        self,
        engine_path: str,
        *,
        engine_name: str | None = None,
        depth: int = 18,
        timeout: float = 60.0,
    ) -> None:
        if not engine_path.strip():
            raise UsiEngineError("Engine path is empty")
        if depth <= 0:
            raise UsiEngineError("Engine depth must be positive")
        self.engine_path = engine_path
        self.engine_name = engine_name
        self.depth = depth
        self.timeout = timeout

    def analyze_sfen(self, sfen: str) -> EngineAnalysis:
        if not sfen.strip():
            raise UsiEngineError("SFEN is empty")

        process = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdin is not None
        assert process.stdout is not None

        lines: list[str] = []
        try:
            self._send(process, "usi")
            lines.extend(self._read_until(process, "usiok"))
            self._send(process, f"setoption name MultiPV value {MAX_CANDIDATES}")
            self._send(process, "isready")
            lines.extend(self._read_until(process, "readyok"))
            self._send(process, f"position sfen {sfen}")
            self._send(process, f"go depth {self.depth}")
            lines.extend(self._read_until(process, "bestmove"))
            self._send(process, "quit")
        finally:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()

        return parse_usi_analysis(
            lines,
            engine_name=self.engine_name,
            requested_depth=self.depth,
        )

    @staticmethod
    def _send(process: subprocess.Popen, command: str) -> None:
        if process.stdin is None:
            raise UsiEngineError("Engine stdin is closed")
        process.stdin.write(f"{command}\n")
        process.stdin.flush()

    def _read_until(self, process: subprocess.Popen, marker: str) -> list[str]:
        if process.stdout is None:
            raise UsiEngineError("Engine stdout is closed")
        lines: list[str] = []
        while True:
            line = process.stdout.readline()
            if line == "":
                raise UsiEngineError(f"Engine stopped before {marker}")
            stripped = line.strip()
            lines.append(stripped)
            if stripped.startswith(marker):
                return lines


def parse_usi_analysis(
    lines: list[str],
    *,
    engine_name: str | None = None,
    requested_depth: int,
) -> EngineAnalysis:
    parsed_engine_name = engine_name
    latest_eval: int | None = None
    latest_pv: str | None = None
    best_move: str | None = None
    candidates_by_rank: dict[int, dict] = {}

    for line in lines:
        name_match = UsiEngineAnalyzer._RE_NAME.match(line)
        if name_match and parsed_engine_name is None:
            parsed_engine_name = name_match.group(1).strip()
            continue

        info_match = UsiEngineAnalyzer._RE_INFO.match(line)
        if info_match:
            eval_value = _score_to_eval(info_match.group(1), info_match.group(2))
            pv = info_match.group(3).strip() if info_match.group(3) else None
            multipv_match = UsiEngineAnalyzer._RE_MULTIPV.search(line)
            multipv = int(multipv_match.group(1)) if multipv_match else 1
            if multipv == 1:
                latest_eval = eval_value
                latest_pv = pv
            if pv:
                candidates_by_rank[multipv] = {
                    "move": pv.split()[0],
                    "eval": eval_value,
                }
            continue

        bestmove_match = UsiEngineAnalyzer._RE_BESTMOVE.match(line)
        if bestmove_match:
            best_move = bestmove_match.group(1)

    if best_move is None and latest_pv:
        best_move = latest_pv.split()[0]

    return EngineAnalysis(
        eval=latest_eval,
        best_move=best_move,
        pv=latest_pv,
        candidates=[
            candidate
            for _, candidate in sorted(candidates_by_rank.items())
        ][:MAX_CANDIDATES],
        engine_name=parsed_engine_name or "USI Engine",
        engine_depth=requested_depth,
    )


def _score_to_eval(score_type: str, raw_value: str) -> int:
    value = int(raw_value)
    if score_type == "cp":
        return value
    return MATE_EVAL if value > 0 else -MATE_EVAL
