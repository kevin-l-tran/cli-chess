# Architecture

This document describes the current high-level architecture of the chess program. It reflects the current application-layer design: a lean, pull-based `GameSession` controller with explicit commands, immutable render snapshots, session timing, and draw-offer support.

## Overview

The program is structured as a layered system with clear boundaries between:

- **Engine** code for chess rules and game-state transitions
- **Application** code for session orchestration and UI-facing game state
- **Presentation** code for terminal rendering and user interaction
- **Adapters** for external engines, protocols, or remote services

The current design favors a compact, pull-based controller. The UI calls explicit application entrypoints to mutate session state, then pulls a fresh `Snapshot` with `session.snapshot()` for rendering.

The application layer is not a generic event bus. It exposes only stable session commands and read models that represent game-adjacent behavior.

## Layer responsibilities

### `engine/` - Engine layer

**Purpose:** Implement chess rules and core game mechanics.

Owns:

- Board representation
- Legal move generation
- Move application and undo
- Check, checkmate, stalemate, repetition, and 50-move-rule draw detection
- Domain-level game state such as side to move, move history, castling rights, and outcome
- Draw-offer facts attached to committed moves
- Explicit draw acceptance when the latest committed move offered a draw

Constraints:

- Must not import from any outer layer
- Must not import from `application/`, `ui/`, or `adapter/`
- Should avoid UI logic, subprocess management, networking, and I/O

The engine is the source of truth for legal chess behavior. It decides whether moves are legal, applies moves, tracks the game outcome, and records whether a committed move included a draw offer.

The engine may expose small query helpers for engine-owned facts. For example, a helper such as `pending_draw_offer_side_is_white()` can report whether the latest committed move created a currently pending draw offer. That keeps the application layer from decoding engine evaluation internals directly.

### `application/` - Application layer

**Purpose:** Orchestrate a running chess session and expose a compact API to the UI.

Owns:

- A reference to the active engine `Game`
- Session lifecycle actions such as restart, undo, resign, draw acceptance, and move confirmation
- Session configuration and mode policy
- Cached legal moves for the current position
- Move-draft state and parsing results
- Last-move highlight state
- Promotion-selection flow
- Session timing and clock projection
- User-facing feedback such as action and error messages
- Application-level terminal state for outcomes such as resignation and timeout
- Construction of immutable render snapshots for the UI

Derives:

- The pending draw-offer side from the engine's latest committed move
- Draw-offer availability from session mode, terminal state, and pending offer state
- Capability flags such as `can_confirm_move`, `can_offer_draw`, `can_resign`, and undo availability

Does **not** own:

- Board orientation
- Keyboard focus cursor
- Hover state
- Screen-space coordinates
- Other purely presentation-level view controls

Those concerns belong to the UI layer.

Constraints:

- May import from `engine/`
- Must not import from `ui/` or `adapter/`
- May define ports that adapters implement later

## Current session shape

The application layer centers on `GameSession`, which exposes explicit methods such as:

- `set_move_text()`
- `clear_move_text()`
- `click_square()`
- `select_promotion_piece()`
- `confirm_move_draft()`
- `accept_draw_offer()`
- `undo()`
- `resign()`
- `restart_game()`
- `snapshot()`

This is intentionally not a generic intent bus. The session no longer relies on a broad `dispatch()` surface or a publication/subscription mechanism. Instead, the UI invokes explicit entrypoints and then requests the latest snapshot.

## `ui/` - Presentation layer

**Purpose:** Render state in the terminal and translate user interaction into application calls.

Owns:

- Terminal rendering of the board, side panels, prompts, clocks, and feedback
- Screen-to-square coordinate mapping
- Board orientation and flipped rendering
- Keyboard/controller focus state
- Hover state and other transient presentation details
- Promotion popup presentation and placement
- Presentation copy for draw-offer prompts

Constraints:

- May import from `application/`
- Must not import from `engine/` or `adapter/`

The UI is responsible for projecting logical application data onto the screen. For example, the application provides board glyphs and logical squares, while the UI decides whether to render the board from White's or Black's perspective.

When a draw offer is pending, the UI should render the offer from `snapshot.draw_offered_by`. In the current model, the receiving player can either call `session.accept_draw_offer()` or make a legal move to implicitly decline the offer.

## `adapter/` - External engine and protocol adapters

**Purpose:** Integrate external engines or protocols such as UCI, online play, or future service boundaries.

Owns:

- Subprocess management and I/O
- Protocol parsing and formatting
- Conversion between internal representations and external representations such as FEN or UCI moves
- Future remote-session message transport, if online multiplayer is implemented

Constraints:

- May import from `application/` port interfaces
- Must not import from `ui/` or `engine/`

## Dependency rules

Allowed dependencies:

```text
ui       -> application -> engine
adapter  -> application -> engine
```

The engine remains the innermost layer. The UI and adapters stay outside the application layer and communicate through its public API.

## Current application data model

### Session-owned state

`GameSession` owns only state that affects game-oriented behavior or stable UI-facing semantics:

- current move draft text
- current parse result for that draft
- cached legal moves for the current position
- last move source and destination for highlighting
- session timing state
- application-level terminal state for resignation and timeout
- latest user-facing feedback message

This state is mutable internally, but it is exposed to the UI through immutable result objects and snapshots.

`GameSession` does not store mutable pending draw-offer state. A pending draw offer is derived from the latest committed engine move. If the latest move offered a draw and the game is still active, `snapshot.draw_offered_by` identifies the offering side. If another move is committed, that new move replaces the latest move and the previous offer is implicitly declined.

### Engine-derived state

The application derives several facts from the engine:

- current side to move
- legal moves
- checked king square
- last committed move
- terminal engine outcome
- pending draw-offer side

The application may adapt engine-specific representations into application-facing types. For example, an engine helper can return whether the pending draw offer was made by White, while `GameSession` converts that into `PlayerSide` values such as `"white"` or `"black"`.

### Session policy

`SessionPolicy` contains pure helpers for availability and default choices. It does not mutate session state, call the engine, set feedback, or return command result statuses.

Policy inputs should be already-computed session facts, such as:

- opponent mode
- move count
- parse status
- current phase
- pending draw-offer side

Policy outputs are simple availability flags, such as:

- `can_confirm_move`
- `can_offer_draw`
- `can_undo_halfmove`
- `can_undo_fullmove`
- `can_resign`

In the current draw-offer model, `can_offer_draw` is false when:

- the session is terminal
- draw offers are unsupported for the current opponent mode
- a previous draw offer is still pending

Normal move confirmation is not blocked by a pending draw offer. A successful move by the receiving side implicitly declines the offer.

## Snapshot contract

`session.snapshot()` returns a `Snapshot` value containing logical render data such as:

- board glyphs
- side to move
- candidate move highlights
- last move highlights
- move list entries
- move draft status and canonical resolution
- move autocompletions
- promotion prompt anchor square
- pending draw-offer side
- check information
- game-over flag
- move-confirmation availability
- draw-offer availability
- undo availability
- resignation availability
- promotion-pending flag
- optional clock state
- terminal outcome banner
- latest feedback message

The snapshot does not include presentation-only state such as board orientation, cursor position, hover state, or focus state.

### Draw-offer snapshot semantics

`draw_offered_by: PlayerSide | None` represents a pending draw offer attached to the latest committed move.

- `None` means there is no pending draw offer.
- `"white"` means White offered a draw on the latest committed move.
- `"black"` means Black offered a draw on the latest committed move.

A concluded drawn game is represented separately by `snapshot.outcome`, with a draw terminal reason. Pending draw offers and concluded draws are intentionally distinct.

`can_offer_draw` indicates whether the active side can attach a draw offer to a confirmed move. It is not an accept/decline flag. The UI can derive accept availability from `draw_offered_by is not None` and the game not being over.

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
2. The snapshot exposes `promotion_prompt_position` when the remaining ambiguity is only the promotion piece choice.
3. The UI displays a promotion chooser anchored to that logical square.
4. The UI calls `session.select_promotion_piece(piece)`.
5. The application rewrites the draft to a canonical promoted move.
6. The UI pulls a fresh snapshot and re-renders.

### Move confirmation flow

1. The user confirms the current move draft.
2. The UI calls `session.confirm_move_draft()`.
3. The application synchronizes timing.
4. The application reparses the draft and validates that it resolves to a unique legal move.
5. The application asks the engine to apply the move.
6. The application refreshes timing, cached legal moves, last-move highlight data, terminal state, and feedback.
7. The UI pulls a new snapshot and renders the updated position.

### Draw-offer flow

Draw offers are attached to moves.

1. The user confirms a move with `session.confirm_move_draft(offer_draw=True)`.
2. The application checks `can_offer_draw`.
3. If draw offers are available, the application applies the move through the engine with `draw_offered=True`.
4. The engine records the draw offer on the committed move evaluation.
5. The next snapshot exposes `draw_offered_by` for the side that just moved.
6. The receiving side may call `session.accept_draw_offer()` to accept.
7. If the receiving side instead confirms a legal move, the previous draw offer is implicitly declined because the latest committed move no longer carries that offer.

There is no explicit `decline_draw_offer()` command in the current model. Decline is represented by continued play.

### Draw acceptance flow

1. The UI sees `snapshot.draw_offered_by is not None`.
2. The user chooses to accept the draw.
3. The UI calls `session.accept_draw_offer()`.
4. The application verifies that the session is active and a draw offer is pending.
5. The application asks the engine to accept the draw.
6. The engine concludes the game as a draw.
7. The application records terminal draw state, refreshes derived state, stores feedback, and returns a `DrawActionResult`.
8. The UI pulls a new snapshot and renders the terminal draw outcome.

### Undo / resign / restart flow

These actions follow the same command-then-snapshot pattern:

1. The UI calls an explicit session method such as `undo()`, `resign()`, or `restart_game()`.
2. The application updates engine state and refreshes derived session state.
3. The UI pulls a new snapshot and re-renders.

Undo derives draw-offer state from the restored latest move. Restart clears all move history. Resignation records an application-level terminal outcome.

## Timing model

Timed sessions are coordinated by the application layer.

The session owns:

- optional clock state
- time-control configuration
- timing synchronization around commands and snapshot reads
- timing undo frames for session undo
- timeout terminal state

The engine does not own clocks. The application freezes or advances clocks as part of session orchestration, then projects render-ready clock views into the snapshot.

## Design principles

### 1. Explicit entrypoints over generic intents

The controller design prefers small, explicit methods over a single generic dispatch surface. This keeps supported interactions visible and keeps the public API narrow.

### 2. Pull-based rendering

The application does not push updates to the UI. The UI is responsible for requesting a new snapshot after invoking a session method.

### 3. Logical state in application, presentation state in UI

The application exposes logical squares, highlights, prompts, capabilities, clocks, outcomes, and feedback. The UI decides how to display them, including board orientation, focus, cursor position, and coordinate projection.

### 4. Engine remains authoritative for chess rules

The application never invents legal chess behavior. It derives move legality, engine outcomes, check information, and draw-offer facts from the engine.

### 5. Application owns session workflow

The engine can expose domain facts and perform domain transitions, but the application decides how those facts are surfaced as stable UI-facing commands, results, capabilities, and snapshots.

## Practical consequences

This split has several practical consequences:

- The UI can flip the board without changing application state.
- The UI can manage cursor or focus movement without expanding the application API.
- The session snapshot stays stable because it contains logical state rather than view-local preferences.
- Click handling stays consistent across frontends because the application receives logical squares and owns move-draft semantics.
- Draw offers remain compact: pending offer state is derived from the latest engine move, while the UI receives only `draw_offered_by` and `can_offer_draw`.
- A concluded draw is not confused with a pending draw offer because terminal outcomes are represented separately from `draw_offered_by`.

## Future extension points

This structure leaves room for future growth without reintroducing unnecessary controller surface:

- engine-driven opponent turns via an adapter port
- save/load features at the application boundary
- richer annotations in move history
- richer draw-offer policy for bot play
- online draw-offer negotiation through an adapter-backed protocol
- additional frontends that reuse the same application session API

Online play may eventually require draw offers to become protocol messages rather than purely local latest-move state. That should be handled by an adapter or online-session specialization without moving UI behavior into the engine.

## Summary

The current architecture uses the application layer as a compact chess-session controller rather than a general event router. The engine owns chess rules and domain game state. The application owns session workflow, timing, feedback, capabilities, and immutable snapshots. The UI owns presentation-only concerns and renders by pulling snapshots after calling explicit session methods.
