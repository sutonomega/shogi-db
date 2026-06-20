import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestFrontendFiles(unittest.TestCase):
    def test_index_references_assets(self):
        content = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="gameRows"', content)
        self.assertIn('id="searchInput"', content)
        self.assertIn('id="importForm"', content)
        self.assertIn('id="kifFileInput"', content)
        self.assertIn('id="directoryImportForm"', content)
        self.assertIn('id="directoryPathInput"', content)
        self.assertIn('id="recursiveImportInput"', content)
        self.assertIn('accept=".kif,text/plain,application/octet-stream"', content)
        self.assertIn('id="strategyStatsPanel"', content)
        self.assertIn('id="strategyStatsList"', content)
        self.assertIn('id="enclosureStatsPanel"', content)
        self.assertIn('id="enclosureStatsList"', content)
        self.assertIn('id="blunderPanel"', content)
        self.assertIn('id="blunderList"', content)
        self.assertIn('id="viewerView"', content)
        self.assertIn('id="boardGrid"', content)
        self.assertIn('id="evalGraph"', content)
        self.assertIn('id="moveSlider"', content)
        self.assertIn('id="positionEval"', content)
        self.assertIn('id="blackHand"', content)
        self.assertIn('id="whiteHand"', content)
        self.assertIn('/assets/styles.css', content)
        self.assertIn('/assets/app.js', content)

    def test_app_fetches_games_endpoint(self):
        content = (ROOT / "frontend" / "assets" / "app.js").read_text(encoding="utf-8")

        self.assertIn('fetch("/api/games")', content)
        self.assertIn('fetch("/api/stats/strategies")', content)
        self.assertIn('fetch("/api/stats/enclosures")', content)
        self.assertIn('fetch("/api/stats/blunders")', content)
        self.assertIn('fetch("/api/games/import"', content)
        self.assertIn('fetch("/api/games/import-directory"', content)
        self.assertIn('"Content-Type": "application/octet-stream"', content)
        self.assertIn("importKifFile", content)
        self.assertIn("importKifDirectory", content)
        self.assertIn("kifFileInput.addEventListener", content)
        self.assertIn("directoryImportForm.addEventListener", content)
        self.assertIn("renderStrategyStats", content)
        self.assertIn("renderEnclosureStats", content)
        self.assertIn("renderBlunders", content)
        self.assertIn("renderStatsList", content)
        self.assertIn("formatPercent", content)
        self.assertIn("parseSfen", content)
        self.assertIn("renderBoard", content)
        self.assertIn("renderEvalGraph", content)
        self.assertIn("formatEvalWithDelta", content)
        self.assertIn("mateEvalValue = 100000", content)
        self.assertIn("evalGraphMinScale = 3000", content)
        self.assertIn("isMateEval", content)
        self.assertIn("buildEvalScale", content)
        self.assertIn("drawMissingEvalLines", content)
        self.assertIn('"+詰み"', content)
        self.assertIn('circle.addEventListener("click", () => setCurrentMove(point.index))', content)
        self.assertIn('moveSlider.addEventListener("input"', content)
        self.assertIn('fetch(`/api/games/${gameId}/positions`)', content)
        self.assertIn('window.location.href = `/games/${game.id}`', content)
        self.assertIn("保存済み対局はありません", content)

    def test_styles_define_table_layout(self):
        content = (ROOT / "frontend" / "assets" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".game-table", content)
        self.assertIn(".import-form", content)
        self.assertIn(".directory-import-form", content)
        self.assertIn(".checkbox-field", content)
        self.assertIn(".file-picker", content)
        self.assertIn(".stats-panel", content)
        self.assertIn(".stats-item", content)
        self.assertIn("table-layout: fixed", content)
        self.assertIn(".board-grid", content)
        self.assertIn(".eval-graph", content)
        self.assertIn(".eval-line", content)
        self.assertIn(".eval-missing-line", content)
        self.assertIn(".eval-point.current", content)
        self.assertIn(".eval-point:hover", content)
        self.assertIn(".move-slider", content)
        self.assertIn("aspect-ratio: 1", content)
        self.assertIn("@media (max-width: 640px)", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
