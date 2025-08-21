---
layout: page
title: Configuration
---

The CLI loads optional settings from a JSON file at `~/.dodgem`. If absent, defaults are used.

## Default config keys
- mongo_server: "mongodb://localhost:27017/"
- evalmap_path: Path to the packaged evalmap JSON.GZ (EVALMAP)

## Example ~/.dodgem
```
{
  "mongo_server": "mongodb://localhost:27017/",
  "evalmap_path": "/absolute/path/to/dodgem_eval.json.gz"
}
```

## Notes
- The evalmap file is loaded at runtime; set evalmap_path if you keep it outside the package install.
- You can also override both settings via CLI flags.
