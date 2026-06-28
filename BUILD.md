# Rebuilding the Kebbet Zamen app (.exe)

The Windows app you double-click is a **packaged executable** built with
PyInstaller. The user interface (`ui.html`) and the order parser
(`extract.py`) are **bundled inside the `.exe`**.

> **This means: changing the source code or merging a pull request on GitHub
> does NOT update the `.exe` on your computer.** The `.exe` must be rebuilt
> and the old one replaced. Until you do that, the running app keeps using
> the old bundled code.

## How to rebuild (Windows)

You need a Windows PC with **Python 3** installed (from python.org, with
"Add Python to PATH" checked during install).

1. Get the latest code (this folder) onto the PC — `git pull`, or download
   the repository as a ZIP and extract it.
2. Double-click **`build.bat`** (or run it from a command prompt).
   It installs the dependencies and runs PyInstaller for you.
3. When it finishes, the new app is at **`dist\KebbetZamen.exe`**.
4. Close the currently running Kebbet Zamen app, then replace the `.exe`
   (or the file your shortcut points to) with the freshly built one.
5. Start the new app and re-send the order from the browser extension.

## Manual command (instead of build.bat)

```bat
pip install -r requirements.txt pyinstaller
pyinstaller KebbetZamen.spec
```

## What was fixed

Customer comments on Toters orders (lines that begin with the `message`
icon, e.g. `messageفرمة ناعمة`) are now picked up and printed as their own
note line under the item, kept verbatim with no translation. This requires
the rebuilt `.exe` to take effect.
