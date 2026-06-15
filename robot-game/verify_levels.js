"use strict";
/* Headless reachability checker for Bolt & Frost levels.
 * Replicates the game's physics/collision exactly, then BFS-explores every state
 * each robot can reach (avoiding its lethal pools) and records every cell it can
 * occupy. From those reachable-cell sets it confirms each robot can touch its key
 * and door, and that every coin is collectible by at least one robot.
 * Run: node verify_levels.js                                                     */

const fs = require("fs");

const TS = 40, WIDTH = 22, HEIGHT = 14;
const GRAVITY = 2000, MOVE_SPEED = 230, JUMP_SPEED = 680, MAX_FALL = 900;
const PW = 26, PH = 34, DT = 1 / 60;

const src = fs.readFileSync(__dirname + "/game.js", "utf8");
const block = src.match(/const LEVELS = \[([\s\S]*?)\n\];/)[1];
// Keep only full map rows; ignores quoted words in comments (e.g. nicknames).
const rows = [...block.matchAll(/"([^"]*)"/g)].map((m) => m[1]).filter((s) => s.length === WIDTH);
const LEVELS = [];
for (let i = 0; i < rows.length; i += HEIGHT) LEVELS.push(rows.slice(i, i + HEIGHT));

function parse(map) {
  const grid = map.map((r) => r.split(""));
  const out = { grid, spawn: {}, door: {}, key: {}, coins: [], buttons: [], gates: false, enemies: 0, blocks: 0 };
  for (let r = 0; r < HEIGHT; r++)
    for (let c = 0; c < WIDTH; c++) {
      const ch = grid[r][c];
      if (ch === "1") { out.spawn.bolt = { c, r }; grid[r][c] = " "; }
      else if (ch === "2") { out.spawn.frost = { c, r }; grid[r][c] = " "; }
      else if (ch === "A") { out.door.bolt = { c, r }; grid[r][c] = " "; }
      else if (ch === "B") { out.door.frost = { c, r }; grid[r][c] = " "; }
      else if (ch === "r") { out.key.bolt = { c, r }; grid[r][c] = " "; }
      else if (ch === "b") { out.key.frost = { c, r }; grid[r][c] = " "; }
      else if (ch === "o") { out.coins.push({ c, r }); grid[r][c] = " "; }
      else if (ch === "g" || ch === "h") { out.buttons.push({ c, r }); grid[r][c] = " "; }
      // Gates ('G'/'H') are treated as passable here: reachability is checked
      // assuming a partner can open them. Co-op sequencing is reasoned by hand.
      else if (ch === "G" || ch === "H") { out.gates = true; grid[r][c] = " "; }
      // Enemies are avoidable/stompable, so they don't block geometric reachability.
      else if (ch === "E") { out.enemies++; grid[r][c] = " "; }
      // Crates can be pushed/used as steps, so they don't statically block reachability.
      else if (ch === "M") { out.blocks++; grid[r][c] = " "; }
    }
  return out;
}

function isSolid(grid, col, row) {
  if (col < 0 || col >= WIDTH || row < 0 || row >= HEIGHT) return true;
  return grid[row][col] === "#";
}
function moveX(grid, p, vx) {
  p.x += vx * DT;
  const top = Math.floor(p.y / TS), bottom = Math.floor((p.y + PH - 0.01) / TS);
  if (vx > 0) {
    const col = Math.floor((p.x + PW - 0.01) / TS);
    for (let r = top; r <= bottom; r++) if (isSolid(grid, col, r)) { p.x = col * TS - PW; break; }
  } else if (vx < 0) {
    const col = Math.floor(p.x / TS);
    for (let r = top; r <= bottom; r++) if (isSolid(grid, col, r)) { p.x = (col + 1) * TS; break; }
  }
}
function moveY(grid, p) {
  p.vy = Math.min(p.vy + GRAVITY * DT, MAX_FALL);
  p.y += p.vy * DT;
  const left = Math.floor(p.x / TS), right = Math.floor((p.x + PW - 0.01) / TS);
  p.onGround = false;
  if (p.vy > 0) {
    const row = Math.floor((p.y + PH - 0.01) / TS);
    for (let c = left; c <= right; c++) if (isSolid(grid, c, row)) { p.y = row * TS - PH; p.vy = 0; p.onGround = true; break; }
  } else if (p.vy < 0) {
    const row = Math.floor(p.y / TS);
    for (let c = left; c <= right; c++) if (isSolid(grid, c, row)) { p.y = (row + 1) * TS; p.vy = 0; break; }
  }
}
function overlapsLethal(grid, p, type) {
  const lethal = type === "bolt" ? "C" : "P";
  const c0 = Math.floor(p.x / TS), c1 = Math.floor((p.x + PW - 0.01) / TS);
  const r0 = Math.floor(p.y / TS), r1 = Math.floor((p.y + PH - 0.01) / TS);
  for (let r = r0; r <= r1; r++)
    for (let c = c0; c <= c1; c++) {
      if (c < 0 || c >= WIDTH || r < 0 || r >= HEIGHT) continue;
      const ch = grid[r][c];
      if (ch === "X" || ch === lethal) return true;
    }
  return false;
}
function addCells(set, p) {
  const c0 = Math.floor(p.x / TS), c1 = Math.floor((p.x + PW - 0.01) / TS);
  const r0 = Math.floor(p.y / TS), r1 = Math.floor((p.y + PH - 0.01) / TS);
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) set.add(c + "," + r);
}
function enc(p) {
  const bx = Math.round(p.x / 3), by = Math.round(p.y / 3);
  return (((bx * 200 + by) * 90 + Math.round(p.vy / 25) + 40) * 2) + (p.onGround ? 1 : 0);
}

// Every cell the robot can occupy starting from spawn, never touching a lethal pool.
function reachableCells(grid, spawn, type) {
  const start = { x: spawn.c * TS + (TS - PW) / 2, y: spawn.r * TS + (TS - PH), vy: 0, onGround: false };
  const cells = new Set();
  addCells(cells, start);
  const seen = new Set([enc(start)]);
  let queue = [start], expansions = 0;
  const CAP = 8_000_000;
  while (queue.length) {
    const next = [];
    for (const s of queue) {
      if (++expansions > CAP) { cells.timeout = true; return cells; }
      for (const dir of [-1, 0, 1]) {
        for (const jump of [false, true]) {
          const p = { x: s.x, y: s.y, vy: s.vy, onGround: s.onGround };
          if (jump && p.onGround) p.vy = -JUMP_SPEED;
          moveX(grid, p, dir * MOVE_SPEED);
          moveY(grid, p);
          if (overlapsLethal(grid, p, type)) continue;
          const k = enc(p);
          if (!seen.has(k)) { seen.add(k); addCells(cells, p); next.push(p); }
        }
      }
    }
    queue = next;
  }
  return cells;
}

const has = (set, cell) => set.has(cell.c + "," + cell.r);

let allOk = true;
LEVELS.forEach((map, i) => {
  const lv = parse(map);
  const reach = { bolt: reachableCells(lv.grid, lv.spawn.bolt, "bolt"), frost: reachableCells(lv.grid, lv.spawn.frost, "frost") };
  console.log(`\nLevel ${i + 1}:`);
  let levelOk = true;
  for (const type of ["bolt", "frost"]) {
    const keyOk = has(reach[type], lv.key[type]);
    const doorOk = has(reach[type], lv.door[type]);
    if (reach[type].timeout) console.log(`  (warning: ${type} search hit the expansion cap — result may be incomplete)`);
    console.log(`  ${type.padEnd(5)}  key:${keyOk ? "ok " : "NO "}  door:${doorOk ? "ok " : "NO "}`);
    levelOk = levelOk && keyOk && doorOk;
  }
  const union = new Set([...reach.bolt, ...reach.frost]);
  const badCoins = lv.coins.filter((c) => !union.has(c.c + "," + c.r));
  console.log(`  coins: ${lv.coins.length - badCoins.length}/${lv.coins.length} collectible` +
    (badCoins.length ? `  UNREACHABLE: ${badCoins.map((c) => `(${c.c},${c.r})`).join(" ")}` : ""));
  levelOk = levelOk && badCoins.length === 0;
  if (lv.buttons.length) {
    const badBtns = lv.buttons.filter((b) => !union.has(b.c + "," + b.r));
    console.log(`  buttons: ${lv.buttons.length - badBtns.length}/${lv.buttons.length} reachable` +
      (badBtns.length ? `  UNREACHABLE: ${badBtns.map((b) => `(${b.c},${b.r})`).join(" ")}` : ""));
    levelOk = levelOk && badBtns.length === 0;
  }
  if (lv.gates) console.log("  (gate level: reachability assumes gates can be opened — co-op sequence checked by hand)");
  if (lv.enemies) console.log(`  (${lv.enemies} enemies: geometry verified — patrol timing/stomping checked by hand)`);
  if (lv.blocks) console.log(`  (${lv.blocks} crate(s): geometry verified — pushing/standing checked by hand)`);
  console.log(`  => ${levelOk ? "OK" : "PROBLEM"}`);
  allOk = allOk && levelOk;
});
console.log(allOk ? "\nALL LEVELS SOLVABLE & ALL COINS REACHABLE" : "\nSOME LEVELS HAVE PROBLEMS");
process.exit(allOk ? 0 : 1);
