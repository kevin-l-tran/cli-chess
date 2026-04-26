# Move Language Specification

This document defines the official move-entry language accepted by the application.

These strings are application-layer input forms. They are not the engine’s internal move encoding. The parser interprets them against the current legal move set and uses them for both:

- live draft and highlight updates while the user is typing
- final move resolution when the user submits the move

The move language is designed so that:

- draft input and submitted input use the same matching rules
- a draft is simply a partial form of an accepted complete move spelling
- notation that resembles standard algebraic notation keeps its normal meaning
- explicit long forms are also supported for clarity and click-to-input synchronization

A move is considered resolved only when the current input identifies exactly one legal move.

---

## 1. Core model

The parser does not use a separate fuzzy search language for draft input.

Instead:

- the application defines a set of accepted complete move strings for each legal move in the current position
- a draft is valid if it is either:
  - a complete accepted move string for at least one legal move, or
  - a prefix of at least one accepted complete move string for at least one legal move

This makes the move language prefix-closed over the accepted complete spellings.

Examples:

- `N` is valid if at least one legal move has an accepted spelling beginning with `N`
- `Nb1-` is valid if at least one legal move has an accepted spelling beginning with `Nb1-`
- `e` is valid if at least one legal pawn move has an accepted spelling beginning with `e`
- `e4` is valid if it is a complete accepted spelling or a valid prefix of one

The parser always evaluates input against the current legal move set.

### Empty input

The empty string is treated specially.

If the normalized input is empty:

- status is `empty`
- there are no matching moves
- there are no highlights
- no move resolves

The empty string does not act as a prefix of all legal moves.

---

## 2. Normalization and case rules

Before parsing:

- trim surrounding whitespace
- remove internal spaces

Examples of equivalent normalized input:

- `Nc3`
- `N c3`
- `Nb1-c3`
- `N b1 - c 3`
- `O-O`
- `o-o`
- `0-0`

The parser does not normalize case.

Rules:

- piece letters must be uppercase
- file letters must be lowercase
- ranks must be numeric

Accepted:

- `Nc3`
- `Nb1-c3`
- `e4`

Rejected:

- `nc3`
- `NB1-C3`
- `E4`

### Castling alias exception

Castling forms are a special token family and are exempt from the ordinary piece-letter case rule.

Accepted castling spellings are:

- `O-O`
- `O-O-O`

Additional accepted aliases are:

- `0-0`
- `0-0-0`
- `o-o`
- `o-o-o`

---

## 3. Tokens

### 3.1 Piece letters

Accepted piece letters:

- `K` = king
- `Q` = queen
- `R` = rook
- `B` = bishop
- `N` = knight
- `P` = pawn

Rules:

- piece letters must be uppercase
- in SAN-style notation, pawn moves omit `P`
- in explicit long notation, pawns must use `P`

### 3.2 Files and ranks

- files: `a` through `h`
- ranks: `1` through `8`

### 3.3 Dividers

Accepted dividers:

- `-`
- `x`

Rules:

- in SAN-style notation, `x` is used for captures and quiet moves have no divider
- in explicit long notation, `-` is used for non-captures
- in explicit long notation, `x` is used for captures
- in explicit long notation, the divider may be omitted when a destination is present

Examples:

- `Qxh5` is a valid SAN capture spelling
- `Qh5` is a valid SAN quiet spelling
- `Qd1xh5` is a valid explicit long capture spelling
- `Qd1-h5` is a valid explicit long quiet spelling
- `Qd1h5` is also accepted as an explicit long spelling

### 3.4 Promotion pieces

Accepted promotion pieces:

- `Q`
- `R`
- `B`
- `N`

Rejected:

- `K`
- `P`

---

## 4. Accepted complete move notations

The application accepts three groups of complete move spellings:

1. SAN
2. explicit long notation
3. castling aliases

These groups are all part of the same move-entry language.

---

## 5. SAN

The parser accepts one SAN spelling per legal move, derived from the current legal move set.

For piece moves, SAN uses the minimal required disambiguation:

- no disambiguation if the move is already unique
- file disambiguation if needed and sufficient
- rank disambiguation if needed and sufficient
- full source-square disambiguation if file and rank are both insufficient

The parser does not generate extra SAN-compatible overspecified spellings beyond the required SAN form.

### 5.1 Pawn quiet move

Format:

`<ToSquare>`

Examples:

- `e4`
- `c3`

Meaning:

- a pawn moves to the destination square

### 5.2 Pawn capture

Format:

`<FromFile>x<ToSquare>`

Examples:

- `exd5`
- `cxb6`

Meaning:

- a pawn from the given file captures on the destination square

### 5.3 Pawn promotion

Format:

- `<ToSquare>=<PromoPiece>`
- `<FromFile>x<ToSquare>=<PromoPiece>`

Examples:

- `e8=Q`
- `fxe8=N`

Meaning:

- a pawn move or capture that promotes to the requested piece

### 5.4 Piece quiet move

Format:

`<Piece><Disambiguator><ToSquare>`

Where `<Disambiguator>` may be empty, a file, a rank, or a full source square.

Examples:

- `Nc3`
- `Nbd2`
- `R1e2`
- `Nb1c3`

Meaning:

- a move by that piece type to the destination square, with the minimum required disambiguation

### 5.5 Piece capture

Format:

`<Piece><Disambiguator>x<ToSquare>`

Where `<Disambiguator>` may be empty, a file, a rank, or a full source square.

Examples:

- `Qxh5`
- `Raxd1`
- `N5xd7`
- `Qd1xh5`

Meaning:

- a capture by that piece type on the destination square, with the minimum required disambiguation

### 5.6 Castling

Accepted SAN castling forms:

- `O-O`
- `O-O-O`

Accepted aliases:

- `0-0`
- `0-0-0`
- `o-o`
- `o-o-o`

Meaning:

- castling according to standard chess notation

---

## 6. Explicit long notation

Explicit long notation is supported alongside SAN.

Its purpose is to provide:

- an exact source-to-destination spelling
- a stable click-to-input form
- a notation family that users can type without relying on SAN ambiguity rules

In explicit long notation:

- the piece letter is always present
- the source square is always present
- the destination square is always present
- pawns must use `P`
- the divider may be present or omitted

### 6.1 Explicit long move

Format:

- `<Piece><FromSquare>-<ToSquare>`
- `<Piece><FromSquare>x<ToSquare>`
- `<Piece><FromSquare><ToSquare>`

Examples:

- `Nb1-c3`
- `Nb1c3`
- `Pe2-e4`
- `Pe2e4`
- `Qd1-h5`
- `Qd1xh5`
- `Qd1h5`
- `Ke1-g1`

Meaning:

- exact piece, exact source, exact destination

Rules:

- `-` is used for non-captures when a divider is present
- `x` is used for captures when a divider is present
- dividerless forms are also accepted
- castling may also be represented as a king move

### 6.2 Explicit long promotion

Format:

- `<Piece><FromSquare>-<ToSquare>=<PromoPiece>`
- `<Piece><FromSquare>x<ToSquare>=<PromoPiece>`
- `<Piece><FromSquare><ToSquare>=<PromoPiece>`

Examples:

- `Pe7-e8=Q`
- `Pe7e8=Q`
- `Pa7-a8=N`
- `Pa7a8=R`

Meaning:

- exact source and destination with explicit promotion piece

Rules:

- only `Q`, `R`, `B`, and `N` are valid promotion targets
- pawns must use `P` in explicit long notation

---

## 7. Matching semantics

For a given normalized input:

1. generate the legal moves in the current position
2. generate the accepted complete spellings for each legal move
3. keep only those legal moves for which at least one accepted spelling begins with the input text

This resulting move set is the draft’s match set.

The parser exposes:

- `matching_moves`
- `source_to_target_highlights`
- `resolved_move`
- `canonical_text`
- `status`

Where:

- `matching_moves` = legal moves whose accepted spelling set has at least one spelling with the given prefix
- `source_to_target_highlights` = one `(source_square, target_square)` pair for each matching move

Unlike a source-only and target-only highlight model, this representation keeps the source/target pairing for each match.

---

## 8. Resolution outcomes

### 8.1 Empty input

The normalized text is empty.

Effect:

- status is `empty`
- no move resolves
- no matching moves
- no highlights

### 8.2 No legal match

The text does not identify any legal move.

Examples:

- `e5` in the initial position
- `Nc4` in the initial position
- `Nb1-c2`
- `Pe2e5`
- `Zc3`
- `i9`
- `N--c3`
- `=Q`

Effect:

- status is `no_match`
- no move resolves
- no matching moves

### 8.3 Ambiguous draft

The text identifies more than one legal move.

Examples:

- `N`
- `e`
- `Nb1-`
- `Pe2`
- `Nc3` in a position where two knights can legally move to `c3`

Effect:

- status is `ambiguous`
- expose all matching moves
- expose all matching source/target pairs
- do not submit

### 8.4 Resolved draft

The text identifies exactly one legal move.

Examples:

- `e4` in the initial position
- `Nc3` in the initial position
- `Nb1-c3`
- `Pe2e4`

Effect:

- status is `resolved`
- expose `resolved_move`
- expose `canonical_text`
- allow submission

---

## 9. Canonical text

If exactly one legal move resolves, the parser exposes `canonical_text`.

Every resolved move has exactly one canonical text, regardless of which accepted spelling resolved it.

For ordinary moves, the canonical form is explicit long notation:

`<Piece><FromSquare><Divider><ToSquare>`

Where:

- `-` is used for non-captures
- `x` is used for captures

Promotion canonical form:

`<Piece><FromSquare><Divider><ToSquare>=<PromoPiece>`

Examples:

- `Nb1-c3`
- `Pe2-e4`
- `Qd1xh5`
- `Pe7-e8=Q`

### Castling canonical text

Castling canonical text remains the castling token itself:

- kingside castling canonicalizes to `O-O`
- queenside castling canonicalizes to `O-O-O`

Examples:

- `O-O` canonicalizes to `O-O`
- `0-0` canonicalizes to `O-O`
- `o-o` canonicalizes to `O-O`

---

## 10. Click-to-input synchronization

Board clicks should produce explicit long notation drafts.

Examples:

- clicking the knight on `b1` autofills `Nb1-`
- clicking `c3` after that updates the draft to `Nb1-c3`

Typing and clicking both use the same move language and the same matching rules.

---

## 11. Examples from the initial position

### Input: `N`

Matches:

- `Nb1-a3`
- `Nb1-c3`
- `Ng1-f3`
- `Ng1-h3`

Accepted spellings beginning with `N` include:

- `Na3`, `Nc3`, `Nf3`, `Nh3`
- `Nb1-a3`, `Nb1-c3`, `Ng1-f3`, `Ng1-h3`
- `Nb1a3`, `Nb1c3`, `Ng1f3`, `Ng1h3`

### Input: `Nb1-`

Matches:

- `Nb1-a3`
- `Nb1-c3`

### Input: `Nc3`

Matches:

- `Nb1-c3`

Resolved move:

- `Nb1-c3`

### Input: `e`

Matches:

- `Pe2-e3`
- `Pe2-e4`

SAN spellings beginning with `e` include:

- `e3`
- `e4`

### Input: `Pe2`

Matches:

- `Pe2-e3`
- `Pe2-e4`

### Input: `O-`

Matches:

- `O-O`
- `O-O-O` if both castling moves are legal
- otherwise whichever legal castling move exists

### Input: `0-`

Matches:

- `0-0`
- `0-0-0` if both castling moves are legal
- otherwise whichever legal castling move exists

---

## 12. Summary of accepted complete forms

Accepted SAN examples:

- `e4`
- `c3`
- `exd5`
- `e8=Q`
- `fxe8=N`
- `Nc3`
- `Qh5`
- `Qxh5`
- `Nbd2`
- `R1e2`
- `Nb1c3`
- `Qd1xh5`
- `O-O`
- `O-O-O`

Accepted explicit long examples:

- `Nb1-c3`
- `Nb1c3`
- `Pe2-e4`
- `Pe2e4`
- `Qd1-h5`
- `Qd1xh5`
- `Qd1h5`
- `Ke1-g1`
- `Pe7-e8=Q`
- `Pe7e8=Q`

Accepted castling aliases:

- `0-0`
- `0-0-0`
- `o-o`
- `o-o-o`

Accepted incomplete draft examples:

- `N`
- `Nb`
- `Nb1-`
- `e`
- `ex`
- `O-`
- `0-`
- `Pe2`

Rejected examples:

- `nb1-c3`
- `NB1-C3`
- `e2e4`
- `a7a8=Q`
- `=Q`
- `N--c3`
- `Zc3`