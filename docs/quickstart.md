---
layout: page
title: Quickstart
---

## Run the CLI

- General help  
  ```bash
  dodgem -h
  ````

- Play 10 games on 4x4 with CPU level 4 vs. 4 (requires MongoDB)

  ```bash
  dodgem -n 4 -p -r 10 -l 4
  ```

- Play a game without MongoDB (levels 1–3) at level 2 vs. 3 by showing the process

  ```bash
  dodgem -n 4 -p -l 2 -g 3 -r 1 -v 3
  ```

- Show MongoDB status for n=4

  ```bash
  dodgem -n 4 -s
  ```

- Build the MongoDB evaluation DB for 4x4

  ```bash
  dodgem -n 4 -c
  ```

## Launch the GUI

```bash
dodgem --gui
```
