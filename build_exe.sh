#!/usr/bin/env bash
set -euo pipefail

# Build a standalone executable for the stream manager GUI.
python3 -m PyInstaller \
  --noconsole \
  --onefile \
  --name stream_manager_gui_with_editing_and_threading \
  --hidden-import=requests \
  --hidden-import=vlc \
  --collect-submodules requests \
  --collect-submodules vlc \
  stream_manager_gui_with_editing_and_threading.py
