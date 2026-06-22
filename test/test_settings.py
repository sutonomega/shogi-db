import os
import tempfile
import unittest
from pathlib import Path

from src.settings import AppSettings, load_settings, save_settings


class TestSettings(unittest.TestCase):
    def test_load_settings_from_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SHOGI_DB_SETTINGS_PATH"] = str(Path(tmp) / "config.json")
            os.environ["SUISHO_ENGINE_PATH"] = "/mnt/share/Suisho5-AVX2.exe"
            os.environ["SHOGI_DB_LLM_COMMAND"] = "ollama run llama3.1"

            settings = load_settings()

            self.assertEqual(settings.suisho_engine_path, "/mnt/share/Suisho5-AVX2.exe")
            self.assertEqual(settings.llm_command, "ollama run llama3.1")

    def test_save_and_load_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SHOGI_DB_SETTINGS_PATH"] = str(Path(tmp) / "config.json")

            save_settings(AppSettings(
                suisho_engine_path="/engine.exe",
                llm_command="ollama run llama3.1",
                board_theme="dark",
                piece_theme="futamoji",
            ))

            settings = load_settings()

            self.assertEqual(settings.suisho_engine_path, "/engine.exe")
            self.assertEqual(settings.llm_command, "ollama run llama3.1")
            self.assertEqual(settings.board_theme, "dark")
            self.assertEqual(settings.piece_theme, "futamoji")
