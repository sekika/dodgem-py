---
layout: page
title: CLI usage
---

## Command
```bash
dodgem [options]
```

## Options
- -c, --create
  Create the evaluation database in MongoDB for the selected board size (-n).
- -e, --evalmap
  Create the evalmap JSON.GZ from MongoDB and write it to --evalmap-path.
- -l, --level INT
  CPU level for the first player (1–4). Default 3.
- -g, --gote INT
  CPU level for the second player. 0 = use first player level; otherwise 1–4. Default 0.
- -n, --num INT
  Board size (3–5). Default 4.
- -p, --play
  Play games (requires -l and optionally -g and -r).
- -r, --rep INT
  Number of games to play in --play mode. Default 10.
- -s, --status
  Show MongoDB status summary for the selected board size.
- -t, --traverse [KEY]
  Interactively traverse the MongoDB tree from the given key. If omitted, starts at "ini".
- -v, --verbose INT
  Verbose level. Higher values print more info (0–5).
- --mongo-server URI
  MongoDB server URI. Overrides config.
- --evalmap-path PATH
  Path to evalmap JSON.GZ. Overrides config.
- --gui
  Launch the Tkinter GUI.

## Examples
- Play 50 games on a 5x5 board at L3 vs L2:
  ```bash
  dodgem -n 5 -p -r 50 -l 3 -g 2
  ```

- Show DB status with more detail:
  ```bash
  dodgem -n 4 -s -v 3
  ```

## Notes
- Level 4 uses [MongoDB lookups](../database) during search. Levels 1–3 use depth-limited search and evalmap.
- The default evalmap is bundled; you can regenerate it from your MongoDB via -e.
