# Engine Component Features

The engine component is responsible for the core chess rules and game-state mechanics. In the project architecture, the engine layer owns board representation, move generation, legality checks, applying and undoing moves, and other domain-level game state, while staying independent of UI and external adapters.

## What the current engine provides

### Game state management
- A `Game` object wraps the active `Board`, tracks whose turn it is, stores the move history, and records the final outcome once the game is over.

### Legal move generation and enforcement
- The engine exposes the current legal move set through `get_moves()`.
- `make_move()` rejects illegal moves and also prevents moves from being played after the game has already concluded. 

### Move application with undo support
- Moves are applied through board-level command pairs that support both apply and undo behavior.
- The engine keeps these commands in history so it can undo the last half-move or the last full move.

### Check, checkmate, and draw detection
- After each move, the engine evaluates whether the side to move is in check.
- It detects checkmate when the current player is in check and has no legal moves.
- It detects draws in three main ways in the current implementation:
  - stalemate
  - threefold repetition tracking
  - the 50-move rule via 100 stale half-moves
- It also supports draw offers and explicit draw acceptance.

### Structured error handling
- The engine defines domain-specific exceptions for illegal moves, attempts to move after game conclusion, and invalid draw acceptance.
