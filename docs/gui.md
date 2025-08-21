---
layout: page
title: GUI
---

## Launch
- `dodgem --gui`
- You can set the initial players with the -l and -g options. Use level 0 to select a human player.
- You can also specify -v, --mongo-server, and --evalmap-path.

## Features
- Board sizes: 3, 4, 5
- Player types: Human or Computer per side
- CPU levels: 1–4
- Visual grid with clickable pieces
- Status label indicating the current turn, win/draw status, and game result
- The board automatically resizes to fit the width of the window

## Basic operation
1. Choose board size, player types, and CPU levels.
2. Click Start Game.
3. For human turns:
   - Click your piece to select it.
   - Click a destination square to move.
   - To remove a piece (exiting), click the piece again when removal is available.
4. The status label updates after each move. The GUI will auto-advance computer turns.

## Notes
- If either side uses CPU level 4, or if the verbosity level is greater than 3, the GUI opens a MongoDB connection.
- The GUI uses the same core Dodgem engine and evalmap as the CLI.
