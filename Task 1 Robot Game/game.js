"use strict";

/* ------------------------------------------------------------------ *
 * Bolt & Frost — a two-player local co-op puzzle platformer.
 *
 * Player 1 "Bolt"  (orange) : WASD       — immune to plasma, dies in coolant
 * Player 2 "Frost" (cyan)   : arrow keys — immune to coolant, dies in plasma
 * Acid kills both. Collect your matching key, grab coins, then both reach
 * your door. Score = coins + level bonus + speed bonus − deaths.
 *
 * Tile legend:
 *   #  solid          (space) air
 *   1  Bolt spawn      2  Frost spawn
 *   A  Bolt door       B  Frost door
 *   r  red key (Bolt)  b  blue key (Frost)   o  coin (either robot)
 *   C  coolant (kills Bolt)  P  plasma (kills Frost)  X  acid (kills both)
 * Every map is WIDTH x HEIGHT characters; verify_levels.js proves solvability.
 * ------------------------------------------------------------------ */

const TS = 40, WIDTH = 22, HEIGHT = 14;
const GRAVITY = 2000, MOVE_SPEED = 230, JUMP_SPEED = 680, MAX_FALL = 900;

const COIN_VALUE = 50;       // points per coin
const LEVEL_BONUS = 250;     // points for clearing a level
const TIME_PAR = 40;         // seconds; finishing faster earns a speed bonus
const TIME_BONUS_PER_SEC = 8;
const DEATH_PENALTY = 30;    // points docked per death at run's end
const STOMP_VALUE = 100;     // points per enemy stomped
const ENEMY_SPEED = 95;      // px / s patrol speed
const STOMP_BOUNCE = 520;    // px / s upward bounce after a stomp

const LEVELS = [
  // Level 1 — gentle intro: cross your own hazard pool to your key & door.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#   o   o    o   o   #",
    "#                    #",
    "#1 B  r  CC  b  PP A2#",
    "######################",
  ],
  // Level 2 — "Stepping Stones": hop the platforms across the central acid lake.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#      o    o  o     #",
    "#      ##  ## ##     #",
    "#1B r XXXXXXXXXX b A2#",
    "######################",
  ],
  // Level 3 — cross the gauntlet, climb an offset staircase to your door.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "# B                A #",
    "# ##              ## #",
    "#   o  o o  o o  o   #",
    "#   ##          ##   #",
    "#1     Pr XX bC     2#",
    "######################",
  ],
  // Level 4 — "The Tower": climb the central zig-zag staircase to the doors up top.
  [
    "######################",
    "#                    #",
    "#         AB         #",
    "#         ##         #",
    "#       o            #",
    "#       ##           #",
    "#         o          #",
    "#         ##         #",
    "#       o            #",
    "#       ##           #",
    "#         o          #",
    "#         ##         #",
    "#1  C r       b P   2#",
    "######################",
  ],
  // Level 5 — "The Pyramid": climb up and over the pyramid spanning the acid lake.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#         o          #",
    "#                    #",
    "#         o          #",
    "#         ##         #",
    "#       r    b       #",
    "#       ##  ##       #",
    "#     o        o     #",
    "#     ##      ##     #",
    "#1B   XXXXXXXXXX   A2#",
    "######################",
  ],
  // Level 6 — finale: symmetric gauntlet (Bolt's coolant left, Frost's plasma
  // right, shared acid centre — two fair jumps each), then the staircase climb.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "# B                A #",
    "# ##              ## #",
    "#     o  o  o  o     #",
    "#   ##          ##   #",
    "#1  C  r  XX b  P   2#",
    "######################",
  ],
  // Level 7 — "Twin Peaks": each robot climbs its own side, no crossing.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "# A                B #",
    "# ##              ## #",
    "#   oo          oo   #",
    "#   ##          ##   #",
    "#1 C r  XXXXXX  b P 2#",
    "######################",
  ],
  // Level 8 — "The Gauntlet": a long, dense crossing — fair, well-spaced jumps.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#    o   o  o   o    #",
    "#                    #",
    "#1B Cr P  XX  bC P A2#",
    "######################",
  ],
  // Level 9 — "High Tower": cross the gauntlet, then a three-step climb each side.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "# B                A #",
    "# ##              ## #",
    "#                    #",
    "#   ##          ##   #",
    "#     o  o  o  o     #",
    "#     ##      ##     #",
    "#1  Cr   XX b C P   2#",
    "######################",
  ],
  // Level 10 — "The Citadel": jump your pool, then up and over the pyramid.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#         o          #",
    "#                    #",
    "#         o          #",
    "#         ##         #",
    "#       r    b       #",
    "#       ##  ##       #",
    "#     o        o     #",
    "#     ##      ##     #",
    "#1B C XXXXXXXXXX PbA2#",
    "######################",
  ],
  // Level 11 — "Switch Room": stand on a button (g) to open the gate (G). Two
  // buttons flank the gate so you can ferry each other across, then both finish.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#12  g     G g rb  AB#",
    "######################",
  ],
  // Level 12 — "Patrol": stomp the patrolling enemies (land on top) or dodge them.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#   o   o  o   o     #",
    "#                    #",
    "#1B r E       E b  A2#",
    "######################",
  ],
  // Level 13 — "Crate & Switch": shove the crate (M) onto the button to hold the
  // gate open, so neither robot has to stay behind. Then both cross to the doors.
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#          G         #",
    "#g M12     G  rb  AB #",
    "######################",
  ],
  // Level 14 — "Switchback": crate onto the button opens the gate, then run the
  // hazard gauntlet beyond it. (crate + button + gate + element pools + coins)
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#      G             #",
    "#      G             #",
    "#      G             #",
    "#    o G   o    o    #",
    "#      G             #",
    "#g  M12G  Cr XX bP AB#",
    "######################",
  ],
  // Level 15 — "Patrol Tower": cross the hazard floor past a roaming enemy, then
  // climb the staircase to your door. (element pools + enemy + staircase + coins)
  [
    "######################",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "#                    #",
    "# B                A #",
    "# ##              ## #",
    "#    o   o   o   o   #",
    "#   ##          ##   #",
    "#1  Cr XX E bP      2#",
    "######################",
  ],
];

// Fail loudly on a malformed map rather than mis-rendering it.
LEVELS.forEach((lvl, i) => {
  if (lvl.length !== HEIGHT) throw new Error(`Level ${i + 1} has ${lvl.length} rows, expected ${HEIGHT}`);
  lvl.forEach((row, r) => {
    if (row.length !== WIDTH) throw new Error(`Level ${i + 1} row ${r} width ${row.length}, expected ${WIDTH}`);
  });
});

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const COLORS = {
  bolt: "#ff8c2b", frost: "#38bdf8",
  coolant: "#2f73e6", plasma: "#ff7a18", acid: "#22c55e",
  coin: "#ffd24a", wall: "#283555", wallTop: "#34456e",
};

// ---- Game state ----------------------------------------------------
let grid, players, keys, doors, coins, buttons, enemies, blocks, keysRemaining;
let gateOpen = {};   // { G: bool, H: bool } — a gate is open while its button is held
let levelIndex = 0;
let state = "play";          // "play" | "dead" | "win" | "complete"
let stateTime = 0;
let runScore = 0, runCoins = 0, runDeaths = 0, runStartTime = 0, levelStartTime = 0, runStartLevel = 0;
let runActive = false, pendingLevel = 0, pauseStart = 0;
const pressed = new Set();

function makePlayer(type, col, row) {
  return {
    type, color: COLORS[type], w: 26, h: 34,
    x: col * TS + (TS - 26) / 2, y: row * TS + (TS - 34),
    vx: 0, vy: 0, onGround: false, blink: 0,
  };
}

function loadLevel(index) {
  const map = LEVELS[index];
  grid = map.map((row) => row.split(""));
  keys = []; coins = []; doors = {}; players = []; buttons = []; enemies = []; blocks = [];
  for (let r = 0; r < HEIGHT; r++) {
    for (let c = 0; c < WIDTH; c++) {
      const ch = grid[r][c];
      switch (ch) {
        case "1": players[0] = makePlayer("bolt", c, r); grid[r][c] = " "; break;
        case "2": players[1] = makePlayer("frost", c, r); grid[r][c] = " "; break;
        case "A": doors.bolt = { col: c, row: r }; grid[r][c] = " "; break;
        case "B": doors.frost = { col: c, row: r }; grid[r][c] = " "; break;
        case "r": keys.push({ col: c, row: r, type: "bolt", got: false }); grid[r][c] = " "; break;
        case "b": keys.push({ col: c, row: r, type: "frost", got: false }); grid[r][c] = " "; break;
        case "o": coins.push({ col: c, row: r, got: false }); grid[r][c] = " "; break;
        case "g": case "h": buttons.push({ col: c, row: r, group: ch.toUpperCase() }); grid[r][c] = " "; break;
        case "E": enemies.push({ w: 28, h: 26, x: c * TS + (TS - 28) / 2, y: r * TS + (TS - 26), vx: 0, vy: 0, dir: -1, onGround: false, alive: true }); grid[r][c] = " "; break;
        case "M": blocks.push({ w: TS, h: TS, x: c * TS, y: r * TS, vy: 0 }); grid[r][c] = " "; break;
        // 'G' / 'H' gates stay in the grid; their solidity is toggled by gateOpen.
        default: break;
      }
    }
  }
  keysRemaining = keys.length;
  state = "play";
}

function coinsGot() { return coins.filter((c) => c.got).length; }
function stompedCount() { return enemies.filter((e) => !e.alive).length; }
function levelPoints() { return coinsGot() * COIN_VALUE + stompedCount() * STOMP_VALUE; }
function provisionalScore() { return runScore + levelPoints(); }

function startRun(index, now) {
  levelIndex = index;
  runStartLevel = index;
  runScore = 0; runCoins = 0; runDeaths = 0;
  runStartTime = now; levelStartTime = now;
  runActive = true;
  hideEndModal(); hideMenu();
  startMusic();
  loadLevel(index);
}

// ---- Collision -----------------------------------------------------
function isSolid(col, row) {
  if (col < 0 || col >= WIDTH || row < 0 || row >= HEIGHT) return true;
  const ch = grid[row][col];
  if (ch === "#") return true;
  if (ch === "G" || ch === "H") return !gateOpen[ch]; // gate: solid unless its button is held
  return false;
}
function moveX(p, dt) {
  p.x += p.vx * dt;
  const top = Math.floor(p.y / TS), bottom = Math.floor((p.y + p.h - 0.01) / TS);
  if (p.vx > 0) {
    const col = Math.floor((p.x + p.w - 0.01) / TS);
    for (let r = top; r <= bottom; r++) if (isSolid(col, r)) { p.x = col * TS - p.w; p.vx = 0; break; }
  } else if (p.vx < 0) {
    const col = Math.floor(p.x / TS);
    for (let r = top; r <= bottom; r++) if (isSolid(col, r)) { p.x = (col + 1) * TS; p.vx = 0; break; }
  }
}
function moveY(p, dt) {
  p.vy = Math.min(p.vy + GRAVITY * dt, MAX_FALL);
  p.y += p.vy * dt;
  const left = Math.floor(p.x / TS), right = Math.floor((p.x + p.w - 0.01) / TS);
  p.onGround = false;
  if (p.vy > 0) {
    const row = Math.floor((p.y + p.h - 0.01) / TS);
    for (let c = left; c <= right; c++) if (isSolid(c, row)) { p.y = row * TS - p.h; p.vy = 0; p.onGround = true; break; }
  } else if (p.vy < 0) {
    const row = Math.floor(p.y / TS);
    for (let c = left; c <= right; c++) if (isSolid(c, row)) { p.y = (row + 1) * TS; p.vy = 0; break; }
  }
}
function overlappedCells(p) {
  const cells = [];
  const c0 = Math.floor(p.x / TS), c1 = Math.floor((p.x + p.w - 0.01) / TS);
  const r0 = Math.floor(p.y / TS), r1 = Math.floor((p.y + p.h - 0.01) / TS);
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++)
    if (c >= 0 && c < WIDTH && r >= 0 && r < HEIGHT) cells.push(grid[r][c]);
  return cells;
}
function hazardKills(p) {
  for (const ch of overlappedCells(p)) {
    if (ch === "X") return true;
    if (ch === "C" && p.type === "bolt") return true;
    if (ch === "P" && p.type === "frost") return true;
  }
  return false;
}
function aabbHitsCell(p, col, row) {
  return p.x < (col + 1) * TS && p.x + p.w > col * TS &&
         p.y < (row + 1) * TS && p.y + p.h > row * TS;
}

// Patrolling enemies: walk back and forth, turning at walls and platform edges.
function updateEnemies(dt) {
  for (const e of enemies) {
    if (!e.alive) continue;
    if (e.onGround) { // don't walk off a ledge
      const aheadCol = Math.floor((e.dir > 0 ? e.x + e.w + 2 : e.x - 2) / TS);
      const footRow = Math.floor((e.y + e.h + 2) / TS);
      if (!isSolid(aheadCol, footRow)) e.dir *= -1;
    }
    e.vx = e.dir * ENEMY_SPEED;
    moveX(e, dt);
    if (e.vx === 0) e.dir *= -1; // bumped a wall
    moveY(e, dt);
  }
}

// Stomp from above = kill enemy + bounce; any other contact = robot dies.
// Returns true if a robot was killed (caller should end the level).
function resolveEnemyHits() {
  for (const e of enemies) {
    if (!e.alive) continue;
    for (const p of players) {
      const overlap = p.x < e.x + e.w && p.x + p.w > e.x && p.y < e.y + e.h && p.y + p.h > e.y;
      if (!overlap) continue;
      if (p.vy > 0 && p.y + p.h < e.y + e.h * 0.6) { e.alive = false; p.vy = -STOMP_BOUNCE; sfx("stomp"); }
      else return true;
    }
  }
  return false;
}

// A gate group is open while any robot stands on one of its buttons (hold-to-open).
function computeGates() {
  gateOpen = {};
  for (const b of buttons) {
    if (!(b.group in gateOpen)) gateOpen[b.group] = false;
    if (players.some((p) => aabbHitsCell(p, b.col, b.row)) ||
        blocks.some((bl) => aabbHitsCell(bl, b.col, b.row))) gateOpen[b.group] = true; // a crate can hold a button too
  }
}

// ---- Pushable blocks (crates) --------------------------------------
function rectsOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}
function gridSolidAt(x, y, w, h) {
  const c0 = Math.floor(x / TS), c1 = Math.floor((x + w - 0.01) / TS);
  const r0 = Math.floor(y / TS), r1 = Math.floor((y + h - 0.01) / TS);
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) if (isSolid(c, r)) return true;
  return false;
}
function blockBlocked(rect, self) {
  if (gridSolidAt(rect.x, rect.y, rect.w, rect.h)) return true;
  return blocks.some((o) => o !== self && o.alive !== false && rectsOverlap(rect, o));
}

// Crates fall and rest on the grid or on each other (lower ones settle first).
function settleBlocks(dt) {
  for (const b of [...blocks].sort((a, z) => z.y - a.y)) {
    b.vy = Math.min(b.vy + GRAVITY * dt, MAX_FALL);
    const ny = b.y + b.vy * dt;
    if (!blockBlocked({ x: b.x, y: ny, w: b.w, h: b.h }, b)) { b.y = ny; continue; }
    let ry = b.y; // creep down to the resting position
    while (ry < ny && !blockBlocked({ x: b.x, y: ry + 1, w: b.w, h: b.h }, b)) ry += 1;
    b.y = ry; b.vy = 0;
  }
}

// A walking robot pushes a crate horizontally if the space ahead is clear.
function pushBlocksX(p) {
  for (const b of blocks) {
    if (!rectsOverlap(p, b)) continue;
    if (p.vx > 0) {
      const nbx = p.x + p.w;
      if (!blockBlocked({ x: nbx, y: b.y, w: b.w, h: b.h }, b)) { b.x = nbx; p.x = b.x - p.w; }
      else { p.x = b.x - p.w; p.vx = 0; }
    } else if (p.vx < 0) {
      const nbx = p.x - b.w;
      if (!blockBlocked({ x: nbx, y: b.y, w: b.w, h: b.h }, b)) { b.x = nbx; p.x = b.x + b.w; }
      else { p.x = b.x + b.w; p.vx = 0; }
    }
  }
}

// Robots stand on crate tops and bonk their heads from below.
function landBlocksY(p) {
  for (const b of blocks) {
    if (!rectsOverlap(p, b)) continue;
    if (p.vy > 0) { p.y = b.y - p.h; p.vy = 0; p.onGround = true; }
    else if (p.vy < 0) { p.y = b.y + b.h; p.vy = 0; }
  }
}

// ---- Input ---------------------------------------------------------
const JUMP_KEYS = { bolt: "w", frost: "arrowup" };
window.addEventListener("keydown", (e) => {
  if (document.activeElement && document.activeElement.tagName === "INPUT") return;
  const k = e.key.toLowerCase();
  if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(k)) e.preventDefault();
  if (k === "r" && (state === "play" || state === "dead")) { loadLevel(levelIndex); return; }
  if (!pressed.has(k) && state === "play") {
    if (k === JUMP_KEYS.bolt && players[0].onGround) { players[0].vy = -JUMP_SPEED; sfx("jump"); }
    if (k === JUMP_KEYS.frost && players[1].onGround) { players[1].vy = -JUMP_SPEED; sfx("jump"); }
  }
  pressed.add(k);
});
window.addEventListener("keyup", (e) => pressed.delete(e.key.toLowerCase()));

function readInput() {
  players[0].vx = ((pressed.has("d") ? 1 : 0) - (pressed.has("a") ? 1 : 0)) * MOVE_SPEED;
  players[1].vx = ((pressed.has("arrowright") ? 1 : 0) - (pressed.has("arrowleft") ? 1 : 0)) * MOVE_SPEED;
}

// ---- Update --------------------------------------------------------
function update(dt, now) {
  if (state !== "play") {
    if (state === "dead" && now - stateTime > 1100) loadLevel(levelIndex);
    if (state === "win" && now - stateTime > 1300) advanceLevel(now);
    return;
  }
  computeGates();
  readInput();
  settleBlocks(dt);
  for (const p of players) {
    moveX(p, dt); pushBlocksX(p);
    moveY(p, dt); landBlocksY(p);
    p.blink = (p.blink + dt) % 3;
  }
  updateEnemies(dt);

  for (const c of coins) if (!c.got && (aabbHitsCell(players[0], c.col, c.row) || aabbHitsCell(players[1], c.col, c.row))) { c.got = true; sfx("coin"); }
  for (const key of keys) {
    if (key.got) continue;
    for (const p of players) if (p.type === key.type && aabbHitsCell(p, key.col, key.row)) { key.got = true; keysRemaining--; }
  }

  if (resolveEnemyHits() || hazardKills(players[0]) || hazardKills(players[1])) { state = "dead"; stateTime = now; runDeaths++; sfx("death"); return; }

  const boltAtDoor = aabbHitsCell(players[0], doors.bolt.col, doors.bolt.row);
  const frostAtDoor = aabbHitsCell(players[1], doors.frost.col, doors.frost.row);
  if (keysRemaining === 0 && boltAtDoor && frostAtDoor) {
    const elapsed = (now - levelStartTime) / 1000;
    const timeBonus = Math.max(0, Math.round((TIME_PAR - elapsed) * TIME_BONUS_PER_SEC));
    runScore += levelPoints() + LEVEL_BONUS + timeBonus;
    runCoins += coinsGot();
    state = "win"; stateTime = now; sfx("win");
  }
}

function advanceLevel(now) {
  if (levelIndex + 1 < LEVELS.length) {
    levelIndex++; loadLevel(levelIndex); levelStartTime = now;
  } else {
    state = "complete"; stateTime = now;
    const finalScore = Math.max(0, runScore - runDeaths * DEATH_PENALTY);
    showEndModal(finalScore, runCoins, (now - runStartTime) / 1000, runDeaths, runStartLevel);
  }
}

// ---- Leaderboard (localStorage) ------------------------------------
const LB_KEY = "boltfrost_leaderboard_v1";
function loadLB() { try { return JSON.parse(localStorage.getItem(LB_KEY)) || []; } catch { return []; } }
function saveLB(list) { try { localStorage.setItem(LB_KEY, JSON.stringify(list)); } catch { /* storage may be blocked */ } }
function addRun(run) {
  const list = loadLB();
  list.push(run);
  list.sort((a, b) => b.score - a.score);
  const top = list.slice(0, 10);
  saveLB(top);
  return top;
}
function fmtTime(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}
function renderLB(highlightIdx) {
  const body = document.getElementById("lb-body");
  const list = loadLB();
  if (!list.length) { body.innerHTML = '<tr><td colspan="6" class="lb-empty">No runs yet — finish a game to set a record!</td></tr>'; return; }
  body.innerHTML = list.map((run, i) => {
    const span = run.startLevel > 0 ? `L${run.startLevel + 1}-${LEVELS.length}` : `L1-${LEVELS.length}`;
    return `<tr class="${i === highlightIdx ? "lb-hi" : ""}">
      <td>${i + 1}</td><td>${run.name}</td><td>${run.score}</td>
      <td>${run.coins}</td><td>${fmtTime(run.time)}</td><td>${span}</td></tr>`;
  }).join("");
}

// ---- End-of-run modal ----------------------------------------------
let pendingRun = null;
function showEndModal(score, coins, time, deaths, startLevel) {
  pendingRun = { score, coins, time, deaths, startLevel };
  document.getElementById("final-stats").innerHTML =
    `Score <b>${score}</b> &middot; ${coins} coins &middot; ${fmtTime(time)} &middot; ${deaths} death${deaths === 1 ? "" : "s"}`;
  document.getElementById("save-row").style.display = "flex";
  document.getElementById("again-btn").style.display = "none";
  document.getElementById("end-modal").classList.add("show");
  const input = document.getElementById("name-input");
  input.value = ""; input.focus();
}
function hideEndModal() { document.getElementById("end-modal").classList.remove("show"); }

// ---- Audio: procedural music + SFX (zero-dependency WebAudio) -------
let audioCtx = null, masterGain = null, musicGain = null, soundOn = true;
let musicTimer = null, nextNoteTime = 0, beat = 0;
const MELODY = [330, 0, 392, 440, 0, 392, 330, 294, 330, 392, 523, 440, 392, 0, 294, 0];
const BASS = [110, 110, 147, 98];
function ensureAudio() {
  if (audioCtx) { if (audioCtx.state === "suspended") audioCtx.resume(); return; }
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  audioCtx = new AC();
  masterGain = audioCtx.createGain(); masterGain.gain.value = soundOn ? 0.5 : 0; masterGain.connect(audioCtx.destination);
  musicGain = audioCtx.createGain(); musicGain.gain.value = 0.10; musicGain.connect(masterGain);
}
function tone(freq, time, dur, type, peak, dest) {
  if (!freq || !audioCtx) return;
  const o = audioCtx.createOscillator(), g = audioCtx.createGain();
  o.type = type || "triangle"; o.frequency.value = freq;
  o.connect(g); g.connect(dest || masterGain);
  g.gain.setValueAtTime(0.0001, time);
  g.gain.exponentialRampToValueAtTime(peak || 0.4, time + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, time + dur);
  o.start(time); o.stop(time + dur + 0.03);
}
function musicScheduler() {
  if (!audioCtx) return;
  while (nextNoteTime < audioCtx.currentTime + 0.25) {
    tone(MELODY[beat % MELODY.length], nextNoteTime, 0.16, "triangle", 0.5, musicGain);
    if (beat % 4 === 0) tone(BASS[((beat / 4) | 0) % BASS.length], nextNoteTime, 0.34, "sawtooth", 0.5, musicGain);
    nextNoteTime += 0.2; beat++;
  }
}
function startMusic() {
  ensureAudio();
  if (audioCtx && !musicTimer) { nextNoteTime = audioCtx.currentTime + 0.1; musicTimer = setInterval(musicScheduler, 60); }
}
function toggleSound() {
  soundOn = !soundOn; ensureAudio();
  if (masterGain) masterGain.gain.value = soundOn ? 0.5 : 0;
  return soundOn;
}
function sfx(name) {
  if (!audioCtx || !soundOn) return;
  const t = audioCtx.currentTime;
  if (name === "coin") { tone(988, t, 0.09, "square", 0.3); tone(1319, t + 0.05, 0.1, "square", 0.3); }
  else if (name === "stomp") { tone(300, t, 0.12, "square", 0.4); tone(150, t + 0.06, 0.14, "square", 0.4); }
  else if (name === "death") { tone(160, t, 0.45, "sawtooth", 0.4); tone(90, t + 0.12, 0.4, "sawtooth", 0.4); }
  else if (name === "win") { [523, 659, 784, 1047].forEach((f, i) => tone(f, t + i * 0.1, 0.2, "triangle", 0.4)); }
  else if (name === "jump") { tone(523, t, 0.07, "square", 0.18); }
}

// ---- Menu ----------------------------------------------------------
function showMenu(resume) {
  if (resume) pauseStart = performance.now(); // freeze the run timers while paused
  state = "menu";
  document.getElementById("resume-btn").style.display = resume ? "block" : "none";
  document.getElementById("menu").classList.add("show");
}
function hideMenu() { document.getElementById("menu").classList.remove("show"); }

// Manual level pick: warn that skipping levels means fewer points.
function pickLevel(i) {
  if (i === 0) { startRun(0, performance.now()); return; }
  pendingLevel = i;
  document.getElementById("confirm-text").textContent =
    `Starting at Level ${i + 1} skips levels 1–${i}, so you'll miss their coins and clear/speed bonuses and finish with a lower score. Start here anyway?`;
  document.getElementById("confirm-modal").classList.add("show");
}

function wireUI() {
  // Level-select buttons.
  const bar = document.getElementById("level-bar");
  for (let i = 0; i < LEVELS.length; i++) {
    const btn = document.createElement("button");
    btn.textContent = i + 1;
    btn.className = "lvl-btn";
    btn.addEventListener("click", () => pickLevel(i));
    bar.appendChild(btn);
  }
  // Main menu + controls.
  document.getElementById("menu-btn").addEventListener("click", () => showMenu(runActive));
  document.getElementById("start-btn").addEventListener("click", () => startRun(0, performance.now()));
  document.getElementById("restart-btn").addEventListener("click", () => startRun(0, performance.now()));
  document.getElementById("resume-btn").addEventListener("click", () => {
    const pausedFor = performance.now() - pauseStart; // don't count menu time against the timer
    levelStartTime += pausedFor; runStartTime += pausedFor;
    hideMenu(); state = "play";
  });
  document.getElementById("sound-btn").addEventListener("click", (e) => { e.target.textContent = toggleSound() ? "🔊 Sound: On" : "🔇 Sound: Off"; });
  document.getElementById("confirm-no").addEventListener("click", () => document.getElementById("confirm-modal").classList.remove("show"));
  document.getElementById("confirm-yes").addEventListener("click", () => { document.getElementById("confirm-modal").classList.remove("show"); startRun(pendingLevel, performance.now()); });
  // Save score.
  document.getElementById("save-btn").addEventListener("click", () => {
    const raw = document.getElementById("name-input").value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8) || "ANON";
    const saved = { name: raw, ...pendingRun };
    const top = addRun(saved);
    renderLB(top.indexOf(saved));
    document.getElementById("save-row").style.display = "none";
    document.getElementById("again-btn").style.display = "inline-block";
  });
  document.getElementById("name-input").addEventListener("keydown", (e) => { if (e.key === "Enter") document.getElementById("save-btn").click(); });
  document.getElementById("again-btn").addEventListener("click", () => startRun(0, performance.now()));
  renderLB(-1);
}

// ---- Rendering -----------------------------------------------------
function drawBackground() {
  const g = ctx.createLinearGradient(0, 0, 0, canvas.height);
  g.addColorStop(0, "#101935"); g.addColorStop(1, "#0a0f22");
  ctx.fillStyle = g; ctx.fillRect(0, 0, canvas.width, canvas.height);
}
function drawTiles(now) {
  const wob = Math.sin(now / 240) * 2;
  for (let r = 0; r < HEIGHT; r++) for (let c = 0; c < WIDTH; c++) {
    const ch = grid[r][c], x = c * TS, y = r * TS;
    if (ch === "#") {
      ctx.fillStyle = COLORS.wall; ctx.fillRect(x, y, TS, TS);
      ctx.fillStyle = COLORS.wallTop; ctx.fillRect(x, y, TS, 5);
    } else if (ch === "C" || ch === "P" || ch === "X") {
      ctx.fillStyle = ch === "C" ? COLORS.coolant : ch === "P" ? COLORS.plasma : COLORS.acid;
      ctx.globalAlpha = 0.85; ctx.fillRect(x, y + 8 + wob, TS, TS - 8 - wob);
      ctx.globalAlpha = 0.35; ctx.fillRect(x, y + 4 + wob, TS, 6);
      ctx.globalAlpha = 1;
    } else if (ch === "G" || ch === "H") {
      const open = gateOpen[ch];
      ctx.fillStyle = open ? "rgba(150,170,210,0.18)" : "#8aa0cf";
      ctx.fillRect(x + 12, y, TS - 24, TS);
      if (!open) { ctx.fillStyle = "#aebcdf"; ctx.fillRect(x + 12, y, TS - 24, 4); }
    }
  }
}

function drawBlocks() {
  for (const b of blocks) {
    ctx.fillStyle = "#a9743c";
    ctx.fillRect(b.x + 1, b.y + 1, b.w - 2, b.h - 2);
    ctx.strokeStyle = "#6e4a22";
    ctx.lineWidth = 2;
    ctx.strokeRect(b.x + 3, b.y + 3, b.w - 6, b.h - 6);
    ctx.beginPath();
    ctx.moveTo(b.x + 3, b.y + 3); ctx.lineTo(b.x + b.w - 3, b.y + b.h - 3);
    ctx.moveTo(b.x + b.w - 3, b.y + 3); ctx.lineTo(b.x + 3, b.y + b.h - 3);
    ctx.stroke();
  }
}

function drawEnemies() {
  for (const e of enemies) {
    if (!e.alive) continue;
    ctx.fillStyle = "#d23b4f";
    roundRect(e.x, e.y, e.w, e.h, 5); ctx.fill();
    ctx.fillStyle = "#7a1020"; ctx.fillRect(e.x, e.y + e.h - 4, e.w, 4); // treads
    const look = e.dir > 0 ? 3 : -3; // eyes glance in travel direction
    ctx.fillStyle = "#fff";
    ctx.fillRect(e.x + 6 + look, e.y + 8, 5, 5);
    ctx.fillRect(e.x + e.w - 11 + look, e.y + 8, 5, 5);
    ctx.fillStyle = "#3a0d14";
    ctx.fillRect(e.x + 8 + look, e.y + 10, 2, 3);
    ctx.fillRect(e.x + e.w - 9 + look, e.y + 10, 2, 3);
  }
}

function drawButtons() {
  for (const b of buttons) {
    const x = b.col * TS, y = b.row * TS, lit = gateOpen[b.group];
    ctx.fillStyle = lit ? "#7CFC00" : "#c0843a";
    ctx.fillRect(x + 6, y + TS - (lit ? 5 : 9), TS - 12, lit ? 5 : 9);
    ctx.fillStyle = "rgba(255,255,255,0.5)";
    ctx.fillRect(x + 6, y + TS - (lit ? 5 : 9), TS - 12, 2);
  }
}
function drawCoins(now) {
  for (const coin of coins) {
    if (coin.got) continue;
    const cx = coin.col * TS + TS / 2, cy = coin.row * TS + TS / 2;
    const rx = 7 * Math.abs(Math.cos(now / 250 + coin.col)); // spin shimmer
    ctx.fillStyle = COLORS.coin;
    ctx.beginPath(); ctx.ellipse(cx, cy, Math.max(2, rx), 7, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.7)";
    ctx.beginPath(); ctx.ellipse(cx - rx / 3, cy - 2, Math.max(1, rx / 3), 2.5, 0, 0, Math.PI * 2); ctx.fill();
  }
}
function drawKeys() {
  for (const key of keys) {
    if (key.got) continue;
    const cx = key.col * TS + TS / 2, cy = key.row * TS + TS / 2;
    ctx.fillStyle = key.type === "bolt" ? COLORS.bolt : COLORS.frost;
    ctx.beginPath(); ctx.arc(cx, cy - 4, 7, 0, Math.PI * 2); ctx.fill();
    ctx.fillRect(cx - 2, cy - 4, 4, 14); ctx.fillRect(cx - 2, cy + 6, 7, 3);
  }
}
function drawDoor(door, type, open) {
  const x = door.col * TS, y = door.row * TS;
  ctx.fillStyle = open ? (type === "bolt" ? COLORS.bolt : COLORS.frost) : "#3a466b";
  ctx.fillRect(x + 4, y + 2, TS - 8, TS - 2);
  ctx.fillStyle = open ? "rgba(255,255,255,0.85)" : "#10182f";
  ctx.fillRect(x + 9, y + 7, TS - 18, TS - 9);
  if (!open) {
    ctx.fillStyle = type === "bolt" ? COLORS.bolt : COLORS.frost;
    ctx.beginPath(); ctx.arc(x + TS / 2, y + TS / 2, 4, 0, Math.PI * 2); ctx.fill();
  }
}
function roundRect(x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function drawRobot(p) {
  const { x, y, w, h, color } = p;
  ctx.fillStyle = "#1b2440"; ctx.fillRect(x, y + h - 6, w, 6);
  ctx.fillStyle = color; roundRect(x, y + 4, w, h - 8, 6); ctx.fill();
  ctx.fillStyle = "rgba(0,0,0,0.35)"; roundRect(x + 4, y + 8, w - 8, 11, 4); ctx.fill();
  const blinking = p.blink > 2.85;
  ctx.fillStyle = blinking ? "rgba(255,255,255,0.2)" : "#ffffff";
  ctx.fillRect(x + 8, y + 12, 4, blinking ? 1 : 4);
  ctx.fillRect(x + w - 12, y + 12, 4, blinking ? 1 : 4);
  ctx.strokeStyle = color; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x + w / 2, y + 4); ctx.lineTo(x + w / 2, y - 4); ctx.stroke();
  ctx.fillStyle = "#ffffff"; ctx.beginPath(); ctx.arc(x + w / 2, y - 5, 2.5, 0, Math.PI * 2); ctx.fill();
}
function drawHud(now) {
  ctx.fillStyle = "rgba(8,12,26,0.7)"; ctx.fillRect(0, 0, canvas.width, 30);
  ctx.fillStyle = "#e7ecff"; ctx.font = "15px 'Segoe UI', sans-serif"; ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  const elapsed = state === "play" ? (now - levelStartTime) / 1000 : 0;
  ctx.fillText(`Lvl ${levelIndex + 1}/${LEVELS.length}    Score ${provisionalScore()}    Coins ${runCoins + coinsGot()}    ${fmtTime(elapsed)}    Deaths ${runDeaths}`, 12, 16);
  ctx.textAlign = "right";
  ctx.fillStyle = keysRemaining === 0 ? COLORS.acid : "#e7ecff";
  ctx.fillText(keysRemaining === 0 ? "Doors open!" : `Keys left: ${keysRemaining}`, canvas.width - 12, 16);
}
function drawCenterMessage(title, subtitle, color) {
  ctx.fillStyle = "rgba(5,8,18,0.72)"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.textAlign = "center";
  ctx.fillStyle = color; ctx.font = "bold 42px 'Segoe UI', sans-serif";
  ctx.fillText(title, canvas.width / 2, canvas.height / 2 - 14);
  if (subtitle) { ctx.fillStyle = "#cdd6f4"; ctx.font = "18px 'Segoe UI', sans-serif"; ctx.fillText(subtitle, canvas.width / 2, canvas.height / 2 + 28); }
}
function render(now) {
  drawBackground();
  drawTiles(now);
  const open = keysRemaining === 0;
  drawDoor(doors.bolt, "bolt", open); drawDoor(doors.frost, "frost", open);
  drawButtons();
  drawBlocks();
  drawCoins(now); drawKeys();
  drawEnemies();
  for (const p of players) drawRobot(p);
  drawHud(now);
  if (state === "dead") drawCenterMessage("Robot destroyed!", "Restarting level…", "#ff5c5c");
  else if (state === "win") drawCenterMessage("Level complete!", "", COLORS.acid);
  else if (state === "complete") drawCenterMessage("Run finished!", "", "#ffd166");
}

// ---- Main loop -----------------------------------------------------
let last = performance.now();
function frame(now) {
  let dt = (now - last) / 1000; last = now;
  if (dt > 0.033) dt = 0.033;
  update(dt, now);
  render(now);
  requestAnimationFrame(frame);
}

wireUI();
loadLevel(0);     // set up a scene to render behind the menu
showMenu(false);  // boot into the main menu
requestAnimationFrame(frame);
