import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.api_server import create_server


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

        positions_response = self._get_json("/api/games/1/positions")
        self.assertEqual(len(positions_response["positions"]), 3)
        self.assertEqual(positions_response["positions"][1]["move"], "7g7f")

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

    def _get_json(self, path: str) -> dict:
        with urlopen(f"{self.base_url}{path}", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
