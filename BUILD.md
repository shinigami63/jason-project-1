# Getting the Kebbet Zamen app

The Windows app is **built automatically by GitHub Actions**
(`.github/workflows/build.yml`) every time changes land on the `master`
branch. Each build publishes an installer, `KebzetZamenSetup.exe`, and the
plain app folder as a zip.

The app itself is a `KebzetZamen` folder: `KebzetZamen.exe` with an
`_internal` folder beside it holding `ui.html`, `extract.py` and the Arabic
font. The `.exe` on its own will not run.

> **Important:** merging a pull request does **not** update the app already on
> your computer. Each merge produces a **new** build, and the app has to
> install it — see below.

## Updating: from inside the app

Once the app is installed, updates don't involve this page at all.

**Settings → App Version → Check for Updates.** If a newer build has been
published, press **Download & Install**: the app fetches the installer from
GitHub, checks it against the SHA-256 GitHub published for that file,
installs it and starts itself again. Your files are untouched.

The app knows its own version because the build stamps one in
(`1.0.<build number>`, always increasing), and the release is named with the
same string.

## Installing the first time

Get the installer from the permanent release link:

**https://github.com/shinigami63/jason-project-1/releases/latest/download/KebzetZamenSetup.exe**

Run it. It installs to `%LOCALAPPDATA%\Programs\KebbetZamen`, makes a desktop
and Start-menu shortcut, and registers an uninstaller — **no administrator
prompt**, because it installs for your user only.

On its first start the app looks for files from an older install sitting next
to the old `.exe` and copies them into its data folder (see below). Your
dictionary, combos and order history carry over on their own — nothing to do.
The old copies are left where they are, as a fallback.

> The very first move to the installer has to be done by hand — an app built
> before this existed has no version and no update button. After that, the
> button handles it.

### Installing by hand instead

The plain folder is published too, for installing without a setup program:

**https://github.com/shinigami63/jason-project-1/releases/latest/download/KebzetZamen-Windows.zip**

Unzip it wherever you want the app to live, make a shortcut to
`KebzetZamen.exe` inside the folder, and to update, unzip a newer one over it.

## Where your files are kept

The shop's own files live **outside** the app folder, by default in:

```
C:\Users\<you>\AppData\Local\KebbetZamen\
├── dictionary.json
├── combos.json
├── preferences.json
├── settings.json
└── order_history.db
```

The app shows the folder it is using under **Settings → Your Files**. Because
nothing of yours is inside the program folder, updating or reinstalling the
app can't disturb it — replace the folder, delete it, move it to another
drive, it makes no difference.

**This is the folder to back up.** The app folder itself is disposable; it can
always be downloaded again.

### Putting it in OneDrive

Under **Settings → Your Files**, type the folder you want and press **Use
This Folder** — for example `C:\Users\User\OneDrive\KebbetZamen`. The app
copies what it currently has into that folder, starts using it immediately,
and keeps using it after a restart. **Back to Default Folder** undoes it.

Files already in the target folder are kept, never overwritten — so pointing
a second machine at an existing folder adopts what's there rather than
flattening it.

> **Run the app on one computer at a time when the folder is synced.** If two
> computers share it and both have the app open, OneDrive will produce
> conflict copies and the two order histories will diverge. The app opens
> `order_history.db` only for the moment of a write, so ordinary single-machine
> use is fine.

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
