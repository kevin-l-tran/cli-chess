# Architecture

This document describes the high-level architecture and intended responsibilities of each top-level package in this project.

## Overview

The program is structured as a layered system with boundaries between:

- **Engine** code (chess rules and move generation)
- **Application** code (orchestration and UI-facing state)
- **Presentation** code (UI)
- **Adapters** for external engines (e.g., Stockfish via UCI)

## Layer responsibilities

### `engine/` — Engine layer

**Purpose:** Implement chess rules and mechanics.

Owns:

- Board representation
- Move generation and legality
- Applying/undoing moves
- Evaluation helpers (if applicable)
- Domain-level application state (whose turn, castling rights, etc.)

Constraints:

- Must not import from any other layer
- Should avoid any I/O, subprocess management, or terminal concerns

This layer should be fully testable with normal unit tests (`engine/tests/`).

---

### `application/` — Application layer

**Purpose:** Orchestrate a running chess session and bridge between UI intents and engine operations.

Owns:

- A reference to the engine objects (e.g., `engine.game.Game`)
- Session lifecycle (new application, load/save, resign, draw offers, etc.)
- High-level policies (undo behavior, confirmation rules, input behavior)
- UI-adjacent state that is not part of chess rules (e.g., board orientation)
- Producing render-friendly snapshots/view-models for the UI

Constraints:

- May import from `engine/`
- Must not import from `ui/` or `adapter/`
- May define "ports" (interfaces) that `adapter/` implements

---

### `ui/` — Presentation layer

**Purpose:** Render state in the terminal and translate user interaction into application intents.

Owns:

- Terminal user interface implementation
- Event handlers for mouse/keyboard

Constraints:

- May import from `application/`
- Must not import from `engine/` or `adapter/`
- Should avoid handling user interactions, except to send them to the application layer

---

### `adapter/` — External engine adapters

**Purpose:** Integrate external chess engines or protocols (e.g., Stockfish UCI).

Owns:

- Subprocess management and I/O
- Protocol parsing and formatting (UCI)
- Converting between internal engine representations and external formats (FEN, UCI moves)

Constraints:

- May import from `application/` (port interfaces)
- Must not import from `ui/` or `engine/`

## Dependency rules

Allowed dependencies (outer → inner):

```
ui  ───────▶  application  ──────▶  engine
adapter ───▶  application  ──────▶  engine
```

## Data flow and control flow

### Typical UI input flow

1. User clicks a square or types in the move input.
2. UI translates that into an **intent** (e.g., `SquareClicked`, `MoveInputChanged`, `ConfirmMove`).
3. UI calls the session controller (application layer), e.g. `session.dispatch(intent)`.
4. Session:
    - updates UI state (cursor/selection/draft)
    - calls domain methods as required (generate moves, make move, undo)
    - updates caches (legal move set for current position)
    - produces a new snapshot (view-model)
5. UI renders the snapshot (board pieces, highlights, move list, status).

### Engine/bot move flow (if playing vs AI)

1. After player move, session determines it is the engine’s turn.
2. Session requests analysis via an engine port (e.g., `engine_port.search(position, limits)`).
3. Adapter runs the external engine and returns the result asynchronously.
4. Session validates the result is still applicable (position unchanged), then applies it via `engine`.
5. Session publishes a new snapshot for UI.
