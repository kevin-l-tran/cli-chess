# Architecture (Updated)

This document describes the current high-level architecture of the project and reflects the recent simplifications in the application layer.

## Overview

The program is structured as a layered system with clear boundaries between:

- **Engine** code for chess rules and state transitions
- **Application** code for session orchestration and UI-facing game state
- **Presentation** code for terminal rendering and user interaction
- **Adapters** for external engines or protocols

The current design favors a **lean, pull-based session controller**. The UI calls explicit application entrypoints to mutate session state, then pulls a fresh snapshot with `snapshot()` for rendering.

## Layer responsibilities

### `engine/` — Engine layer

**Purpose:** Implement chess rules and mechanics.

Owns:

- Board representation
- Legal move generation
- Move application and undo
- Check, mate, and draw detection
- Domain-level game state such as side to move, move history, castling rights, and outcome

Constraints:

- Must not import from any outer layer
- Should avoid UI logic, subprocess management, and I/O

This layer is the source of truth for what moves are legal and what the current game state is.

---

### `application/` — Application layer

**Purpose:** Orchestrate a running chess session and expose a compact API to the UI.

Owns:

- A reference to the active engine `Game`
- Session lifecycle actions such as new game, restart, undo, resign, and move confirmation
- Cached legal moves for the current position
- Move-draft state and parsing results
- Last-move highlight state
- Promotion-selection flow
- User-facing feedback such as error messages and outcome banners
- Construction of immutable render snapshots for the UI

Does **not** own:

- Board orientation
- Keyboard focus cursor
- Hover state
- Other purely presentation-level view controls

Those concerns now belong to the UI layer.

Constraints:

- May import from `engine/`
- Must not import from `ui/` or `adapter/`
- May define ports that adapters implement later

### Current session shape

The application layer currently centers on `GameSession`, which exposes explicit methods such as:

- `set_move_text()`
- `clear_move_text()`
- `click_square()`
- `select_promotion_piece()`
- `confirm_move_draft()`
- `undo()`
- `resign()`
- `restart_game()`
- `snapshot()`

This is intentionally **not** a generic intent bus. The session no longer relies on a broad `dispatch()` surface or a publication/subscription mechanism. Instead, the UI invokes explicit entrypoints and then requests the latest snapshot.

---

### `ui/` — Presentation layer

**Purpose:** Render state in the terminal and translate user interaction into application calls.

Owns:

- Terminal rendering of the board, side panels, prompts, and feedback
- Screen-to-square coordinate mapping
- Board orientation and flipped rendering
- Keyboard/controller focus state
- Hover state and other transient presentation details
- Promotion popup presentation and placement

Constraints:

- May import from `application/`
- Must not import from `engine/` or `adapter/`

The UI is responsible for projecting logical application data onto the screen. For example, the application provides board glyphs and logical squares, while the UI decides whether to render the board from White's or Black's perspective.

---

### `adapter/` — External engine adapters

**Purpose:** Integrate external engines or protocols such as UCI.

Owns:

- Subprocess management and I/O
- Protocol parsing and formatting
- Conversion between internal engine data and external representations such as FEN or UCI moves

Constraints:

- May import from `application/` port interfaces
- Must not import from `ui/` or `engine/`

## Dependency rules

Allowed dependencies:

```text
ui       ─────▶ application ─────▶ engine
adapter  ─────▶ application ─────▶ engine
```

The engine remains the innermost layer. The UI and adapters stay outside the application layer and communicate through its public API.

## Current application data model

### Session-owned state

`GameSession` owns only state that affects game-oriented behavior or stable UI-facing semantics:

- current move draft text
- current parse result for that draft
- cached legal moves for the current position
- last move source and destination for highlighting
- user-facing error message
- outcome banner

This state is mutable internally, but it is exposed to the UI through immutable result objects and snapshots.

### Snapshot contract

`snapshot()` returns a `Snapshot` value containing logical render data such as:

- board glyphs
- side to move
- candidate move highlights
- last move highlights
- move list entries
- move draft status and canonical resolution
- move autocompletions
- promotion prompt anchor square
- check information
- outcome banner
- last error message

Notably, the snapshot no longer includes presentation-only state like board orientation or cursor position.

## Input and control flow

### Typed move flow

1. The user types text into the move input.
2. The UI calls `session.set_move_text(text)`.
3. The application reparses the text against the current legal move set.
4. The UI calls `session.snapshot()` and renders the updated draft state, highlights, and autocomplete information.

### Click-to-draft flow

1. The user clicks a displayed board square.
2. The UI converts that screen position into a logical `Square`.
3. The UI calls `session.click_square(square)`.
4. The application rewrites the move draft using the current parse result and legal moves.
5. The UI pulls a new snapshot and re-renders the draft, highlights, and promotion prompt if needed.

The application does not treat a click as a direct move by default. A click edits the current move draft.

### Promotion selection flow

1. The current draft narrows to a promotion family, such as `Pe7-e8=`.
2. The snapshot exposes a `promotion_prompt_position` when the remaining ambiguity is only the promotion piece choice.
3. The UI displays a promotion chooser anchored to that logical square.
4. The UI calls `session.select_promotion_piece(piece)`.
5. The application rewrites the draft to a canonical promoted move, and the UI then re-renders from a fresh snapshot.

### Move confirmation flow

1. The user confirms the current move draft.
2. The UI calls `session.confirm_move_draft()`.
3. The application reparses the draft, validates that it resolves to a unique legal move, and asks the engine to apply it.
4. The application refreshes cached legal moves, last-move highlight data, and feedback state.
5. The UI pulls a new snapshot and renders the updated position.

### Undo / resign / restart flow

These actions follow the same pattern:

1. The UI calls an explicit session method such as `undo()`, `resign()`, or `restart_game()`.
2. The application updates engine state and refreshes derived session state.
3. The UI pulls a new snapshot and re-renders.

## Design principles

### 1. Explicit entrypoints over generic intents

The current controller design prefers small, explicit methods over a single generic dispatch surface. This keeps the session API narrow and makes each supported interaction obvious.

### 2. Pull-based rendering

The application does not push updates to the UI. The UI is responsible for requesting a new snapshot after invoking a session method.

### 3. Logical state in application, projection state in UI

The application exposes logical squares, highlights, and prompts. The UI decides how to display them, including orientation and coordinate projection.

### 4. Engine remains authoritative

The application never invents legal chess behavior. It derives all move legality and game outcome information from the engine.

## Practical consequences of the new split

This updated architecture has a few important consequences:

- The UI can flip the board without changing application state.
- The UI can manage cursor or focus movement without expanding the application API.
- The session snapshot stays smaller and more stable because it contains logical state rather than view-local preferences.
- Click handling stays consistent across frontends because the application still receives logical squares and owns move-draft semantics.

## Future extension points

This structure leaves room for future growth without reintroducing unnecessary controller surface:

- engine-driven opponent turns via an adapter port
- save/load features at the application boundary
- clocks and time-control orchestration
- richer move feedback or annotations in snapshots
- additional frontends that reuse the same application session API

## Summary

The current architecture uses the application layer as a compact chess-session controller rather than a general event router. The application owns gameplay-adjacent session state and produces logical snapshots. The UI owns presentation-only concerns such as orientation and focus, and it renders by pulling snapshots after calling explicit session methods.
