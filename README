## Project description

A terminal-based chess program planned as a layered system (engine, application, UI, adapters) that will support local play, external engine integration, and a secure online multiplayer mode implemented via a custom cryptographic server.

## Target feature set

### 1) Responsive terminal UI (TUI)

- Terminal UI that renders:
    - The chess board, pieces, highlights, and status panels.
    - A move input area that supports both mouse-driven selection and typed move input (e.g., `Nc3`), with immediate feedback.

### 2) External chess engine interfacing (e.g., Stockfish)

- An adapter layer intended to integrate external engines/protocols (such as UCI), including:
    - Subprocess management and I/O.
    - Protocol parsing/formatting.
    - Conversion between internal representations and standard formats (FEN, UCI moves).

### 3) Local multiplayer

- Two-player local play on the same client:
    - Alternating turns in a single session.
    - Shared board and move list, with the same move validation and UI flows as other modes.

### 4) Online multiplayer with secure lobbies

#### Lobby semantics

- Game lobby rules:
    - There are exactly two `players` per lobby.
    - Optionally, a lobby may have `spectators`.

- Messaging rules:
    - Arbitrary messaging is not planned to be supported. All `messages` are chess moves.
    - Players can only send and receive chess moves (e.g., `Nc3`, UCI like `e2e4`).
    - Spectators can only recieve, not send, chess moves.

- Discovery and invites:
    - Authenticated users can query who is online.
    - A player can invite another user to play.
    - Spectators may join `public lobbies` without invites; `private lobbies` restrict spectator access.

#### Cryptographic requirements (per lobby)

- Users register and authenticate to the central server using username/password, with server-tracked online/offline presence.
- When a lobby is formed, the server:
    - Generates a symmetric session key for that lobby.
    - Encrypts that symmetric key separately for each participant using the participant’s public key (server is assumed to know all public keys).
    - Distributes the encrypted session key to all lobby participants; if an invited player is offline, the requester is notified.

- During play:
    - Every move message is encrypted using the symmetric session key (confidentiality).
    - Every move message is digitally signed, and each user can choose between:
        - RSA signatures, or
        - DSA signatures (both must be supported).

- Session constraints:
    - Concurrent session support is not prioritized as of now.
    - Users can disconnect at any time; disconnecting updates their status to offline.
