---
layout: page
title: CPU levels
---
This program has four CPU levels. On this page, we evaluate the playing strength of each level.

Level 4 uses a complete evaluation database (stored in [MongoDB](../database)) and therefore plays perfectly. However, because of its size, it is available only in the local CLI/GUI versions; the [online version](https://sekika.github.io/dodgem/) supports levels 1–3 only. Levels 1–3 use a subset of this database called the [evalmap](../evalmap); both reliance on the evalmap and search depth vary by level.

## Round-robin league

To assess strength, we ran a round-robin league among Dodgem CPU levels L1–L4. Results are shown below.

- Rows are the first player (First); columns are the second player (Second).
- Each cell is Wins–Losses–Draws from the first player’s perspective over 100 games.

### 3x3 board

| First \ Second | L1       | L2       | L3       | L4       |
|----------------|----------|----------|----------|----------|
| L1             | 59-41-0  | 17-83-0  | 40-60-0  | 39-61-0  |
| L2             | 87-13-0  | 78-19-3  | 85-15-0  | 78-22-0  |
| L3             | 100-0-0  | 100-0-0  | 100-0-0  | 100-0-0  |
| L4             | 100-0-0  | 100-0-0  | 100-0-0  | 100-0-0  |

- Both L3 and L4 won every match when playing first, demonstrating perfect play.

### 4x4 board

| First \ Second | L1       | L2        | L3        | L4        |
|----------------|----------|-----------|-----------|-----------|
| L1             | 77-23-0  | 49-47-4   | 2-48-50   | 0-29-71   |
| L2             | 91-7-2   | 63-28-9   | 3-34-63   | 0-14-86   |
| L3             | 100-0-0  | 100-0-0   | 0-0-100   | 0-0-100   |
| L4             | 92-0-8   | 86-0-14   | 0-0-100   | 0-0-100   |

- L4 did not lose a single match, demonstrating perfect play.
- L3 did not lose any matches when playing first, but lost a few when playing second, indicating that while its play is not perfect, it remains very difficult to beat.

### 5x5 board

Calculation in progress

## Code

The following code was used for the round-robin matches on this page.

```python
def main():
    import argparse
    description = "Round-robin league of dodgem"

    parser = argparse.ArgumentParser(
        description=description
    )
    parser.add_argument('-n', '--num', type=int,
                        default=4, help='board size (3-5)')
    parser.add_argument('-r', '--rep', type=int, default=100,
                        help='repetition (default: 100)')
    args = parser.parse_args()
    league(args.num, args.rep)


def league(num, rep):
    from dodgem import Dodgem
    print(f'A round-robin league on a {num}x{num} board, with {rep} games per paring.', flush=True)
    d = Dodgem(num)
    d.verbose = 0
    for sente in range(1, 5):
        for gote in range(1, 5):
            if sente != gote:
                d.refresh_evalmap = True
            else:
                d.refresh_evalmap = False
            d.level = [sente, gote]
            win, loss, draw = d.play_games(rep)
            print(f'L{sente}-L{gote}: {win}-{loss}-{draw}', flush=True)


if __name__ == "__main__":
    main()
```
