# Move Language Specification

This document defines the official move language accepted by the application.

These strings are **application-layer input forms**. They are not the engine's internal move encoding. The parser interprets them against the **current legal move set** and uses them for both:

- live draft/highlight updates while the user is typing
- final move resolution when the user submits the move

The move language is designed so that:

- **draft input and submitted input use the same grammar**
- draft input is simply a **partial form** of accepted move notation
- notation that resembles **standard algebraic notation** keeps its standard meaning
- explicit long forms are also supported for clarity and click-to-input synchronization

A move is considered **resolved** only when the current input identifies exactly one legal move.

---

## 1. Core model

The parser does not treat draft input as a separate fuzzy filter language.

Instead:

- the application defines a set of **accepted complete move strings**
- a draft is valid if it is either:
    - a complete accepted move string, or
    - a prefix of at least one accepted complete move string for at least one legal move in the current position

This makes the language **prefix-closed** over accepted move notations.

Examples:

- `N` is valid if at least one legal move has an accepted notation beginning with `N`
- `Nb1-` is valid if at least one legal move has an accepted notation beginning with `Nb1-`
- `e` is valid if at least one legal pawn move has an accepted notation beginning with `e`
- `e4` is valid if it is a complete accepted notation or a valid prefix of one

The parser always evaluates input against the **current legal move set**.

---

## 2. Accepted complete move notations

The application accepts two families of complete move notations:

1. **Standard algebraic notation (SAN) + SAN-compatible extensions**
2. **Explicit long notation**

Both families are part of the same official move language.

---

## 3. Normalization and case rules

Before parsing:

- trim surrounding whitespace
- remove internal spaces

Accepted examples after normalization:

- `Nc3`
- `N c3`
- `Nb1-c3`
- `N b1 - c 3`
- `O-O`
- `o-o`
- `0-0`

Case rules:

- piece letters must be uppercase
- file letters must be lowercase
- ranks must be numeric
- the parser does **not** normalize case

Accepted:

- `Nc3`
- `Nb1-c3`
- `e4`

Rejected:

- `nc3`
- `NB1-C3`
- `E4`

### Castling alias exception

Castling forms are a special token family and are exempt from the ordinary piece-letter case rules.

Accepted castling spellings are:

- `O-O`
- `O-O-O`

Optional aliases:

- `0-0`
- `0-0-0`
- `o-o`
- `o-o-o`

---

## 4. Tokens

### 4.1 Piece letters

Accepted piece letters:

- `K` = king
- `Q` = queen
- `R` = rook
- `B` = bishop
- `N` = knight
- `P` = pawn

Rules:

- piece letters must be uppercase
- in SAN, pawn moves omit `P`
- in explicit long notation, pawns must use `P`

### 4.2 Files and ranks

- files: `a` through `h`
- ranks: `1` through `8`

### 4.3 Dividers

Accepted dividers:

- `-`
- `x`

Rules:

- in explicit long notation, the divider is optional when a destination is present
- `x` is part of the accepted spelling for captures
- `-` is part of the accepted spelling for non-captures
- a spelling that uses the wrong divider for the move kind is **not** an accepted move spelling

Examples:

- `Qd1xh5` is a valid capture spelling
- `Qd1-h5` is a valid non-capture spelling
- `Qd1xh5` is not a valid spelling for a non-capturing move
- `Qd1-h5` is not a valid spelling for a capturing move

### 4.4 Promotion pieces

Accepted promotion pieces:

- `Q`
- `R`
- `B`
- `N`

Rejected:

- `K`
- `P`

---

## 5. SAN Compatible Policy

The application accepts both strict SAN and SAN-compatible overspecified forms.

In particular:

- absence of a piece letter indicates a **pawn move**
- SAN disambiguation fields keep their standard meaning
- SAN capture, promotion, and castling forms are supported
- piece moves may include optional source disambiguation even when strict SAN would not require it
- pawn SAN-style forms do **not** include an explicit `P`
- pawn SAN-style forms do **not** include any source disambiguation without capture
- pawn SAN-style forms **only** include the file during capture

Therefore, all of the following may be accepted for the same legal move when applicable:

- `Nc3`
- `Nbc3`
- `N1c3`
- `Nb1c3`

This permissiveness applies to piece moves and piece captures only.

Examples that are **not** SAN-compatible pawn forms:

- `Pe2e4`
- `e2e4`
- `a7a8=Q`

Those forms are either explicit long notation (`Pe2e4`) or rejected (`e2e4`, `a7a8=Q`).

---

### 5.1 Pawn quiet move

Format:

`<ToSquare>`

Examples:

- `e4`
- `c3`

Meaning:

- a pawn moves to the destination square

---

### 5.2 Pawn capture

Format:

`<FromFile>x<ToSquare>`

Examples:

- `exd5`
- `cxb6`

Meaning:

- a pawn from the given file captures on the destination square

---

### 5.3 Pawn promotion

Format:

- `<ToSquare>=<PromoPiece>`
- `<FromFile>x<ToSquare>=<PromoPiece>`

Examples:

- `e8=Q`
- `fxe8=N`

Meaning:

- a pawn move or capture that promotes to the requested piece

---

### 5.4 Piece quiet move

Format:

`<Piece><ToSquare>`

Examples:

- `Nc3`
- `Qh5`
- `Bb5`

Meaning:

- a move by that piece type to the destination square

---

### 5.5 Piece capture

Format:

`<Piece>x<ToSquare>`

Examples:

- `Qxh5`
- `Bxe6`

Meaning:

- a capture by that piece type on the destination square

---

### 5.6 Piece disambiguation by file

Format:

- `<Piece><FromFile><ToSquare>`
- `<Piece><FromFile>x<ToSquare>`

Examples:

- `Nbd2`
- `Raxd1`

Meaning:

- the move is restricted to pieces of that type on the specified file

---

### 5.7 Piece disambiguation by rank

Format:

- `<Piece><FromRank><ToSquare>`
- `<Piece><FromRank>x<ToSquare>`

Examples:

- `R1e2`
- `N5xd7`

Meaning:

- the move is restricted to pieces of that type on the specified rank

---

### 5.8 Piece disambiguation by full source square

Format:

- `<Piece><FromSquare><ToSquare>`
- `<Piece><FromSquare>x<ToSquare>`

Examples:

- `Nb1c3`
- `Qd1xh5`

Meaning:

- the move is restricted to the exact source square

Notes:

- this is accepted as an extension-compatible SAN-style explicit form
- this form overlaps with explicit long notation and is accepted by design

---

### 5.9 Castling

Accepted complete forms:

- `O-O`
- `O-O-O`

Optional complete aliases:

- `0-0`
- `0-0-0`
- `o-o`
- `o-o-o`

Meaning:

- castling according to standard chess notation

Notes:

- if a castling move resolves, its canonical text is the corresponding explicit king move

---

## 6. Explicit long notation

Explicit long notation is supported alongside SAN-compatible notation.

Its purpose is to provide:

- a precise, stable application-facing move spelling
- an intuitive click-to-input form
- explicit source-to-destination notation for users who prefer it

In explicit long notation:

- the piece letter is always present
- pawns must use `P`
- the source is always explicit
- the destination is always explicit
- the divider is optional when a destination is present

Notes:

- some explicit long spellings, such as `Nb1c3` and `Qd1xh5`, also fit the SAN-compatible extension rules
- the move language is defined by accepted spellings, not by requiring each spelling to belong to exactly one notation family

---

### 6.1 Explicit long move

Format:

- `<Piece><FromSquare><Divider><ToSquare>`
- `<Piece><FromSquare><ToSquare>`

Examples:

- `Nb1-c3`
- `Nb1c3`
- `Pe2-e4`
- `Pe2e4`
- `Ke1-g1`
- `Qd1xh5`

Meaning:

- exact piece, exact source, exact destination

Notes:

- omission of the divider is allowed when the destination is present
- if a divider is used, `x` is allowed only and always when the move is a capture
- castling is represented as a king move

---

### 6.2 Explicit long promotion

Format:

- `<Piece><FromSquare><Divider><ToSquare>=<PromoPiece>`
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

## 7. Draft validity

An input string is a **valid draft** if and only if at least one of the following is true:

1. it is a complete accepted move notation for at least one legal move
2. it is a prefix of at least one accepted complete move notation for at least one legal move

Examples:

- `N` is a valid draft if at least one legal move begins with `N`
- `Nb` is a valid draft if at least one legal move has a valid accepted spelling beginning with `Nb`
- `e` is a valid draft if at least one legal pawn move has a valid SAN spelling beginning with `e`
- `Pe` is a valid draft if at least one legal pawn move has an explicit long spelling beginning with `Pe`
- `Nb1-` is a valid draft if at least one legal move has an explicit long spelling beginning with `Nb1-`

---

## 8. Matching semantics

For a given normalized input:

1. generate the set of legal moves in the current position
2. generate all accepted complete spellings for each legal move
3. keep only those legal moves for which at least one accepted spelling begins with the input text

This resulting move set is the draft's match set.

The parser should expose:

- `matching_moves`
- `source_highlights`
- `target_highlights`
- `resolved_move`
- `canonical_text`
- `status`

Where:

- `matching_moves` = legal moves whose accepted notation set has at least one spelling with the given prefix
- `source_highlights` = all distinct source squares among matching moves
- `target_highlights` = all distinct destination squares among matching moves

---

## 9. Resolution outcomes

### 9.1 No legal match

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

- no move resolves
- no matching moves

---

### 9.2 Ambiguous draft

The text identifies more than one legal move.

Examples:

- `N`
- `Nb`
- `e`
- `Nb1-`
- `Nc3` in a position where two knights can legally move to `c3`

Effect:

- highlight all matching source and destination squares
- do not submit

---

### 9.3 Unambiguous draft

The text identifies exactly one legal move.

Examples:

- `e4` in the initial position
- `Nc3` in the initial position
- `Nb1-c3`
- `Pe2e4`

Effect:

- expose `resolved_move`
- expose canonical text
- allow submission

---

## 10. Canonical text

If exactly one legal move resolves, the parser should expose `canonical_text`.

Every resolved move has exactly one canonical text, regardless of which accepted spelling resolved it.

The canonical application-facing form is explicit long notation:

`<Piece><FromSquare><Divider><ToSquare>`

Examples:

- `Nb1-c3`
- `Pe2-e4`
- `Ke1-g1`

Promotion canonical form:

`<Piece><FromSquare>-<ToSquare>=<PromoPiece>`

Examples:

- `Pe7-e8=Q`

Rules:

- canonical text is derived from the resolved legal move, not from the raw user spelling
- SAN input will canonicalize to explicit long notation
- castling will canonicalize to the corresponding king move

Examples:

- `e4` canonicalizes to `Pe2-e4`
- `Nc3` canonicalizes to `Nb1-c3` if that is the resolved move
- `O-O` canonicalizes to `Ke1-g1`
- `e8=Q` canonicalizes to `Pe7-e8=Q`

---

## 11. Highlight semantics

For every draft with matching legal moves:

- `source_highlights` = all distinct sources among `matching_moves`
- `target_highlights` = all distinct destinations among `matching_moves`

If the draft resolves uniquely:

- `resolved_move` is the unique move
- `canonical_text` is exposed
- the UI may emphasize the resolved source and destination specially

---

## 12. Click-to-input synchronization

Board clicks should produce explicit long notation drafts.

Examples:

- clicking the knight on `b1` autofills `Nb1-`
- clicking `c3` after that updates the draft to `Nb1-c3`

Typing and clicking both use the same move language and the same matching rules.

---

## 13. Examples from the initial position

### Input: `N`

Matches:

- `Nb1-a3`
- `Nb1-c3`
- `Ng1-f3`
- `Ng1-h3`

Accepted spellings beginning with `N` include SAN and explicit long forms such as:

- `Na3`, `Nc3`, `Nf3`, `Nh3`
- `Nb1-a3`, `Nb1-c3`, `Ng1-f3`, `Ng1-h3`

Highlights:

- sources: `b1`, `g1`
- targets: `a3`, `c3`, `f3`, `h3`

---

### Input: `Nb1-`

Matches:

- `Nb1-a3`
- `Nb1-c3`

Highlights:

- source: `b1`
- targets: `a3`, `c3`

---

### Input: `Nc3`

Matches:

- `Nb1-c3`

Highlights:

- source: `b1`
- target: `c3`

Resolved move:

- `Nb1-c3`

---

### Input: `e`

Matches:

- `Pe2-e3`
- `Pe2-e4`

SAN spellings beginning with `e` include:

- `e3`
- `e4`

Highlights:

- source: `e2`
- targets: `e3`, `e4`

---

### Input: `e4`

Matches:

- `Pe2-e4`

Resolved move:

- `Pe2-e4`

---

### Input: `Pe2`

Matches:

- `Pe2-e3`
- `Pe2-e4`

Highlights:

- source: `e2`
- targets: `e3`, `e4`

---

## 14. Out of scope

This document specifies move-entry strings only.

It does not specify notation or commands for:

- resignation
- draw offers or draw acceptance
- comments or annotations
- en passant annotations
- check/checkmate annotations
- PGN result tokens
- engine-internal move encoding

---

## 15. Summary of accepted complete forms

Accepted complete SAN examples:

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

Accepted complete explicit long examples:

- `Nb1-c3`
- `Nb1c3`
- `Pe2-e4`
- `Pe2e4`
- `Qd1-h5`
- `Qd1xh5`
- `Ke1-g1`
- `Pe7-e8=Q`
- `Pe7e8=Q`

Accepted incomplete draft examples:

- `N`
- `Nb`
- `Nb1-`
- `e`
- `ex`
- `O-`
- `Pe2`

Rejected examples:

- `nb1-c3`
- `NB1-C3`
- `e2e4`
- `a7a8=Q`
- `=Q`
- `N--c3`
- `Zc3`
