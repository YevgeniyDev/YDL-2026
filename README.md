# YDL-2026 — Data Lab Projects

A collection of projects developed for the data lab. Each project lives in its own
folder with a self-contained description, source, and notes.

## Current Task: Robotics-Themed Browser Game

Build a simple, playable game related to **Robotics Engineering**, implemented with
plain **HTML, CSS, and JavaScript** (no frameworks or build step required).

### Goals

- Runnable by opening a single `index.html` in any modern browser.
- Small in scope — completable as a first project, but polished enough to demo.
- Tied to a real robotics concept so it teaches or illustrates something, not just
  reskinned arcade mechanics.

### Constraints

- Vanilla HTML / CSS / JS only.
- No external build tooling; keep dependencies to zero (or CDN-only if truly needed).
- Self-contained in its own subfolder (e.g. `robot-game/`).

## Game Concept Suggestions

Ordered roughly by implementation effort (lowest first). Each ties to a genuine
robotics idea.

### 1. Robot Command Sequencer *(recommended starting point)*
Program a robot on a tile grid by queuing a sequence of commands
(`forward`, `turn left`, `turn right`) to reach a goal while avoiding obstacles.
- **Robotics concept:** motion planning, command sequencing, discrete control.
- **Why start here:** grid + turn-based logic is easy to render with the DOM or a
  small canvas; no physics or timing loops needed.
- **Stretch:** add loops/functions (à la *Lightbot*), limited command budget, stars
  for efficiency.

### 2. Line-Following Robot Simulator
A robot drives along a track and must stay on the line using simulated sensors.
The player tunes parameters (e.g. turn strength / sensor sensitivity) to complete laps.
- **Robotics concept:** sensor feedback, control loops, basic PID intuition.
- **Effort:** medium — needs an animation loop and simple steering math.

### 3. Robotic Arm Pick-and-Place
Control a 2–3 joint robotic arm by setting joint angles to grab blocks and stack them.
- **Robotics concept:** forward kinematics, joint articulation, end-effector control.
- **Effort:** medium-high — canvas drawing of linked segments + collision/grab logic.

### 4. Conveyor Sorting Robot
Objects of different types stream down a conveyor; the player/robot sorts them into
the correct bins under time pressure.
- **Robotics concept:** classification, actuation timing, throughput optimization.
- **Effort:** medium — moving sprites + timing, scales nicely in difficulty.

## Implemented: `robot-game/` — *Bolt & Frost*

A two-player local co-op puzzle platformer (concept #1, evolved into a *Fireboy &
Watergirl*-style game). Both players share one keyboard:

- **Bolt** (Player 1, orange): `W` jump, `A`/`D` move. Immune to **plasma**, dies in **coolant**.
- **Frost** (Player 2, cyan): `↑` jump, `←`/`→` move. Immune to **coolant**, dies in **plasma**.
- **Acid** destroys both. Each robot collects its **matching key** and **coins**, then both reach their **exit door**.
- **15 levels** of increasing difficulty (flat runs, stepping stones, towers, pyramids, a buttons-&-gates switch room, an enemy-patrol stage, a crate-pushing puzzle, plus two finales that combine these mechanics), with a **level select**. Any death restarts the level (`R` to restart manually).
- **Buttons & gates:** stand on a button to hold its gate open for your partner — true co-op puzzles.
- **Enemies:** patrolling bots — stomp them from above for points, but side contact is fatal.
- **Movable crates:** push them into place (or onto a button) and climb on top to reach ledges.
- **Main menu** (Start / Resume / Restart) plus a **Menu** button to pause mid-run.
- **Procedural background music + sound effects** (zero audio files; toggle in the menu).
- **Skip warning:** choosing a level past 1 from the level-select asks you to confirm, since you forfeit the skipped levels' points.
- **Score** = coins + level-clear bonus + speed bonus − deaths. Best runs are saved to a **local leaderboard**.

Open `robot-game/index.html` in a browser to play. Level layouts are machine-verified
solvable (and all coins reachable) by `node robot-game/verify_levels.js`.

## Suggested Structure

```
YDL-2026/
└── robot-game/
    ├── index.html      # markup + canvas/DOM container
    ├── style.css        # layout and visuals
    └── game.js          # game logic
```

## Running

Open `robot-game/index.html` directly in a browser. No server or build step required.
