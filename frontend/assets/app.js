const state = {
  games: [],
  strategyStats: [],
  enclosureStats: [],
  blunders: [],
  blunderExplanations: {},
  positions: [],
  moveFrequencies: [],
  moveFrequencyTotal: 0,
  moveFrequencyRequestId: 0,
  openings: [],
  openingTotal: 0,
  openingRequestId: 0,
  openingComparisonPrompt: "",
  openingComparisonText: "",
  openingComparisonMissing: [],
  openingComparisonStatus: "未作成",
  openingComparisonRequestId: 0,
  explanationPrompt: "",
  explanationText: "",
  explanationMissing: [],
  explanationStatus: "未作成",
  explanationRequestId: 0,
  game: null,
  query: "",
  currentMove: 0,
  selectedCandidateMove: null,
  candidateAnalysisStatus: "idle",
  candidateStatusText: "候補手は水匠解析付きKIFまたは局面解析後に表示されます",
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

const japaneseFiles = {
  1: "１",
  2: "２",
  3: "３",
  4: "４",
  5: "５",
  6: "６",
  7: "７",
  8: "８",
  9: "９",
};

const japaneseRanks = {
  a: "一",
  b: "二",
  c: "三",
  d: "四",
  e: "五",
  f: "六",
  g: "七",
  h: "八",
  i: "九",
};

const rowsElement = document.querySelector("#gameRows");
const statusPanel = document.querySelector("#statusPanel");
const gameRegistrationPanel = document.querySelector("#gameRegistrationPanel");
const openingRebuildSummary = document.querySelector("#openingRebuildSummary");
const openingRebuildButton = document.querySelector("#openingRebuildButton");
const cancelOpeningRebuildButton = document.querySelector("#cancelOpeningRebuildButton");
const openingManagementPanel = document.querySelector("#openingManagementPanel");
const openingManagementSummary = document.querySelector("#openingManagementSummary");
const openingImportForm = document.querySelector("#openingImportForm");
const openingFileInput = document.querySelector("#openingFileInput");
const openingFileName = document.querySelector("#openingFileName");
const openingImportButton = document.querySelector("#openingImportButton");
const openingDirectoryImportForm = document.querySelector("#openingDirectoryImportForm");
const openingDirectoryPathInput = document.querySelector("#openingDirectoryPathInput");
const openingRecursiveImportInput = document.querySelector("#openingRecursiveImportInput");
const openingDirectoryImportButton = document.querySelector("#openingDirectoryImportButton");
const openingCancelDirectoryImportButton = document.querySelector("#openingCancelDirectoryImportButton");
const strategyStatsPanel = document.querySelector("#strategyStatsPanel");
const strategyStatsList = document.querySelector("#strategyStatsList");
const strategyStatsSummary = document.querySelector("#strategyStatsSummary");
const enclosureStatsPanel = document.querySelector("#enclosureStatsPanel");
const enclosureStatsList = document.querySelector("#enclosureStatsList");
const enclosureStatsSummary = document.querySelector("#enclosureStatsSummary");
const blunderPanel = document.querySelector("#blunderPanel");
const blunderList = document.querySelector("#blunderList");
const blunderSummary = document.querySelector("#blunderSummary");
const summaryText = document.querySelector("#summaryText");
const searchInput = document.querySelector("#searchInput");
const importForm = document.querySelector("#importForm");
const kifFileInput = document.querySelector("#kifFileInput");
const importFileName = document.querySelector("#importFileName");
const importButton = document.querySelector("#importButton");
const directoryImportForm = document.querySelector("#directoryImportForm");
const directoryPathInput = document.querySelector("#directoryPathInput");
const recursiveImportInput = document.querySelector("#recursiveImportInput");
const directoryImportButton = document.querySelector("#directoryImportButton");
const cancelDirectoryImportButton = document.querySelector("#cancelDirectoryImportButton");
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
const moveSlider = document.querySelector("#moveSlider");
const viewerTitle = document.querySelector("#viewerTitle");
const positionMoveNumber = document.querySelector("#positionMoveNumber");
const positionMove = document.querySelector("#positionMove");
const positionEval = document.querySelector("#positionEval");
const positionSfen = document.querySelector("#positionSfen");
const candidateList = document.querySelector("#candidateList");
const candidateSummary = document.querySelector("#candidateSummary");
const candidateStatus = document.querySelector("#candidateStatus");
const analyzeCandidateButton = document.querySelector("#analyzeCandidateButton");
const evalGraph = document.querySelector("#evalGraph");
const evalSummary = document.querySelector("#evalSummary");
const evalGraphStatus = document.querySelector("#evalGraphStatus");
const moveFrequencyList = document.querySelector("#moveFrequencyList");
const moveFrequencySummary = document.querySelector("#moveFrequencySummary");
const openingList = document.querySelector("#openingList");
const openingSummary = document.querySelector("#openingSummary");
const openingComparisonSummary = document.querySelector("#openingComparisonSummary");
const openingComparisonMissing = document.querySelector("#openingComparisonMissing");
const openingComparisonPrompt = document.querySelector("#openingComparisonPrompt");
const openingComparisonOutput = document.querySelector("#openingComparisonOutput");
const buildOpeningComparisonButton = document.querySelector("#buildOpeningComparisonButton");
const generateOpeningComparisonButton = document.querySelector("#generateOpeningComparisonButton");
const explanationSummary = document.querySelector("#explanationSummary");
const explanationMissing = document.querySelector("#explanationMissing");
const explanationPrompt = document.querySelector("#explanationPrompt");
const explanationOutput = document.querySelector("#explanationOutput");
const buildExplanationPromptButton = document.querySelector("#buildExplanationPromptButton");
const generateExplanationButton = document.querySelector("#generateExplanationButton");
const svgNamespace = "http://www.w3.org/2000/svg";
const mateEvalValue = 100000;
const evalGraphMinScale = 3000;
const evalGraphMaxScale = 3000;
const evalGraphScaleStep = 500;

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
  gameRegistrationPanel.hidden = false;
  openingManagementPanel.hidden = false;
  strategyStatsPanel.hidden = false;
  enclosureStatsPanel.hidden = false;
  blunderPanel.hidden = false;
  gameListView.hidden = false;
  viewerView.hidden = true;
  backButton.hidden = true;
  refreshButton.hidden = false;
}

function showViewerView() {
  pageSubtitle.textContent = "棋譜ビューア";
  listToolbar.hidden = true;
  gameRegistrationPanel.hidden = true;
  openingManagementPanel.hidden = true;
  strategyStatsPanel.hidden = true;
  enclosureStatsPanel.hidden = true;
  blunderPanel.hidden = true;
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

function updateImportFileName() {
  const file = kifFileInput.files?.[0] || null;
  importFileName.textContent = file ? file.name : "未選択";
  importButton.disabled = !file;
}

function updateOpeningFileName() {
  const file = openingFileInput.files?.[0] || null;
  openingFileName.textContent = file ? file.name : "未選択";
  openingImportButton.disabled = !file;
}

function renderStrategyStats() {
  renderStatsList({
    stats: state.strategyStats,
    listElement: strategyStatsList,
    summaryElement: strategyStatsSummary,
    labelKey: "strategy",
    emptyText: "戦法データはありません",
  });
}

function renderEnclosureStats() {
  renderStatsList({
    stats: state.enclosureStats,
    listElement: enclosureStatsList,
    summaryElement: enclosureStatsSummary,
    labelKey: "enclosure",
    emptyText: "囲いデータはありません",
  });
}

function renderBlunders() {
  blunderList.textContent = "";
  blunderSummary.textContent = `${state.blunders.length}件`;

  if (!state.blunders.length) {
    const empty = document.createElement("p");
    empty.className = "stats-empty";
    empty.textContent = "評価値急落データはありません";
    blunderList.appendChild(empty);
    return;
  }

  for (const blunder of state.blunders) {
    const key = blunderKey(blunder);
    const explanation = state.blunderExplanations[key] || {};
    const item = document.createElement("article");
    item.className = "stats-item";

    const name = document.createElement("strong");
    name.textContent = `${blunder.move_number}手目 ${moveLabelForCandidate(blunder.move, blunder.previous_sfen)}`;
    item.appendChild(name);

    const details = document.createElement("span");
    details.textContent = `評価値 ${formatEval(blunder.eval_before)} → ${formatEval(blunder.eval_after)}`;
    item.appendChild(details);

    const record = document.createElement("small");
    record.textContent = `${blunder.black} vs ${blunder.white} / ${blunder.eval_delta} / 発生 ${blunder.occurrence_count}回 ${blunder.game_count}局`;
    item.appendChild(record);

    const actions = document.createElement("div");
    actions.className = "stats-item-actions";
    const explainButton = document.createElement("button");
    explainButton.type = "button";
    explainButton.textContent = explanation.status === "生成中" ? "生成中" : "理由生成";
    explainButton.disabled = explanation.status === "生成中";
    explainButton.addEventListener("click", () => generateBlunderExplanation(blunder));
    actions.appendChild(explainButton);
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.textContent = "局面へ";
    viewButton.addEventListener("click", () => openBlunderPosition(blunder));
    actions.appendChild(viewButton);
    item.appendChild(actions);

    if (explanation.status || explanation.text) {
      const explanationBlock = document.createElement("pre");
      explanationBlock.className = "blunder-explanation-output";
      explanationBlock.textContent = explanation.text || explanation.status;
      item.appendChild(explanationBlock);
    }

    blunderList.appendChild(item);
  }
}

function blunderKey(blunder) {
  return `${blunder.game_id}:${blunder.move_number}`;
}

function openBlunderPosition(blunder) {
  window.location.href = `/games/${blunder.game_id}?move=${blunder.move_number}`;
}

function renderMoveFrequencies() {
  moveFrequencyList.textContent = "";
  moveFrequencySummary.textContent = `${state.moveFrequencyTotal}回`;
  const position = state.positions[state.currentMove];

  if (!state.moveFrequencies.length) {
    const empty = document.createElement("p");
    empty.className = "stats-empty";
    empty.textContent = "この局面の実戦手はありません";
    moveFrequencyList.appendChild(empty);
    return;
  }

  for (const frequency of state.moveFrequencies) {
    const item = document.createElement("article");
    item.className = "move-frequency-item";

    const heading = document.createElement("div");
    heading.className = "move-frequency-heading";

    const move = document.createElement("strong");
    move.textContent = moveLabelForCandidate(frequency.move, position?.sfen);
    heading.appendChild(move);

    const count = document.createElement("span");
    count.textContent = `${frequency.count}回`;
    heading.appendChild(count);
    item.appendChild(heading);

    const bar = document.createElement("div");
    bar.className = "move-frequency-bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.round((frequency.ratio || 0) * 100)}%`;
    bar.appendChild(fill);
    item.appendChild(bar);

    const details = document.createElement("small");
    details.textContent = `割合 ${formatPercent(frequency.ratio)} / 平均評価値 ${formatEval(frequency.avg_eval)}`;
    item.appendChild(details);

    moveFrequencyList.appendChild(item);
  }
}

function renderOpenings() {
  openingList.textContent = "";
  openingSummary.textContent = `${state.openingTotal}回`;
  const position = state.positions[state.currentMove];

  if (!state.openings.length) {
    const empty = document.createElement("p");
    empty.className = "stats-empty";
    empty.textContent = "この局面の登録済み定跡はありません";
    openingList.appendChild(empty);
    return;
  }

  for (const opening of state.openings) {
    const item = document.createElement("article");
    item.className = "opening-item";

    const heading = document.createElement("div");
    heading.className = "opening-heading";

    const move = document.createElement("strong");
    move.textContent = moveLabelForCandidate(opening.move, position?.sfen);
    heading.appendChild(move);

    const count = document.createElement("span");
    count.textContent = `${opening.count}回`;
    heading.appendChild(count);
    item.appendChild(heading);

    const bar = document.createElement("div");
    bar.className = "opening-bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.round((opening.ratio || 0) * 100)}%`;
    bar.appendChild(fill);
    item.appendChild(bar);

    const details = document.createElement("small");
    details.textContent = `割合 ${formatPercent(opening.ratio)} / 平均評価値 ${formatEval(opening.avg_eval)}`;
    item.appendChild(details);

    openingList.appendChild(item);
  }
}

function renderOpeningComparison() {
  openingComparisonSummary.textContent = state.openingComparisonStatus;
  openingComparisonMissing.textContent = state.openingComparisonMissing.length
    ? `不足: ${state.openingComparisonMissing.join("、")}`
    : "不足項目はありません";
  openingComparisonPrompt.textContent = state.openingComparisonPrompt || "現在局面の定跡比較を作成できます";
  openingComparisonOutput.textContent = state.openingComparisonText || "比較解説はまだありません";
  buildOpeningComparisonButton.disabled = state.openingComparisonStatus === "作成中" || state.openingComparisonStatus === "生成中";
  generateOpeningComparisonButton.disabled = state.openingComparisonStatus === "生成中";
}

function resetOpeningComparison() {
  state.openingComparisonRequestId += 1;
  state.openingComparisonPrompt = "";
  state.openingComparisonText = "";
  state.openingComparisonMissing = [];
  state.openingComparisonStatus = "未作成";
  renderOpeningComparison();
}

function renderExplanationPrompt() {
  explanationSummary.textContent = state.explanationStatus;
  explanationMissing.textContent = state.explanationMissing.length
    ? `不足: ${state.explanationMissing.join("、")}`
    : "不足: なし";
  explanationPrompt.textContent = state.explanationPrompt || "現在局面のプロンプトを作成できます";
  explanationOutput.textContent = state.explanationText || "生成結果はまだありません";
  buildExplanationPromptButton.disabled = !state.positions[state.currentMove];
  generateExplanationButton.disabled = !state.positions[state.currentMove];
}

function resetExplanationPrompt() {
  state.explanationPrompt = "";
  state.explanationText = "";
  state.explanationMissing = [];
  state.explanationStatus = "未作成";
  state.explanationRequestId += 1;
  renderExplanationPrompt();
}

function renderStatsList({ stats, listElement, summaryElement, labelKey, emptyText }) {
  listElement.textContent = "";
  summaryElement.textContent = `${stats.length}件`;

  if (!stats.length) {
    const empty = document.createElement("p");
    empty.className = "stats-empty";
    empty.textContent = emptyText;
    listElement.appendChild(empty);
    return;
  }

  for (const itemStats of stats) {
    const item = document.createElement("article");
    item.className = "stats-item";

    const name = document.createElement("strong");
    name.textContent = itemStats[labelKey];
    item.appendChild(name);

    const details = document.createElement("span");
    details.textContent = `${itemStats.games}局 / 勝率 ${formatPercent(itemStats.win_rate)}`;
    item.appendChild(details);

    const record = document.createElement("small");
    record.textContent = `${itemStats.wins}勝 ${itemStats.losses}敗 ${itemStats.draws}分`;
    item.appendChild(record);

    listElement.appendChild(item);
  }
}

function formatPercent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${Math.round(value * 100)}%`;
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
  if (!position) {
    boardGrid.textContent = "";
    blackHand.textContent = "なし";
    whiteHand.textContent = "なし";
    moveCounter.textContent = "0 / 0";
    viewerTitle.textContent = "対局";
    positionMoveNumber.textContent = "0手目";
    positionMove.textContent = "開始局面";
    positionEval.textContent = "なし";
    positionSfen.textContent = "";
    renderEngineCandidates(null);
    updateMoveControls();
    renderEvalGraph();
    return;
  }

  const parsed = parseSfen(position.sfen);
  const moveInfo = selectedCandidateMoveInfo(position) || currentMoveInfo();
  boardGrid.textContent = "";

  for (let rowIndex = 0; rowIndex < parsed.squares.length; rowIndex += 1) {
    for (let columnIndex = 0; columnIndex < parsed.squares[rowIndex].length; columnIndex += 1) {
      const piece = parsed.squares[rowIndex][columnIndex];
      const square = document.createElement("div");
      const classes = ["square"];
      if (isMoveSquare(moveInfo?.from, rowIndex, columnIndex)) classes.push("move-from");
      if (isMoveSquare(moveInfo?.to, rowIndex, columnIndex)) classes.push("move-to");
      square.className = classes.join(" ");
      square.dataset.file = String(9 - columnIndex);
      square.dataset.rank = String.fromCharCode("a".charCodeAt(0) + rowIndex);
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
  positionMove.textContent = moveInfo?.label || "開始局面";
  positionEval.textContent = formatEvalWithDelta(state.currentMove);
  positionSfen.textContent = position.sfen;
  renderEngineCandidates(position);
  renderEvalGraph();
  renderExplanationPrompt();
  updateMoveControls();
}

function renderEngineCandidates(position) {
  candidateList.textContent = "";
  state.selectedCandidateMove = position?.candidates?.some((candidate) => candidate.move === state.selectedCandidateMove)
    ? state.selectedCandidateMove
    : null;
  const candidates = Array.isArray(position?.candidates) ? position.candidates.slice(0, 5) : [];
  candidateSummary.textContent = `${candidates.length}件`;
  candidateStatus.textContent = state.candidateStatusText;
  analyzeCandidateButton.disabled = !position?.id || state.candidateAnalysisStatus === "running";
  analyzeCandidateButton.textContent = state.candidateAnalysisStatus === "running" ? "解析中" : "この局面を解析";

  if (!candidates.length) {
    const empty = document.createElement("p");
    empty.className = "candidate-empty";
    empty.textContent = "候補手データはありません。水匠解析付きKIFを登録するか、この局面を解析してください。";
    candidateList.appendChild(empty);
    return;
  }

  const actualMove = position?.move || null;
  candidates.forEach((candidate, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = [
      "candidate-item",
      candidate.move === state.selectedCandidateMove ? "selected" : "",
      candidate.move === actualMove ? "actual" : "",
    ].filter(Boolean).join(" ");
    button.addEventListener("click", () => {
      state.selectedCandidateMove = state.selectedCandidateMove === candidate.move ? null : candidate.move;
      renderBoard();
    });

    const rank = document.createElement("span");
    rank.className = "candidate-rank";
    rank.textContent = `${index + 1}.`;
    button.appendChild(rank);

    const move = document.createElement("strong");
    move.textContent = moveLabelForCandidate(candidate.move, position.sfen);
    button.appendChild(move);

    const evalValue = document.createElement("span");
    evalValue.className = "candidate-eval";
    evalValue.textContent = formatEval(candidate.eval);
    button.appendChild(evalValue);

    if (candidate.move === actualMove) {
      const actual = document.createElement("small");
      actual.textContent = "実戦手";
      button.appendChild(actual);
    }

    candidateList.appendChild(button);
  });
}

function updateMoveControls() {
  const max = Math.max(state.positions.length - 1, 0);
  firstMoveButton.disabled = state.currentMove === 0;
  prevMoveButton.disabled = state.currentMove === 0;
  nextMoveButton.disabled = state.currentMove >= max;
  lastMoveButton.disabled = state.currentMove >= max;
  moveSlider.max = `${max}`;
  moveSlider.value = `${state.currentMove}`;
  moveSlider.disabled = max === 0;
}

function pieceLabel(piece) {
  if (piece.startsWith("+")) {
    return promotedLabels[piece[1].toUpperCase()] || piece;
  }
  return pieceLabels[piece.toUpperCase()] || piece;
}

function currentMoveInfo() {
  const position = state.positions[state.currentMove];
  if (!position?.move) return null;
  return moveInfoForPosition(state.currentMove);
}

function selectedCandidateMoveInfo(position) {
  if (!state.selectedCandidateMove || !position?.sfen) return null;
  const move = parseUsiMove(state.selectedCandidateMove);
  if (!move) return null;
  return {
    label: moveLabelForCandidate(state.selectedCandidateMove, position.sfen),
    from: move.from,
    to: move.to,
  };
}

function moveInfoForPosition(index) {
  const position = state.positions[index];
  if (!position?.move) return null;
  const move = parseUsiMove(position.move);
  if (!move) return { label: position.move, from: null, to: null };

  const previousPosition = state.positions[index - 1] || null;
  const previousMove = parseUsiMove(state.positions[index - 1]?.move);
  const previousBoard = previousPosition?.sfen ? parseSfen(previousPosition.sfen).squares : null;
  const sourcePiece = move.dropPiece || pieceAt(previousBoard, move.from);
  const sideMark = (position.move_number ?? index) % 2 === 1 ? "▲" : "△";
  const sameDestination = previousMove && move.to && previousMove.to
    && previousMove.to.file === move.to.file
    && previousMove.to.rank === move.to.rank;
  const destination = sameDestination ? "同" : `${japaneseFiles[move.to.file] || move.to.file}${japaneseRanks[move.to.rank] || move.to.rank}`;
  const pieceName = pieceLabel(sourcePiece || "");
  const suffix = move.dropPiece ? "打" : move.promote ? "成" : "";

  return {
    label: `${sideMark}${destination}${pieceName || position.move}${suffix}`,
    from: move.from,
    to: move.to,
  };
}

function moveLabelForCandidate(moveText, sfen) {
  const move = parseUsiMove(moveText);
  if (!move || !sfen) return moveText || "なし";

  const parsed = parseSfen(sfen);
  const sourcePiece = move.dropPiece || pieceAt(parsed.squares, move.from);
  const sideMark = parsed.turn === "w" ? "△" : "▲";
  const destination = `${japaneseFiles[move.to.file] || move.to.file}${japaneseRanks[move.to.rank] || move.to.rank}`;
  const pieceName = pieceLabel(sourcePiece || "");
  const suffix = move.dropPiece ? "打" : move.promote ? "成" : "";
  return `${sideMark}${destination}${pieceName || moveText}${suffix}`;
}

function parseUsiMove(move) {
  if (typeof move !== "string") return null;
  const drop = move.match(/^([PLNSGBR])\*([1-9])([a-i])$/);
  if (drop) {
    return {
      dropPiece: drop[1],
      from: null,
      to: { file: Number(drop[2]), rank: drop[3] },
      promote: false,
    };
  }

  const normal = move.match(/^([1-9])([a-i])([1-9])([a-i])(\+)?$/);
  if (!normal) return null;
  return {
    dropPiece: null,
    from: { file: Number(normal[1]), rank: normal[2] },
    to: { file: Number(normal[3]), rank: normal[4] },
    promote: Boolean(normal[5]),
  };
}

function pieceAt(squares, square) {
  if (!squares || !square) return null;
  const row = square.rank.charCodeAt(0) - "a".charCodeAt(0);
  const column = 9 - square.file;
  return squares[row]?.[column] || null;
}

function isMoveSquare(square, rowIndex, columnIndex) {
  if (!square) return false;
  return square.file === 9 - columnIndex
    && square.rank === String.fromCharCode("a".charCodeAt(0) + rowIndex);
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
  if (isMateEval(evalValue)) return evalValue > 0 ? "+詰み" : "-詰み";
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
  if (isMateEval(current) || isMateEval(previous)) return formatEval(current);

  const delta = current - previous;
  return `${formatEval(current)} (${delta >= 0 ? "+" : ""}${delta})`;
}

function isMateEval(value) {
  return Math.abs(value) >= mateEvalValue;
}

function clippedEval(value, scale) {
  return Math.max(-scale, Math.min(scale, value));
}

function isClippedEval(value, scale) {
  return !isMateEval(value) && Math.abs(value) > scale;
}

function buildEvalScale(points) {
  const maxAbsEval = points.reduce((max, point) => {
    if (point.eval === null || isMateEval(point.eval)) return max;
    return Math.max(max, Math.abs(point.eval));
  }, 0);
  const scaledMax = Math.ceil(maxAbsEval / evalGraphScaleStep) * evalGraphScaleStep;
  return Math.min(evalGraphMaxScale, Math.max(evalGraphMinScale, scaledMax));
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
  const padding = { top: 18, right: 22, bottom: 30, left: 0 };
  const graphWidth = width - padding.left - padding.right;
  const graphHeight = height - padding.top - padding.bottom;
  const maxIndex = Math.max(points.length - 1, 1);
  const evalScale = buildEvalScale(points);
  const xFor = (index) => padding.left + (index / maxIndex) * graphWidth;
  const yFor = (evalValue) => padding.top + ((evalScale - clippedEval(evalValue, evalScale)) / (evalScale * 2)) * graphHeight;

  drawGraphLine(padding.left, yFor(evalScale), width - padding.right, yFor(evalScale), "eval-grid");
  drawGraphLine(padding.left, yFor(0), width - padding.right, yFor(0), "eval-zero");
  drawGraphLine(padding.left, yFor(-evalScale), width - padding.right, yFor(-evalScale), "eval-grid");
  drawGraphLine(xFor(state.currentMove), padding.top, xFor(state.currentMove), height - padding.bottom, "eval-current");
  drawMissingEvalLines(points, xFor, yFor(0));

  for (const label of [
    { text: `+${evalScale}`, y: yFor(evalScale) },
    { text: "0", y: yFor(0) },
    { text: `-${evalScale}`, y: yFor(-evalScale) },
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
    const clipped = isClippedEval(point.eval, evalScale);
    const circle = svgElement("circle", {
      cx: xFor(point.index).toFixed(1),
      cy: yFor(point.eval).toFixed(1),
      r: point.index === state.currentMove ? 4.8 : 3.2,
      class: point.index === state.currentMove ? "eval-point current" : "eval-point",
      "data-move-index": point.index,
      role: "button",
      tabindex: "0",
    });
    const title = svgElement("title");
    title.textContent = clipped
      ? `${point.moveNumber}手目 ${formatEval(point.eval)} (表示上限外)`
      : `${point.moveNumber}手目 ${formatEval(point.eval)}`;
    circle.appendChild(title);
    circle.addEventListener("click", () => setCurrentMove(point.index));
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        setCurrentMove(point.index);
      }
    });
    evalGraph.appendChild(circle);
  }
}

function drawMissingEvalLines(points, xFor, y) {
  let startIndex = null;
  for (const point of points) {
    if (point.eval === null) {
      if (startIndex === null) startIndex = point.index;
      continue;
    }
    if (startIndex !== null && startIndex < point.index) {
      drawGraphLine(xFor(startIndex), y, xFor(point.index), y, "eval-missing-line");
    }
    startIndex = null;
  }
  const lastPoint = points[points.length - 1];
  if (startIndex !== null && lastPoint && startIndex < lastPoint.index) {
    drawGraphLine(xFor(startIndex), y, xFor(lastPoint.index), y, "eval-missing-line");
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
  state.selectedCandidateMove = null;
  resetOpeningComparison();
  resetExplanationPrompt();
  renderBoard();
  loadMoveFrequencies();
  loadOpenings();
}

function moveNumberFromQuery() {
  const value = new URLSearchParams(window.location.search).get("move");
  if (!value) return 0;
  const moveNumber = Number(value);
  return Number.isInteger(moveNumber) && moveNumber >= 0 ? moveNumber : 0;
}

async function loadGames() {
  showListView();
  setStatus("読み込み中");
  try {
    const gamesResponse = await fetch("/api/games");
    if (!gamesResponse.ok) {
      throw new Error(`HTTP ${gamesResponse.status}`);
    }
    const payload = await gamesResponse.json();
    state.games = Array.isArray(payload.games) ? payload.games : [];
    setStatus("");
    renderList();
    loadStats();
  } catch (error) {
    state.games = [];
    setStatus(`対局一覧を取得できませんでした: ${error.message}`, "error");
    renderList();
  }
}

async function loadStats() {
  try {
    const [strategyStatsResponse, enclosureStatsResponse, blundersResponse] = await Promise.all([
      fetch("/api/stats/strategies"),
      fetch("/api/stats/enclosures"),
      fetch("/api/stats/blunders"),
    ]);
    if (!strategyStatsResponse.ok) {
      throw new Error(`HTTP ${strategyStatsResponse.status}`);
    }
    if (!enclosureStatsResponse.ok) {
      throw new Error(`HTTP ${enclosureStatsResponse.status}`);
    }
    if (!blundersResponse.ok) {
      throw new Error(`HTTP ${blundersResponse.status}`);
    }
    const strategyStatsPayload = await strategyStatsResponse.json();
    const enclosureStatsPayload = await enclosureStatsResponse.json();
    const blundersPayload = await blundersResponse.json();
    state.strategyStats = Array.isArray(strategyStatsPayload.strategies) ? strategyStatsPayload.strategies : [];
    state.enclosureStats = Array.isArray(enclosureStatsPayload.enclosures) ? enclosureStatsPayload.enclosures : [];
    state.blunders = Array.isArray(blundersPayload.blunders) ? blundersPayload.blunders : [];
    state.blunderExplanations = {};
  } catch (error) {
    state.strategyStats = [];
    state.enclosureStats = [];
    state.blunders = [];
    state.blunderExplanations = {};
    setStatus(`統計情報を取得できませんでした: ${error.message}`, "error");
  } finally {
    renderStrategyStats();
    renderEnclosureStats();
    renderBlunders();
  }
}

async function generateBlunderExplanation(blunder) {
  const key = blunderKey(blunder);
  state.blunderExplanations = {
    ...state.blunderExplanations,
    [key]: { status: "生成中", text: "" },
  };
  renderBlunders();

  try {
    const response = await fetch("/api/blunders/explain", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        game_id: blunder.game_id,
        move_number: blunder.move_number,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    state.blunderExplanations = {
      ...state.blunderExplanations,
      [key]: {
        status: "生成済み",
        text: typeof payload.explanation === "string" ? payload.explanation : "",
      },
    };
  } catch (error) {
    state.blunderExplanations = {
      ...state.blunderExplanations,
      [key]: { status: "失敗", text: "" },
    };
    setStatus(`悪手理由解説を生成できませんでした: ${error.message}`, "error");
  } finally {
    renderBlunders();
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
    state.currentMove = Math.min(moveNumberFromQuery(), Math.max(state.positions.length - 1, 0));
    state.moveFrequencies = [];
    state.moveFrequencyTotal = 0;
    state.openings = [];
    state.openingTotal = 0;
    resetOpeningComparison();
    resetExplanationPrompt();
    setStatus("");
    renderBoard();
    loadMoveFrequencies();
    loadOpenings();
  } catch (error) {
    state.game = null;
    state.positions = [];
    state.moveFrequencies = [];
    state.moveFrequencyTotal = 0;
    state.openings = [];
    state.openingTotal = 0;
    resetOpeningComparison();
    resetExplanationPrompt();
    setStatus(`局面データを取得できませんでした: ${error.message}`, "error");
    renderBoard();
    renderMoveFrequencies();
    renderOpenings();
  }
}

async function loadMoveFrequencies() {
  const position = state.positions[state.currentMove];
  const requestId = state.moveFrequencyRequestId + 1;
  state.moveFrequencyRequestId = requestId;

  if (!position?.sfen) {
    state.moveFrequencies = [];
    state.moveFrequencyTotal = 0;
    renderMoveFrequencies();
    return;
  }

  try {
    const response = await fetch(`/api/positions?sfen=${encodeURIComponent(position.sfen)}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (requestId !== state.moveFrequencyRequestId) return;
    state.moveFrequencies = Array.isArray(payload.moves) ? payload.moves : [];
    state.moveFrequencyTotal = Number.isFinite(payload.total) ? payload.total : 0;
  } catch (error) {
    if (requestId !== state.moveFrequencyRequestId) return;
    state.moveFrequencies = [];
    state.moveFrequencyTotal = 0;
  } finally {
    if (requestId === state.moveFrequencyRequestId) {
      renderMoveFrequencies();
    }
  }
}

async function loadOpenings() {
  const position = state.positions[state.currentMove];
  const requestId = state.openingRequestId + 1;
  state.openingRequestId = requestId;

  if (!position?.sfen) {
    state.openings = [];
    state.openingTotal = 0;
    renderOpenings();
    return;
  }

  try {
    const query = new URLSearchParams({
      source: "professional",
      sfen: position.sfen,
    });
    const response = await fetch(`/api/openings?${query.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (requestId !== state.openingRequestId) return;
    state.openings = Array.isArray(payload.moves) ? payload.moves : [];
    state.openingTotal = Number.isFinite(payload.total) ? payload.total : 0;
  } catch (error) {
    if (requestId !== state.openingRequestId) return;
    state.openings = [];
    state.openingTotal = 0;
  } finally {
    if (requestId === state.openingRequestId) {
      renderOpenings();
    }
  }
}

async function importOpeningFile(file) {
  openingImportButton.disabled = true;
  openingManagementSummary.textContent = "登録中";
  setStatus("定跡KIFを登録中");
  try {
    const response = await fetch("/api/openings/import?source=professional", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
      },
      body: file,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    await loadOpenings();
    openingManagementSummary.textContent = `${payload.count}件`;
    setStatus(`定跡KIFを登録しました: ${payload.count}件`);
    openingFileInput.value = "";
    updateOpeningFileName();
  } catch (error) {
    openingManagementSummary.textContent = "失敗";
    setStatus(`定跡KIFを登録できませんでした: ${error.message}`, "error");
  } finally {
    updateOpeningFileName();
  }
}

async function importOpeningDirectory(directoryPath, recursive) {
  openingDirectoryImportButton.disabled = true;
  openingCancelDirectoryImportButton.hidden = false;
  openingCancelDirectoryImportButton.disabled = true;
  openingManagementSummary.textContent = "0/0";
  setStatus("定跡KIFフォルダを登録中");
  try {
    const response = await fetch("/api/openings/import-directory", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        path: directoryPath,
        recursive,
        source: "professional",
        async: true,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    openingCancelDirectoryImportButton.dataset.jobId = payload.id;
    openingCancelDirectoryImportButton.disabled = false;
    await pollOpeningDirectoryImportJob(payload.id);
  } catch (error) {
    openingManagementSummary.textContent = "失敗";
    setStatus(`定跡KIFフォルダを登録できませんでした: ${error.message}`, "error");
  } finally {
    openingDirectoryImportButton.disabled = false;
    openingCancelDirectoryImportButton.hidden = true;
    openingCancelDirectoryImportButton.disabled = false;
    delete openingCancelDirectoryImportButton.dataset.jobId;
  }
}

async function pollOpeningDirectoryImportJob(jobId) {
  let payload = null;
  while (true) {
    const response = await fetch(`/api/openings/import-directory/jobs/${jobId}`);
    payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setOpeningDirectoryImportStatus(payload);
    if (payload.done) break;
    await wait(500);
  }
  await loadOpenings();
  if (payload.status === "canceled") {
    setStatus(`定跡一括登録をキャンセルしました: ${payload.processed}/${payload.total}`);
    return;
  }
  openingManagementSummary.textContent = `${payload.openings_count}手`;
  const failedText = payload.failed ? ` / 失敗 ${payload.failed}件` : "";
  setStatus(`定跡一括登録完了: ${payload.imported}/${payload.total}件${failedText}`);
}

function setOpeningDirectoryImportStatus(payload) {
  if (payload.status === "scanning") {
    openingManagementSummary.textContent = "スキャン中";
    setStatus("定跡KIFフォルダをスキャン中");
    return;
  }
  if (payload.status === "failed") {
    openingManagementSummary.textContent = "失敗";
    setStatus(`定跡一括登録失敗: ${payload.errors?.[0]?.error || "不明なエラー"}`, "error");
    return;
  }
  const total = Number.isFinite(payload.total) ? payload.total : 0;
  const processed = Number.isFinite(payload.processed) ? payload.processed : 0;
  openingManagementSummary.textContent = `${processed}/${total}`;
  if (payload.status === "canceling") {
    setStatus(`定跡一括登録をキャンセル中: ${processed}/${total}`);
    return;
  }
  setStatus(`定跡一括登録中: ${processed}/${total}`);
}

async function cancelOpeningDirectoryImport() {
  const jobId = openingCancelDirectoryImportButton.dataset.jobId;
  if (!jobId) return;
  openingCancelDirectoryImportButton.disabled = true;
  setStatus("定跡一括登録をキャンセル中");
  try {
    const response = await fetch(`/api/openings/import-directory/jobs/${jobId}/cancel`, {
      method: "POST",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setOpeningDirectoryImportStatus(payload);
  } catch (error) {
    setStatus(`定跡一括登録をキャンセルできませんでした: ${error.message}`, "error");
    openingCancelDirectoryImportButton.disabled = false;
  }
}

async function rebuildOpenings() {
  openingRebuildButton.disabled = true;
  cancelOpeningRebuildButton.hidden = false;
  cancelOpeningRebuildButton.disabled = true;
  openingRebuildSummary.textContent = "0/0";
  setStatus("定跡DBを更新中");
  try {
    const response = await fetch("/api/openings/rebuild", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        source: "self",
        async: true,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    cancelOpeningRebuildButton.dataset.jobId = payload.id;
    cancelOpeningRebuildButton.disabled = false;
    await pollOpeningRebuildJob(payload.id);
  } catch (error) {
    openingRebuildSummary.textContent = "失敗";
    setStatus(`定跡DBを更新できませんでした: ${error.message}`, "error");
  } finally {
    openingRebuildButton.disabled = false;
    cancelOpeningRebuildButton.hidden = true;
    cancelOpeningRebuildButton.disabled = false;
    delete cancelOpeningRebuildButton.dataset.jobId;
  }
}

async function pollOpeningRebuildJob(jobId) {
  let payload = null;
  while (true) {
    const response = await fetch(`/api/openings/rebuild/jobs/${jobId}`);
    payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setOpeningRebuildStatus(payload);
    if (payload.done) break;
    await wait(500);
  }
  if (payload.status === "canceled") {
    setStatus(`定跡DB更新をキャンセルしました: ${payload.processed}/${payload.total}`);
    return;
  }
  openingRebuildSummary.textContent = `${payload.count}件`;
  setStatus(`定跡DB更新完了: ${payload.processed}/${payload.total}`);
}

function setOpeningRebuildStatus(payload) {
  if (payload.status === "scanning") {
    openingRebuildSummary.textContent = "集計準備中";
    setStatus("定跡DB更新の対象を確認中");
    return;
  }
  if (payload.status === "failed") {
    openingRebuildSummary.textContent = "失敗";
    setStatus(`定跡DB更新失敗: ${payload.errors?.[0]?.error || "不明なエラー"}`, "error");
    return;
  }
  const total = Number.isFinite(payload.total) ? payload.total : 0;
  const processed = Number.isFinite(payload.processed) ? payload.processed : 0;
  openingRebuildSummary.textContent = `${processed}/${total}`;
  if (payload.status === "canceling") {
    setStatus(`定跡DB更新をキャンセル中: ${processed}/${total}`);
    return;
  }
  setStatus(`定跡DB更新中: ${processed}/${total}`);
}

async function cancelOpeningRebuild() {
  const jobId = cancelOpeningRebuildButton.dataset.jobId;
  if (!jobId) return;
  cancelOpeningRebuildButton.disabled = true;
  setStatus("定跡DB更新をキャンセル中");
  try {
    const response = await fetch(`/api/openings/rebuild/jobs/${jobId}/cancel`, {
      method: "POST",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setOpeningRebuildStatus(payload);
  } catch (error) {
    setStatus(`定跡DB更新をキャンセルできませんでした: ${error.message}`, "error");
    cancelOpeningRebuildButton.disabled = false;
  }
}

function openingComparisonSources() {
  return ["self", "professional", "yaneou"];
}

async function loadOpeningComparisonPrompt() {
  const position = state.positions[state.currentMove];
  if (!position?.id) return;

  const requestId = state.openingComparisonRequestId + 1;
  state.openingComparisonRequestId = requestId;
  state.openingComparisonStatus = "作成中";
  renderOpeningComparison();

  try {
    const query = new URLSearchParams({
      sources: openingComparisonSources().join(","),
    });
    const response = await fetch(`/api/positions/${position.id}/opening-comparison-prompt?${query.toString()}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    if (requestId !== state.openingComparisonRequestId) return;
    state.openingComparisonPrompt = typeof payload.prompt === "string" ? payload.prompt : "";
    state.openingComparisonMissing = Array.isArray(payload.materials?.missing) ? payload.materials.missing : [];
    state.openingComparisonStatus = "作成済み";
  } catch (error) {
    if (requestId !== state.openingComparisonRequestId) return;
    state.openingComparisonPrompt = "";
    state.openingComparisonMissing = [];
    state.openingComparisonStatus = "失敗";
    setStatus(`定跡比較を作成できませんでした: ${error.message}`, "error");
  } finally {
    if (requestId === state.openingComparisonRequestId) {
      renderOpeningComparison();
    }
  }
}

async function generateOpeningComparison() {
  const position = state.positions[state.currentMove];
  if (!position?.id) return;

  const requestId = state.openingComparisonRequestId + 1;
  state.openingComparisonRequestId = requestId;
  state.openingComparisonStatus = "生成中";
  renderOpeningComparison();

  try {
    const response = await fetch(`/api/positions/${position.id}/opening-comparison-explain`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ sources: openingComparisonSources() }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    if (requestId !== state.openingComparisonRequestId) return;
    state.openingComparisonPrompt = typeof payload.prompt === "string" ? payload.prompt : "";
    state.openingComparisonText = typeof payload.explanation === "string" ? payload.explanation : "";
    state.openingComparisonMissing = Array.isArray(payload.materials?.missing) ? payload.materials.missing : [];
    state.openingComparisonStatus = "生成済み";
  } catch (error) {
    if (requestId !== state.openingComparisonRequestId) return;
    state.openingComparisonText = "";
    state.openingComparisonStatus = "失敗";
    setStatus(`定跡比較解説を生成できませんでした: ${error.message}`, "error");
  } finally {
    if (requestId === state.openingComparisonRequestId) {
      renderOpeningComparison();
    }
  }
}

async function loadExplanationPrompt() {
  const position = state.positions[state.currentMove];
  if (!position?.id) return;

  const requestId = state.explanationRequestId + 1;
  state.explanationRequestId = requestId;
  buildExplanationPromptButton.disabled = true;
  state.explanationStatus = "作成中";
  renderExplanationPrompt();

  try {
    const response = await fetch(`/api/positions/${position.id}/explanation-prompt`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    if (requestId !== state.explanationRequestId) return;
    state.explanationPrompt = typeof payload.prompt === "string" ? payload.prompt : "";
    state.explanationMissing = Array.isArray(payload.materials?.missing) ? payload.materials.missing : [];
    state.explanationStatus = "作成済み";
  } catch (error) {
    if (requestId !== state.explanationRequestId) return;
    state.explanationPrompt = "";
    state.explanationMissing = [];
    state.explanationStatus = "失敗";
    setStatus(`局面解説プロンプトを作成できませんでした: ${error.message}`, "error");
  } finally {
    if (requestId === state.explanationRequestId) {
      renderExplanationPrompt();
    }
  }
}

async function generateExplanation() {
  const position = state.positions[state.currentMove];
  if (!position?.id) return;

  const requestId = state.explanationRequestId + 1;
  state.explanationRequestId = requestId;
  buildExplanationPromptButton.disabled = true;
  generateExplanationButton.disabled = true;
  state.explanationStatus = "生成中";
  renderExplanationPrompt();

  try {
    const response = await fetch(`/api/positions/${position.id}/explain`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    if (requestId !== state.explanationRequestId) return;
    state.explanationPrompt = typeof payload.prompt === "string" ? payload.prompt : "";
    state.explanationText = typeof payload.explanation === "string" ? payload.explanation : "";
    state.explanationMissing = Array.isArray(payload.materials?.missing) ? payload.materials.missing : [];
    state.explanationStatus = "生成済み";
  } catch (error) {
    if (requestId !== state.explanationRequestId) return;
    state.explanationText = "";
    state.explanationStatus = "失敗";
    setStatus(`局面解説を生成できませんでした: ${error.message}`, "error");
  } finally {
    if (requestId === state.explanationRequestId) {
      renderExplanationPrompt();
    }
  }
}

async function analyzeCurrentPositionForCandidates() {
  const position = state.positions[state.currentMove];
  if (!position?.id || state.candidateAnalysisStatus === "running") return;

  state.candidateAnalysisStatus = "running";
  state.candidateStatusText = "局面を解析中です";
  renderEngineCandidates(position);
  setStatus("局面を解析中");

  try {
    const response = await fetch(`/api/positions/${position.id}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    if (payload.position) {
      state.positions[state.currentMove] = payload.position;
    }
    state.selectedCandidateMove = null;
    state.candidateStatusText = "局面解析が完了しました";
    setStatus("局面解析が完了しました");
    renderBoard();
  } catch (error) {
    state.candidateStatusText = `局面解析に失敗しました: ${error.message}`;
    setStatus(`局面解析に失敗しました: ${error.message}`, "error");
    renderEngineCandidates(position);
  } finally {
    state.candidateAnalysisStatus = "idle";
    renderEngineCandidates(state.positions[state.currentMove]);
  }
}

async function importKifFile(file) {
  importButton.disabled = true;
  setStatus("登録中");
  try {
    const response = await fetch("/api/games/import", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
      },
      body: file,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    kifFileInput.value = "";
    updateImportFileName();
    await loadGames();
    setStatus(`登録しました: ${payload.game.black} vs ${payload.game.white}`);
  } catch (error) {
    setStatus(`KIFを登録できませんでした: ${error.message}`, "error");
  } finally {
    updateImportFileName();
  }
}

async function importKifDirectory(directoryPath, recursive) {
  directoryImportButton.disabled = true;
  cancelDirectoryImportButton.hidden = false;
  cancelDirectoryImportButton.disabled = true;
  setStatus("一括登録中");
  try {
    const response = await fetch("/api/games/import-directory", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        path: directoryPath,
        recursive,
        async: true,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    cancelDirectoryImportButton.dataset.jobId = payload.id;
    cancelDirectoryImportButton.disabled = false;
    await pollDirectoryImportJob(payload.id);
  } catch (error) {
    setStatus(`KIFフォルダを登録できませんでした: ${error.message}`, "error");
  } finally {
    directoryImportButton.disabled = false;
    cancelDirectoryImportButton.hidden = true;
    cancelDirectoryImportButton.disabled = false;
    delete cancelDirectoryImportButton.dataset.jobId;
  }
}

async function pollDirectoryImportJob(jobId) {
  let payload = null;
  while (true) {
    const response = await fetch(`/api/games/import-directory/jobs/${jobId}`);
    payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setDirectoryImportStatus(payload);
    if (payload.done) break;
    await wait(500);
  }
  await loadGames();
  if (payload.status === "canceled") {
    setStatus(`一括登録をキャンセルしました: ${payload.processed}/${payload.total}`);
    return;
  }
  const failedText = payload.failed ? ` / 失敗 ${payload.failed}件` : "";
  setStatus(`一括登録完了: ${payload.imported} / ${payload.total}件${failedText}`);
}

function setDirectoryImportStatus(payload) {
  if (payload.status === "scanning") {
    setStatus("KIFフォルダをスキャン中");
    return;
  }
  if (payload.status === "failed") {
    setStatus(`一括登録失敗: ${payload.errors?.[0]?.error || "不明なエラー"}`, "error");
    return;
  }
  if (payload.status === "canceling") {
    setStatus(`一括登録をキャンセル中: ${payload.processed}/${payload.total}`);
    return;
  }
  const total = Number.isFinite(payload.total) ? payload.total : 0;
  const processed = Number.isFinite(payload.processed) ? payload.processed : 0;
  setStatus(`一括登録中: ${processed}/${total}`);
}

async function cancelDirectoryImport() {
  const jobId = cancelDirectoryImportButton.dataset.jobId;
  if (!jobId) return;
  cancelDirectoryImportButton.disabled = true;
  setStatus("一括登録をキャンセル中");
  try {
    const response = await fetch(`/api/games/import-directory/jobs/${jobId}/cancel`, {
      method: "POST",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setDirectoryImportStatus(payload);
  } catch (error) {
    setStatus(`キャンセルできませんでした: ${error.message}`, "error");
    cancelDirectoryImportButton.disabled = false;
  }
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});

kifFileInput.addEventListener("change", updateImportFileName);
openingFileInput.addEventListener("change", updateOpeningFileName);

importForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const file = kifFileInput.files?.[0] || null;
  if (!file) return;
  importKifFile(file);
});

directoryImportForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const directoryPath = directoryPathInput.value.trim();
  if (!directoryPath) {
    setStatus("KIFフォルダのパスを入力してください", "error");
    return;
  }
  importKifDirectory(directoryPath, recursiveImportInput.checked);
});

cancelDirectoryImportButton.addEventListener("click", cancelDirectoryImport);
openingRebuildButton.addEventListener("click", rebuildOpenings);
cancelOpeningRebuildButton.addEventListener("click", cancelOpeningRebuild);
openingImportForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const file = openingFileInput.files?.[0] || null;
  if (!file) return;
  importOpeningFile(file);
});

openingDirectoryImportForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const directoryPath = openingDirectoryPathInput.value.trim();
  if (!directoryPath) {
    setStatus("定跡KIFフォルダのパスを入力してください", "error");
    return;
  }
  importOpeningDirectory(directoryPath, openingRecursiveImportInput.checked);
});
openingCancelDirectoryImportButton.addEventListener("click", cancelOpeningDirectoryImport);
buildOpeningComparisonButton.addEventListener("click", loadOpeningComparisonPrompt);
generateOpeningComparisonButton.addEventListener("click", generateOpeningComparison);
buildExplanationPromptButton.addEventListener("click", loadExplanationPrompt);
generateExplanationButton.addEventListener("click", generateExplanation);
analyzeCandidateButton.addEventListener("click", analyzeCurrentPositionForCandidates);

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
moveSlider.addEventListener("input", (event) => setCurrentMove(Number(event.target.value)));

const gameId = gameIdFromPath();
if (gameId) {
  loadViewer(gameId);
} else {
  loadGames();
}
