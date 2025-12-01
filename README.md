# ETS2 Radio Utility

This repository contains a GUI utility for managing Euro Truck Simulator 2 radio streams. Use the included build script to package the application into a standalone executable.

## Prerequisites
- Python 3.9 or newer installed on your build machine.
- `pip` upgraded to the latest version.
- Build dependencies installed in a virtual environment or the system interpreter:
  ```bash
  python3 -m pip install --upgrade pip
  python3 -m pip install pyinstaller requests
  ```
- On Windows, install the Microsoft Visual C++ Redistributable if prompted when running the built executable.

## Build the executable
Run the build script from the repository root:
```bash
./build_exe.sh
```
The script calls:
```bash
python3 -m PyInstaller --noconsole --onefile --name stream_manager_gui_with_editing_and_threading --hidden-import=requests --collect-submodules requests stream_manager_gui_with_editing_and_threading.py
```
Notes:
- `--hidden-import=requests` and `--collect-submodules requests` ensure that `requests` and its transitive modules are bundled into the executable.
- The resulting binary is written to `dist/stream_manager_gui_with_editing_and_threading` (with `.exe` on Windows).

## Running the executable
- Windows: double-click `stream_manager_gui_with_editing_and_threading.exe` or launch it from PowerShell/CMD without needing Python installed.
- macOS: run `./stream_manager_gui_with_editing_and_threading` from Terminal after removing the quarantine flag if necessary (`xattr -d com.apple.quarantine stream_manager_gui_with_editing_and_threading`).
- The GUI runs without a console window because the build uses `--noconsole`.

## Code signing and notarization
- **Windows:**
  1. Obtain a code-signing certificate (`.pfx`).
  2. Sign the executable after building:
     ```powershell
     signtool sign /fd SHA256 /f path\to\certificate.pfx /p "your-password" dist\stream_manager_gui_with_editing_and_threading.exe
     signtool verify /pa dist\stream_manager_gui_with_editing_and_threading.exe
     ```
- **macOS:**
  1. Sign with an Apple Developer ID certificate:
     ```bash
     codesign --deep --force --options runtime --sign "Developer ID Application: Your Name (TEAMID)" dist/stream_manager_gui_with_editing_and_threading
     ```
  2. Submit for notarization:
     ```bash
     xcrun notarytool submit dist/stream_manager_gui_with_editing_and_threading --apple-id your-apple-id --team-id TEAMID --password app-specific-password --wait
     xcrun stapler staple dist/stream_manager_gui_with_editing_and_threading
     ```

## Testing on a clean VM
1. Provision a fresh Windows or macOS virtual machine with no Python runtime installed.
2. Copy the built executable from `dist/` to the VM (e.g., via shared folder or `scp`).
3. On Windows, ensure the Microsoft Visual C++ Redistributable is present if the app reports missing runtime DLLs.
4. Launch the executable and verify that:
   - The GUI loads and can manage streams without installing additional dependencies.
   - Network operations succeed (confirm radio streams load), confirming bundled `requests` works.
5. Repeat after signing/notarizing to confirm OS trust dialogs show the expected signer information.
