---
layout: page
title: Rules
---

## Board and pieces
- Square board of size n×n (n = 3, 4, 5).
- Two players:
  - First (Blue, internally index 0)
  - Second (Red, internally index 1)
- Initial positions:
  - First’s pieces on the leftmost column, excluding the top-left corner
  - Second’s pieces on the bottom row, excluding the bottom-left corner
  - Internally stored as indices 0..n^2-1 row-major

## Movement
- Blue moves first, then Red, alternating turns.
- Blue pieces move to the right as their forward direction; they may also move vertically (up or down) by one square.
- Red pieces move upward as their forward direction; they may also move horizontally (left or right) by one square.
- Pieces may move only to empty squares. No jumps, captures, or stacking.
- When a piece reaches its exit edge (Blue: rightmost column; Red: top row), it can be removed on a subsequent move.

## Termination
- Players must not block their opponent’s movement completely. Equivalently, if you have no legal move on your turn, you win.
- The player who removes all of their own pieces first wins.

## Repetition and draws
- If the same position appears three times, the game is a draw.
