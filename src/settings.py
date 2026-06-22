import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


BOARD_THEMES = {"light", "warm", "resin", "dark"}

PIECE_THEMES = {
    "hitomoji",
    "hitomoji_wood",
    "hitomoji_gothic",
    "hitomoji_dark",
    "hitomoji_gothic_dark",
    "futamoji",
}


@dataclass
class AppSettings:
    suisho_engine_path: str = ""
    llm_command: str = ""
    board_theme: str = "light"
    piece_theme: str = "hitomoji"


def settings_path() -> Path:
    explicit_path = os.environ.get(
        "SHOGI_DB_SETTINGS_PATH"
    )
    if explicit_path:
        return Path(explicit_path).expanduser()

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "shogi-db" / "config.json"

    return (
        Path.home()
        / ".config"
        / "shogi-db"
        / "config.json"
    )


def load_settings() -> AppSettings:
    path = settings_path()

    data = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))

    settings = AppSettings(
        suisho_engine_path=str(
            data.get("suisho_engine_path")
            or os.environ.get("SUISHO_ENGINE_PATH", "")
        ),
        llm_command=str(
            data.get("llm_command")
            or os.environ.get("SHOGI_DB_LLM_COMMAND", "")
        ),
        board_theme=str(data.get("board_theme") or "light"),
        piece_theme=str(data.get("piece_theme") or "hitomoji"),
    )

    if settings.board_theme not in BOARD_THEMES:
        settings.board_theme = "light"

    if settings.piece_theme not in PIECE_THEMES:
        settings.piece_theme = "hitomoji"

    return settings


def save_settings(settings: AppSettings) -> AppSettings:
    if settings.board_theme not in BOARD_THEMES:
        raise ValueError("invalid board_theme")

    if settings.piece_theme not in PIECE_THEMES:
        raise ValueError("invalid piece_theme")

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return settings
