---
layout: page
title: MongoDB
---

This program connects to the MongoDB server specified by the `mongo_server` setting in the [configuration](../configuration) and uses the "dodgem\_db" database. [Install MongoDB](https://www.mongodb.com/docs/manual/administration/install-community/), start `mongod`, and run this program. Once it is running, you can build the database and play Dodgem at level 4, a perfect opponent.

## Collections per board size n
- eval_n
  - Documents keyed by the position key string: _id = "[[a...],[b...],turn]"
  - Fields:
    - value: evaluation score
      - ≥ +100: the current side to move has a forced win (from that node perspective).
      - ≤ -100: the current side to move has a forced loss.
      - 0 means forced draw
    - depth: depth bucket (decreases with deeper seek)
    - remain: heuristic remain (pieces)
- depth_n
  - Index/bucket documents for candidate positions grouped by depth and remain.
  - Keys:
    - _id = "d{depth}r{remain}" with field key = [list of position keys] for small buckets
    - For large buckets (greater than 300,000 positions, due to MongoDB’s 16 MB document size limit):
      - A parent document with _id "d{depth}r{remain}" and { "large": 1 }
      - Sharded sub-documents per batch:
        _id: "d{depth}r{remain}i{index}"
        fields: { "dr": "d{depth}r{remain}", "index": index, "key": [...] }

## Building the database
- Use:
  ```bash
  dodgem -n 4 -c
  ```
- Steps inside create_database():
  1) Initialize the depth/remain buckets via create_depth_database()
  2) For remain = 1..max_remain:
     - For each depth bucket, compute evaluations with a shallow search (evaluate_simple)
     - Track undetermined positions and re-search them with progressively deeper limits
     - Store terminal wins/losses as ±eval_win (default 100) and forced draws as 0
     - Keep aggregate stats in special _id documents "r{remain}"

## Status and traversal
- Status summary with distribution by depth (and optionally remain or side):
  ```bash
  dodgem -n 4 -s -v 2
  dodgem -n 4 -s -v 3
  ```
- Interactive traversal from the initial position:
  ```bash
  dodgem -n 4 -t
  ```
  or from a specific key:
  ```bash
  dodgem -n 4 -t '[[0,4,8],[13,14,15],0]'
  ```

## Key fields and logic
- value
  - Positive values (≥100) represent forced wins for the turn; negative (≤-100) for opponent; 0 for forced draw.
- depth
  - The engine generates candidate positions starting from the maximum depth, as defined by calc_max_depth(), and proceeds downward.
- remain
  - remain represents the distance to exit for both sides. Since the remain value never increases during play, the engine evaluates positions starting from the smallest remain values and progressing to larger ones.

## Performance tips
- Run MongoDB on localhost with sufficient memory.
- Adjust verbose (-v) to monitor progress. High verbosity levels print additional aggregation info.
- Consider running per board size (n=3 first, then n=4).
- Building the database for n=5 requires months of processing time on a typical personal computer.
- The database contains 1,963 positions for n=3, 393,900 positions for n=4, and 164,308,067 positions for n=5.
- Creating databases for all board sizes (n=3, 4, 5) requires 14 GB of disk space.

## Download
The complete database dump is available as a [compressed archive](https://seki.jpn.org/dodgem/dodgem-mongodump.tar.gz) (2.8 GB). You can download and import it into your MongoDB instance with the following commands:
```
wget https://seki.jpn.org/dodgem/dodgem-mongodump.tar.gz
tar xfvz dodgem-mongodump.tar.gz
mongorestore --drop mongodump
```
