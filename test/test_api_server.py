import json
import tempfile
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.api_server import (
    DirectoryImportJobStore,
    create_server,
    import_directory_payload,
    import_game_payload,
    is_import_post_path,
    start_import_directory_payload,
)
from src.api import ShogiDbApi
from src.game_repository import GameRepository


KIF_TEXT = """\
開始日時：2024/02/10 19:00:00
手合割：平手
先手：解析太郎
後手：棋譜花子
手数----指手---------消費時間--
   1 ７六歩(77)
   2 ３四歩(33)
   3 投了
"""


class TestApiServer(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=True)
        try:
            self.server = create_server(self.temp_db.name, port=0)
        except PermissionError as exc:
            self.temp_db.close()
            self.skipTest(f"HTTP server sockets are unavailable: {exc}")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_db.close()

    def test_import_list_and_positions_endpoints(self):
        import_response = self._post_json("/api/games/import", {"kif": KIF_TEXT})

        self.assertEqual(import_response["game"]["id"], 1)
        self.assertEqual(import_response["positions_count"], 3)

        games_response = self._get_json("/api/games")
        self.assertEqual(len(games_response["games"]), 1)
        self.assertEqual(games_response["games"][0]["black"], "解析太郎")

        stats_response = self._get_json("/api/stats/strategies")
        self.assertEqual(stats_response["strategies"], [])

        enclosure_stats_response = self._get_json("/api/stats/enclosures")
        self.assertEqual(enclosure_stats_response["enclosures"], [])

        blunders_response = self._get_json("/api/stats/blunders")
        self.assertEqual(blunders_response["blunders"], [])

        positions_response = self._get_json("/api/games/1/positions")
        self.assertEqual(len(positions_response["positions"]), 3)
        self.assertEqual(positions_response["positions"][1]["move"], "7g7f")

        prompt_response = self._get_json("/api/positions/1/explanation-prompt")
        self.assertEqual(prompt_response["position"]["id"], 1)
        self.assertIn("SFEN:", prompt_response["prompt"])
        self.assertIn("評価値", prompt_response["materials"]["missing"])

        comparison_response = self._get_json(
            "/api/positions/1/opening-comparison-prompt?sources=self,professional"
        )
        self.assertEqual(comparison_response["position"]["id"], 1)
        self.assertEqual(comparison_response["sources"], ["self", "professional"])
        self.assertIn("source別定跡候補:", comparison_response["prompt"])
        self.assertIn("定跡候補:professional", comparison_response["materials"]["missing"])

        comparison_explain_response = self._post_json(
            "/api/positions/1/opening-comparison-explain",
            {
                "sources": ["self", "professional"],
                "llm_command": "python3 -c \"import sys; print('比較解説:' + sys.stdin.read().splitlines()[0])\"",
                "timeout": 5,
            },
        )
        self.assertEqual(comparison_explain_response["position"]["id"], 1)
        self.assertTrue(comparison_explain_response["explanation"].startswith("比較解説:"))

        explain_response = self._post_json(
            "/api/positions/1/explain",
            {
                "llm_command": "python3 -c \"import sys; print('解説:' + sys.stdin.read().splitlines()[0])\"",
                "timeout": 5,
            },
        )
        self.assertEqual(explain_response["position"]["id"], 1)
        self.assertTrue(explain_response["explanation"].startswith("解説:"))

    def test_blunder_explanation_prompt_endpoint(self):
        kif_text = """\
開始日時：2024/03/03 10:00:00
手合割：平手
先手：悪手太郎
後手：悪手花子
手数----指手---------消費時間--
   1 ７六歩(77)
**解析 0
*評価値 +100  読み筋 7g7f 3c3d
   2 ３四歩(33)
**解析 0
*評価値 +80  読み筋 3c3d 2g2f
   3 ２六歩(27)
**解析 0
*評価値 -120  読み筋 2g2f 8c8d
   4 投了
まで3手で先手の勝ち
"""
        self._post_json("/api/games/import", {"kif": kif_text})

        response = self._get_json("/api/blunders/explanation-prompt?game_id=1&move_number=3")

        self.assertEqual(response["materials"]["move"], "2g2f")
        self.assertEqual(response["materials"]["eval_delta"], -200)
        self.assertIn("着手前SFEN:", response["prompt"])

        explain_response = self._post_json(
            "/api/blunders/explain",
            {
                "game_id": 1,
                "move_number": 3,
                "llm_command": "python3 -c \"import sys; print('悪手解説:' + sys.stdin.read().splitlines()[0])\"",
                "timeout": 5,
            },
        )
        self.assertEqual(explain_response["materials"]["move"], "2g2f")
        self.assertTrue(explain_response["explanation"].startswith("悪手解説:"))

    def test_import_endpoint_accepts_cp932_kif_body(self):
        import_response = self._post_bytes(
            "/api/games/import",
            KIF_TEXT.encode("cp932"),
            "application/octet-stream",
        )

        self.assertEqual(import_response["game"]["black"], "解析太郎")
        self.assertEqual(import_response["positions_count"], 3)

    def test_missing_endpoint_returns_404(self):
        with self.assertRaises(HTTPError) as context:
            self._get_json("/api/missing")

        self.assertEqual(context.exception.code, 404)

    def _post_json(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_bytes(self, path: str, body: bytes, content_type: str) -> dict:
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, path: str) -> dict:
        with urlopen(f"{self.base_url}{path}", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


class TestImportGamePayload(unittest.TestCase):
    def setUp(self):
        self.repository = GameRepository()
        self.api = ShogiDbApi(self.repository)

    def tearDown(self):
        self.repository.close()

    def test_accepts_json_kif_text(self):
        response = import_game_payload(
            self.api,
            "application/json",
            json.dumps({"kif": KIF_TEXT}).encode("utf-8"),
        )

        self.assertEqual(response["game"]["black"], "解析太郎")
        self.assertEqual(response["positions_count"], 3)

    def test_accepts_cp932_kif_even_when_content_type_is_json(self):
        response = import_game_payload(
            self.api,
            "application/json",
            KIF_TEXT.encode("cp932"),
        )

        self.assertEqual(response["game"]["black"], "解析太郎")
        self.assertEqual(response["positions_count"], 3)

    def test_import_directory_payload(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "game.kif").write_bytes(KIF_TEXT.encode("cp932"))

            response = import_directory_payload(
                self.api,
                {"path": str(directory), "recursive": False},
            )

        self.assertEqual(response["total"], 1)
        self.assertEqual(response["imported"], 1)

    def test_import_directory_payload_requires_path(self):
        with self.assertRaisesRegex(Exception, "path"):
            import_directory_payload(
                self.api,
                {"recursive": False},
            )

    def test_start_import_directory_payload_tracks_progress(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "game.kif").write_bytes(KIF_TEXT.encode("cp932"))
            job_store = DirectoryImportJobStore(self.api)

            job = start_import_directory_payload(
                job_store,
                {"path": str(directory), "recursive": False},
            )
            for _ in range(100):
                job = job_store.get(job["id"])
                if job["done"]:
                    break
                sleep(0.01)

        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["processed"], 1)
        self.assertEqual(job["total"], 1)
        self.assertEqual(job["imported"], 1)

    def test_import_directory_job_can_be_canceled(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "game.kif").write_bytes(KIF_TEXT.encode("cp932"))
            job_store = DirectoryImportJobStore(self.api)

            job = job_store.start(str(directory), recursive=False)
            canceled = job_store.cancel(job["id"])

        self.assertIn(canceled["status"], ("canceling", "completed"))

    def test_import_post_path_accepts_directory_cancel_endpoint(self):
        self.assertTrue(is_import_post_path("/api/games/import"))
        self.assertTrue(is_import_post_path("/api/games/import-directory"))
        self.assertTrue(is_import_post_path("/api/openings/rebuild"))
        self.assertTrue(is_import_post_path("/api/positions/123/analyze"))
        self.assertTrue(is_import_post_path("/api/positions/123/explain"))
        self.assertTrue(
            is_import_post_path("/api/games/import-directory/jobs/job-id/cancel")
        )
        self.assertFalse(is_import_post_path("/api/games/import-directory/jobs/job-id"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
