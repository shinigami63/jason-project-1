# Getting the Kebbet Zamen app

The Windows app you double-click is **built automatically by GitHub Actions**
(`.github/workflows/build.yml`) every time changes land on the `master`
branch. The build produces a **`KebzetZamen` folder** containing
`KebzetZamen.exe` and an `_internal` folder next to it — `ui.html`,
`extract.py` and the Arabic font live inside `_internal`. The app needs that
folder; the `.exe` on its own will not run.

> **Important:** changing the source or merging a pull request does **not**
> update the app already on your computer. Each merge produces a **new**
> build — you have to download it and put it in place of the old one.

## Download the latest app

After the workflow finishes (a minute or two after a merge), get the newest
build from the permanent release link:

**https://github.com/shinigami63/jason-project-1/releases/latest/download/KebzetZamen-Windows.zip**

### First time

1. Unzip it wherever you want the app to live (e.g. `C:\KebzetZamen`).
2. Open the `KebzetZamen` folder, right-click `KebzetZamen.exe` →
   **Send to → Desktop (create shortcut)**.
3. Start it from that shortcut.

### Updating an existing installation

1. Close the Kebbet Zamen app if it is running.
2. Unzip the download **on top of** your existing `KebzetZamen` folder and
   choose **Replace the files in the destination**.
3. Start it again and re-send the order from the browser extension.

Extracting over the folder is the safe way to update: the zip contains only
`KebzetZamen.exe` and `_internal`, so your own files sitting in that folder —
`dictionary.json`, `combos.json`, `preferences.json`, `settings.json` and
`order_history.db` — are left untouched. **Do not delete the old folder and
unzip a fresh one**, or you lose your dictionary and your order history with
it. (If you do want to move the app somewhere else, copy those five files
into the new folder before deleting the old one.)

### Alternative: download from the Actions run

If you prefer, open the **Actions** tab, click the most recent **"Build
Windows EXE"** run, and download the **`KebzetZamen-Windows`** artifact at the
bottom of the page (a `.zip` of the same folder).

## "Virus detected" when downloading

The app is not signed with a code-signing certificate, so Windows and Chrome
have no way to tell who built it and sometimes flag it. It is a false
positive. Two things make it much less likely, and the build already does the
first:

- The app is built as a **folder** (`--onedir`), not a single self-extracting
  `.exe`. A onefile build unpacks a whole Python runtime into a temp folder on
  every launch, which looks like what malware does, and gets flagged far more
  often.
- Signing the `.exe` with a bought certificate would remove the warnings
  entirely. Not set up.

If a download is still blocked, check that the file is really the one your own
CI built: compare its SHA-256 (`Get-FileHash .\KebzetZamen-Windows.zip
-Algorithm SHA256` in PowerShell) against the digest shown on the release
asset, then allow it.

## What was fixed

Customer comments on Toters orders (lines that begin with the `message`
icon, e.g. `messageفرمة ناعمة`) are now picked up and printed as their own
note line under the item, kept verbatim with no translation. This only shows
up once you are running a freshly built app.
