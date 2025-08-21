---
layout: page
title: API reference
---

## Package layout
- dodgem/__init__.py
  - from .dodgem import Dodgem, EVALMAP
- dodgem/main.py
  - CLI entrypoint main()
- dodgem/dodgem.py
  - Core engine and database/evalmap logic
- dodgem/gui.py
  - Tkinter GUI

## Key classes and functions

### Dodgem (dodgem.dodgem.Dodgem)
- Constructor: Dodgem(n=4, evalmap=EVALMAP)
  - n: board size (3–5)
  - evalmap: path to evalmap JSON.GZ; defaults to packaged file
  - Loads evalmap and initializes game state
- Public attributes (not exhaustive):
  - n, draw_repetition, max_depth, max_remain, eval_win, refresh_evalmap
  - mongo_server, db_name, verbose, chars
  - evalmap_path, eval_map
  - pieces, turn, level
- Key methods:
  - start()
    Reset to initial position and set the first side to move.
  - play_games(repetition)
    Run multiple games and summarize results. Uses internal play_game which loops until termination.
  - set_level()
    Configure search parameters for the side to move based on level settings (1–4).
  - play_comp()
    Compute and make a move for the current side using search, evalmap, and optionally MongoDB (level 4).
  - evaluate(pieces, turn, depth)
    Negamax-like depth-limited evaluation using evalmap as a memo cache and optional MongoDB lookups.
  - next_positions(pieces, turn), move_available(pieces, i, turn)
    Generate next legal positions and legal moves for a piece.
  - remain(pieces)
    Compute a heuristic measure of remaining “distance to exit” for both sides.
  - is_finished()
    Check end conditions and set winner/draw flags.
  - min_remain(pos)
    Filter a list of positions to those with minimum remain().
  - show_position(pos)
    Render the board to stdout using box characters (debug/verbose).
  - load_evalmap(), create_evalmap()
    Load or build evalmap JSON.GZ from MongoDB selection criteria.
  - open_mongodb()
    Connect to MongoDB and set up the collections.
  - create_database()
    Build the evaluation DB by iterating remain and depth, including bucket indexes in depth collections.
  - show_status()
    Print DB totals and distributions.
  - traverse(key, history)
    Interactive traversal of the game tree using MongoDB.
  - evaluate_simple(pieces, turn, depth, history)
    Simplified evaluator used when recomputing undetermined positions.

### CLI entrypoint (dodgem.main.main)
- Parses arguments, reads `~/.dodgem`, wires everything to Dodgem.
- Adds a `--gui` flag that starts the Tkinter GUI via dodgem.gui.launch_gui.

### GUI (dodgem.gui)
- launch_gui(mongo_server, evalmap_path, verbose)
- DodgemGUI class integrates the engine for interactive play.
