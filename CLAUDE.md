# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status

This repo (`YDL-2026`) is a data-lab project collection. As of now it contains **no
source code** — only `README.md` (task brief) and `.gitattributes`. The sections below
describe the conventions the first project must follow, taken from `README.md`. Update
this file once code exists.

## Current Task

Build a robotics-themed browser game in **vanilla HTML / CSS / JS** — no frameworks, no
build step, zero dependencies (CDN-only if truly unavoidable). See `README.md` for the
four candidate game concepts; concept #1 (Robot Command Sequencer) is the recommended
starting point.

## Conventions

- **One folder per project.** The game lives in its own subfolder (e.g. `robot-game/`),
  not at the repo root.
- **Standard per-project layout:** `index.html` (markup + canvas/DOM container),
  `style.css` (layout/visuals), `game.js` (logic).
- **Runnable by opening `index.html` directly in a browser** — there is intentionally no
  dev server, bundler, package manager, or test runner. Don't introduce one without a
  reason; it contradicts the project's zero-tooling constraint.
- Each game must tie to a genuine robotics concept (motion planning, control loops,
  kinematics, classification), not be a reskinned generic arcade mechanic.

## Running

Open the project's `index.html` in any modern browser. No build or server step.
