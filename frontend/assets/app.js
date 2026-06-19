const state = {
  games: [],
  positions: [],
  game: null,
  query: "",
  currentMove: 0,
};

const pieceLabels = {
  P: "歩",
  L: "香",
  N: "桂",
  S: "銀",
  G: "金",
  B: "角",
  R: "飛",
  K: "玉",
};

const promotedLabels = {
  P: "と",
  L: "杏",
  N: "圭",
  S: "全",
  B: "馬",
  R: "龍",
};

const rowsElement = document.querySelector("#gameRows");
const statusPanel = document.querySelector("#statusPanel");
const summaryText = document.querySelector("#summaryText");
const searchInput = document.querySelector("#searchInput");
const refreshButton = document.querySelector("#refreshButton");
const backButton = document.querySelector("#backButton");
const pageSubtitle = document.querySelector("#pageSubtitle");
const listToolbar = document.querySelector("#listToolbar");
const gameListView = document.querySelector("#gameListView");
const viewerView = document.querySelector("#viewerView");
const boardGrid = document.querySelector("#boardGrid");
const blackHand = document.querySelector("#blackHand");
const whiteHand = document.querySelector("#whiteHand");
const moveCounter = document.querySelector("#moveCounter");
const firstMoveButton = document.querySelector("#firstMoveButton");
const prevMoveButton = document.querySelector("#prevMoveButton");
const nextMoveButton = document.querySelector("#nextMoveButton");
const lastMoveButton = document.querySelector("#lastMoveButton");
const viewerTitle = document.querySelector("#viewerTitle");
const positionMoveNumber = document.querySelector("#positionMoveNumber");
const positionMove = document.querySelector("#positionMove");
const positionEval = document.querySelector("#positionEval");
const positionSfen = document.querySelector("#positionSfen");
const evalGraph = document.querySelector("#evalGraph");
const evalSummary = document.querySelector("#evalSummary");
const evalGraphStatus = document.querySelector("#evalGraphStatus");
const svgNamespace = "http://www.w3.org/2000/svg";

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

function gameIdFromPath() {
  const match = window.location.pathname.match(/^\/games\/(\d+)$/);
  return match ? Number(match[1]) : null;
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

function showListView() {
  pageSubtitle.textContent = "対局一覧";
  listToolbar.hidden = false;
  gameListView.hidden = false;
  viewerView.hidden = true;
  backButton.hidden = true;
  refreshButton.hidden = false;
}

function showViewerView() {
  pageSubtitle.textContent = "棋譜ビューア";
  listToolbar.hidden = true;
  gameListView.hidden = true;
  viewerView.hidden = false;
  backButton.hidden = false;
  refreshButton.hidden = true;
}

function renderList() {
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

function parseSfen(sfen) {
  const [boardPart, turn, handsPart] = sfen.split(" ");
  const squares = [];
  for (const row of boardPart.split("/")) {
    const parsedRow = [];
    for (let index = 0; index < row.length; index += 1) {
      const char = row[index];
      if (/\d/.test(char)) {
        for (let count = 0; count < Number(char); count += 1) {
          parsedRow.push(null);
        }
        continue;
      }
      if (char === "+") {
        index += 1;
        parsedRow.push(`+${row[index]}`);
        continue;
      }
      parsedRow.push(char);
    }
    squares.push(parsedRow);
  }
  return {
    squares,
    turn,
    hands: parseHands(handsPart),
  };
}

function parseHands(handsPart) {
  const hands = { black: [], white: [] };
  if (!handsPart || handsPart === "-") return hands;

  let countText = "";
  for (const char of handsPart) {
    if (/\d/.test(char)) {
      countText += char;
      continue;
    }
    const count = countText ? Number(countText) : 1;
    countText = "";
    const owner = char === char.toUpperCase() ? "black" : "white";
    hands[owner].push({
      piece: pieceLabels[char.toUpperCase()] || char,
      count,
    });
  }
  return hands;
}

function renderBoard() {
  const position = state.positions[state.currentMove];
  if (!position) return;

  const parsed = parseSfen(position.sfen);
  boardGrid.textContent = "";

  for (const row of parsed.squares) {
    for (const piece of row) {
      const square = document.createElement("div");
      square.className = "square";
      if (piece) {
        const span = document.createElement("span");
        const basePiece = piece.replace("+", "");
        span.className = `piece ${basePiece === basePiece.toLowerCase() ? "white" : "black"}`;
        span.textContent = pieceLabel(piece);
        square.appendChild(span);
      }
      boardGrid.appendChild(square);
    }
  }

  blackHand.textContent = formatHand(parsed.hands.black);
  whiteHand.textContent = formatHand(parsed.hands.white);
  moveCounter.textContent = `${state.currentMove} / ${Math.max(state.positions.length - 1, 0)}`;
  viewerTitle.textContent = state.game ? `${state.game.black} vs ${state.game.white}` : "対局";
  positionMoveNumber.textContent = `${position.move_number}手目`;
  positionMove.textContent = position.move || "開始局面";
  positionEval.textContent = formatEvalWithDelta(state.currentMove);
  positionSfen.textContent = position.sfen;
  renderEvalGraph();

  firstMoveButton.disabled = state.currentMove === 0;
  prevMoveButton.disabled = state.currentMove === 0;
  nextMoveButton.disabled = state.currentMove >= state.positions.length - 1;
  lastMoveButton.disabled = state.currentMove >= state.positions.length - 1;
}

function pieceLabel(piece) {
  if (piece.startsWith("+")) {
    return promotedLabels[piece[1].toUpperCase()] || piece;
  }
  return pieceLabels[piece.toUpperCase()] || piece;
}

function formatHand(pieces) {
  if (!pieces.length) return "なし";
  return pieces.map((item) => `${item.piece}${item.count > 1 ? item.count : ""}`).join(" ");
}

function numericEval(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatEval(value) {
  const evalValue = numericEval(value);
  if (evalValue === null) return "なし";
  return evalValue > 0 ? `+${evalValue}` : `${evalValue}`;
}

function formatEvalWithDelta(index) {
  const current = numericEval(state.positions[index]?.eval);
  if (current === null) return "なし";

  let previous = null;
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    previous = numericEval(state.positions[cursor]?.eval);
    if (previous !== null) break;
  }
  if (previous === null) return formatEval(current);

  const delta = current - previous;
  return `${formatEval(current)} (${delta >= 0 ? "+" : ""}${delta})`;
}

function clippedEval(value) {
  return Math.max(-1000, Math.min(1000, value));
}

function renderEvalGraph() {
  evalGraph.textContent = "";
  const points = state.positions.map((position, index) => ({
    index,
    moveNumber: position.move_number ?? index,
    eval: numericEval(position.eval),
  }));
  const visiblePoints = points.filter((point) => point.eval !== null);

  if (!visiblePoints.length) {
    evalGraph.hidden = true;
    evalGraphStatus.hidden = false;
    evalSummary.textContent = "評価値なし";
    return;
  }

  evalGraph.hidden = false;
  evalGraphStatus.hidden = true;
  const currentEval = numericEval(state.positions[state.currentMove]?.eval);
  evalSummary.textContent = currentEval === null ? "現在値なし" : formatEval(currentEval);

  const width = 640;
  const height = 220;
  const padding = { top: 18, right: 22, bottom: 30, left: 44 };
  const graphWidth = width - padding.left - padding.right;
  const graphHeight = height - padding.top - padding.bottom;
  const maxIndex = Math.max(points.length - 1, 1);
  const xFor = (index) => padding.left + (index / maxIndex) * graphWidth;
  const yFor = (evalValue) => padding.top + ((1000 - clippedEval(evalValue)) / 2000) * graphHeight;

  drawGraphLine(padding.left, yFor(1000), width - padding.right, yFor(1000), "eval-grid");
  drawGraphLine(padding.left, yFor(0), width - padding.right, yFor(0), "eval-zero");
  drawGraphLine(padding.left, yFor(-1000), width - padding.right, yFor(-1000), "eval-grid");
  drawGraphLine(xFor(state.currentMove), padding.top, xFor(state.currentMove), height - padding.bottom, "eval-current");

  for (const label of [
    { text: "+1000", y: yFor(1000) },
    { text: "0", y: yFor(0) },
    { text: "-1000", y: yFor(-1000) },
  ]) {
    const text = svgElement("text", {
      x: 8,
      y: label.y + 4,
      class: "eval-axis-label",
    });
    text.textContent = label.text;
    evalGraph.appendChild(text);
  }

  const lastMoveNumber = points[points.length - 1]?.moveNumber ?? maxIndex;
  for (const label of [
    { text: "0手", x: padding.left, anchor: "start" },
    { text: `${lastMoveNumber}手`, x: width - padding.right, anchor: "end" },
  ]) {
    const text = svgElement("text", {
      x: label.x.toFixed(1),
      y: height - 8,
      class: "eval-axis-label",
      "text-anchor": label.anchor,
    });
    text.textContent = label.text;
    evalGraph.appendChild(text);
  }

  let pathData = "";
  for (const point of points) {
    if (point.eval === null) {
      appendEvalPath(pathData);
      pathData = "";
      continue;
    }
    const command = pathData ? "L" : "M";
    pathData += `${command} ${xFor(point.index).toFixed(1)} ${yFor(point.eval).toFixed(1)} `;
  }
  appendEvalPath(pathData);

  for (const point of visiblePoints) {
    const circle = svgElement("circle", {
      cx: xFor(point.index).toFixed(1),
      cy: yFor(point.eval).toFixed(1),
      r: point.index === state.currentMove ? 4.8 : 3.2,
      class: point.index === state.currentMove ? "eval-point current" : "eval-point",
    });
    const title = svgElement("title");
    title.textContent = `${point.moveNumber}手目 ${formatEval(point.eval)}`;
    circle.appendChild(title);
    evalGraph.appendChild(circle);
  }
}

function appendEvalPath(pathData) {
  if (!pathData.trim()) return;
  evalGraph.appendChild(svgElement("path", {
    d: pathData.trim(),
    class: "eval-line",
  }));
}

function drawGraphLine(x1, y1, x2, y2, className) {
  evalGraph.appendChild(svgElement("line", {
    x1: x1.toFixed(1),
    y1: y1.toFixed(1),
    x2: x2.toFixed(1),
    y2: y2.toFixed(1),
    class: className,
  }));
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNamespace, name);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, value);
  }
  return element;
}

function setCurrentMove(moveNumber) {
  const max = Math.max(state.positions.length - 1, 0);
  state.currentMove = Math.max(0, Math.min(moveNumber, max));
  renderBoard();
}

async function loadGames() {
  showListView();
  setStatus("読み込み中");
  try {
    const response = await fetch("/api/games");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.games = Array.isArray(payload.games) ? payload.games : [];
    setStatus("");
    renderList();
  } catch (error) {
    state.games = [];
    setStatus(`対局一覧を取得できませんでした: ${error.message}`, "error");
    renderList();
  }
}

async function loadViewer(gameId) {
  showViewerView();
  setStatus("読み込み中");
  try {
    const response = await fetch(`/api/games/${gameId}/positions`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.game = payload.game;
    state.positions = Array.isArray(payload.positions) ? payload.positions : [];
    state.currentMove = 0;
    setStatus("");
    renderBoard();
  } catch (error) {
    state.game = null;
    state.positions = [];
    setStatus(`局面データを取得できませんでした: ${error.message}`, "error");
    renderBoard();
  }
}

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});

refreshButton.addEventListener("click", () => {
  loadGames();
});

backButton.addEventListener("click", () => {
  window.location.href = "/";
});

firstMoveButton.addEventListener("click", () => setCurrentMove(0));
prevMoveButton.addEventListener("click", () => setCurrentMove(state.currentMove - 1));
nextMoveButton.addEventListener("click", () => setCurrentMove(state.currentMove + 1));
lastMoveButton.addEventListener("click", () => setCurrentMove(state.positions.length - 1));

const gameId = gameIdFromPath();
if (gameId) {
  loadViewer(gameId);
} else {
  loadGames();
}
