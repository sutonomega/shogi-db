const state = {
  games: [],
  query: "",
};

const rowsElement = document.querySelector("#gameRows");
const statusPanel = document.querySelector("#statusPanel");
const summaryText = document.querySelector("#summaryText");
const searchInput = document.querySelector("#searchInput");
const refreshButton = document.querySelector("#refreshButton");

function formatDate(value) {
  if (!value) return "未設定";
  return value;
}

function formatWinner(value) {
  if (value === "black") return "先手勝ち";
  if (value === "white") return "後手勝ち";
  if (value === "draw") return "引き分け";
  return "不明";
}

function normalize(value) {
  return String(value || "").toLowerCase();
}

function visibleGames() {
  const query = normalize(state.query);
  if (!query) return state.games;
  return state.games.filter((game) => {
    const target = [
      game.played_at,
      game.black,
      game.white,
      formatWinner(game.winner),
      game.move_count,
    ].join(" ");
    return normalize(target).includes(query);
  });
}

function setStatus(message, kind = "info") {
  if (!message) {
    statusPanel.hidden = true;
    statusPanel.textContent = "";
    statusPanel.className = "status-panel";
    return;
  }
  statusPanel.hidden = false;
  statusPanel.textContent = message;
  statusPanel.className = `status-panel ${kind}`;
}

function render() {
  const games = visibleGames();
  summaryText.textContent = `${games.length}局`;
  rowsElement.textContent = "";

  if (!games.length) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = state.games.length ? "条件に一致する対局はありません" : "保存済み対局はありません";
    row.appendChild(cell);
    rowsElement.appendChild(row);
    return;
  }

  for (const game of games) {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.addEventListener("click", () => {
      window.location.href = `/games/${game.id}`;
    });
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        window.location.href = `/games/${game.id}`;
      }
    });

    row.appendChild(tableCell(formatDate(game.played_at)));
    row.appendChild(tableCell(game.black));
    row.appendChild(tableCell(game.white));

    const winnerCell = document.createElement("td");
    const winner = document.createElement("span");
    winner.className = "winner";
    winner.textContent = formatWinner(game.winner);
    winnerCell.appendChild(winner);
    row.appendChild(winnerCell);

    row.appendChild(tableCell(`${game.move_count ?? 0}手`));
    rowsElement.appendChild(row);
  }
}

function tableCell(text) {
  const cell = document.createElement("td");
  cell.textContent = text;
  return cell;
}

async function loadGames() {
  setStatus("読み込み中");
  try {
    const response = await fetch("/api/games");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.games = Array.isArray(payload.games) ? payload.games : [];
    setStatus("");
    render();
  } catch (error) {
    state.games = [];
    setStatus(`対局一覧を取得できませんでした: ${error.message}`, "error");
    render();
  }
}

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  render();
});

refreshButton.addEventListener("click", () => {
  loadGames();
});

loadGames();
