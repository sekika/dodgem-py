---
layout: page
title: Installation
---

## Requirements
- Python 3.10+ (uses structural pattern matching)
- pip
- MongoDB server (only required for database features and CPU level 4; not needed for levels 1–3)
- Tkinter for the GUI

## Install
- This installs the package and its Python dependencies automatically
```bash
pip install dodgem-game
```

## Tkinter notes
- Tkinter is part of the Python standard library, but on some systems the Tcl/Tk runtime is provided by the OS and may need to be installed.
- Windows
  - The official python.org installer typically includes Tcl/Tk. If the GUI fails to start, reinstall Python ensuring Tcl/Tk is selected.
- macOS
  - The python.org installers usually include Tkinter and a working Tcl/Tk, so most users do not need extra steps.
  - **If using Homebrew Python**:
    - Install the Tcl/Tk runtime:  
      ```bash
      brew install tcl-tk
      ```
    - Install Python bindings for Tcl/Tk:  
      ```bash
      brew install python-tk
      ```
    - Ensure your Python can locate the Homebrew Tcl/Tk libraries (Homebrew often installs Tcl/Tk in `/opt/homebrew/opt/tcl-tk` and Python may need the correct `PATH` and `PKG_CONFIG_PATH`).
  - **If using pyenv**:
    - Install Tcl/Tk with Homebrew (as above).
    - Rebuild Python so that `_tkinter` is linked against the Homebrew Tcl/Tk:  
      ```bash
      env PATH="/opt/homebrew/opt/tcl-tk/bin:$PATH" \
          LDFLAGS="-L/opt/homebrew/opt/tcl-tk/lib" \
          CPPFLAGS="-I/opt/homebrew/opt/tcl-tk/include" \
          PKG_CONFIG_PATH="/opt/homebrew/opt/tcl-tk/lib/pkgconfig" \
          pyenv install <python-version>
      ```
  - **If not using Homebrew or pyenv**:
    - Use the python.org installer for macOS, which already includes Tkinter and a working Tcl/Tk.
- Linux
  - Debian/Ubuntu: `sudo apt-get install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - Arch Linux: `sudo pacman -S tk`
  - openSUSE: `sudo zypper install python3-tk`
- The GUI works without MongoDB at CPU levels 1–3. Level 4 uses MongoDB.

## MongoDB server (optional)
- Only required to create/use the evaluation database and for CPU level 4
- Not required for basic play at levels 1–3 or for using the bundled evalmap

## Next step
- See [Quickstart](../quickstart) for common CLI and GUI commands
