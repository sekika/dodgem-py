---
layout: page
title: FAQ
---

What Python versions are supported?
- Python 3.10+ (uses match-case in set_level).

Do I need MongoDB?
- Not for basic play at CPU levels 1–3. For level 4 search and for building or exporting the evalmap, you need MongoDB and the pymongo package.

What is the position key format?
- A canonical JSON string with no spaces: "[[a...],[b...],turn]". Lists are sorted to ensure canonical form.

How are wins, losses, and draws encoded?
- value ≥ +100: forced win for First (Blue)
- value ≤ -100: forced win for Second (Red)
- value = 0: forced draw

Why does “opponent cannot move” result in a loss for me?
- Dodgem has the rule “when the opponent cannot move, you lose.”

Why does the GUI sometimes open MongoDB?
- If either player uses CPU level 4 or if verbose is very high, the engine opens MongoDB to support lookups and logging.

Where is the evalmap stored?
- A packaged default is included and referenced by EVALMAP. You can override with --evalmap-path or `~/.dodgem`.
