# Dodgem

Dodgem is a Python package for playing and analyzing the board game **Dodgem**. It provides:

* A command-line interface to play games, build an offline MongoDB evaluation database by perfect analysis, and traverse the game tree
* Perfect-opponent play on 3×3, 4×4, and 5×5 boards using the MongoDB database with a simple Tkinter GUI
* A compact gzipped JSON file (a curated subset of the MongoDB database) that can be fully loaded into memory, eliminating the need for a large on-disk MongoDB instance
* A Python API for programmatic use
* An [online Dodgem page](https://sekika.github.io/dodgem/) that uses the JSON file

![Dodgem GUI](https://sekika.github.io/dodgem-py/dodgem.png "Dodgem GUI")

## Features
- [CPU levels](https://sekika.github.io/dodgem-py/level/): 1–3 (search + evalmap), 4 (MongoDB-backed, perfect play)
- Evalmap JSON.GZ bundled and refreshable from your MongoDB
- MongoDB-based computation and status reporting

## Requirements
- Python 3.10+
- pip
- MongoDB server (only required for database features and CPU level 4; not needed for levels 1–3)
- Tkinter for the GUI

## Installation
```bash
pip install dodgem-game
```

## Quickstart
- Help
```bash
dodgem -h
```

- Play 10 games on 4x4 at level 4 vs. 4 (requires MongoDB)
```bash
dodgem -n 4 -p -r 10 -l 4
```

- Play a game without MongoDB (levels 1–3) at lavel 2 vs. 3 by showing the process
```bash
dodgem -n 4 -p -l 2 -g 3 -r 1 -v 3
```

- GUI
```bash
dodgem --gui
```

## About the data
- The MongoDB evaluation database is computed offline by a nearly perfect analysis.
- The evalmap (JSON.GZ) is a curated subset of that MongoDB database, packaged for fast lookup without MongoDB.

The evalmap produced by this package is used by the online Dodgem page. The online version uses only the evalmap subset (no MongoDB), so it supports CPU levels 1–3. Level 4 (MongoDB-backed) is available in the local CLI/GUI.

## Database and Evalmap
- Create MongoDB evaluation DB (per board size):
```bash
dodgem -n 4 -c
```

- Export evalmap JSON.GZ from MongoDB (for all board sizes):
```bash
dodgem -e
```

- Show DB status:
```bash
dodgem -n 4 -s
```

## Minimal Python API example
```python
from dodgem import Dodgem

d = Dodgem(n=4)             # loads bundled evalmap by default
d.level = [3, 3]            # both sides level 3 (no MongoDB required)
d.play_games(repetition=5)  # play 5 games and print a summary
```

## Documentation
See https://sekika.github.io/dodgem-py/
- Installation, Quickstart, CLI, GUI
- Game rules, API reference, configuration
- Evalmap format, MongoDB database details
- CPU levels, FAQ
